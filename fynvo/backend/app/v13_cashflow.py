from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .finance import today_local
from .forecast import generate_forecast
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter(prefix="/api/v1.3", tags=["cash-flow-v1.3"])
DB = Depends(get_db)
USER = Depends(get_current_user)


class BufferUpdate(BaseModel):
    minimum_balance: str | None = None


class OccurrenceOverrideCreate(BaseModel):
    source_type: str = Field(pattern="^(income|recurring_expense|bill|planned_spending)$")
    source_id: int
    occurrence_date: date
    amount: str | None = None
    rescheduled_date: date | None = None
    status: str = Field(default="due", pattern="^(due|overdue|paid|skipped|rescheduled)$")
    apply_future: bool = False
    notes: str | None = None


class PurchaseSimulation(BaseModel):
    amount: str
    proposed_date: date
    account_id: int
    description: str | None = None
    horizon: str = "30d"


def _column_names(connection, table: str) -> set[str]:
    return {
        str(row["name"])
        for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()
    }


def _add_column(connection, table: str, definition: str, columns: set[str]) -> None:
    column = definition.split()[0]
    if column not in columns:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
        columns.add(column)


def run_v13_migrations(engine) -> None:
    with engine.begin() as connection:
        account_columns = _column_names(connection, "accounts")
        _add_column(connection, "accounts", "minimum_balance_cents INTEGER", account_columns)
        _add_column(connection, "accounts", "archived_at DATETIME", account_columns)

        bill_columns = _column_names(connection, "bills")
        for definition in (
            "original_status VARCHAR(80)",
            "original_amount_cents INTEGER",
            "remaining_amount_cents INTEGER",
            "pay_cycle_date DATE",
            "source_account_text VARCHAR(140)",
            "resolved_at DATETIME",
            "paid_at DATETIME",
        ):
            _add_column(connection, "bills", definition, bill_columns)

        if "amount_cents" in bill_columns:
            connection.execute(text("""
                UPDATE bills
                SET original_amount_cents=COALESCE(original_amount_cents, amount_cents),
                    remaining_amount_cents=COALESCE(remaining_amount_cents, original_amount_cents, amount_cents)
            """))
        else:
            connection.execute(text("""
                UPDATE bills
                SET remaining_amount_cents=COALESCE(remaining_amount_cents, original_amount_cents)
            """))

        planned_columns = _column_names(connection, "planned_spending")
        _add_column(connection, "planned_spending", "archived_at DATETIME", planned_columns)

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS forecast_occurrence_overrides (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                source_type VARCHAR(40) NOT NULL,
                source_id INTEGER NOT NULL,
                occurrence_date DATE NOT NULL,
                amount_cents INTEGER,
                rescheduled_date DATE,
                status VARCHAR(24) NOT NULL DEFAULT 'due',
                apply_future BOOLEAN NOT NULL DEFAULT 0,
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(user_id, source_type, source_id, occurrence_date),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_forecast_override_source ON forecast_occurrence_overrides(user_id, source_type, source_id, occurrence_date)"))
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (13)"))
        elif int(current) < 13:
            connection.execute(text("UPDATE schema_version SET version=13"))


def _account_rows(db: DbSession, user: User) -> list[dict[str, Any]]:
    rows = db.execute(text("""
        SELECT id, name, account_type, opening_balance_cents, minimum_balance_cents, archived_at
        FROM accounts
        WHERE user_id=:uid AND archived_at IS NULL
        ORDER BY name
    """), {"uid": user.id}).mappings().all()
    return [dict(row) for row in rows]


def _account_starting_balances(db: DbSession, user: User, start: date) -> dict[int, int]:
    balances = {int(row["id"]): int(row["opening_balance_cents"] or 0) for row in _account_rows(db, user)}
    rows = db.execute(text("""
        SELECT account_id, COALESCE(SUM(amount_cents), 0) AS total
        FROM transactions
        WHERE user_id=:uid AND transaction_date < :start
        GROUP BY account_id
    """), {"uid": user.id, "start": start}).mappings().all()
    for row in rows:
        balances[int(row["account_id"])] = balances.get(int(row["account_id"]), 0) + int(row["total"] or 0)
    return balances


def _overrides(db: DbSession, user: User) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text("""
        SELECT * FROM forecast_occurrence_overrides
        WHERE user_id=:uid
        ORDER BY occurrence_date, id
    """), {"uid": user.id}).mappings().all()]


def _apply_overrides(events: list[dict], overrides: list[dict]) -> list[dict]:
    exact = {(row["source_type"], int(row["source_id"]), str(row["occurrence_date"])[:10]): row for row in overrides}
    future: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in overrides:
        if bool(row.get("apply_future")):
            future[(row["source_type"], int(row["source_id"]))].append(row)
    result = []
    for event in events:
        source_id = event.get("source_id")
        if source_id is None:
            result.append(event)
            continue
        occurrence_key = str(event.get("original_due_date") or event["date"])[:10]
        key = (event.get("source_type"), int(source_id), occurrence_key)
        override = exact.get(key)
        if override is None:
            eligible = [row for row in future.get((event.get("source_type"), int(source_id)), []) if str(row["occurrence_date"])[:10] <= occurrence_key]
            override = eligible[-1] if eligible else None
        if not override:
            result.append(event)
            continue
        if override["status"] in {"paid", "skipped"}:
            continue
        updated = dict(event)
        if override.get("amount_cents") is not None:
            cents = int(override["amount_cents"])
            cents = -abs(cents) if updated["direction"] == "expense" else abs(cents)
            updated["amount_cents"] = cents
            updated["amount"] = cents_to_decimal(cents)
            updated["estimated"] = False
            updated["confidence"] = "confirmed"
            updated["explanation"] = "Occurrence override amount"
        if override.get("rescheduled_date"):
            updated["date"] = str(override["rescheduled_date"])[:10]
        updated["occurrence_status"] = override["status"]
        updated["override_id"] = override["id"]
        result.append(updated)
    return result


def _overdue_bill_events(db: DbSession, user: User, start: date) -> list[dict]:
    rows = db.execute(text("""
        SELECT id, name, remaining_amount_cents, due_date, account_id, bill_type
        FROM bills
        WHERE user_id=:uid AND is_active=1 AND paid_at IS NULL AND resolved_at IS NULL
          AND due_date IS NOT NULL AND due_date < :start AND remaining_amount_cents IS NOT NULL
        ORDER BY due_date
    """), {"uid": user.id, "start": start}).mappings().all()
    result = []
    for row in rows:
        cents = -abs(int(row["remaining_amount_cents"] or 0))
        result.append({
            "date": start.isoformat(),
            "original_due_date": str(row["due_date"])[:10],
            "name": row["name"],
            "amount_cents": cents,
            "amount": cents_to_decimal(cents),
            "direction": "expense",
            "source_type": "bill",
            "source_id": int(row["id"]),
            "category": row["bill_type"] or "Uncategorised",
            "account_id": row["account_id"],
            "confidence": "confirmed",
            "financial_layer": "committed",
            "estimated": False,
            "occurrence_status": "overdue",
            "explanation": f"Overdue since {str(row['due_date'])[:10]}; retained in forecast until resolved",
        })
    return result


def _future_transfers(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    rows = db.execute(text("""
        SELECT id, from_account_id, to_account_id, amount_cents, transaction_date, description
        FROM transfers
        WHERE user_id=:uid AND transaction_date BETWEEN :start AND :end
        ORDER BY transaction_date, id
    """), {"uid": user.id, "start": start, "end": end}).mappings().all()
    return [{
        "date": str(row["transaction_date"])[:10],
        "name": row["description"],
        "amount_cents": 0,
        "amount": "0.00",
        "transfer_amount_cents": int(row["amount_cents"]),
        "direction": "transfer",
        "source_type": "transfer",
        "source_id": int(row["id"]),
        "from_account_id": int(row["from_account_id"]),
        "to_account_id": int(row["to_account_id"]),
        "confidence": "confirmed",
        "financial_layer": "committed",
        "estimated": False,
        "explanation": "Internal transfer; household net cash-flow effect is zero",
    } for row in rows]


def _recalculate(events: list[dict], starting_balance: int, account_balances: dict[int, int]) -> tuple[list[dict], dict[str, Any], int, dict[int, int]]:
    balance = starting_balance
    by_account = dict(account_balances)
    timeline = []
    lowest = {"date": None, "balance_cents": balance, "balance": cents_to_decimal(balance)}
    for event in sorted(events, key=lambda row: (row["date"], 0 if row["direction"] == "income" else 1, row["name"])):
        row = dict(event)
        if row["direction"] == "transfer":
            amount = int(row.get("transfer_amount_cents") or 0)
            by_account[int(row["from_account_id"])] = by_account.get(int(row["from_account_id"]), 0) - amount
            by_account[int(row["to_account_id"])] = by_account.get(int(row["to_account_id"]), 0) + amount
        else:
            delta = int(row["amount_cents"])
            balance += delta
            if row.get("account_id") is not None:
                account_id = int(row["account_id"])
                by_account[account_id] = by_account.get(account_id, 0) + delta
        row["forecast_balance_cents"] = balance
        row["forecast_balance"] = cents_to_decimal(balance)
        row["account_balances"] = {str(k): cents_to_decimal(v) for k, v in by_account.items()}
        timeline.append(row)
        if balance < lowest["balance_cents"]:
            lowest = {"date": row["date"], "balance_cents": balance, "balance": cents_to_decimal(balance), "source": row["name"]}
    return timeline, lowest, balance, by_account


def cashflow_projection(db: DbSession, user: User, horizon: str = "30d", mode: str = "expected", start: date | None = None) -> dict:
    base = generate_forecast(db, user, horizon, mode, start)
    start_date = date.fromisoformat(base["start_date"])
    end_date = date.fromisoformat(base["end_date"])
    account_balances = _account_starting_balances(db, user, start_date)
    events = [row for row in base["events"] if row.get("source_type") != "transfer"]
    existing_bill_ids = {int(row["source_id"]) for row in events if row.get("source_type") == "bill" and row.get("source_id") is not None}
    events += [row for row in _overdue_bill_events(db, user, start_date) if int(row["source_id"]) not in existing_bill_ids]
    events += _future_transfers(db, user, start_date, end_date)
    events = _apply_overrides(events, _overrides(db, user))
    timeline, lowest, final_balance, final_balances = _recalculate(events, sum(account_balances.values()), account_balances)

    accounts = _account_rows(db, user)
    warnings = []
    for account in accounts:
        account_id = int(account["id"])
        buffer_cents = account.get("minimum_balance_cents")
        running = account_balances.get(account_id, 0)
        first_buffer = None
        first_negative = None
        for event in timeline:
            if event["direction"] == "transfer":
                amount = int(event.get("transfer_amount_cents") or 0)
                if int(event["from_account_id"]) == account_id:
                    running -= amount
                if int(event["to_account_id"]) == account_id:
                    running += amount
            elif event.get("account_id") is not None and int(event["account_id"]) == account_id:
                running += int(event["amount_cents"])
            if buffer_cents is not None and running < int(buffer_cents) and first_buffer is None:
                first_buffer = (event, running)
            if running < 0 and first_negative is None:
                first_negative = (event, running)
        if first_buffer:
            event, running = first_buffer
            warnings.append({"kind": "low_balance", "account_id": account_id, "account_name": account["name"], "date": event["date"], "projected_balance": cents_to_decimal(running), "safety_buffer": cents_to_decimal(buffer_cents), "shortfall": cents_to_decimal(int(buffer_cents) - running), "cause": event["name"]})
        if first_negative:
            event, running = first_negative
            warnings.append({"kind": "negative_balance", "account_id": account_id, "account_name": account["name"], "date": event["date"], "projected_balance": cents_to_decimal(running), "required_to_avoid": cents_to_decimal(abs(running)), "cause": event["name"]})

    income = sum(int(row["amount_cents"]) for row in timeline if row["direction"] == "income")
    expenses = -sum(int(row["amount_cents"]) for row in timeline if row["direction"] == "expense")
    return {
        **base,
        "starting_balance": cents_to_decimal(sum(account_balances.values())),
        "final_balance": cents_to_decimal(final_balance),
        "net_movement": cents_to_decimal(final_balance - sum(account_balances.values())),
        "income_total": cents_to_decimal(income),
        "expense_total": cents_to_decimal(expenses),
        "lowest_balance": lowest,
        "events": timeline,
        "account_starting_balances": {str(k): cents_to_decimal(v) for k, v in account_balances.items()},
        "account_final_balances": {str(k): cents_to_decimal(v) for k, v in final_balances.items()},
        "warnings": warnings,
        "chart_points": [{"date": start_date.isoformat(), "balance": cents_to_decimal(sum(account_balances.values())), "kind": "actual"}] + [{"date": row["date"], "balance": row["forecast_balance"], "kind": "forecast", "contributors": [row["name"]]} for row in timeline],
        "explanations": list(base.get("explanations", [])) + ["Internal transfers update individual account projections but have zero household net effect.", "Unresolved overdue bills remain in the forecast until paid, skipped or rescheduled."],
    }


@router.get("/cash-flow")
def get_cashflow(horizon: str = "30d", mode: str = "expected", start: date | None = None, current_user: User = USER, db: DbSession = DB):
    return cashflow_projection(db, current_user, horizon, mode, start)


@router.get("/upcoming")
def upcoming(horizon: str = "30d", current_user: User = USER, db: DbSession = DB):
    projection = cashflow_projection(db, current_user, horizon, "expected")
    today = today_local()
    groups: dict[str, list[dict]] = {"Overdue": [], "Today": [], "Tomorrow": [], "Next 7 Days": [], "Later This Month": [], "Future": []}
    for row in projection["events"]:
        event_date = date.fromisoformat(row["date"])
        if row.get("occurrence_status") == "overdue" or row.get("original_due_date"):
            group = "Overdue"
        elif event_date == today:
            group = "Today"
        elif event_date == today + timedelta(days=1):
            group = "Tomorrow"
        elif event_date <= today + timedelta(days=7):
            group = "Next 7 Days"
        elif event_date.year == today.year and event_date.month == today.month:
            group = "Later This Month"
        else:
            group = "Future"
        groups[group].append(row)
    return {"groups": [{"name": name, "items": items, "income": cents_to_decimal(sum(int(x["amount_cents"]) for x in items if x["direction"] == "income")), "expenses": cents_to_decimal(-sum(int(x["amount_cents"]) for x in items if x["direction"] == "expense"))} for name, items in groups.items()]}


@router.get("/calendar")
def calendar_view(start: date | None = None, days: int = 31, current_user: User = USER, db: DbSession = DB):
    start = start or today_local()
    days = max(1, min(days, 366))
    projection = cashflow_projection(db, current_user, f"{days}d", "expected", start)
    groups: dict[str, dict[str, Any]] = {}
    for row in projection["events"]:
        group = groups.setdefault(row["date"], {"date": row["date"], "income_cents": 0, "expense_cents": 0, "items": []})
        if row["direction"] == "income":
            group["income_cents"] += int(row["amount_cents"])
        elif row["direction"] == "expense":
            group["expense_cents"] += -int(row["amount_cents"])
        group["items"].append(row)
    return {"start_date": start.isoformat(), "days": [{**group, "income": cents_to_decimal(group["income_cents"]), "expenses": cents_to_decimal(group["expense_cents"]), "net": cents_to_decimal(group["income_cents"] - group["expense_cents"])} for group in groups.values()]}


@router.put("/accounts/{account_id}/buffer")
def update_buffer(account_id: int, payload: BufferUpdate, current_user: User = USER, db: DbSession = DB):
    found = db.execute(text("SELECT id FROM accounts WHERE id=:id AND user_id=:uid"), {"id": account_id, "uid": current_user.id}).scalar()
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    cents = None if payload.minimum_balance in (None, "") else parse_money(payload.minimum_balance)
    db.execute(text("UPDATE accounts SET minimum_balance_cents=:amount, updated_at=:now WHERE id=:id AND user_id=:uid"), {"amount": cents, "now": utcnow(), "id": account_id, "uid": current_user.id})
    db.commit()
    return {"account_id": account_id, "minimum_balance": None if cents is None else cents_to_decimal(cents)}


@router.post("/occurrence-overrides", status_code=status.HTTP_201_CREATED)
def create_override(payload: OccurrenceOverrideCreate, current_user: User = USER, db: DbSession = DB):
    now = utcnow()
    amount_cents = None if payload.amount in (None, "") else parse_money(payload.amount)
    db.execute(text("""
        INSERT INTO forecast_occurrence_overrides(user_id, source_type, source_id, occurrence_date, amount_cents, rescheduled_date, status, apply_future, notes, created_at, updated_at)
        VALUES (:uid,:source_type,:source_id,:occurrence_date,:amount,:rescheduled,:status,:apply_future,:notes,:now,:now)
        ON CONFLICT(user_id, source_type, source_id, occurrence_date) DO UPDATE SET
          amount_cents=excluded.amount_cents, rescheduled_date=excluded.rescheduled_date, status=excluded.status,
          apply_future=excluded.apply_future, notes=excluded.notes, updated_at=excluded.updated_at
    """), {"uid": current_user.id, "source_type": payload.source_type, "source_id": payload.source_id, "occurrence_date": payload.occurrence_date, "amount": amount_cents, "rescheduled": payload.rescheduled_date, "status": payload.status, "apply_future": payload.apply_future, "notes": payload.notes, "now": now})
    db.commit()
    return {"status": "ok", "isolated_occurrence": not payload.apply_future}


@router.post("/purchase-simulator")
def purchase_simulator(payload: PurchaseSimulation, current_user: User = USER, db: DbSession = DB):
    projection = cashflow_projection(db, current_user, payload.horizon, "expected", payload.proposed_date)
    account_balances = {int(k): parse_money(v) for k, v in projection["account_starting_balances"].items()}
    if payload.account_id not in account_balances:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    amount = parse_money(payload.amount)
    balance_before = account_balances[payload.account_id]
    for row in projection["events"]:
        if row["date"] > payload.proposed_date.isoformat():
            break
        if row["direction"] == "transfer":
            transfer_amount = int(row.get("transfer_amount_cents") or 0)
            if int(row["from_account_id"]) == payload.account_id:
                balance_before -= transfer_amount
            if int(row["to_account_id"]) == payload.account_id:
                balance_before += transfer_amount
        elif row.get("account_id") is not None and int(row["account_id"]) == payload.account_id:
            balance_before += int(row["amount_cents"])
    after = balance_before - amount
    lowest = after
    running = after
    for row in projection["events"]:
        if row["date"] <= payload.proposed_date.isoformat():
            continue
        if row["direction"] == "transfer":
            transfer_amount = int(row.get("transfer_amount_cents") or 0)
            if int(row["from_account_id"]) == payload.account_id:
                running -= transfer_amount
            if int(row["to_account_id"]) == payload.account_id:
                running += transfer_amount
        elif row.get("account_id") is not None and int(row["account_id"]) == payload.account_id:
            running += int(row["amount_cents"])
        lowest = min(lowest, running)
    account = next(row for row in _account_rows(db, current_user) if int(row["id"]) == payload.account_id)
    buffer_cents = account.get("minimum_balance_cents")
    return {"description": payload.description, "balance_before": cents_to_decimal(balance_before), "projected_balance_after": cents_to_decimal(after), "lowest_projected_balance_afterwards": cents_to_decimal(lowest), "safety_buffer": None if buffer_cents is None else cents_to_decimal(buffer_cents), "buffer_breached": buffer_cents is not None and lowest < int(buffer_cents), "negative_balance_predicted": lowest < 0, "isolated": True}
