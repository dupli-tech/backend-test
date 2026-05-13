import uuid

from app.models import Customer, CustomerCreate, CustomerStored, CustomerUpdate

_db: dict[str, CustomerStored] = {}


class DuplicateDocumentError(Exception):
    pass


def _to_customer(stored: CustomerStored) -> Customer:
    return Customer(**stored.model_dump(exclude={"hashed_password"}))


def create_customer(data: CustomerCreate, hashed_password: str) -> Customer:
    for existing in _db.values():
        if existing.document == data.document:
            raise DuplicateDocumentError(data.document)
    stored = CustomerStored(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        document=data.document,
        hashed_password=hashed_password,
    )
    _db[stored.id] = stored
    return _to_customer(stored)


def get_customer(customer_id: str) -> Customer | None:
    stored = _db.get(customer_id)
    if not stored or not stored.is_active:
        return None
    return _to_customer(stored)


def get_customer_stored(customer_id: str) -> CustomerStored | None:
    return _db.get(customer_id)


def get_customer_by_email(email: str) -> CustomerStored | None:
    for stored in _db.values():
        if stored.email == email:
            return stored
    return None


def list_customers(
    offset: int = 0,
    limit: int = 20,
    *,
    include_inactive: bool = False,
    search: str | None = None,
    email: str | None = None,
) -> tuple[list[Customer], int]:
    if include_inactive:
        filtered = list(_db.values())
    else:
        filtered = [s for s in _db.values() if s.is_active]
    if search:
        search_lower = search.lower()
        filtered = [s for s in filtered if search_lower in s.name.lower()]
    if email:
        filtered = [s for s in filtered if s.email == email]
    total = len(filtered)
    page = filtered[offset : offset + limit]
    return [_to_customer(s) for s in page], total


def update_customer(customer_id: str, data: CustomerUpdate) -> Customer | None:
    stored = _db.get(customer_id)
    if not stored:
        return None
    updates = data.model_dump(exclude_unset=True)
    updated = stored.model_copy(update=updates)
    _db[customer_id] = updated
    return _to_customer(updated)


def get_customer_by_document(document: str) -> Customer | None:
    for stored in _db.values():
        if stored.document == document:
            return _to_customer(stored)
    return None


def delete_customer(customer_id: str) -> bool:
    stored = _db.get(customer_id)
    if not stored or not stored.is_active:
        return False
    _db[customer_id] = stored.model_copy(update={"is_active": False})
    return True


def deposit_customer(customer_id: str, amount: float) -> Customer | None:
    stored = _db.get(customer_id)
    if not stored or not stored.is_active:
        return None
    updated = stored.model_copy(
        update={"balance": stored.balance + amount}
    )
    _db[customer_id] = updated
    return _to_customer(updated)


def restore_customer(customer_id: str) -> Customer | None | str:
    stored = _db.get(customer_id)
    if not stored:
        return None
    if stored.is_active:
        return "already_active"
    restored = stored.model_copy(update={"is_active": True})
    _db[customer_id] = restored
    return _to_customer(restored)
