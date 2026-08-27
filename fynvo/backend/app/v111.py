from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import payments_v17 as legacy
from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)

_schedule_lock = Lock()


def _as_date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _schedule_key(recurring_expense_id: int, occurrence_date: Any) -> tuple[int, str]:
    return int(recurring_expense_id), _as_date(occurrence_date).isoformat()


def ensure_scheduled_payments(db: DbSession, user: User, horizon_days: int = 120, today: date | None = None) -> dict[str, int]:
    """Incrementally materialise expected occurrences using immutable occurrence identity."""
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

        rule_ids = sorted({int(row["id"]) for row in rules})
        id_list = ",".join(str(value) for value in rule_ids)
        existing_rows = db.execute(text(f"""
            SELECT id,recurring_expense_id,COALESCE(occurrence_date,expected_date) AS occurrence_date,
                   expected_date,status,expected_amount_cents,payment_method,payment_handling,account_id,card_id
            FROM scheduled_payments
            WHERE user_id=:uid AND recurring_expense_id IN ({id_list})
        """), {"uid": user.id}).mappings().all()
        existing = {_schedule_key(row["recurring_expense_id"], row["occurrence_date"]): row for row in existing_rows}
        now = utcnow()
        dirty = False

        for rule in rules:
            first_due = _as_date(rule["next_due_date"])
            method = rule["payment_method"] or ("direct_debit" if rule["direct_debit"] else "not_set")
            handling = rule.get("payment_handling") or legacy.default_payment_handling(method)
            grace = int(rule.get("auto_payment_grace_days") or legacy.DEFAULT_GRACE_DAYS)
            account_id = int(rule["card_account_id"]) if method == "automatic_card_payment" and rule.get("card_account_id") else rule["account_id"]
            end_date = _as_date(rule["end_date"]) if rule.get("end_date") else None
            occurrence_date = first_due
            generated = 0

            while occurrence_date <= end and generated < 400:
                if end_date and occurrence_date > end_date:
                    break
                stats["occurrences"] += 1
                key = _schedule_key(rule["id"], occurrence_date)
                current = existing.get(key)

                if current:
                    effective_date = _as_date(current["expected_date"])
                    status_name = legacy._status_for(effective_date, handling, grace, today)
                    if current["status"] not in legacy.TERMINAL_STATUSES:
                        status_changed = current["status"] != status_name
                        values_changed = any((
                            current["expected_amount_cents"] != rule["amount_cents"],
                            current["payment_method"] != method,
                            current["payment_handling"] != handling,
                            current["account_id"] != account_id,
                            current["card_id"] != rule["card_id"],
                        ))
                        if status_changed or values_changed:
                            update = db.execute(text("""
                                UPDATE scheduled_payments
                                SET expected_amount_cents=:amount,payment_method=:method,
                                    payment_handling=:handling,account_id=:account_id,card_id=:card_id,
                                    status=:status,updated_at=:now
                                WHERE id=:id AND user_id=:uid AND status=:from_status
                            """), {
                                "amount": rule["amount_cents"], "method": method, "handling": handling,
                                "account_id": account_id, "card_id": rule["card_id"], "status": status_name,
                                "now": now, "id": current["id"], "uid": user.id, "from_status": current["status"],
                            })
                            if update.rowcount:
                                dirty = True
                                stats["updated"] += 1
                                if status_changed:
                                    db.execute(text("""
                                        INSERT INTO scheduled_payment_history(
                                            user_id,scheduled_payment_id,from_status,to_status,source,created_at
                                        ) VALUES(:uid,:sid,:from_status,:to_status,'system',:now)
                                    """), {
                                        "uid": user.id, "sid": current["id"], "from_status": current["status"],
                                        "to_status": status_name, "now": now,
                                    })
                                    stats["history"] += 1
                else:
                    status_name = legacy._status_for(occurrence_date, handling, grace, today)
                    inserted = db.execute(text("""
                        INSERT OR IGNORE INTO scheduled_payments(
                            user_id,recurring_expense_id,occurrence_date,expected_date,expected_amount_cents,status,
                            payment_method,payment_handling,account_id,card_id,created_at,updated_at,version
                        ) VALUES(:uid,:rid,:occurrence_date,:expected_date,:amount,:status,:method,:handling,:account_id,:card_id,:now,:now,1)
                    """), {
                        "uid": user.id, "rid": rule["id"], "occurrence_date": occurrence_date,
                        "expected_date": occurrence_date, "amount": rule["amount_cents"], "status": status_name,
                        "method": method, "handling": handling, "account_id": account_id, "card_id": rule["card_id"], "now": now,
                    })
                    if inserted.rowcount:
                        payment_id = db.execute(text("""
                            SELECT id FROM scheduled_payments
                            WHERE user_id=:uid AND recurring_expense_id=:rid AND occurrence_date=:occurrence_date
                        """), {"uid": user.id, "rid": rule["id"], "occurrence_date": occurrence_date}).scalar_one()
                        db.execute(text("""
                            INSERT INTO scheduled_payment_history(
                                user_id,scheduled_payment_id,from_status,to_status,source,created_at
                            ) VALUES(:uid,:sid,NULL,:status,'system',:now)
                        """), {"uid": user.id, "sid": payment_id, "status": status_name, "now": now})
                        dirty = True
                        stats["inserted"] += 1
                        stats["history"] += 1
                        existing[key] = {
                            "id": payment_id, "recurring_expense_id": rule["id"], "occurrence_date": occurrence_date,
                            "expected_date": occurrence_date, "status": status_name,
                            "expected_amount_cents": rule["amount_cents"], "payment_method": method,
                            "payment_handling": handling, "account_id": account_id, "card_id": rule["card_id"],
                        }

                generated += 1
                next_due = legacy._next_occurrence(occurrence_date, rule["frequency"], rule["interval_count"])
                if next_due is None or next_due <= occurrence_date:
                    break
                occurrence_date = next_due

        if dirty:
            db.commit()
        return stats


def _scheduled_rows(db: DbSession, user: User, status_filter: str | None = None) -> list[dict[str, Any]]:
    sql = """
        SELECT sp.*,r.name,a.name AS account_name,
               CASE WHEN c.id IS NULL THEN NULL ELSE c.name || ' ••••' || c.last_four END AS card_name,
               ca.name AS linked_account_name
        FROM scheduled_payments sp JOIN recurring_expenses r ON r.id=sp.recurring_expense_id
        LEFT JOIN accounts a ON a.id=sp.account_id
        LEFT JOIN cards c ON c.id=sp.card_id
        LEFT JOIN accounts ca ON ca.id=c.account_id
        WHERE sp.user_id=:uid
    """
    params: dict[str, Any] = {"uid": user.id}
    if status_filter:
        sql += " AND sp.status=:status"
        params["status"] = status_filter
    sql += " ORDER BY sp.expected_date,sp.id"
    return [legacy._scheduled_response(row) for row in db.execute(text(sql), params).all()]


@router.get("/scheduled-payments")
def scheduled_payments(status_filter: str | None = None, current_user: User = USER, db: DbSession = DB):
    ensure_scheduled_payments(db, current_user)
    return _scheduled_rows(db, current_user, status_filter)


@router.get("/payments/attention")
def payment_attention(current_user: User = USER, db: DbSession = DB):
    ensure_scheduled_payments(db, current_user)
    return [row for row in _scheduled_rows(db, current_user) if row["status"] in {"overdue", "due", "due_today", "auto_payment_unconfirmed"}]


def _transaction_response(row: Any) -> dict[str, Any]:
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    return {
        "id": data["id"], "account_id": data.get("account_id"), "account_name": data.get("account_name"),
        "date": _as_date(data["transaction_date"]).isoformat(),
        "amount": cents_to_decimal(data.get("amount_cents") or 0),
        "transaction_type": data.get("transaction_type"), "description": data.get("description"),
        "merchant": data.get("merchant"), "category": data.get("category"), "category_id": data.get("category_id"),
        "notes": data.get("notes"), "source": data.get("source"), "status": data.get("status"),
        "raw_description": data.get("raw_description"), "import_batch_id": data.get("import_batch_id"),
        "reconciliation_status": data.get("reconciliation_status") or data.get("reconciliation_state") or "unmatched",
        "matched_type": data.get("matched_type"), "matched_id": data.get("matched_id"),
    }


@router.get("/payments/transactions")
def reconciliation_transactions(limit: int = Query(default=1000, ge=1, le=2000), current_user: User = USER, db: DbSession = DB):
    rows = db.execute(text("""
        SELECT t.*,a.name AS account_name
        FROM transactions t JOIN accounts a ON a.id=t.account_id
        WHERE t.user_id=:uid
        ORDER BY t.transaction_date DESC,t.id DESC
        LIMIT :limit
    """), {"uid": current_user.id, "limit": limit}).all()
    return [_transaction_response(row) for row in rows]


class TransactionCategoryPayload(BaseModel):
    category_id: int | None = None


@router.put("/payments/transactions/{transaction_id}/category")
def categorise_transaction(transaction_id: int, payload: TransactionCategoryPayload, current_user: User = USER, db: DbSession = DB):
    tx = db.execute(text("SELECT id FROM transactions WHERE id=:id AND user_id=:uid"), {"id": transaction_id, "uid": current_user.id}).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    category_name = None
    if payload.category_id is not None:
        category = db.execute(text("SELECT id,name,is_active FROM categories WHERE id=:id AND user_id=:uid"), {"id": payload.category_id, "uid": current_user.id}).mappings().first()
        if not category:
            raise HTTPException(status_code=400, detail="The selected Category is no longer available")
        if not category["is_active"]:
            raise HTTPException(status_code=409, detail="Choose an active Category")
        category_name = category["name"]
    db.execute(text("UPDATE transactions SET category_id=:category_id,category=:category,updated_at=:now WHERE id=:id AND user_id=:uid"), {
        "category_id": payload.category_id, "category": category_name, "now": utcnow(), "id": transaction_id, "uid": current_user.id,
    })
    db.commit()
    row = db.execute(text("""
        SELECT t.*,a.name AS account_name FROM transactions t JOIN accounts a ON a.id=t.account_id
        WHERE t.id=:id AND t.user_id=:uid
    """), {"id": transaction_id, "uid": current_user.id}).first()
    return _transaction_response(row)


def _match_candidates(date_tolerance_days: int, user: User, db: DbSession) -> list[dict[str, Any]]:
    ensure_scheduled_payments(db, user)
    tx_rows = db.execute(text("""
        SELECT * FROM transactions
        WHERE user_id=:uid AND transaction_type='expense'
          AND COALESCE(reconciliation_status,'unmatched') NOT IN ('matched','ignored','duplicate')
        ORDER BY transaction_date DESC,id DESC
    """), {"uid": user.id}).mappings().all()
    mapping_rows = db.execute(text("SELECT * FROM recurring_match_mappings WHERE user_id=:uid"), {"uid": user.id}).mappings().all()
    mappings = {(int(row["recurring_expense_id"]), row["merchant_key"], int(row["account_id"]) if row["account_id"] is not None else None): row for row in mapping_rows}
    decisions = db.execute(text("SELECT transaction_id,scheduled_payment_id,decision FROM scheduled_payment_match_decisions WHERE user_id=:uid"), {"uid": user.id}).mappings().all()
    rejected = {(int(row["transaction_id"]), int(row["scheduled_payment_id"])) for row in decisions if row["decision"] == "rejected" and row["scheduled_payment_id"] is not None}
    ignored = {int(row["transaction_id"]) for row in decisions if row["decision"] == "ignored"}
    scheduled = db.execute(text("""
        SELECT sp.*,r.name,r.payee_merchant,r.amount_type
        FROM scheduled_payments sp JOIN recurring_expenses r ON r.id=sp.recurring_expense_id
        WHERE sp.user_id=:uid AND sp.status NOT IN ('paid','skipped','cancelled') AND sp.matched_transaction_id IS NULL
    """), {"uid": user.id}).mappings().all()

    candidates: list[dict[str, Any]] = []
    for tx in tx_rows:
        if int(tx["id"]) in ignored:
            continue
        tx_date = _as_date(tx["transaction_date"])
        merchant_key = " ".join(str(tx.get("merchant") or tx.get("description") or "").strip().lower().split())
        for payment in scheduled:
            if (int(tx["id"]), int(payment["id"])) in rejected:
                continue
            expected_date = _as_date(payment["expected_date"])
            day_delta = abs((tx_date - expected_date).days)
            if day_delta > date_tolerance_days:
                continue
            same_account = bool(payment["account_id"] and tx.get("account_id") and int(payment["account_id"]) == int(tx["account_id"]))
            if payment["account_id"] and tx.get("account_id") and not same_account:
                continue
            expected = int(payment["expected_amount_cents"] or 0)
            actual = abs(int(tx["amount_cents"] or 0))
            variance = abs(expected - actual)
            allowed = max(100, round(expected * 0.05)) if payment["amount_type"] == "fixed" else max(1000, round(expected * 0.30))
            learned = mappings.get((int(payment["recurring_expense_id"]), merchant_key, int(tx["account_id"]) if tx.get("account_id") is not None else None))
            payee = " ".join(str(payment.get("payee_merchant") or payment.get("name") or "").strip().lower().split())
            merchant_match = bool(payee and (payee in merchant_key or merchant_key in payee))
            if variance > allowed and not learned:
                continue
            exact_amount = variance == 0
            score = 35 if exact_amount else 25 if variance <= allowed else 0
            score += 30 if day_delta <= 1 else 20 if day_delta <= 3 else 10
            score += 30 if merchant_match else 20 if learned else 0
            if same_account:
                score += 5
            confidence = "high" if score >= 80 else "medium" if score >= 55 else "low"
            evidence = []
            if exact_amount:
                evidence.append("Amount matches")
            elif payment["amount_type"] != "fixed":
                evidence.append("Amount is within the expected variable range")
            else:
                evidence.append("Amount is within the expected tolerance")
            if same_account:
                evidence.append("Account matches")
            if merchant_match:
                evidence.append("Merchant matches")
            if learned:
                evidence.append("Previously confirmed merchant mapping")
            evidence.append(f"Transaction is {day_delta} day{'s' if day_delta != 1 else ''} from effective expected date")
            candidates.append({
                "transaction_id": int(tx["id"]), "scheduled_payment_id": int(payment["id"]),
                "recurring_expense_id": int(payment["recurring_expense_id"]), "name": payment["name"],
                "transaction_date": tx_date.isoformat(), "expected_date": expected_date.isoformat(),
                "original_expected_date": _as_date(payment.get("occurrence_date") or payment["expected_date"]).isoformat(),
                "transaction_amount": cents_to_decimal(actual), "expected_amount": cents_to_decimal(expected),
                "variance": cents_to_decimal(actual - expected), "confidence": confidence, "score": score,
                "evidence": evidence, "merchant": tx.get("merchant") or tx.get("description"),
                "payment_method": payment["payment_method"], "account_id": payment["account_id"],
            })
    return sorted(candidates, key=lambda row: (-row["score"], row["transaction_id"], row["scheduled_payment_id"]))


@router.get("/payments/match-candidates")
def match_candidates(date_tolerance_days: int = Query(default=7, ge=1, le=31), current_user: User = USER, db: DbSession = DB):
    return _match_candidates(date_tolerance_days, current_user, db)


class MatchPayload(BaseModel):
    transaction_id: int
    confidence: str | None = None


class NotePayload(BaseModel):
    note: str | None = None


@router.post("/scheduled-payments/{payment_id}/match")
def confirm_match(payment_id: int, payload: MatchPayload, current_user: User = USER, db: DbSession = DB):
    payment = db.execute(text("SELECT * FROM scheduled_payments WHERE id=:id AND user_id=:uid"), {"id": payment_id, "uid": current_user.id}).mappings().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    if payment["status"] in legacy.TERMINAL_STATUSES or payment["matched_transaction_id"] is not None:
        raise HTTPException(status_code=409, detail="This Scheduled Payment has already been resolved")
    transaction = db.execute(text("SELECT * FROM transactions WHERE id=:id AND user_id=:uid"), {"id": payload.transaction_id, "uid": current_user.id}).mappings().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if (transaction.get("reconciliation_status") or transaction.get("reconciliation_state") or "unmatched") in {"matched", "ignored", "duplicate"}:
        raise HTTPException(status_code=409, detail="This Transaction is already resolved")
    now = utcnow()
    db.execute(text("""
        UPDATE scheduled_payments
        SET status='paid',actual_date=:actual_date,actual_amount_cents=:actual_amount,
            matched_transaction_id=:txid,match_confidence=:confidence,confirmation_source='transaction',updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {"actual_date": transaction["transaction_date"], "actual_amount": abs(int(transaction["amount_cents"] or 0)), "txid": transaction["id"], "confidence": payload.confidence or "confirmed", "now": now, "id": payment_id, "uid": current_user.id})
    db.execute(text("""
        UPDATE transactions SET reconciliation_status='matched',matched_type='scheduled_payment',matched_id=:payment_id,updated_at=:now
        WHERE id=:txid AND user_id=:uid
    """), {"payment_id": payment_id, "now": now, "txid": transaction["id"], "uid": current_user.id})
    db.execute(text("""
        INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,note,created_at)
        VALUES(:uid,:sid,:from_status,'paid','transaction',:note,:now)
    """), {"uid": current_user.id, "sid": payment_id, "from_status": payment["status"], "note": f"Matched transaction {transaction['id']}", "now": now})
    db.commit()
    return {"status": "paid", "scheduled_payment_id": payment_id, "transaction_id": int(transaction["id"])}


@router.post("/scheduled-payments/{payment_id}/reject-match")
def reject_match(payment_id: int, payload: MatchPayload, current_user: User = USER, db: DbSession = DB):
    payment = db.execute(text("SELECT id FROM scheduled_payments WHERE id=:id AND user_id=:uid"), {"id": payment_id, "uid": current_user.id}).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    transaction = db.execute(text("SELECT id FROM transactions WHERE id=:id AND user_id=:uid"), {"id": payload.transaction_id, "uid": current_user.id}).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.execute(text("""
        INSERT OR IGNORE INTO scheduled_payment_match_decisions(user_id,transaction_id,scheduled_payment_id,decision,created_at)
        VALUES(:uid,:txid,:sid,'rejected',:now)
    """), {"uid": current_user.id, "txid": payload.transaction_id, "sid": payment_id, "now": utcnow()})
    db.commit()
    return {"status": "rejected"}


@router.post("/payments/transactions/{transaction_id}/ignore")
def ignore_transaction(transaction_id: int, current_user: User = USER, db: DbSession = DB):
    transaction = db.execute(text("SELECT id FROM transactions WHERE id=:id AND user_id=:uid"), {"id": transaction_id, "uid": current_user.id}).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.execute(text("""
        INSERT OR IGNORE INTO scheduled_payment_match_decisions(user_id,transaction_id,scheduled_payment_id,decision,created_at)
        VALUES(:uid,:txid,NULL,'ignored',:now)
    """), {"uid": current_user.id, "txid": transaction_id, "now": utcnow()})
    db.execute(text("UPDATE transactions SET reconciliation_status='ignored',updated_at=:now WHERE id=:id AND user_id=:uid"), {"now": utcnow(), "id": transaction_id, "uid": current_user.id})
    db.commit()
    return {"status": "ignored"}


@router.post("/scheduled-payments/{payment_id}/skip")
def skip_payment(payment_id: int, payload: NotePayload, current_user: User = USER, db: DbSession = DB):
    payment = db.execute(text("SELECT id,status FROM scheduled_payments WHERE id=:id AND user_id=:uid"), {"id": payment_id, "uid": current_user.id}).mappings().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    if payment["status"] in legacy.TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="This Scheduled Payment has already been resolved")
    now = utcnow()
    db.execute(text("UPDATE scheduled_payments SET status='skipped',note=:note,updated_at=:now WHERE id=:id AND user_id=:uid"), {"note": payload.note, "now": now, "id": payment_id, "uid": current_user.id})
    db.execute(text("""
        INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,note,created_at)
        VALUES(:uid,:sid,:from_status,'skipped','ui',:note,:now)
    """), {"uid": current_user.id, "sid": payment_id, "from_status": payment["status"], "note": payload.note, "now": now})
    db.commit()
    return {"id": payment_id, "status": "skipped"}


def _coverage_status(account: dict[str, Any], imports: list[dict[str, Any]], today: date) -> dict[str, Any]:
    confirmed = [row for row in imports if row["coverage_status"] == "confirmed" and row["coverage_end"]]
    latest = max(confirmed, key=lambda row: _as_date(row["coverage_end"])) if confirmed else None
    if not latest:
        return {"status": "unknown", "label": "Coverage unknown", "detail": "No confirmed import coverage window"}
    age = (today - _as_date(latest["coverage_end"])).days
    if age <= 7:
        return {"status": "current", "label": "Coverage current", "detail": f"Confirmed through {latest['coverage_end']}"}
    return {"status": "stale", "label": "Coverage stale", "detail": f"Last confirmed through {latest['coverage_end']}"}


def command_centre_payment_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["status"] for row in rows)
    due = [row for row in rows if row["status"] not in legacy.TERMINAL_STATUSES]
    return {
        "counts": dict(counts),
        "requires_attention": sum(counts.get(key, 0) for key in ("overdue", "due", "due_today", "auto_payment_unconfirmed")),
        "scheduled_total": cents_to_decimal(sum(int(round(float(row["expected_amount"] or 0) * 100)) for row in due)),
    }
