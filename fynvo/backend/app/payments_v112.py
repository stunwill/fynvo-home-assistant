from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import payments_v17, v1, v111
from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)

PAYMENT_METHODS = set(v1.PAYMENT_METHODS)
PAYMENT_HANDLING = {"automatic", "manual"}
TERMINAL_BILL_STATUSES = {"paid", "cancelled"}
ACTIONABLE_STATUSES = {"overdue", "due_today", "auto_payment_unconfirmed", "match_review_available"}


def _columns(connection, table: str) -> set[str]:
    return {str(row["name"]) for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()}


def _add_column(connection, table: str, definition: str, columns: set[str]) -> None:
    column = definition.split()[0]
    if column not in columns:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
        columns.add(column)


def ensure_v112_schema(engine) -> None:
    """Add Bill payment metadata without replacing existing financial records."""
    with engine.begin() as connection:
        columns = _columns(connection, "bills")
        for definition in (
            "payment_method VARCHAR(40) NOT NULL DEFAULT 'not_set'",
            "payment_handling VARCHAR(20) NOT NULL DEFAULT 'manual'",
            "auto_payment_grace_days INTEGER NOT NULL DEFAULT 3",
            "card_id INTEGER REFERENCES cards(id)",
            "expense_type_id INTEGER REFERENCES expense_types(id)",
            "payee_merchant VARCHAR(180)",
            "actual_date DATE",
            "actual_amount_cents INTEGER",
            "matched_transaction_id INTEGER REFERENCES transactions(id)",
            "confirmation_source VARCHAR(40)",
            "cancelled_at DATETIME",
            "version INTEGER NOT NULL DEFAULT 1",
        ):
            _add_column(connection, "bills", definition, columns)
        connection.execute(text("""
            UPDATE bills
            SET payment_handling = CASE
                WHEN payment_method IN ('direct_debit','automatic_card_payment') THEN 'automatic'
                ELSE 'manual'
            END
            WHERE payment_handling IS NULL OR payment_handling=''
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bill_payment_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                bill_id INTEGER NOT NULL,
                from_status VARCHAR(40),
                to_status VARCHAR(40) NOT NULL,
                source VARCHAR(40) NOT NULL,
                note TEXT,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(bill_id) REFERENCES bills(id)
            )
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_bill_payment_history ON bill_payment_history(user_id,bill_id,created_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_bill_payment_centre ON bills(user_id,is_active,due_date,payment_handling,payment_method)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_bill_tx_unique ON bills(user_id,matched_transaction_id) WHERE matched_transaction_id IS NOT NULL"))


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _require_account(db: DbSession, user: User, account_id: int | None) -> dict[str, Any] | None:
    if account_id is None:
        return None
    row = db.execute(text("SELECT id,name,is_active,archived_at FROM accounts WHERE id=:id AND user_id=:uid"), {"id": account_id, "uid": user.id}).mappings().first()
    if not row or not row["is_active"] or row["archived_at"]:
        raise HTTPException(status_code=400, detail="The selected Account is no longer available")
    return dict(row)


def _require_card(db: DbSession, user: User, card_id: int | None) -> dict[str, Any] | None:
    if card_id is None:
        return None
    row = db.execute(text("""
        SELECT c.id,c.account_id,c.name,c.last_four,c.is_active,a.name AS account_name,a.is_active AS account_active,a.archived_at
        FROM cards c JOIN accounts a ON a.id=c.account_id AND a.user_id=c.user_id
        WHERE c.id=:id AND c.user_id=:uid
    """), {"id": card_id, "uid": user.id}).mappings().first()
    if not row or not row["is_active"] or not row["account_active"] or row["archived_at"]:
        raise HTTPException(status_code=400, detail="The selected Card is no longer available")
    return dict(row)


def _bill_status(row: dict[str, Any], today: date | None = None) -> str:
    today = today or date.today()
    if row.get("cancelled_at") or not bool(row.get("is_active", True)):
        return "cancelled"
    if row.get("paid_at") or row.get("actual_date") or row.get("remaining_amount_cents") == 0:
        return "paid"
    if row.get("original_amount_cents") is None and row.get("remaining_amount_cents") is None:
        return "unknown"
    due = _as_date(row.get("due_date"))
    handling = row.get("payment_handling") or payments_v17.default_payment_handling(row.get("payment_method"))
    grace = int(row.get("auto_payment_grace_days") or payments_v17.DEFAULT_GRACE_DAYS)
    if due is None:
        original = str(row.get("original_status") or "").lower()
        return "overdue" if "overdue" in original else "upcoming"
    if due > today:
        return "upcoming"
    if handling == "automatic":
        if due + timedelta(days=grace) < today:
            return "auto_payment_unconfirmed"
        return "expected_automatically"
    if due == today:
        return "due_today"
    return "overdue"


def _bill_response(row: Any, today: date | None = None) -> dict[str, Any]:
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    current = today or date.today()
    due = _as_date(data.get("due_date"))
    expected_cents = data.get("original_amount_cents")
    if expected_cents is None:
        expected_cents = data.get("remaining_amount_cents")
    actual_cents = data.get("actual_amount_cents")
    state = _bill_status(data, current)
    difference = None if actual_cents is None or expected_cents is None else int(actual_cents) - int(expected_cents)
    payment_method = data.get("payment_method") or "not_set"
    return {
        "id": int(data["id"]), "source_type": "bill", "source_id": int(data["id"]),
        "recurring_expense_id": data.get("recurring_expense_id"), "name": data.get("name"),
        "provider": data.get("provider"), "payee_merchant": data.get("payee_merchant") or data.get("provider"),
        "bill_type": data.get("bill_type"), "priority": data.get("priority") or "normal",
        "category_id": data.get("category_id"), "category": data.get("category_name") or data.get("bill_type"),
        "expense_type_id": data.get("expense_type_id"), "expense_type": data.get("expense_type_name") or data.get("bill_type"),
        "expected_date": due.isoformat() if due else None, "due_date": due.isoformat() if due else None,
        "expected_amount": cents_to_decimal(int(expected_cents)) if expected_cents is not None else None,
        "amount": cents_to_decimal(int(data["remaining_amount_cents"])) if data.get("remaining_amount_cents") is not None else None,
        "actual_date": _as_date(data.get("actual_date")).isoformat() if data.get("actual_date") else None,
        "actual_amount": cents_to_decimal(int(actual_cents)) if actual_cents is not None else None,
        "difference": cents_to_decimal(difference) if difference is not None else None,
        "status": state, "days_overdue": (current - due).days if due and state == "overdue" else None,
        "payment_method": payment_method,
        "payment_method_label": v1.PAYMENT_METHODS.get(payment_method, payment_method.replace("_", " ").title()),
        "payment_handling": data.get("payment_handling") or payments_v17.default_payment_handling(payment_method),
        "auto_payment_grace_days": int(data.get("auto_payment_grace_days") or payments_v17.DEFAULT_GRACE_DAYS),
        "account_id": data.get("account_id"), "account_name": data.get("account_name"),
        "card_id": data.get("card_id"), "card_name": data.get("card_display_name"), "linked_account_name": data.get("linked_account_name"),
        "notes": data.get("notes"), "matched_transaction_id": data.get("matched_transaction_id"),
        "confirmation_source": data.get("confirmation_source"), "version": int(data.get("version") or 1),
        "is_active": bool(data.get("is_active", True)), "original_status": data.get("original_status"),
        "requires_action": state in ACTIONABLE_STATUSES,
    }


def _bill_rows(db: DbSession, user: User) -> list[dict[str, Any]]:
    rows = db.execute(text("""
        SELECT b.*,a.name AS account_name,
               CASE WHEN c.id IS NULL THEN NULL ELSE c.name || ' ••••' || c.last_four END AS card_display_name,
               ca.name AS linked_account_name,cat.name AS category_name,et.name AS expense_type_name
        FROM bills b
        LEFT JOIN accounts a ON a.id=b.account_id AND a.user_id=b.user_id
        LEFT JOIN cards c ON c.id=b.card_id AND c.user_id=b.user_id
        LEFT JOIN accounts ca ON ca.id=c.account_id AND ca.user_id=b.user_id
        LEFT JOIN categories cat ON cat.id=b.category_id AND cat.user_id=b.user_id
        LEFT JOIN expense_types et ON et.id=b.expense_type_id AND et.user_id=b.user_id
        WHERE b.user_id=:uid
        ORDER BY b.due_date IS NULL,b.due_date,b.id
    """), {"uid": user.id}).all()
    return [_bill_response(row) for row in rows]


def list_bills_v112(db: DbSession, user: User, filter_value: str = "all") -> list[dict[str, Any]]:
    from .finance import ensure_seed_data

    ensure_seed_data(db, user)
    rows = _bill_rows(db, user)
    if filter_value == "overdue":
        return [row for row in rows if row["status"] == "overdue"]
    if filter_value == "due_soon":
        return [row for row in rows if row["status"] in {"due_today", "upcoming"} and row.get("due_date") and _as_date(row["due_date"]) <= date.today() + timedelta(days=7)]
    if filter_value == "paid":
        return [row for row in rows if row["status"] == "paid"]
    if filter_value == "active":
        return [row for row in rows if row["status"] not in TERMINAL_BILL_STATUSES]
    return rows


class BillPayload(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    amount: str | None = None
    due_date: date | None = None
    provider: str | None = Field(default=None, max_length=140)
    payee_merchant: str | None = Field(default=None, max_length=180)
    bill_type: str | None = Field(default=None, max_length=80)
    priority: str = "normal"
    category_id: int | None = None
    expense_type_id: int | None = None
    payment_handling: str = "manual"
    payment_method: str = "not_set"
    account_id: int | None = None
    card_id: int | None = None
    auto_payment_grace_days: int = Field(default=3, ge=0, le=30)
    notes: str | None = None
    recurring_expense_id: int | None = None
    paid_through_date: date | None = None
    version: int | None = None


class BillUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    amount: str | None = None
    due_date: date | None = None
    provider: str | None = Field(default=None, max_length=140)
    payee_merchant: str | None = Field(default=None, max_length=180)
    bill_type: str | None = Field(default=None, max_length=80)
    priority: str | None = None
    category_id: int | None = None
    expense_type_id: int | None = None
    payment_handling: str | None = None
    payment_method: str | None = None
    account_id: int | None = None
    card_id: int | None = None
    auto_payment_grace_days: int | None = Field(default=None, ge=0, le=30)
    notes: str | None = None
    recurring_expense_id: int | None = None
    paid_through_date: date | None = None
    version: int | None = None
    status: str | None = None


def _validate_bill_payload(db: DbSession, user: User, payload: BillPayload) -> tuple[int | None, int | None]:
    if payload.priority not in {"high", "normal", "low"}:
        raise HTTPException(status_code=400, detail="Invalid Bill priority")
    if payload.payment_method not in PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="Invalid Payment Method")
    if payload.payment_handling not in PAYMENT_HANDLING:
        raise HTTPException(status_code=400, detail="Invalid Payment Handling")
    if payload.payment_method == "direct_debit":
        if payload.account_id is None:
            raise HTTPException(status_code=400, detail="Direct Debit requires an Account")
        _require_account(db, user, payload.account_id)
        return payload.account_id, None
    if payload.payment_method == "automatic_card_payment":
        if payload.card_id is None:
            raise HTTPException(status_code=400, detail="Automatic Card Payment requires a Card")
        card = _require_card(db, user, payload.card_id)
        return int(card["account_id"]), payload.card_id
    if payload.account_id is not None:
        _require_account(db, user, payload.account_id)
    if payload.card_id is not None:
        _require_card(db, user, payload.card_id)
    return payload.account_id, payload.card_id


def create_bill_v112(db: DbSession, user: User, payload: Any) -> dict[str, Any]:
    values = payload if isinstance(payload, BillPayload) else BillPayload(**payload.model_dump()) if hasattr(payload, "model_dump") else BillPayload(**dict(payload))
    account_id, card_id = _validate_bill_payload(db, user, values)
    amount = parse_money(values.amount) if values.amount not in (None, "") else None
    now = utcnow()
    db.execute(text("""
        INSERT INTO bills(
            user_id,recurring_expense_id,name,provider,payee_merchant,bill_type,priority,
            original_amount_cents,remaining_amount_cents,due_date,account_id,card_id,category_id,expense_type_id,
            payment_method,payment_handling,auto_payment_grace_days,paid_through_date,notes,is_active,source,created_at,updated_at,version
        ) VALUES(
            :uid,:recurring_id,:name,:provider,:payee,:bill_type,:priority,
            :amount,:amount,:due,:account_id,:card_id,:category_id,:expense_type_id,
            :method,:handling,:grace,:paid_through,:notes,1,'manual',:now,:now,1
        )
    """), {
        "uid": user.id, "recurring_id": values.recurring_expense_id, "name": values.name.strip(),
        "provider": values.provider, "payee": values.payee_merchant or values.provider, "bill_type": values.bill_type,
        "priority": values.priority, "amount": amount, "due": values.due_date, "account_id": account_id,
        "card_id": card_id, "category_id": values.category_id, "expense_type_id": values.expense_type_id,
        "method": values.payment_method, "handling": values.payment_handling, "grace": values.auto_payment_grace_days,
        "paid_through": values.paid_through_date, "notes": values.notes, "now": now,
    })
    bill_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    db.commit()
    return next(row for row in _bill_rows(db, user) if row["id"] == bill_id)


def _date_range(kind: str, start: date | None, end: date | None, current: date | None = None) -> tuple[date | None, date | None]:
    current = current or date.today()
    if kind == "today":
        return current, current
    if kind == "next_7_days":
        return current, current + timedelta(days=7)
    if kind == "next_14_days":
        return current, current + timedelta(days=14)
    if kind == "next_30_days":
        return current, current + timedelta(days=30)
    if kind == "this_month":
        next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        return current, next_month - timedelta(days=1)
    if kind == "next_month":
        next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        following = (next_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        return next_month, following - timedelta(days=1)
    if kind == "overdue":
        return None, current - timedelta(days=1)
    if kind == "custom":
        return start, end
    if kind == "history":
        return start, end or current
    raise HTTPException(status_code=400, detail="Unsupported Date Range")


def _within(item: dict[str, Any], start: date | None, end: date | None, range_kind: str) -> bool:
    when = _as_date(item.get("expected_date") or item.get("due_date") or item.get("actual_date"))
    if range_kind == "overdue":
        return item.get("status") == "overdue"
    if range_kind in {"today", "next_7_days", "next_14_days", "next_30_days"} and item.get("status") == "overdue":
        return True
    if when is None:
        return False
    return (start is None or when >= start) and (end is None or when <= end)


def _status_bucket(item: dict[str, Any]) -> str:
    state = item.get("status")
    if state in {"due", "due_today"}:
        return "requires_payment"
    if state == "expected_automatically":
        return "expected_automatically"
    if state == "auto_payment_unconfirmed":
        return "awaiting_confirmation"
    return state or "upcoming"


def _sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
    priority = {
        "overdue": 0, "auto_payment_unconfirmed": 1, "due_today": 2, "due": 2,
        "expected_automatically": 3, "upcoming": 5, "paid": 8, "skipped": 9, "cancelled": 10,
    }.get(item.get("status"), 6)
    return priority, str(item.get("expected_date") or item.get("due_date") or "9999-12-31"), str(item.get("name") or "")


@router.get("/payment-planning")
def payment_planning(current_user: User = USER, db: DbSession = DB):
    from .payment_planning import build_payment_planning

    return build_payment_planning(db, current_user)


@router.get("/payment-planning/pay-cycle")
def pay_cycle_planning(current_user: User = USER, db: DbSession = DB):
    from .payment_planning import build_pay_cycle_planning

    return build_pay_cycle_planning(db, current_user)


@router.get("/payment-centre")
def payment_centre(
    date_range: str = Query(default="next_30_days"), date_from: date | None = None, date_to: date | None = None,
    search: str | None = None, status_filter: str | None = None, source: str | None = None,
    category_id: int | None = None, payment_method: str | None = None, payment_handling: str | None = None,
    account_id: int | None = None, card_id: int | None = None, requires_action: bool | None = None,
    current_user: User = USER, db: DbSession = DB,
):
    from .payment_planning import canonical_payment_rows

    start, end = _date_range(date_range, date_from, date_to)
    rows = canonical_payment_rows(db, current_user)
    rows = [row for row in rows if _within(row, start, end, date_range)]
    if search:
        needle = " ".join(search.lower().split())
        rows = [row for row in rows if needle in " ".join(str(row.get(key) or "").lower() for key in ("name", "payee_merchant", "provider", "category", "account_name", "card_name"))]
    if status_filter:
        requested = {part.strip() for part in status_filter.split(",") if part.strip()}
        rows = [row for row in rows if row.get("status") in requested or _status_bucket(row) in requested]
    if source:
        rows = [row for row in rows if row.get("source_type") == source]
    if category_id is not None:
        rows = [row for row in rows if row.get("category_id") == category_id]
    if payment_method:
        rows = [row for row in rows if row.get("payment_method") == payment_method]
    if payment_handling:
        rows = [row for row in rows if row.get("payment_handling") == payment_handling]
    if account_id is not None:
        rows = [row for row in rows if row.get("account_id") == account_id]
    if card_id is not None:
        rows = [row for row in rows if row.get("card_id") == card_id]
    if requires_action is not None:
        rows = [row for row in rows if bool(row.get("requires_action")) is requires_action]
    rows.sort(key=_sort_key)

    summary_cents: dict[str, int] = {
        "total_scheduled": 0, "overdue": 0, "requires_payment": 0, "expected_automatically": 0,
        "awaiting_confirmation": 0, "upcoming": 0, "paid": 0, "skipped": 0, "cancelled": 0,
    }
    counts = {key: 0 for key in summary_cents}
    for row in rows:
        amount = parse_money(row.get("actual_amount") if row.get("status") == "paid" and row.get("actual_amount") is not None else row.get("expected_amount") or row.get("amount") or "0")
        summary_cents["total_scheduled"] += abs(amount)
        counts["total_scheduled"] += 1
        bucket = _status_bucket(row)
        if bucket in summary_cents:
            summary_cents[bucket] += abs(amount)
            counts[bucket] += 1
    return {
        "date_range": {"kind": date_range, "start": start.isoformat() if start else None, "end": end.isoformat() if end else None},
        "summary": {key: {"amount": cents_to_decimal(value), "count": counts[key]} for key, value in summary_cents.items()},
        "rows": rows,
    }


@router.get("/payment-centre/{source_type}/{source_id}")
def payment_detail(source_type: str, source_id: int, current_user: User = USER, db: DbSession = DB):
    if source_type == "bill":
        return bill_detail(source_id, current_user, db)
    if source_type != "scheduled_payment":
        raise HTTPException(status_code=404, detail="Payment source not found")
    row = next((item for item in _scheduled_payment_rows(db, current_user) if int(item["id"]) == source_id), None)
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    history = db.execute(text("SELECT from_status,to_status,source,note,created_at FROM scheduled_payment_history WHERE user_id=:uid AND scheduled_payment_id=:sid ORDER BY created_at,id"), {"uid": current_user.id, "sid": source_id}).mappings().all()
    transaction = None
    if row.get("matched_transaction_id"):
        transaction = db.execute(text("SELECT id,transaction_date,amount_cents,description,merchant FROM transactions WHERE id=:id AND user_id=:uid"), {"id": row["matched_transaction_id"], "uid": current_user.id}).mappings().first()
    return {
        **row, "history": [dict(item) for item in history],
        "matched_transaction": None if transaction is None else {
            "id": transaction["id"], "date": _as_date(transaction["transaction_date"]).isoformat(),
            "amount": cents_to_decimal(abs(int(transaction["amount_cents"] or 0))),
            "description": transaction["description"], "merchant": transaction["merchant"],
        },
    }


@router.get("/payment-centre/health/check")
def payment_centre_health(current_user: User = USER, db: DbSession = DB):
    duplicate_scheduled = db.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT recurring_expense_id,COALESCE(occurrence_date,expected_date),COUNT(*) count
            FROM scheduled_payments WHERE user_id=:uid
            GROUP BY recurring_expense_id,COALESCE(occurrence_date,expected_date) HAVING count>1
        )
    """), {"uid": current_user.id}).scalar() or 0
    duplicate_bill_matches = db.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT matched_transaction_id,COUNT(*) count FROM bills
            WHERE user_id=:uid AND matched_transaction_id IS NOT NULL GROUP BY matched_transaction_id HAVING count>1
        )
    """), {"uid": current_user.id}).scalar() or 0
    return {"status": "ok" if not duplicate_scheduled and not duplicate_bill_matches else "error", "duplicate_scheduled_payments": int(duplicate_scheduled), "duplicate_bill_matches": int(duplicate_bill_matches)}
