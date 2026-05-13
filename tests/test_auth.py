from fastapi.testclient import TestClient
from jose import jwt

from app.auth import ALGORITHM, JWT_SECRET
from app.main import app
from app.store import _db
from app.user_store import _user_db

client = TestClient(app)


def setup_function():
    _db.clear()
    _user_db.clear()


# ── Helpers ───────────────────────────────────────────────────────────


def _register_user(
    name: str = "Admin",
    email: str = "admin@bpay.com",
    password: str = "secret123",
) -> dict:
    r = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    return r.json()


def _login_user(
    email: str = "admin@bpay.com", password: str = "secret123"
) -> dict:
    r = client.post(
        "/auth/login",
        json={"email": email, "password": password, "entity_type": "user"},
    )
    return r.json()


def _create_customer_payload(**overrides) -> dict:
    base = {
        "name": "João",
        "email": "joao@bpay.com",
        "document": "12345678900",
        "password": "cust-pass",
    }
    base.update(overrides)
    return base


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── User Registration ────────────────────────────────────────────────


def test_register_user_201():
    r = client.post(
        "/auth/register",
        json={"name": "Admin", "email": "admin@bpay.com", "password": "s3cret"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Admin"
    assert data["email"] == "admin@bpay.com"
    assert data["role"] == "operator"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email_409():
    _register_user()
    r = client.post(
        "/auth/register",
        json={"name": "Other", "email": "admin@bpay.com", "password": "other"},
    )
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_password_is_hashed():
    _register_user(password="plaintext123")
    user = list(_user_db.values())[0]
    assert user.hashed_password != "plaintext123"
    assert user.hashed_password.startswith("$2b$")


# ── User Login ────────────────────────────────────────────────────────


def test_login_user_returns_tokens():
    _register_user()
    r = client.post(
        "/auth/login",
        json={
            "email": "admin@bpay.com",
            "password": "secret123",
            "entity_type": "user",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_401():
    _register_user()
    r = client.post(
        "/auth/login",
        json={
            "email": "admin@bpay.com",
            "password": "wrong",
            "entity_type": "user",
        },
    )
    assert r.status_code == 401


def test_login_nonexistent_email_401():
    r = client.post(
        "/auth/login",
        json={
            "email": "nobody@bpay.com",
            "password": "x",
            "entity_type": "user",
        },
    )
    assert r.status_code == 401


# ── Customer Login ────────────────────────────────────────────────────


def test_login_customer_returns_tokens():
    _register_user()
    tokens = _login_user()
    client.post(
        "/customers",
        json=_create_customer_payload(),
        headers=_auth_header(tokens["access_token"]),
    )
    r = client.post(
        "/auth/login",
        json={
            "email": "joao@bpay.com",
            "password": "cust-pass",
            "entity_type": "customer",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_customer_wrong_password_401():
    _register_user()
    tokens = _login_user()
    client.post(
        "/customers",
        json=_create_customer_payload(),
        headers=_auth_header(tokens["access_token"]),
    )
    r = client.post(
        "/auth/login",
        json={
            "email": "joao@bpay.com",
            "password": "wrong",
            "entity_type": "customer",
        },
    )
    assert r.status_code == 401


# ── Token Claims ──────────────────────────────────────────────────────


def test_token_contains_expected_claims():
    _register_user()
    tokens = _login_user()
    payload = jwt.decode(
        tokens["access_token"], JWT_SECRET, algorithms=[ALGORITHM]
    )
    assert "sub" in payload
    assert payload["entity_type"] == "user"
    assert "exp" in payload
    assert "iat" in payload


# ── Refresh Token ─────────────────────────────────────────────────────


def test_refresh_returns_new_tokens():
    _register_user()
    tokens = _login_user()
    r = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_with_invalid_token_401():
    r = client.post("/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


def test_refresh_with_access_token_401():
    _register_user()
    tokens = _login_user()
    r = client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert r.status_code == 401


# ── GET /auth/me ──────────────────────────────────────────────────────


def test_me_user():
    _register_user()
    tokens = _login_user()
    r = client.get("/auth/me", headers=_auth_header(tokens["access_token"]))
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "admin@bpay.com"
    assert data["role"] == "operator"
    assert "hashed_password" not in data


def test_me_customer():
    _register_user()
    tokens = _login_user()
    client.post(
        "/customers",
        json=_create_customer_payload(),
        headers=_auth_header(tokens["access_token"]),
    )
    cust_tokens = client.post(
        "/auth/login",
        json={
            "email": "joao@bpay.com",
            "password": "cust-pass",
            "entity_type": "customer",
        },
    ).json()
    r = client.get(
        "/auth/me", headers=_auth_header(cust_tokens["access_token"])
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "joao@bpay.com"
    assert data["document"] == "12345678900"
    assert "hashed_password" not in data


# ── Protected Endpoints ──────────────────────────────────────────────


def test_customers_without_token_401():
    r = client.get("/customers")
    assert r.status_code == 401


def test_create_customer_without_token_401():
    r = client.post("/customers", json=_create_customer_payload())
    assert r.status_code == 401


def test_health_remains_public():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_details_remains_public():
    r = client.get("/health/details")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
