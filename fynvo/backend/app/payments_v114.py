from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import finance, forecast, payments_v17, v111
from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)
_schedule_lock = Lock()

EDITABLE_STATUSES = {
    "upcoming", "due", "due_today", "overdue", "expected_automatically",
    "auto_payment_unconfirmed", "unknown",
}


class ScheduledPaymentReschedulePayload(BaseModel):
    expected_date: date
    reason: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    version: int | None = None


class ScheduledPaymentRestorePayload(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    version: int | None = None


def _columns(connection, table: str) -> set[str]:
    return {str(row["name"]) for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()}


def _add_column(connection, table: str, definition: str, columns: set[str]) -> None:
    column = definition.split()[0]
    if column not in columns:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
        columns.add(column)


def ensure_v114_schema(engine) -> None:
    with engine.begin() as connection:
        columns = _columns(connection, "scheduled_payments")
        for definition in (
            "occurrence_date DATE",
            "override_reason VARCHAR(120)",
            "override_note TEXT",
            "override_at DATETIME",
            "override_by_user_id INTEGER REFERENCES users(id)",
            "version INTEGER NOT NULL DEFAULT 1",
        ):
            _add_column(connection, "scheduled_payments", definition, columns)
        connection.execute(text("UPDATE scheduled_payments SET occurrence_date=expected_date WHERE occurrence_date IS NULL"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduled_payment_occurrence_unique ON scheduled_payments(user_id,recurring_expense_id,occurrence_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scheduled_payment_effective_date ON scheduled_payments(user_id,expected_date,status)"))

        history_columns = _columns(connection, "scheduled_payment_history")
        for definition in ("previous_expected_date DATE", "new_expected_date DATE", "reason VARCHAR(120)"):
            _add_column(connection, "scheduled_payment_history", definition, history_columns)

        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (14)"))
        elif int(current) < 14:
            connection.execute(text("UPDATE schema_version SET version=14"))


def _schedule_key(recurring_expense_id: int, occurrence_date: Any) -> tuple[int, str]:
    return int(recurring_expense_id), v111._as_date(occurrence_date).isoformat()


def ensure_scheduled_payments(db: DbSession, user: User, horizon_days: int = 120, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    end = today + timedelta(days=horizon_days)
    stats = {"rules": 0, "occurrences": 0, "inserted": 0, "updated": 0, "history": 0}
    with _schedule_lock:
        rules = db.execute(text("""
            SELECT r.*,c.account_id AS card_account_id
            FROM recurring_expenses r
            LEFT JOIN cards c ON c.id=r.card_id AND c.user_id=r.user_id
            WHERE r.user_id=:uid AND r.is_active=1 AND r.next_due_date IS NOT NULL
        """), {"uid": user.id}).mappings().all()
        stats["rules"] = len(rules)
        if not rules:
            return stats
        ids = ",".join(str(int(row["id"])) for row in rules)
        existing_rows = db.execute(text(f"""
            SELECT id,recurring_expense_id,COALESCE(occurrence_date,expected_date) AS occurrence_date,
                   expected_date,status,expected_amount_cents,payment_method,payment_handling,account_id,card_id
            FROM scheduled_payments WHERE user_id=:uid AND recurring_expense_id IN ({ids})
        """), {"uid": user.id}).mappings().all()
        existing = {_schedule_key(row["recurring_expense_id"], row["occurrence_date"]): row for row in existing_rows}
        now = utcnow()
        dirty = False
        for rule in rules:
            occurrence = v111._as_date(rule["next_due_date"])
            method = rule["payment_method"] or ("direct_debit" if rule["direct_debit"] else "not_set")
            handling = rule.get("payment_handling") or payments_v17.default_payment_handling(method)
            grace = int(rule.get("auto_payment_grace_days") or payments_v17.DEFAULT_GRACE_DAYS)
            account_id = int(rule["card_account_id"]) if method == "automatic_card_payment" and rule.get("card_account_id") else rule["account_id"]
            end_date = v111._as_date(rule["end_date"]) if rule.get("end_date") else None
            generated = 0
            while occurrence <= end and generated < 400:
                if end_date and occurrence > end_date:
                    break
                stats["occurrences"] += 1
                key = _schedule_key(rule["id"], occurrence)
                current = existing.get(key)
                if current:
                    effective = v111._as_date(current["expected_date"])
                    status_name = payments_v17._status_for(effective, handling, grace, today)
                    if current["status"] not in payments_v17.TERMINAL_STATUSES:
                        status_changed = current["status"] != status_name
                        values_changed = any((
                            current["expected_amount_cents"] != rule["amount_cents"],
                            current["payment_method"] != method,
                            current["payment_handling"] != handling,
                            current["account_id"] != account_id,
                            current["card_id"] != rule["card_id"],
                        ))
                        if status_changed or values_changed:
                            updated = db.execute(text("""
                                UPDATE scheduled_payments SET expected_amount_cents=:amount,payment_method=:method,
                                    payment_handling=:handling,account_id=:account_id,card_id=:card_id,
                                    status=:status,updated_at=:now
                                WHERE id=:id AND user_id=:uid AND status=:from_status
                            """), {
                                "amount": rule["amount_cents"], "method": method, "handling": handling,
                                "account_id": account_id, "card_id": rule["card_id"], "status": status_name,
                                "now": now, "id": current["id"], "uid": user.id, "from_status": current["status"],
                            })
                            if updated.rowcount:
                                dirty = True
                                stats["updated"] += 1
                                if status_changed:
                                    db.execute(text("""
                                        INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,created_at)
                                        VALUES(:uid,:sid,:from_status,:to_status,'system',:now)
                                    """), {"uid": user.id, "sid": current["id"], "from_status": current["status"], "to_status": status_name, "now": now})
                                    stats["history"] += 1
                else:
                    status_name = payments_v17._status_for(occurrence, handling, grace, today)
                    inserted = db.execute(text("""
                        INSERT OR IGNORE INTO scheduled_payments(
                            user_id,recurring_expense_id,occurrence_date,expected_date,expected_amount_cents,status,
                            payment_method,payment_handling,account_id,card_id,created_at,updated_at,version
                        ) VALUES(:uid,:rid,:occurrence,:expected,:amount,:status,:method,:handling,:account_id,:card_id,:now,:now,1)
                    """), {
                        "uid": user.id, "rid": rule["id"], "occurrence": occurrence, "expected": occurrence,
                        "amount": rule["amount_cents"], "status": status_name, "method": method,
                        "handling": handling, "account_id": account_id, "card_id": rule["card_id"], "now": now,
                    })
                    if inserted.rowcount:
                        payment_id = db.execute(text("""
                            SELECT id FROM scheduled_payments
                            WHERE user_id=:uid AND recurring_expense_id=:rid AND occurrence_date=:occurrence
                        """), {"uid": user.id, "rid": rule["id"], "occurrence": occurrence}).scalar_one()
                        db.execute(text("""
                            INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,created_at)
                            VALUES(:uid,:sid,NULL,:status,'system',:now)
                        """), {"uid": user.id, "sid": payment_id, "status": status_name, "now": now})
                        existing[key] = {
                            "id": payment_id, "recurring_expense_id": rule["id"], "occurrence_date": occurrence,
                            "expected_date": occurrence, "status": status_name, "expected_amount_cents": rule["amount_cents"],
                            "payment_method": method, "payment_handling": handling, "account_id": account_id, "card_id": rule["card_id"],
                        }
                        dirty = True
                        stats["inserted"] += 1
                        stats["history"] += 1
                generated += 1
                next_occurrence = payments_v17._next_occurrence(occurrence, rule["frequency"], rule["interval_count"])
                if next_occurrence is None or next_occurrence <= occurrence:
                    break
                occurrence = next_occurrence
        if dirty:
            db.commit()
        return stats


def _payment_row(db: DbSession, user: User, payment_id: int) -> dict[str, Any]:
    row = db.execute(text("""
        SELECT sp.*,r.name,r.frequency,r.interval_count,r.auto_payment_grace_days
        FROM scheduled_payments sp
        JOIN recurring_expenses r ON r.id=sp.recurring_expense_id AND r.user_id=sp.user_id
        WHERE sp.id=:id AND sp.user_id=:uid
    """), {"id": payment_id, "uid": user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    return dict(row)


def _validate_editable(row: dict[str, Any]) -> None:
    if row.get("matched_transaction_id") is not None:
        raise HTTPException(status_code=409, detail="Unmatch the Transaction before changing this payment date")
    if row.get("status") not in EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Completed payments cannot have their expected date changed")


def _assert_version(row: dict[str, Any], version: int | None) -> None:
    if version is not None and int(version) != int(row.get("version") or 1):
        raise HTTPException(status_code=409, detail="This payment changed since it was opened. Refresh and try again")


def _history_note(old_date: date, new_date: date, reason: str | None, note: str | None) -> str:
    value = f"Payment date changed from {old_date.isoformat()} to {new_date.isoformat()}."
    if reason:
        value += f" Reason: {reason}."
    if note:
        value += f" {note.strip()}"
    return value


def _mutate_expected_date(db: DbSession, user: User, row: dict[str, Any], new_date: date, reason: str | None, note: str | None, restoring: bool = False) -> dict[str, Any]:
    old_date = v111._as_date(row["expected_date"])
    occurrence_date = v111._as_date(row.get("occurrence_date") or row["expected_date"])
    if new_date == old_date:
        return row
    duplicate = db.execute(text("""
        SELECT id FROM scheduled_payments
        WHERE user_id=:uid AND recurring_expense_id=:rid AND expected_date=:expected AND id<>:id
    """), {"uid": user.id, "rid": row["recurring_expense_id"], "expected": new_date, "id": row["id"]}).scalar()
    if duplicate:
        raise HTTPException(status_code=409, detail="Another payment in this recurring series already uses that date")
    handling = row.get("payment_handling") or payments_v17.default_payment_handling(row.get("payment_method"))
    grace = int(row.get("auto_payment_grace_days") or payments_v17.DEFAULT_GRACE_DAYS)
    status_name = payments_v17._status_for(new_date, handling, grace, date.today())
    now = utcnow()
    current_version = int(row.get("version") or 1)
    updated = db.execute(text("""
        UPDATE scheduled_payments SET occurrence_date=:occurrence_date,expected_date=:expected_date,status=:status,
            override_reason=:reason,override_note=:override_note,override_at=:override_at,
            override_by_user_id=:override_by,version=version+1,updated_at=:now
        WHERE id=:id AND user_id=:uid AND version=:version
    """), {
        "occurrence_date": occurrence_date, "expected_date": new_date, "status": status_name,
        "reason": None if restoring else reason, "override_note": None if restoring else note,
        "override_at": None if restoring else now, "override_by": None if restoring else user.id,
        "now": now, "id": row["id"], "uid": user.id, "version": current_version,
    })
    if not updated.rowcount:
        db.rollback()
        raise HTTPException(status_code=409, detail="This payment changed since it was opened. Refresh and try again")
    history_reason = "Restored original date" if restoring else reason
    db.execute(text("""
        INSERT INTO scheduled_payment_history(
            user_id,scheduled_payment_id,from_status,to_status,source,note,
            previous_expected_date,new_expected_date,reason,created_at
        ) VALUES(:uid,:sid,:from_status,:to_status,'ui',:note,:previous_date,:new_date,:reason,:now)
    """), {
        "uid": user.id, "sid": row["id"], "from_status": row.get("status"), "to_status": status_name,
        "note": _history_note(old_date, new_date, history_reason, note), "previous_date": old_date,
        "new_date": new_date, "reason": history_reason, "now": now,
    })
    db.commit()
    return _payment_row(db, user, int(row["id"]))


@router.post("/scheduled-payments/{payment_id}/reschedule")
def reschedule_scheduled_payment(payment_id: int, payload: ScheduledPaymentReschedulePayload, current_user: User = USER, db: DbSession = DB):
    row = _payment_row(db, current_user, payment_id)
    _validate_editable(row)
    _assert_version(row, payload.version)
    return _mutate_expected_date(db, current_user, row, payload.expected_date, payload.reason, payload.note)


@router.post("/scheduled-payments/{payment_id}/restore-original-date")
def restore_scheduled_payment_date(payment_id: int, payload: ScheduledPaymentRestorePayload, current_user: User = USER, db: DbSession = DB):
    row = _payment_row(db, current_user, payment_id)
    _validate_editable(row)
    _assert_version(row, payload.version)
    occurrence_date = v111._as_date(row.get("occurrence_date") or row["expected_date"])
    return _mutate_expected_date(db, current_user, row, occurrence_date, None, payload.note, restoring=True)


def scheduled_occurrence_events(db: DbSession, user: User, start: date, end: date) -> list[dict[str, Any]]:
    horizon = max(120, (end - date.today()).days + 7)
    ensure_scheduled_payments(db, user, horizon_days=horizon)
    rows = db.execute(text("""
        SELECT sp.id AS scheduled_payment_id,sp.recurring_expense_id,sp.expected_date,sp.expected_amount_cents,
               sp.status,r.name,r.category,r.expense_type,r.source_account_text,r.account_id
        FROM scheduled_payments sp JOIN recurring_expenses r ON r.id=sp.recurring_expense_id AND r.user_id=sp.user_id
        WHERE sp.user_id=:uid AND sp.expected_date BETWEEN :start AND :end
          AND sp.status NOT IN ('skipped','cancelled')
        ORDER BY sp.expected_date,sp.id
    """), {"uid": user.id, "start": start, "end": end}).mappings().all()
    return [{
        "date": v111._as_date(row["expected_date"]).isoformat(), "name": row["name"],
        "amount_cents": int(row["expected_amount_cents"] or 0), "amount": cents_to_decimal(int(row["expected_amount_cents"] or 0)),
        "kind": "recurring_expense", "category": row["category"] or "Miscellaneous",
        "provider": row["expense_type"], "account": row["source_account_text"], "source": "recurring_expense",
        "source_id": int(row["recurring_expense_id"]), "scheduled_payment_id": int(row["scheduled_payment_id"]),
        "status": row["status"],
    } for row in rows]


def wrap_schedule_events(original: Callable) -> Callable:
    def occurrence_aware(db: DbSession, user: User, start: date, end: date) -> list[dict[str, Any]]:
        original_rows = original(db, user, start, end)
        other_rows = [row for row in original_rows if row.get("kind") != "recurring_expense"]
        return sorted(other_rows + scheduled_occurrence_events(db, user, start, end), key=lambda item: (item["date"], item["kind"], item["name"]))
    occurrence_aware._v114_occurrence_aware = True
    return occurrence_aware


def wrap_forecast_recurring_events(original: Callable) -> Callable:
    def occurrence_aware(db: DbSession, user: User, start: date, end: date, scenario: dict | None = None) -> list[dict[str, Any]]:
        base = original(db, user, start, end, scenario)
        income = [row for row in base if row.get("source_type") != "recurring_expense"]
        scenario = scenario or {}
        removed = set(scenario.get("remove_recurring_ids", []))
        scheduled = [row for row in scheduled_occurrence_events(db, user, start, end) if row["source_id"] not in removed]
        recurring = [{
            "date": row["date"], "name": row["name"], "amount_cents": -abs(int(row["amount_cents"])),
            "amount": cents_to_decimal(-abs(int(row["amount_cents"]))), "direction": "expense",
            "source_type": "recurring_expense", "source_id": row["source_id"], "category": row["category"],
            "account_id": None, "confidence": "confirmed", "financial_layer": "committed", "estimated": False,
            "explanation": "Scheduled recurring payment; effective occurrence date",
            "scheduled_payment_id": row["scheduled_payment_id"],
        } for row in scheduled]
        return income + recurring
    occurrence_aware._v114_occurrence_aware = True
    return occurrence_aware


# Install the v1.14 occurrence model over existing call sites without replacing
# the proven v1.11 reconciliation endpoints or recurrence calculations.
v111.ensure_scheduled_payments = ensure_scheduled_payments
payments_v17.ensure_scheduled_payments = ensure_scheduled_payments
if not getattr(finance.schedule_events, "_v114_occurrence_aware", False):
    finance.schedule_events = wrap_schedule_events(finance.schedule_events)
if not getattr(forecast._recurring_events, "_v114_occurrence_aware", False):
    forecast._recurring_events = wrap_forecast_recurring_events(forecast._recurring_events)
