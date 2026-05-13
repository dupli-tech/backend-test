import uuid
from datetime import UTC, datetime

from app.store import _db
from app.transaction_models import Transaction, TransactionStatus

_tx_db: dict[str, Transaction] = {}


class InsufficientBalanceError(Exception):
    pass


class SelfTransferError(Exception):
    pass


def create_transaction(
    from_id: str, to_id: str, amount: float
) -> Transaction:
    from_stored = _db.get(from_id)
    to_stored = _db.get(to_id)

    if not from_stored or not from_stored.is_active:
        raise KeyError(f"Customer {from_id} not found")
    if not to_stored or not to_stored.is_active:
        raise KeyError(f"Customer {to_id} not found")
    if from_id == to_id:
        raise SelfTransferError
    if from_stored.balance < amount:
        raise InsufficientBalanceError

    _db[from_id] = from_stored.model_copy(
        update={"balance": from_stored.balance - amount}
    )
    _db[to_id] = to_stored.model_copy(
        update={"balance": to_stored.balance + amount}
    )

    tx = Transaction(
        id=str(uuid.uuid4()),
        from_customer_id=from_id,
        to_customer_id=to_id,
        amount=amount,
        created_at=datetime.now(UTC).isoformat(),
        status=TransactionStatus.completed,
    )
    _tx_db[tx.id] = tx
    return tx


def get_transaction(tx_id: str) -> Transaction | None:
    return _tx_db.get(tx_id)


def list_transactions(
    offset: int = 0, limit: int = 20
) -> tuple[list[Transaction], int]:
    all_txs = list(_tx_db.values())
    total = len(all_txs)
    return all_txs[offset : offset + limit], total
