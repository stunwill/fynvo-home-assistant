from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import payments_v17, v111
from .auth import get_current_user
from .database import get_db
from .models import User
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)

EDITABLE_STATUSES = {
    "upcoming",
    "due",
    "due_today",
    "overdue",
    "expected_automatically",
    "auto_payment_unconfirmed",
    "unknown",
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
    """Add durable Scheduled Payment occurrence identity and override metadata."""
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

        connection.execute(text("""
            UPDATE scheduled_payments
            SET occurrence_date=expected_date
            WHERE occurrence_date IS NULL
        """))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduled_payment_occurrence_unique ON scheduled_payments(user_id,recurring_expense_id,occurrence_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scheduled_payment_effective_date ON scheduled_payments(user_id,expected_date,status)"))

        history_columns = _columns(connection, "scheduled_payment_history")
        for definition in (
            "previous_expected_date DATE",
            "new_expected_date DATE",
            "reason VARCHAR(120)",
        ):
            _add_column(connection, "scheduled_payment_history", definition, history_columns)

        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (14)"))
        elif int(current) < 14:
            connection.execute(text("UPDATE schema_version SET version=14"))


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
    current = int(row.get("version") or 1)
    if version is not None and int(version) != current:
        raise HTTPException(status_code=409, detail="This payment changed since it was opened. Refresh and try again")


def _history_note(old_date: date, new_date: date, reason: str | None, note: str | None) -> str:
    text_value = f"Payment date changed from {old_date.isoformat()} to {new_date.isoformat()}."
    if reason:
        text_value += f" Reason: {reason}."
    if note:
        text_value += f" {note.strip()}"
    return text_value


def _mutate_expected_date(
    db: DbSession,
    user: User,
    row: dict[str, Any],
    new_date: date,
    reason: str | None,
    note: str | None,
    restoring: bool = False,
) -> dict[str, Any]:
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
    next_version = int(row.get("version") or 1) + 1
    db.execute(text("""
        UPDATE scheduled_payments
        SET occurrence_date=:occurrence_date,
            expected_date=:expected_date,
            status=:status,
            override_reason=:reason,
            override_note=:note,
            override_at=:override_at,
            override_by_user_id=:override_by,
            version=:version,
            updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {
        "occurrence_date": occurrence_date,
        "expected_date": new_date,
        "status": status_name,
        "reason": None if restoring else reason,
        "note": None if restoring else note,
        "override_at": None if restoring else now,
        "override_by": None if restoring else user.id,
        "version": next_version,
        "now": now,
        "id": row["id"],
        "uid": user.id,
    })
    db.execute(text("""
        INSERT INTO scheduled_payment_history(
            user_id,scheduled_payment_id,from_status,to_status,source,note,
            previous_expected_date,new_expected_date,reason,created_at
        ) VALUES(
            :uid,:sid,:from_status,:to_status,'ui',:note,
            :previous_date,:new_date,:reason,:now
        )
    """), {
        "uid": user.id,
        "sid": row["id"],
        "from_status": row.get("status"),
        "to_status": status_name,
        "note": _history_note(old_date, new_date, "Restored original date" if restoring else reason, note),
        "previous_date": old_date,
        "new_date": new_date,
        "reason": "Restored original date" if restoring else reason,
        "now": now,
    })
    db.commit()
    return _payment_row(db, user, int(row["id"]))


@router.post("/scheduled-payments/{payment_id}/reschedule")
def reschedule_scheduled_payment(
    payment_id: int,
    payload: ScheduledPaymentReschedulePayload,
    current_user: User = USER,
    db: DbSession = DB,
):
    row = _payment_row(db, current_user, payment_id)
    _validate_editable(row)
    _assert_version(row, payload.version)
    return _mutate_expected_date(db, current_user, row, payload.expected_date, payload.reason, payload.note)


@router.post("/scheduled-payments/{payment_id}/restore-original-date")
def restore_scheduled_payment_date(
    payment_id: int,
    payload: ScheduledPaymentRestorePayload,
    current_user: User = USER,
    db: DbSession = DB,
):
    row = _payment_row(db, current_user, payment_id)
    _validate_editable(row)
    _assert_version(row, payload.version)
    occurrence_date = v111._as_date(row.get("occurrence_date") or row["expected_date"])
    return _mutate_expected_date(db, current_user, row, occurrence_date, None, payload.note, restoring=True)
