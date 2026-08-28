from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import payments_v17, payments_v114, v111
from .auth import get_current_user
from .database import get_db
from .models import User
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)

PENDING_STATUSES = {
    "upcoming", "due", "due_today", "overdue", "expected_automatically",
    "auto_payment_unconfirmed", "unknown",
}
SKIP_REASONS = {
    "Not required this time", "Payment paused", "Provider waived payment",
    "Already handled elsewhere", "User requested skip", "Other",
}


class SkipPaymentPayload(BaseModel):
    reason: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    version: int | None = None


class RestorePaymentPayload(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    version: int | None = None


def ensure_v115_schema(engine) -> None:
    with engine.begin() as connection:
        columns = payments_v114._columns(connection, "scheduled_payments")
        for definition in (
            "skip_reason VARCHAR(120)", "skip_note TEXT", "skipped_at DATETIME",
            "skipped_by_user_id INTEGER REFERENCES users(id)",
        ):
            payments_v114._add_column(connection, "scheduled_payments", definition, columns)


def _row(db: DbSession, user: User, payment_id: int) -> dict[str, Any]:
    return payments_v114._payment_row(db, user, payment_id)


def _assert_unmatched(row: dict[str, Any]) -> None:
    if row.get("matched_transaction_id") is not None:
        raise HTTPException(status_code=409, detail="Unmatch the Transaction before changing this payment")


def _calculated_status(row: dict[str, Any]) -> str:
    handling = row.get("payment_handling") or payments_v17.default_payment_handling(row.get("payment_method"))
    grace = int(row.get("auto_payment_grace_days") or payments_v17.DEFAULT_GRACE_DAYS)
    return payments_v17._status_for(v111._as_date(row["expected_date"]), handling, grace, date.today())


def _history(db: DbSession, user: User, payment_id: int, from_status: str, to_status: str, note: str | None, reason: str | None = None) -> None:
    db.execute(text("""
        INSERT INTO scheduled_payment_history(
            user_id,scheduled_payment_id,from_status,to_status,source,note,reason,created_at
        ) VALUES(:uid,:sid,:from_status,:to_status,'ui',:note,:reason,:now)
    """), {"uid": user.id, "sid": payment_id, "from_status": from_status, "to_status": to_status,
            "note": note, "reason": reason, "now": utcnow()})


def _normalise_reason(reason: str | None) -> str | None:
    value = reason.strip() if reason else None
    if value and value not in SKIP_REASONS:
        raise HTTPException(status_code=400, detail="Choose a valid skip reason")
    return value


@router.post("/scheduled-payments/{payment_id}/skip")
def skip_payment(payment_id: int, payload: SkipPaymentPayload, current_user: User = USER, db: DbSession = DB):
    row = _row(db, current_user, payment_id)
    payments_v114._assert_version(row, payload.version)
    _assert_unmatched(row)
    if row["status"] == "skipped":
        return payments_v17._scheduled_response(row)
    if row["status"] not in PENDING_STATUSES:
        raise HTTPException(status_code=409, detail="Only unresolved Scheduled Payments can be skipped")
    reason = _normalise_reason(payload.reason)
    now = utcnow()
    version = int(row.get("version") or 1)
    result = db.execute(text("""
        UPDATE scheduled_payments
        SET status='skipped',skip_reason=:reason,skip_note=:note,skipped_at=:now,
            skipped_by_user_id=:uid,version=version+1,updated_at=:now
        WHERE id=:id AND user_id=:uid AND version=:version
    """), {"reason": reason, "note": payload.note, "now": now, "uid": current_user.id,
            "id": payment_id, "version": version})
    if not result.rowcount:
        db.rollback()
        raise HTTPException(status_code=409, detail="This payment changed since it was opened. Refresh and try again")
    _history(db, current_user, payment_id, row["status"], "skipped", payload.note or "Payment skipped", reason)
    db.commit()
    return payments_v17._scheduled_response(_row(db, current_user, payment_id))


@router.post("/scheduled-payments/{payment_id}/restore")
def restore_payment(payment_id: int, payload: RestorePaymentPayload, current_user: User = USER, db: DbSession = DB):
    row = _row(db, current_user, payment_id)
    payments_v114._assert_version(row, payload.version)
    _assert_unmatched(row)
    if row["status"] != "skipped":
        raise HTTPException(status_code=409, detail="Only skipped Scheduled Payments can be restored")
    status_name = _calculated_status(row)
    now = utcnow()
    version = int(row.get("version") or 1)
    result = db.execute(text("""
        UPDATE scheduled_payments SET status=:status,version=version+1,updated_at=:now
        WHERE id=:id AND user_id=:uid AND version=:version AND status='skipped'
    """), {"status": status_name, "now": now, "id": payment_id, "uid": current_user.id, "version": version})
    if not result.rowcount:
        db.rollback()
        raise HTTPException(status_code=409, detail="This payment changed since it was opened. Refresh and try again")
    _history(db, current_user, payment_id, "skipped", status_name, payload.note or "Skipped payment restored", row.get("skip_reason"))
    db.commit()
    return payments_v17._scheduled_response(_row(db, current_user, payment_id))
