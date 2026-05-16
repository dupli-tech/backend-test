from fastapi.testclient import TestClient

from app.main import app
from app.store import _db
from app.user_store import _user_db

client = TestClient(app)


def setup_function():
    _db.clear()
    _user_db.clear()


# ── Helpers ───────────────────────────────────────────────────────────


def _register_admin() -> dict:
    r = client.post(
        "/auth/register",
        json={
            "name": "Admin",
            "email": "admin@bpay.com",
            "password": "secret123",
            "role": "admin",
        },
    )
    return r.json()


def _login_admin() -> dict:
    r = client.post(
        "/auth/login",
        json={
            "email": "admin@bpay.com",
            "password": "secret123",
            "entity_type": "user",
        },
    )
    return r.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_customer(token: str, **overrides) -> dict:
    base = {
        "name": "João",
        "email": "joao@bpay.com",
        "document": "12345678900",
        "phone": "+5511999887766",
        "password": "cust-pass",
    }
    base.update(overrides)
    r = client.post("/customers", json=base, headers=_auth_header(token))
    return r


# ── Model & Registration ─────────────────────────────────────────────


def test_create_customer_with_valid_phone_201():
    _register_admin()
    tokens = _login_admin()
    r = _create_customer(tokens["access_token"])
    assert r.status_code == 201
    assert r.json()["phone"] == "+5511999887766"


def test_create_customer_invalid_phone_422():
    _register_admin()
    tokens = _login_admin()
    for invalid in ["11999887766", "+5511888776655", "abc", "+5511899887766", ""]:
        r = _create_customer(
            tokens["access_token"], phone=invalid, document="12345678900"
        )
        assert r.status_code == 422, (
            f"Expected 422 for phone={invalid!r}, got {r.status_code}"
        )


def test_create_customer_duplicate_phone_409():
    _register_admin()
    tokens = _login_admin()
    _create_customer(tokens["access_token"])
    r = _create_customer(
        tokens["access_token"],
        email="outro@bpay.com",
        document="98765432100",
        phone="+5511999887766",
    )
    assert r.status_code == 409
    assert "Phone" in r.json()["detail"]


def test_get_customer_includes_phone():
    _register_admin()
    tokens = _login_admin()
    r = _create_customer(tokens["access_token"])
    cid = r.json()["id"]
    r = client.get(f"/customers/{cid}", headers=_auth_header(tokens["access_token"]))
    assert r.status_code == 200
    assert r.json()["phone"] == "+5511999887766"


# ── Login by Phone ───────────────────────────────────────────────────


def test_login_by_phone_200():
    _register_admin()
    tokens = _login_admin()
    _create_customer(tokens["access_token"])
    r = client.post(
        "/auth/login",
        json={
            "phone": "+5511999887766",
            "password": "cust-pass",
            "entity_type": "customer",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_by_phone_nonexistent_401():
    r = client.post(
        "/auth/login",
        json={"phone": "+5521999000000", "password": "x", "entity_type": "customer"},
    )
    assert r.status_code == 401


def test_login_by_phone_wrong_password_401():
    _register_admin()
    tokens = _login_admin()
    _create_customer(tokens["access_token"])
    r = client.post(
        "/auth/login",
        json={
            "phone": "+5511999887766",
            "password": "wrong",
            "entity_type": "customer",
        },
    )
    assert r.status_code == 401


def test_login_by_email_still_works():
    _register_admin()
    tokens = _login_admin()
    _create_customer(tokens["access_token"])
    r = client.post(
        "/auth/login",
        json={
            "email": "joao@bpay.com",
            "password": "cust-pass",
            "entity_type": "customer",
        },
    )
    assert r.status_code == 200


def test_login_with_both_email_and_phone_422():
    r = client.post(
        "/auth/login",
        json={
            "email": "joao@bpay.com",
            "phone": "+5511999887766",
            "password": "x",
            "entity_type": "customer",
        },
    )
    assert r.status_code == 422


def test_login_without_email_or_phone_422():
    r = client.post(
        "/auth/login",
        json={"password": "x", "entity_type": "customer"},
    )
    assert r.status_code == 422


# ── GET /customers/by-phone ──────────────────────────────────────────


def test_get_by_phone_200():
    _register_admin()
    tokens = _login_admin()
    _create_customer(tokens["access_token"])
    r = client.get(
        "/customers/by-phone/+5511999887766",
        headers=_auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["phone"] == "+5511999887766"


def test_get_by_phone_not_found_404():
    _register_admin()
    tokens = _login_admin()
    r = client.get(
        "/customers/by-phone/+5521999000000",
        headers=_auth_header(tokens["access_token"]),
    )
    assert r.status_code == 404


def test_get_by_phone_invalid_format_422():
    _register_admin()
    tokens = _login_admin()
    r = client.get(
        "/customers/by-phone/11999887766",
        headers=_auth_header(tokens["access_token"]),
    )
    assert r.status_code == 422
