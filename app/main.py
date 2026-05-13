import time
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from app.audit_models import AuditEntry
from app.audit_store import list_audit, record_audit
from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_entity,
    hash_password,
    require_role,
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
    deposit_customer,
    get_customer,
    get_customer_by_document,
    get_customer_by_email,
    list_customers,
    restore_customer,
    update_customer,
)
from app.transaction_models import (
    DepositRequest,
    Transaction,
    TransactionCreate,
)
from app.transaction_store import (
    InsufficientBalanceError,
    SelfTransferError,
    create_transaction,
    get_transaction,
    list_transactions,
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
AdminOrOperator = Annotated[dict, Depends(require_role("admin", "operator"))]
AdminOnly = Annotated[dict, Depends(require_role("admin"))]


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
            access_token=create_access_token(user.id, "user", role=user.role),
            refresh_token=create_refresh_token(user.id, "user", role=user.role),
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
    role = payload.get("role")
    return TokenResponse(
        access_token=create_access_token(sub, entity_type, role=role),
        refresh_token=create_refresh_token(sub, entity_type, role=role),
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


@app.get("/customers/me")
def get_my_customer(current: CurrentEntity) -> Customer:
    if current["entity_type"] != "customer":
        raise HTTPException(
            status_code=403, detail="Only customers can access this endpoint"
        )
    customer = get_customer(current["sub"])
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.post("/customers", status_code=201)
def create(data: CustomerCreate, _current: AdminOnly) -> Customer:
    try:
        customer = create_customer(data, hash_password(data.password))
    except DuplicateDocumentError:
        raise HTTPException(status_code=409, detail="Document already exists")
    record_audit(
        "create", "customer", customer.id,
        _current["sub"], _current["entity_type"],
    )
    return customer


@app.get("/customers")
def list_all(
    _current: AdminOrOperator,
    offset: int = 0,
    limit: int = 20,
    include_inactive: bool = False,
    search: str | None = None,
    email: str | None = None,
) -> PaginatedResponse[Customer]:
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422, detail="limit must be between 1 and 100"
        )
    items, total = list_customers(
        offset=offset,
        limit=limit,
        include_inactive=include_inactive,
        search=search,
        email=email,
    )
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@app.get("/customers/{customer_id}")
def get(customer_id: str, _current: AdminOrOperator) -> Customer:
    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.get("/customers/by-document/{document}")
def get_by_document(document: str, _current: AdminOrOperator) -> Customer:
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
    customer_id: str, data: CustomerUpdate, _current: AdminOnly
) -> Customer:
    old = get_customer(customer_id)
    customer = update_customer(customer_id, data)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    changes = data.model_dump(exclude_unset=True)
    diff = {}
    if old:
        for key, new_val in changes.items():
            old_val = getattr(old, key, None)
            if old_val != new_val:
                diff[key] = {"old": old_val, "new": new_val}
    record_audit(
        "update", "customer", customer_id,
        _current["sub"], _current["entity_type"],
        details=diff if diff else None,
    )
    return customer


@app.post("/customers/{customer_id}/restore")
def restore(customer_id: str, _current: AdminOnly) -> Customer:
    result = restore_customer(customer_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if result == "already_active":
        raise HTTPException(
            status_code=409, detail="Customer is already active"
        )
    record_audit(
        "restore", "customer", customer_id,
        _current["sub"], _current["entity_type"],
    )
    return result


@app.post("/customers/{customer_id}/deposit")
def deposit(
    customer_id: str, data: DepositRequest, _current: CurrentEntity
) -> Customer:
    if data.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    customer = deposit_customer(customer_id, data.amount)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    record_audit(
        "deposit", "customer", customer_id,
        _current["sub"], _current["entity_type"],
        details={"amount": data.amount},
    )
    return customer


@app.delete("/customers/{customer_id}", status_code=204)
def delete(customer_id: str, _current: AdminOnly) -> None:
    if not delete_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    record_audit(
        "delete", "customer", customer_id,
        _current["sub"], _current["entity_type"],
    )


# ── Transactions (protected) ─────────────────────────────────────────


@app.post("/transactions", status_code=201)
def create_tx(
    data: TransactionCreate, _current: CurrentEntity
) -> Transaction:
    if data.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    try:
        tx = create_transaction(
            data.from_customer_id, data.to_customer_id, data.amount
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SelfTransferError:
        raise HTTPException(
            status_code=422, detail="Cannot transfer to yourself"
        )
    except InsufficientBalanceError:
        raise HTTPException(
            status_code=422, detail="Insufficient balance"
        )
    record_audit(
        "transfer", "transaction", tx.id,
        _current["sub"], _current["entity_type"],
        details={
            "from": data.from_customer_id,
            "to": data.to_customer_id,
            "amount": data.amount,
        },
    )
    return tx


@app.get("/transactions")
def list_all_tx(
    _current: CurrentEntity, offset: int = 0, limit: int = 20
) -> PaginatedResponse[Transaction]:
    items, total = list_transactions(offset=offset, limit=limit)
    return PaginatedResponse(
        items=items, total=total, offset=offset, limit=limit
    )


@app.get("/transactions/{transaction_id}")
def get_tx(transaction_id: str, _current: CurrentEntity) -> Transaction:
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(
            status_code=404, detail="Transaction not found"
        )
    return tx


# ── Audit Log (admin only) ───────────────────────────────────────────


@app.get("/audit-log")
def get_audit_log(
    _current: AdminOnly,
    offset: int = 0,
    limit: int = 20,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
) -> PaginatedResponse[AuditEntry]:
    items, total = list_audit(
        offset=offset,
        limit=limit,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
    )
    return PaginatedResponse(
        items=items, total=total, offset=offset, limit=limit
    )
