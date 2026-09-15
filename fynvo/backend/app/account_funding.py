from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .ledger import LIQUID_ASSET_TYPES, account_balance_cents
from .models import Account, User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter(tags=["account-funding"])
DB = Depends(get_db)
USER = Depends(get_current_user)
MAX_BALANCE_CENTS = 99_999_999_999_999


class BalanceUpdate(BaseModel):
    account_id: int
    balance: Annotated[str, Field(min_length=1, max_length=30)]


class BulkBalanceUpdate(BaseModel):
    balances: Annotated[list[BalanceUpdate], Field(min_length=1, max_length=250)]


class PreferredBufferUpdate(BaseModel):
    amount: Annotated[str, Field(min_length=1, max_length=30)]


def _columns(connection, table: str) -> set[str]:
    return {str(row["name"]) for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()}


def ensure_account_funding_schema(engine) -> None:
    """Add account-funding fields without rewriting existing account records."""
    with engine.begin() as connection:
        columns = _columns(connection, "accounts")
        definitions = (
            "minimum_balance_cents INTEGER NOT NULL DEFAULT 0",
            "balance_updated_at DATETIME",
            "balance_update_source VARCHAR(40)",
        )
        for definition in definitions:
            column = definition.split()[0]
            if column not in columns:
                connection.execute(text(f"ALTER TABLE accounts ADD COLUMN {definition}"))
                columns.add(column)
        connection.execute(text("UPDATE accounts SET minimum_balance_cents=0 WHERE minimum_balance_cents IS NULL"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_accounts_funding ON accounts(user_id,is_active,archived_at,account_type)"))
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (14)"))
        elif int(current) < 14:
            connection.execute(text("UPDATE schema_version SET version=14"))


def _parse_balance(value: str) -> int:
    if not re.fullmatch(r"-?(?:\d+|\d*\.\d{1,2})", value.strip()):
        raise HTTPException(status_code=400, detail="Every balance must use no more than two decimal places")
    try:
        cents = parse_money(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Every balance must be a valid monetary amount") from exc
    if abs(cents) > MAX_BALANCE_CENTS:
        raise HTTPException(status_code=400, detail="A balance is outside the supported range")
    return cents


@router.patch("/accounts/balances")
def update_balances(payload: BulkBalanceUpdate, current_user: User = USER, db: DbSession = DB):
    ids = [item.account_id for item in payload.balances]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Each Account may appear only once")

    accounts = {
        account.id: account
        for account in db.query(Account).filter(Account.user_id == current_user.id, Account.id.in_(ids)).all()
    }
    missing = sorted(set(ids) - set(accounts))
    if missing:
        raise HTTPException(status_code=404, detail={"message": "One or more Accounts no longer exist", "account_ids": missing})

    parsed: dict[int, int] = {}
    for item in payload.balances:
        account = accounts[item.account_id]
        if not account.is_active or account.archived_at is not None:
            raise HTTPException(status_code=409, detail=f"{account.name} is no longer active")
        parsed[item.account_id] = _parse_balance(item.balance)

    now = utcnow()
    changed: list[dict[str, str | int]] = []
    try:
        for account_id in ids:
            account = accounts[account_id]
            requested = parsed[account_id]
            current = account_balance_cents(db, account)
            if requested == current:
                continue
            transaction_total = current - int(account.opening_balance_cents or 0)
            account.opening_balance_cents = requested - transaction_total
            account.balance_updated_at = now
            account.balance_update_source = "manual"
            account.updated_at = now
            changed.append(
                {
                    "account_id": account.id,
                    "previous_balance": cents_to_decimal(current),
                    "balance": cents_to_decimal(requested),
                }
            )
        if changed:
            db.commit()
        else:
            db.rollback()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Balances could not be updated. No changes were saved") from exc

    return {
        "status": "updated" if changed else "unchanged",
        "updated_count": len(changed),
        "balance_updated_at": now.isoformat() if changed else None,
        "balances": changed,
    }


@router.put("/accounts/{account_id}/preferred-buffer")
def update_preferred_buffer(
    account_id: int,
    payload: PreferredBufferUpdate,
    current_user: User = USER,
    db: DbSession = DB,
):
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_active or account.archived_at is not None or account.account_type not in LIQUID_ASSET_TYPES:
        raise HTTPException(status_code=409, detail="Choose an active liquid Account")
    amount = _parse_balance(payload.amount)
    if amount < 0:
        raise HTTPException(status_code=400, detail="Preferred buffer cannot be negative")
    account.minimum_balance_cents = amount
    account.updated_at = utcnow()
    db.commit()
    return {"account_id": account.id, "preferred_buffer": cents_to_decimal(amount)}


@router.get("/payment-planning/account-funding")
def account_funding(current_user: User = USER, db: DbSession = DB):
    from .payment_planning import build_pay_cycle_planning

    plan = build_pay_cycle_planning(db, current_user)
    return {
        "as_of": plan["as_of"],
        "current_cycle": plan.get("account_funding"),
        "next_cycle": plan.get("payday_allocation"),
        "completeness": plan.get("completeness"),
    }
