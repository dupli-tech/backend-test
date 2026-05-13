import time
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_entity,
    hash_password,
    verify_password,
)
from app.auth_models import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.models import (
    _DOCUMENT_RE,
    Customer,
    CustomerCreate,
    CustomerUpdate,
    PaginatedResponse,
)
from app.store import (
    DuplicateDocumentError,
    create_customer,
    delete_customer,
    get_customer,
    get_customer_by_document,
    get_customer_by_email,
    list_customers,
    update_customer,
)
from app.user_store import (
    DuplicateEmailError,
    create_user,
    get_user,
    get_user_by_email,
)

app = FastAPI(title="BPay Backend Test", version="0.1.0")

_start_time = time.time()

CurrentEntity = Annotated[dict, Depends(get_current_entity)]


# ── Public ────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/details")
def health_details() -> dict:
    return {
        "status": "ok",
        "version": app.version,
        "uptime_seconds": round(time.time() - _start_time, 2),
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ── Auth ──────────────────────────────────────────────────────────────


@app.post("/auth/register", status_code=201)
def register(data: UserCreate) -> UserResponse:
    try:
        user = create_user(data)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already exists")
    return UserResponse(
        id=user.id, name=user.name, email=user.email, role=user.role
    )


@app.post("/auth/login")
def login(data: LoginRequest) -> TokenResponse:
    if data.entity_type == "user":
        user = get_user_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return TokenResponse(
            access_token=create_access_token(user.id, "user"),
            refresh_token=create_refresh_token(user.id, "user"),
        )

    # entity_type == "customer"
    customer = get_customer_by_email(data.email)
    if not customer or not verify_password(
        data.password, customer.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(customer.id, "customer"),
        refresh_token=create_refresh_token(customer.id, "customer"),
    )


@app.post("/auth/refresh")
def refresh(data: RefreshRequest) -> TokenResponse:
    payload = decode_token(data.refresh_token)
    if payload.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token")
    sub = payload["sub"]
    entity_type = payload["entity_type"]
    return TokenResponse(
        access_token=create_access_token(sub, entity_type),
        refresh_token=create_refresh_token(sub, entity_type),
    )


@app.get("/auth/me")
def me(current: CurrentEntity) -> dict:
    if current["entity_type"] == "user":
        user = get_user(current["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user.id, name=user.name, email=user.email, role=user.role
        ).model_dump()

    customer = get_customer(current["sub"])
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer.model_dump()


# ── Customers (protected) ────────────────────────────────────────────


@app.post("/customers", status_code=201)
def create(data: CustomerCreate, _current: CurrentEntity) -> Customer:
    try:
        return create_customer(data, hash_password(data.password))
    except DuplicateDocumentError:
        raise HTTPException(status_code=409, detail="Document already exists")


@app.get("/customers")
def list_all(
    _current: CurrentEntity, offset: int = 0, limit: int = 20
) -> PaginatedResponse[Customer]:
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422, detail="limit must be between 1 and 100"
        )
    items, total = list_customers(offset=offset, limit=limit)
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@app.get("/customers/{customer_id}")
def get(customer_id: str, _current: CurrentEntity) -> Customer:
    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.get("/customers/by-document/{document}")
def get_by_document(document: str, _current: CurrentEntity) -> Customer:
    if not _DOCUMENT_RE.match(document):
        raise HTTPException(
            status_code=422,
            detail="document must be 11 digits (CPF) or 14 digits (CNPJ)",
        )
    customer = get_customer_by_document(document)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.patch("/customers/{customer_id}")
def update(
    customer_id: str, data: CustomerUpdate, _current: CurrentEntity
) -> Customer:
    customer = update_customer(customer_id, data)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.delete("/customers/{customer_id}", status_code=204)
def delete(customer_id: str, _current: CurrentEntity) -> None:
    if not delete_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
