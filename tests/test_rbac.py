from fastapi.testclient import TestClient

from app.main import app
from app.store import _db
from app.user_store import _user_db

client = TestClient(app)


def setup_function():
    _db.clear()
    _user_db.clear()


def _register_and_login(role: str = "operator") -> dict:
    client.post(
        "/auth/register",
        json={
            "name": f"User {role}",
            "email": f"{role}@bpay.com",
            "password": "pwd",
            "role": role,
        },
    )
    r = client.post(
        "/auth/login",
        json={"email": f"{role}@bpay.com", "password": "pwd", "entity_type": "user"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_customer_as_admin() -> str:
    h = _register_and_login("admin")
    r = client.post(
        "/customers",
        json={
            "name": "Test Customer",
            "email": "customer@bpay.com",
            "document": "12345678900",
            "phone": "+5511912345678",
            "password": "cust-pwd",
        },
        headers=h,
    )
    return r.json()["id"]


def _login_customer() -> dict:
    r = client.post(
        "/auth/login",
        json={
            "email": "customer@bpay.com",
            "password": "cust-pwd",
            "entity_type": "customer",
        },
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── Register with role ────────────────────────────────────────────────


def test_register_default_role_operator():
    r = client.post(
        "/auth/register",
        json={"name": "Default", "email": "default@bpay.com", "password": "pwd"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "operator"


def test_register_with_admin_role():
    r = client.post(
        "/auth/register",
        json={
            "name": "Admin",
            "email": "admin@bpay.com",
            "password": "pwd",
            "role": "admin",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "admin"


# ── Operator permissions ──────────────────────────────────────────────


def test_operator_can_list_customers():
    _create_customer_as_admin()
    h = _register_and_login("operator")
    r = client.get("/customers", headers=h)
    assert r.status_code == 200


def test_operator_can_get_customer():
    cid = _create_customer_as_admin()
    h = _register_and_login("operator")
    r = client.get(f"/customers/{cid}", headers=h)
    assert r.status_code == 200


def test_operator_cannot_create_customer():
    h = _register_and_login("operator")
    r = client.post(
        "/customers",
        json={
            "name": "Blocked",
            "email": "blocked@bpay.com",
            "document": "99988877766",
            "phone": "+5511999887766",
            "password": "pwd",
        },
        headers=h,
    )
    assert r.status_code == 403


def test_operator_cannot_update_customer():
    cid = _create_customer_as_admin()
    h = _register_and_login("operator")
    r = client.patch(f"/customers/{cid}", json={"name": "New"}, headers=h)
    assert r.status_code == 403


def test_operator_cannot_delete_customer():
    cid = _create_customer_as_admin()
    h = _register_and_login("operator")
    r = client.delete(f"/customers/{cid}", headers=h)
    assert r.status_code == 403


# ── Admin permissions ─────────────────────────────────────────────────


def test_admin_can_create_customer():
    h = _register_and_login("admin")
    r = client.post(
        "/customers",
        json={
            "name": "New Customer",
            "email": "new@bpay.com",
            "document": "11122233344",
            "phone": "+5511911122233",
            "password": "pwd",
        },
        headers=h,
    )
    assert r.status_code == 201


def test_admin_can_update_customer():
    cid = _create_customer_as_admin()
    h = _register_and_login("admin")
    r = client.patch(f"/customers/{cid}", json={"name": "Updated"}, headers=h)
    assert r.status_code == 200


def test_admin_can_delete_customer():
    cid = _create_customer_as_admin()
    h = _register_and_login("admin")
    r = client.delete(f"/customers/{cid}", headers=h)
    assert r.status_code == 204


def test_admin_can_list_customers():
    h = _register_and_login("admin")
    r = client.get("/customers", headers=h)
    assert r.status_code == 200


# ── Customer permissions ──────────────────────────────────────────────


def test_customer_can_access_me():
    _create_customer_as_admin()
    h = _login_customer()
    r = client.get("/customers/me", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "customer@bpay.com"


def test_customer_cannot_list_customers():
    _create_customer_as_admin()
    h = _login_customer()
    r = client.get("/customers", headers=h)
    assert r.status_code == 403


def test_customer_cannot_create_customer():
    _create_customer_as_admin()
    h = _login_customer()
    r = client.post(
        "/customers",
        json={
            "name": "X",
            "email": "x@bpay.com",
            "document": "99988877700",
            "phone": "+5511999887700",
            "password": "pwd",
        },
        headers=h,
    )
    assert r.status_code == 403


def test_customer_cannot_get_other_customer():
    cid = _create_customer_as_admin()
    h = _login_customer()
    r = client.get(f"/customers/{cid}", headers=h)
    assert r.status_code == 403


def test_customer_cannot_delete_customer():
    cid = _create_customer_as_admin()
    h = _login_customer()
    r = client.delete(f"/customers/{cid}", headers=h)
    assert r.status_code == 403


# ── /customers/me for non-customer ────────────────────────────────────


def test_user_cannot_access_customers_me():
    h = _register_and_login("admin")
    r = client.get("/customers/me", headers=h)
    assert r.status_code == 403
