from fastapi.testclient import TestClient

from app.main import app
from app.store import _db
from app.user_store import _user_db

client = TestClient(app)


def _get_auth_header() -> dict:
    client.post(
        "/auth/register",
        json={"name": "Test Admin", "email": "test-admin@bpay.com", "password": "pwd"},
    )
    r = client.post(
        "/auth/login",
        json={
            "email": "test-admin@bpay.com",
            "password": "pwd",
            "entity_type": "user",
        },
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def setup_function():
    _db.clear()
    _user_db.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_customer():
    h = _get_auth_header()
    r = client.post("/customers", json={
        "name": "João Silva",
        "email": "joao@bpay.com",
        "document": "12345678900",
        "password": "cust-pwd",
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "João Silva"
    assert "id" in data
    assert "hashed_password" not in data


def test_list_customers():
    h = _get_auth_header()
    client.post("/customers", json={
        "name": "Maria",
        "email": "maria@bpay.com",
        "document": "98765432100",
        "password": "pwd",
    }, headers=h)
    r = client.get("/customers", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["offset"] == 0
    assert data["limit"] == 20


def test_get_customer():
    h = _get_auth_header()
    create = client.post("/customers", json={
        "name": "Pedro",
        "email": "pedro@bpay.com",
        "document": "11122233344",
        "password": "pwd",
    }, headers=h)
    cid = create.json()["id"]
    r = client.get(f"/customers/{cid}", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Pedro"


def test_get_customer_not_found():
    h = _get_auth_header()
    r = client.get("/customers/nonexistent", headers=h)
    assert r.status_code == 404


def test_update_customer():
    h = _get_auth_header()
    create = client.post("/customers", json={
        "name": "Ana",
        "email": "ana@bpay.com",
        "document": "55566677788",
        "password": "pwd",
    }, headers=h)
    cid = create.json()["id"]
    r = client.patch(f"/customers/{cid}", json={"name": "Ana Paula"}, headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Ana Paula"
    assert r.json()["email"] == "ana@bpay.com"


def test_delete_customer():
    h = _get_auth_header()
    create = client.post("/customers", json={
        "name": "Carlos",
        "email": "carlos@bpay.com",
        "document": "99988877766",
        "password": "pwd",
    }, headers=h)
    cid = create.json()["id"]
    r = client.delete(f"/customers/{cid}", headers=h)
    assert r.status_code == 204
    r = client.get(f"/customers/{cid}", headers=h)
    assert r.status_code == 404


def test_invalid_document_too_short():
    h = _get_auth_header()
    r = client.post("/customers", json={
        "name": "Test",
        "email": "test@bpay.com",
        "document": "123",
        "password": "pwd",
    }, headers=h)
    assert r.status_code == 422


def test_invalid_document_letters():
    h = _get_auth_header()
    r = client.post("/customers", json={
        "name": "Test",
        "email": "test@bpay.com",
        "document": "1234567890a",
        "password": "pwd",
    }, headers=h)
    assert r.status_code == 422


def test_valid_cpf():
    h = _get_auth_header()
    r = client.post("/customers", json={
        "name": "CPF User",
        "email": "cpf@bpay.com",
        "document": "12345678901",
        "password": "pwd",
    }, headers=h)
    assert r.status_code == 201


def test_valid_cnpj():
    h = _get_auth_header()
    r = client.post("/customers", json={
        "name": "CNPJ User",
        "email": "cnpj@bpay.com",
        "document": "12345678000195",
        "password": "pwd",
    }, headers=h)
    assert r.status_code == 201


def test_duplicate_document():
    h = _get_auth_header()
    client.post("/customers", json={
        "name": "Original",
        "email": "original@bpay.com",
        "document": "11111111111",
        "password": "pwd",
    }, headers=h)
    r = client.post("/customers", json={
        "name": "Duplicate",
        "email": "dup@bpay.com",
        "document": "11111111111",
        "password": "pwd",
    }, headers=h)
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_get_customer_by_document():
    h = _get_auth_header()
    client.post("/customers", json={
        "name": "Busca Doc",
        "email": "busca@bpay.com",
        "document": "22233344455",
        "password": "pwd",
    }, headers=h)
    r = client.get("/customers/by-document/22233344455", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Busca Doc"
    assert r.json()["document"] == "22233344455"


def test_get_customer_by_document_not_found():
    h = _get_auth_header()
    r = client.get("/customers/by-document/99999999999", headers=h)
    assert r.status_code == 404


def test_get_customer_by_document_invalid():
    h = _get_auth_header()
    r = client.get("/customers/by-document/123", headers=h)
    assert r.status_code == 422


def _seed_customers(n: int, headers: dict):
    for i in range(n):
        client.post("/customers", json={
            "name": f"Customer {i}",
            "email": f"c{i}@bpay.com",
            "document": f"{10000000000 + i}",
            "password": "pwd",
        }, headers=headers)


def test_list_customers_default_pagination():
    h = _get_auth_header()
    _seed_customers(25, h)
    r = client.get("/customers", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 20
    assert data["total"] == 25
    assert data["offset"] == 0
    assert data["limit"] == 20


def test_list_customers_custom_limit():
    h = _get_auth_header()
    _seed_customers(10, h)
    r = client.get("/customers?limit=5", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 5
    assert data["total"] == 10


def test_list_customers_offset():
    h = _get_auth_header()
    _seed_customers(5, h)
    r = client.get("/customers?offset=2&limit=2", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["offset"] == 2


def test_list_customers_total_count():
    h = _get_auth_header()
    _seed_customers(3, h)
    r = client.get("/customers?limit=1", headers=h)
    data = r.json()
    assert len(data["items"]) == 1
    assert data["total"] == 3


def test_list_customers_invalid_limit_zero():
    h = _get_auth_header()
    r = client.get("/customers?limit=0", headers=h)
    assert r.status_code == 422


def test_list_customers_invalid_limit_over_100():
    h = _get_auth_header()
    r = client.get("/customers?limit=101", headers=h)
    assert r.status_code == 422


def test_health_unchanged():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_details():
    r = client.get("/health/details")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0
    assert "timestamp" in data


def test_health_details_timestamp_format():
    from datetime import datetime

    r = client.get("/health/details")
    data = r.json()
    datetime.fromisoformat(data["timestamp"])
