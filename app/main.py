from fastapi import FastAPI, HTTPException

from app.models import Customer, CustomerCreate, CustomerUpdate
from app.store import (
    DuplicateDocumentError,
    create_customer,
    delete_customer,
    get_customer,
    list_customers,
    update_customer,
)

app = FastAPI(title="BPay Backend Test", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/customers", status_code=201)
def create(data: CustomerCreate) -> Customer:
    try:
        return create_customer(data)
    except DuplicateDocumentError:
        raise HTTPException(status_code=409, detail="Document already exists")


@app.get("/customers")
def list_all() -> list[Customer]:
    return list_customers()


@app.get("/customers/{customer_id}")
def get(customer_id: str) -> Customer:
    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.patch("/customers/{customer_id}")
def update(customer_id: str, data: CustomerUpdate) -> Customer:
    customer = update_customer(customer_id, data)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.delete("/customers/{customer_id}", status_code=204)
def delete(customer_id: str) -> None:
    if not delete_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
