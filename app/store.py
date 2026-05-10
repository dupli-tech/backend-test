import uuid

from app.models import Customer, CustomerCreate, CustomerUpdate

_db: dict[str, Customer] = {}


class DuplicateDocumentError(Exception):
    pass


def create_customer(data: CustomerCreate) -> Customer:
    for existing in _db.values():
        if existing.document == data.document:
            raise DuplicateDocumentError(data.document)
    customer = Customer(id=str(uuid.uuid4()), **data.model_dump())
    _db[customer.id] = customer
    return customer


def get_customer(customer_id: str) -> Customer | None:
    return _db.get(customer_id)


def list_customers(
    offset: int = 0, limit: int = 20
) -> tuple[list[Customer], int]:
    all_customers = list(_db.values())
    total = len(all_customers)
    return all_customers[offset : offset + limit], total


def update_customer(customer_id: str, data: CustomerUpdate) -> Customer | None:
    customer = _db.get(customer_id)
    if not customer:
        return None
    updates = data.model_dump(exclude_unset=True)
    updated = customer.model_copy(update=updates)
    _db[customer_id] = updated
    return updated


def get_customer_by_document(document: str) -> Customer | None:
    for customer in _db.values():
        if customer.document == document:
            return customer
    return None


def delete_customer(customer_id: str) -> bool:
    return _db.pop(customer_id, None) is not None
