from fastapi.testclient import TestClient

from app.main import app
from app.store import _db

client = TestClient(app)


def setup_function():
    _db.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_customer():
    r = client.post("/customers", json={
        "name": "João Silva",
        "email": "joao@bpay.com",
        "document": "12345678900",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "João Silva"
    assert "id" in data


def test_list_customers():
    client.post("/customers", json={
        "name": "Maria",
        "email": "maria@bpay.com",
        "document": "98765432100",
    })
    r = client.get("/customers")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_customer():
    create = client.post("/customers", json={
        "name": "Pedro",
        "email": "pedro@bpay.com",
        "document": "11122233344",
    })
    cid = create.json()["id"]
    r = client.get(f"/customers/{cid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Pedro"


def test_get_customer_not_found():
    r = client.get("/customers/nonexistent")
    assert r.status_code == 404


def test_update_customer():
    create = client.post("/customers", json={
        "name": "Ana",
        "email": "ana@bpay.com",
        "document": "55566677788",
    })
    cid = create.json()["id"]
    r = client.patch(f"/customers/{cid}", json={"name": "Ana Paula"})
    assert r.status_code == 200
    assert r.json()["name"] == "Ana Paula"
    assert r.json()["email"] == "ana@bpay.com"


def test_delete_customer():
    create = client.post("/customers", json={
        "name": "Carlos",
        "email": "carlos@bpay.com",
        "document": "99988877766",
    })
    cid = create.json()["id"]
    r = client.delete(f"/customers/{cid}")
    assert r.status_code == 204
    r = client.get(f"/customers/{cid}")
    assert r.status_code == 404


def test_invalid_document_too_short():
    r = client.post("/customers", json={
        "name": "Test",
        "email": "test@bpay.com",
        "document": "123",
    })
    assert r.status_code == 422


def test_invalid_document_letters():
    r = client.post("/customers", json={
        "name": "Test",
        "email": "test@bpay.com",
        "document": "1234567890a",
    })
    assert r.status_code == 422


def test_valid_cpf():
    r = client.post("/customers", json={
        "name": "CPF User",
        "email": "cpf@bpay.com",
        "document": "12345678901",
    })
    assert r.status_code == 201


def test_valid_cnpj():
    r = client.post("/customers", json={
        "name": "CNPJ User",
        "email": "cnpj@bpay.com",
        "document": "12345678000195",
    })
    assert r.status_code == 201


def test_duplicate_document():
    client.post("/customers", json={
        "name": "Original",
        "email": "original@bpay.com",
        "document": "11111111111",
    })
    r = client.post("/customers", json={
        "name": "Duplicate",
        "email": "dup@bpay.com",
        "document": "11111111111",
    })
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]
