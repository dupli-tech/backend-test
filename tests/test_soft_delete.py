from fastapi.testclient import TestClient

from app.main import app
from app.store import _db
from app.user_store import _user_db

client = TestClient(app)


def setup_function():
    _db.clear()
    _user_db.clear()


def _admin_header() -> dict:
    client.post(
        "/auth/register",
        json={
            "name": "Admin",
            "email": "admin@bpay.com",
            "password": "pwd",
            "role": "admin",
        },
    )
    r = client.post(
        "/auth/login",
        json={
            "email": "admin@bpay.com",
            "password": "pwd",
            "entity_type": "user",
        },
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_customer(h: dict, doc: str = "12345678900") -> str:
    r = client.post(
        "/customers",
        json={
            "name": "Test",
            "email": f"test-{doc}@bpay.com",
            "document": doc,
            "password": "pwd",
        },
        headers=h,
    )
    return r.json()["id"]


def test_delete_soft_deletes():
    h = _admin_header()
    cid = _create_customer(h)
    r = client.delete(f"/customers/{cid}", headers=h)
    assert r.status_code == 204
    assert cid in _db
    assert not _db[cid].is_active


def test_deleted_not_in_listing():
    h = _admin_header()
    cid = _create_customer(h)
    client.delete(f"/customers/{cid}", headers=h)
    r = client.get("/customers", headers=h)
    assert r.json()["total"] == 0


def test_deleted_included_with_flag():
    h = _admin_header()
    cid = _create_customer(h)
    client.delete(f"/customers/{cid}", headers=h)
    r = client.get("/customers?include_inactive=true", headers=h)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["is_active"] is False


def test_get_deleted_returns_404():
    h = _admin_header()
    cid = _create_customer(h)
    client.delete(f"/customers/{cid}", headers=h)
    r = client.get(f"/customers/{cid}", headers=h)
    assert r.status_code == 404


def test_restore_soft_deleted():
    h = _admin_header()
    cid = _create_customer(h)
    client.delete(f"/customers/{cid}", headers=h)
    r = client.post(f"/customers/{cid}/restore", headers=h)
    assert r.status_code == 200
    assert r.json()["is_active"] is True


def test_restore_active_returns_409():
    h = _admin_header()
    cid = _create_customer(h)
    r = client.post(f"/customers/{cid}/restore", headers=h)
    assert r.status_code == 409


def test_restore_nonexistent_returns_404():
    h = _admin_header()
    r = client.post("/customers/nonexistent/restore", headers=h)
    assert r.status_code == 404


def test_customer_response_has_is_active():
    h = _admin_header()
    cid = _create_customer(h)
    r = client.get(f"/customers/{cid}", headers=h)
    assert r.json()["is_active"] is True
