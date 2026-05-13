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


def _seed(h: dict):
    for name, email, doc in [
        ("João Silva", "joao@bpay.com", "11111111111"),
        ("Maria Silva", "maria@bpay.com", "22222222222"),
        ("Pedro Santos", "pedro@bpay.com", "33333333333"),
        ("Ana Oliveira", "ana@bpay.com", "44444444444"),
    ]:
        client.post(
            "/customers",
            json={
                "name": name,
                "email": email,
                "document": doc,
                "password": "pwd",
            },
            headers=h,
        )


def test_search_by_name_partial():
    h = _admin_header()
    _seed(h)
    r = client.get("/customers?search=silva", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2


def test_search_case_insensitive():
    h = _admin_header()
    _seed(h)
    r = client.get("/customers?search=SILVA", headers=h)
    assert r.json()["total"] == 2


def test_search_no_results():
    h = _admin_header()
    _seed(h)
    r = client.get("/customers?search=nonexistent", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []


def test_filter_by_email():
    h = _admin_header()
    _seed(h)
    r = client.get("/customers?email=joao@bpay.com", headers=h)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["email"] == "joao@bpay.com"


def test_search_with_pagination():
    h = _admin_header()
    _seed(h)
    r = client.get("/customers?search=silva&limit=1", headers=h)
    data = r.json()
    assert len(data["items"]) == 1
    assert data["total"] == 2


def test_empty_search_returns_all():
    h = _admin_header()
    _seed(h)
    r = client.get("/customers", headers=h)
    assert r.json()["total"] == 4


def test_total_reflects_filtered():
    h = _admin_header()
    _seed(h)
    r = client.get("/customers?search=pedro", headers=h)
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Pedro Santos"
