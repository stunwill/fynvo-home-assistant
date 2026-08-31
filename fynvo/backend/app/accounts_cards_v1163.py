from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .ledger import LIABILITY_TYPES, account_response, get_account
from .models import User
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)


def _table_exists(db: DbSession, table: str) -> bool:
    return bool(db.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table}).scalar())


def _column_exists(db: DbSession, table: str, column: str) -> bool:
    if not _table_exists(db, table):
        return False
    return any(row[1] == column for row in db.execute(text(f"PRAGMA table_info({table})")).all())


def _count(db: DbSession, table: str, clause: str, params: dict[str, Any]) -> int:
    if not _table_exists(db, table):
        return 0
    return int(db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {clause}"), params).scalar() or 0)


def _protected_transaction_clause(db: DbSession) -> str:
    conditions = ["transfer_id IS NOT NULL"] if _column_exists(db, "transactions", "transfer_id") else []
    if _table_exists(db, "scheduled_payments") and _column_exists(db, "scheduled_payments", "matched_transaction_id"):
        conditions.append("id IN (SELECT matched_transaction_id FROM scheduled_payments WHERE matched_transaction_id IS NOT NULL)")
    return " OR ".join(conditions) or "0"


def dependency_preview(db: DbSession, user: User, account_id: int) -> dict[str, Any]:
    get_account(db, user, account_id)
    params = {"uid": user.id, "account_id": account_id}
    protected_clause = _protected_transaction_clause(db)
    movable_tx_count = _count(db, "transactions", f"user_id=:uid AND account_id=:account_id AND NOT ({protected_clause})", params)
    protected_tx_count = _count(db, "transactions", f"user_id=:uid AND account_id=:account_id AND ({protected_clause})", params)
    dependencies = [
        {"type": "transactions", "label": "Transactions", "count": movable_tx_count, "classification": "conditionally_safe", "action": "move"},
        {"type": "protected_transactions", "label": "Protected Transactions", "count": protected_tx_count, "classification": "historical", "action": "preserve"},
        {"type": "cards", "label": "Cards", "count": _count(db, "cards", "user_id=:uid AND account_id=:account_id", params), "classification": "safe", "action": "move"},
        {"type": "recurring_expenses", "label": "Recurring Expenses", "count": _count(db, "recurring_expenses", "user_id=:uid AND account_id=:account_id", params), "classification": "conditionally_safe", "action": "move_future_configuration"},
        {"type": "income_sources", "label": "Income", "count": _count(db, "income_sources", "user_id=:uid AND destination_account_id=:account_id", params), "classification": "conditionally_safe", "action": "move_future_configuration"},
        {"type": "bills", "label": "Bills", "count": _count(db, "bills", "user_id=:uid AND account_id=:account_id", params), "classification": "conditionally_safe", "action": "move_future_configuration"},
        {"type": "planned_spending", "label": "Planned Spending", "count": _count(db, "planned_spending", "user_id=:uid AND account_id=:account_id", params), "classification": "conditionally_safe", "action": "move_future_configuration"},
        {"type": "scheduled_payments", "label": "Scheduled Payments", "count": _count(db, "scheduled_payments", "user_id=:uid AND account_id=:account_id", params), "classification": "historical", "action": "preserve"},
        {"type": "transfers_from", "label": "Transfers from Account", "count": _count(db, "transfers", "user_id=:uid AND from_account_id=:account_id", params), "classification": "historical", "action": "preserve"},
        {"type": "transfers_to", "label": "Transfers to Account", "count": _count(db, "transfers", "user_id=:uid AND to_account_id=:account_id", params), "classification": "historical", "action": "preserve"},
    ]
    movable = sum(item["count"] for item in dependencies if item["classification"] != "historical")
    historical = sum(item["count"] for item in dependencies if item["classification"] == "historical")
    return {"account_id": account_id, "dependencies": dependencies, "movable_count": movable, "historical_count": historical, "can_delete": movable == 0 and historical == 0}


@router.get("/accounts/{account_id}/dependencies")
def account_dependencies(account_id: int, current_user: User = USER, db: DbSession = DB):
    return dependency_preview(db, current_user, account_id)


@router.post("/accounts/{account_id}/restore")
def restore_account(account_id: int, current_user: User = USER, db: DbSession = DB):
    account = get_account(db, current_user, account_id)
    account.is_active = True
    account.archived_at = None
    account.updated_at = utcnow()
    db.commit()
    return account_response(db, account)


@router.post("/accounts/{account_id}/move-and-archive")
def move_and_archive(account_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    source = get_account(db, current_user, account_id)
    destination_id = int(payload.get("destination_account_id") or 0)
    destination = get_account(db, current_user, destination_id)
    if destination.id == source.id:
        raise HTTPException(status_code=400, detail="Destination Account must differ from the source Account")
    if not destination.is_active or destination.archived_at:
        raise HTTPException(status_code=409, detail="Destination Account must be active")

    source_is_liability = source.account_type in LIABILITY_TYPES
    destination_is_liability = destination.account_type in LIABILITY_TYPES
    preview = dependency_preview(db, current_user, account_id)
    movable_transactions = next((item["count"] for item in preview["dependencies"] if item["type"] == "transactions"), 0)
    if movable_transactions and source_is_liability != destination_is_liability:
        raise HTTPException(
            status_code=409,
            detail="Transactions cannot be bulk moved between asset and liability Accounts because their stored balance direction differs. Choose a destination with the same Account class, or archive this Account without moving Transactions.",
        )

    now = utcnow()
    protected_clause = _protected_transaction_clause(db)
    try:
        if _table_exists(db, "transactions"):
            db.execute(text(f"UPDATE transactions SET account_id=:destination,updated_at=:now WHERE user_id=:uid AND account_id=:source AND NOT ({protected_clause})"), {"destination": destination.id, "source": source.id, "uid": current_user.id, "now": now})
        if _table_exists(db, "cards"):
            db.execute(text("UPDATE cards SET account_id=:destination,updated_at=:now WHERE user_id=:uid AND account_id=:source"), {"destination": destination.id, "source": source.id, "uid": current_user.id, "now": now})
        if _table_exists(db, "recurring_expenses"):
            db.execute(text("UPDATE recurring_expenses SET account_id=:destination,updated_at=:now WHERE user_id=:uid AND account_id=:source"), {"destination": destination.id, "source": source.id, "uid": current_user.id, "now": now})
        if _table_exists(db, "income_sources"):
            db.execute(text("UPDATE income_sources SET destination_account_id=:destination,updated_at=:now WHERE user_id=:uid AND destination_account_id=:source"), {"destination": destination.id, "source": source.id, "uid": current_user.id, "now": now})
        if _table_exists(db, "bills"):
            db.execute(text("UPDATE bills SET account_id=:destination,updated_at=:now WHERE user_id=:uid AND account_id=:source"), {"destination": destination.id, "source": source.id, "uid": current_user.id, "now": now})
        if _table_exists(db, "planned_spending"):
            db.execute(text("UPDATE planned_spending SET account_id=:destination,updated_at=:now WHERE user_id=:uid AND account_id=:source"), {"destination": destination.id, "source": source.id, "uid": current_user.id, "now": now})
        source.is_active = False
        source.archived_at = now
        source.updated_at = now
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"status": "ok", "account": account_response(db, source), "destination_account_id": destination.id, "preserved_historical_relationships": ["protected_transactions", "scheduled_payments", "transfers"]}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, current_user: User = USER, db: DbSession = DB):
    account = get_account(db, current_user, account_id)
    preview = dependency_preview(db, current_user, account_id)
    blockers = [item for item in preview["dependencies"] if item["count"]]
    if blockers:
        summary = ", ".join(f"{item['count']} {item['label']}" for item in blockers)
        raise HTTPException(status_code=409, detail=f"This Account cannot be permanently deleted because it is referenced by {summary}. Archive it instead, or move eligible records first.")
    db.delete(account)
    db.commit()
    return {"status": "ok"}
