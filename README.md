# backend-test

BPay backend test — CRUD simples de clientes em FastAPI.

## Setup

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest -v
```
