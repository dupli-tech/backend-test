from fastapi.testclient import TestClient

from app.main import app
from app.store import _db
from app.transaction_store import _tx_db
from app.user_store import _user_db

client = TestClient(app)


def setup_function():
    _db.clear()
    _user_db.clear()
    _tx_db.clear()


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


def _create_customer(h: dict, name: str, doc: str) -> str:
    r = client.post(
        "/customers",
        json={
            "name": name,
            "email": f"{name.lower()}@bpay.com",
            "document": doc,
            "phone": f"+55119{doc[-8:]}",
            "password": "pwd",
        },
        headers=h,
    )
    return r.json()["id"]


def test_customer_default_balance_zero():
    h = _admin_header()
    cid = _create_customer(h, "Alice", "11111111111")
    r = client.get(f"/customers/{cid}", headers=h)
    assert r.json()["balance"] == 0.0


def test_deposit_adds_balance():
    h = _admin_header()
    cid = _create_customer(h, "Alice", "11111111111")
    r = client.post(
        f"/customers/{cid}/deposit",
        json={"amount": 100.0},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["balance"] == 100.0


def test_deposit_negative_amount_422():
    h = _admin_header()
    cid = _create_customer(h, "Alice", "11111111111")
    r = client.post(
        f"/customers/{cid}/deposit",
        json={"amount": -10},
        headers=h,
    )
    assert r.status_code == 422


def test_deposit_zero_amount_422():
    h = _admin_header()
    cid = _create_customer(h, "Alice", "11111111111")
    r = client.post(
        f"/customers/{cid}/deposit",
        json={"amount": 0},
        headers=h,
    )
    assert r.status_code == 422


def test_deposit_nonexistent_404():
    h = _admin_header()
    r = client.post(
        "/customers/nonexistent/deposit",
        json={"amount": 50},
        headers=h,
    )
    assert r.status_code == 404


def test_create_transaction():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")
    b = _create_customer(h, "Bob", "22222222222")
    client.post(f"/customers/{a}/deposit", json={"amount": 200}, headers=h)

    r = client.post(
        "/transactions",
        json={
            "from_customer_id": a,
            "to_customer_id": b,
            "amount": 50.0,
        },
        headers=h,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["amount"] == 50.0
    assert data["status"] == "completed"

    ra = client.get(f"/customers/{a}", headers=h)
    rb = client.get(f"/customers/{b}", headers=h)
    assert ra.json()["balance"] == 150.0
    assert rb.json()["balance"] == 50.0


def test_transaction_insufficient_balance():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")
    b = _create_customer(h, "Bob", "22222222222")

    r = client.post(
        "/transactions",
        json={
            "from_customer_id": a,
            "to_customer_id": b,
            "amount": 100.0,
        },
        headers=h,
    )
    assert r.status_code == 422
    assert "Insufficient balance" in r.json()["detail"]


def test_transaction_nonexistent_customer():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")

    r = client.post(
        "/transactions",
        json={
            "from_customer_id": a,
            "to_customer_id": "nonexistent",
            "amount": 10,
        },
        headers=h,
    )
    assert r.status_code == 404


def test_transaction_negative_amount():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")
    b = _create_customer(h, "Bob", "22222222222")

    r = client.post(
        "/transactions",
        json={
            "from_customer_id": a,
            "to_customer_id": b,
            "amount": -10,
        },
        headers=h,
    )
    assert r.status_code == 422


def test_transaction_self_transfer():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")
    client.post(f"/customers/{a}/deposit", json={"amount": 100}, headers=h)

    r = client.post(
        "/transactions",
        json={
            "from_customer_id": a,
            "to_customer_id": a,
            "amount": 10,
        },
        headers=h,
    )
    assert r.status_code == 422
    assert "yourself" in r.json()["detail"]


def test_list_transactions():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")
    b = _create_customer(h, "Bob", "22222222222")
    client.post(f"/customers/{a}/deposit", json={"amount": 200}, headers=h)
    client.post(
        "/transactions",
        json={"from_customer_id": a, "to_customer_id": b, "amount": 30},
        headers=h,
    )

    r = client.get("/transactions", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_get_transaction_by_id():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")
    b = _create_customer(h, "Bob", "22222222222")
    client.post(f"/customers/{a}/deposit", json={"amount": 200}, headers=h)
    tx = client.post(
        "/transactions",
        json={"from_customer_id": a, "to_customer_id": b, "amount": 25},
        headers=h,
    ).json()

    r = client.get(f"/transactions/{tx['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["amount"] == 25.0
    assert "created_at" in r.json()


def test_get_transaction_not_found():
    h = _admin_header()
    r = client.get("/transactions/nonexistent", headers=h)
    assert r.status_code == 404
