from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import payments_v17, payments_v112, payments_v114, v111
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


def _response(row: Any) -> dict[str, Any]:
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    result = payments_v17._scheduled_response(data)
    result.update({
        "skip_reason": data.get("skip_reason"),
        "skip_note": data.get("skip_note"),
        "skipped_at": data.get("skipped_at"),
    })
    return result


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
    _assert_unmatched(row)
    if row["status"] == "skipped":
        return _response(row)
    payments_v114._assert_version(row, payload.version)
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
    return _response(_row(db, current_user, payment_id))


@router.post("/scheduled-payments/{payment_id}/restore")
def restore_payment(payment_id: int, payload: RestorePaymentPayload, current_user: User = USER, db: DbSession = DB):
    row = _row(db, current_user, payment_id)
    payments_v114._assert_version(row, payload.version)
    _assert_unmatched(row)
    if row["status"] != "skipped":
        raise HTTPException(status_code=409, detail="Only skipped Scheduled Payments can be restored")
    status_name = _calculated_status(row)
    reason = row.get("skip_reason")
    now = utcnow()
    version = int(row.get("version") or 1)
    result = db.execute(text("""
        UPDATE scheduled_payments
        SET status=:status,skip_reason=NULL,skip_note=NULL,skipped_at=NULL,skipped_by_user_id=NULL,
            version=version+1,updated_at=:now
        WHERE id=:id AND user_id=:uid AND version=:version AND status='skipped'
    """), {"status": status_name, "now": now, "id": payment_id, "uid": current_user.id, "version": version})
    if not result.rowcount:
        db.rollback()
        raise HTTPException(status_code=409, detail="This payment changed since it was opened. Refresh and try again")
    _history(db, current_user, payment_id, "skipped", status_name, payload.note or "Skipped payment restored", reason)
    db.commit()
    return _response(_row(db, current_user, payment_id))


@router.get("/scheduled-payments/{payment_id}/detail")
def payment_detail(payment_id: int, current_user: User = USER, db: DbSession = DB):
    rows = payments_v112._scheduled_payment_rows(db, current_user)
    row = next((item for item in rows if int(item["id"]) == payment_id), None)
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    raw = _row(db, current_user, payment_id)
    history = db.execute(text("""
        SELECT from_status,to_status,source,note,reason,previous_expected_date,new_expected_date,created_at
        FROM scheduled_payment_history
        WHERE user_id=:uid AND scheduled_payment_id=:sid ORDER BY created_at,id
    """), {"uid": current_user.id, "sid": payment_id}).mappings().all()
    transaction = None
    if row.get("matched_transaction_id"):
        transaction = db.execute(text("""
            SELECT id,transaction_date,amount_cents,description,merchant FROM transactions
            WHERE id=:id AND user_id=:uid
        """), {"id": row["matched_transaction_id"], "uid": current_user.id}).mappings().first()
    return {
        **row,
        "skip_reason": raw.get("skip_reason"),
        "skip_note": raw.get("skip_note"),
        "skipped_at": raw.get("skipped_at"),
        "history": [dict(item) for item in history],
        "matched_transaction": None if transaction is None else {
            "id": transaction["id"], "date": payments_v112._as_date(transaction["transaction_date"]).isoformat(),
            "amount": payments_v112.cents_to_decimal(abs(int(transaction["amount_cents"] or 0))),
            "description": transaction["description"], "merchant": transaction["merchant"],
        },
    }
