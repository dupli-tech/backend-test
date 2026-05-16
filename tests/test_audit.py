from fastapi.testclient import TestClient

from app.audit_store import _audit_db
from app.main import app
from app.store import _db
from app.transaction_store import _tx_db
from app.user_store import _user_db

client = TestClient(app)


def setup_function():
    _db.clear()
    _user_db.clear()
    _tx_db.clear()
    _audit_db.clear()


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


def _operator_header() -> dict:
    client.post(
        "/auth/register",
        json={
            "name": "Op",
            "email": "op@bpay.com",
            "password": "pwd",
            "role": "operator",
        },
    )
    r = client.post(
        "/auth/login",
        json={
            "email": "op@bpay.com",
            "password": "pwd",
            "entity_type": "user",
        },
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_customer(
    h: dict, name: str = "Test", doc: str = "11111111111"
):
    return client.post(
        "/customers",
        json={
            "name": name,
            "email": f"{name.lower()}@bpay.com",
            "document": doc,
            "phone": f"+55119{doc[-8:]}",
            "password": "pwd",
        },
        headers=h,
    ).json()["id"]


def test_create_generates_audit():
    h = _admin_header()
    _create_customer(h)
    r = client.get("/audit-log", headers=h)
    entries = r.json()["items"]
    assert any(e["action"] == "create" for e in entries)


def test_update_generates_audit_with_diff():
    h = _admin_header()
    cid = _create_customer(h)
    client.patch(
        f"/customers/{cid}",
        json={"name": "New Name"},
        headers=h,
    )
    r = client.get("/audit-log", headers=h)
    updates = [e for e in r.json()["items"] if e["action"] == "update"]
    assert len(updates) == 1
    assert updates[0]["details"]["name"]["old"] == "Test"
    assert updates[0]["details"]["name"]["new"] == "New Name"


def test_delete_generates_audit():
    h = _admin_header()
    cid = _create_customer(h)
    client.delete(f"/customers/{cid}", headers=h)
    r = client.get("/audit-log", headers=h)
    assert any(e["action"] == "delete" for e in r.json()["items"])


def test_restore_generates_audit():
    h = _admin_header()
    cid = _create_customer(h)
    client.delete(f"/customers/{cid}", headers=h)
    client.post(f"/customers/{cid}/restore", headers=h)
    r = client.get("/audit-log", headers=h)
    assert any(e["action"] == "restore" for e in r.json()["items"])


def test_deposit_generates_audit():
    h = _admin_header()
    cid = _create_customer(h)
    client.post(
        f"/customers/{cid}/deposit",
        json={"amount": 100},
        headers=h,
    )
    r = client.get("/audit-log", headers=h)
    deposits = [e for e in r.json()["items"] if e["action"] == "deposit"]
    assert len(deposits) == 1
    assert deposits[0]["details"]["amount"] == 100


def test_transfer_generates_audit():
    h = _admin_header()
    a = _create_customer(h, "Alice", "11111111111")
    b = _create_customer(h, "Bob", "22222222222")
    client.post(f"/customers/{a}/deposit", json={"amount": 200}, headers=h)
    client.post(
        "/transactions",
        json={
            "from_customer_id": a,
            "to_customer_id": b,
            "amount": 50,
        },
        headers=h,
    )
    r = client.get("/audit-log", headers=h)
    transfers = [
        e for e in r.json()["items"] if e["action"] == "transfer"
    ]
    assert len(transfers) == 1
    assert transfers[0]["details"]["amount"] == 50


def test_filter_by_entity_type():
    h = _admin_header()
    _create_customer(h)
    r = client.get("/audit-log?entity_type=customer", headers=h)
    assert r.json()["total"] >= 1
    assert all(
        e["entity_type"] == "customer" for e in r.json()["items"]
    )


def test_filter_by_entity_id():
    h = _admin_header()
    cid = _create_customer(h)
    r = client.get(f"/audit-log?entity_id={cid}", headers=h)
    assert r.json()["total"] >= 1
    assert all(e["entity_id"] == cid for e in r.json()["items"])


def test_filter_by_actor_id():
    h = _admin_header()
    _create_customer(h)
    me = client.get("/auth/me", headers=h).json()
    r = client.get(f"/audit-log?actor_id={me['id']}", headers=h)
    assert r.json()["total"] >= 1


def test_audit_log_pagination():
    h = _admin_header()
    for i in range(5):
        _create_customer(h, f"C{i}", f"{10000000000 + i}")
    r = client.get("/audit-log?limit=2", headers=h)
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5


def test_operator_cannot_access_audit_log():
    _admin_header()
    h = _operator_header()
    r = client.get("/audit-log", headers=h)
    assert r.status_code == 403


def test_audit_entry_has_required_fields():
    h = _admin_header()
    _create_customer(h)
    r = client.get("/audit-log", headers=h)
    entry = r.json()["items"][0]
    assert "id" in entry
    assert "action" in entry
    assert "entity_type" in entry
    assert "entity_id" in entry
    assert "actor_id" in entry
    assert "actor_type" in entry
    assert "timestamp" in entry
