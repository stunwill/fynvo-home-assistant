from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import UTC, date, datetime, timedelta
from difflib import SequenceMatcher
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .budget import (
    analyse_budgets,
    create_budget,
    create_category,
    deactivate_budget,
    list_budgets,
    list_categories,
    list_views,
    reset_view,
    save_view,
    update_budget,
    update_category,
)
from .database import get_db
from .finance import bill_response, income_response, recurring_response
from .ledger import create_transaction, list_transactions
from .models import User
from .money import cents_to_decimal, parse_money
from .schemas import TransactionCreate
from .security import utcnow

router = APIRouter(prefix="/api")
DB = Depends(get_db)
USER = Depends(get_current_user)
RECONCILIATION_STATUSES = {"unmatched", "suggested_match", "matched", "ignored", "duplicate", "needs_review"}


def _obj(row: Any) -> Any:
    return SimpleNamespace(**dict(row)) if hasattr(row, "keys") else row


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC).date()
        except ValueError:
            continue
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Australian date: {value}")


def _parse_csv_date(value: str) -> tuple[date | None, str | None]:
    if not value.strip():
        return None, "Missing date"
    try:
        return _as_date(value), None
    except HTTPException:
        return None, f"Invalid date '{value}'"


def _normalise_text(value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    cleaned = re.sub(r"\b(VIC|NSW|QLD|SA|WA|TAS|NT|ACT|AU|AUS)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{3,}\b", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip().title()


def _parse_amount_safe(value: str) -> int | None:
    try:
        return parse_money(value)
    except (ArithmeticError, TypeError, ValueError):
        return None


def _fingerprint(account_id: int, tx_date: date, amount_cents: int, description: str) -> str:
    payload = f"{account_id}|{tx_date.isoformat()}|{amount_cents}|{_normalise_text(description).lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _row_amount(row: dict[str, str], mapping: dict[str, str]) -> tuple[int | None, str | None, str]:
    def value(name: str) -> str:
        source = mapping.get(name)
        return (row.get(source, "") if source else "").strip().replace("$", "").replace(",", "")

    signed = value("amount")
    debit = value("debit")
    credit = value("credit")
    if signed:
        cents = _parse_amount_safe(signed)
        if cents is None:
            return None, f"Invalid amount '{signed}'", "expense"
        return abs(cents), None, "income" if cents >= 0 else "expense"
    if credit:
        cents = _parse_amount_safe(credit)
        return (cents, None, "income") if cents is not None else (None, "Invalid credit amount", "expense")
    if debit:
        cents = _parse_amount_safe(debit)
        return (cents, None, "expense") if cents is not None else (None, "Invalid debit amount", "expense")
    return None, "Missing amount", "expense"


def _find_duplicates(db: DbSession, user: User, account_id: int, tx_date: date, amount_cents: int, description: str) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT id, transaction_date, amount_cents, description, merchant, category, account_id
            FROM transactions
            WHERE user_id=:user_id AND account_id=:account_id
              AND amount_cents=:amount
              AND transaction_date BETWEEN :start AND :end
        """),
        {"user_id": user.id, "account_id": account_id, "amount": amount_cents, "start": tx_date - timedelta(days=2), "end": tx_date + timedelta(days=2)},
    ).mappings().all()
    normal = _normalise_text(description).lower()
    results = []
    for row in rows:
        ratio = SequenceMatcher(None, normal, _normalise_text(row["description"]).lower()).ratio()
        duplicate_status = "exact_duplicate" if row["transaction_date"] == tx_date and ratio > 0.94 else "likely_duplicate" if ratio > 0.72 else "potential_match"
        results.append({"id": row["id"], "status": duplicate_status, "description": row["description"], "date": str(row["transaction_date"]), "amount": cents_to_decimal(abs(row["amount_cents"])), "confidence": round(ratio * 100)})
    return results


def _suggest_category(db: DbSession, user: User, description: str) -> str | None:
    normal = _normalise_text(description).lower()
    if not normal:
        return None
    row = db.execute(
        text("""
            SELECT category FROM transactions
            WHERE user_id=:user_id AND category IS NOT NULL AND lower(description) LIKE :needle
            ORDER BY updated_at DESC LIMIT 1
        """),
        {"user_id": user.id, "needle": f"%{normal.split()[0]}%"},
    ).mappings().first()
    if row:
        return row["category"]
    known = [("woolworths", "Groceries > Supermarket"), ("coles", "Groceries > Supermarket"), ("powershop", "Utilities > Electricity"), ("telstra", "Utilities > Internet"), ("vicroads", "Transport > Car > Registration"), ("budget direct", "Transport > Car > Insurance")]
    return next((category for key, category in known if key in normal), None)


def _matches(db: DbSession, user: User, tx_date: date, amount_cents: int, description: str, category: str | None) -> list[dict]:
    normal = _normalise_text(description).lower()
    candidates = []
    sources = [("bills", "bill", "due_date", "remaining_amount_cents", "name", "bill_type"), ("recurring_expenses", "recurring_expense", "next_due_date", "amount_cents", "name", "category"), ("planned_spending", "planned_spending", "planned_date", "estimated_amount_cents", "name", "category")]
    for table, label, date_col, amount_col, name_col, type_col in sources:
        rows = db.execute(
            text(f"""
                SELECT id, {name_col} AS name, {date_col} AS expected_date, {amount_col} AS expected_amount, {type_col} AS category
                FROM {table}
                WHERE user_id=:user_id AND {amount_col} IS NOT NULL
            """),
            {"user_id": user.id},
        ).mappings().all()
        for row in rows:
            expected_date = _as_date(row["expected_date"])
            days = abs((tx_date - expected_date).days) if expected_date else 99
            amount_delta = abs(abs(amount_cents) - abs(row["expected_amount"] or 0))
            amount_score = 45 if amount_delta == 0 else 30 if amount_delta <= 500 else 15 if amount_delta <= 5000 else 0
            date_score = 30 if days <= 1 else 20 if days <= 7 else 5 if days <= 31 else 0
            text_score = round(SequenceMatcher(None, normal, _normalise_text(row["name"]).lower()).ratio() * 25)
            category_score = 10 if category and row["category"] and category == row["category"] else 0
            confidence = min(100, amount_score + date_score + text_score + category_score)
            if confidence >= 45:
                candidates.append({"source_type": label, "source_id": row["id"], "name": row["name"], "expected_amount": cents_to_decimal(row["expected_amount"]), "actual_amount": cents_to_decimal(amount_cents), "variance": cents_to_decimal(amount_cents - abs(row["expected_amount"] or 0)), "expected_date": str(expected_date) if expected_date else None, "confidence": confidence})
    return sorted(candidates, key=lambda item: item["confidence"], reverse=True)[:3]


def _preview_rows(db: DbSession, user: User, csv_text: str, mapping: dict[str, str], account_id: int) -> list[dict]:
    if len(csv_text.encode("utf-8")) > 2_000_000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="CSV file is too large")
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV header row is required")
    rows = []
    for index, row in enumerate(reader, start=1):
        if not any((value or "").strip() for value in row.values()):
            continue
        date_col = mapping.get("date")
        desc_col = mapping.get("description") or mapping.get("merchant")
        tx_date, date_error = _parse_csv_date(row.get(date_col, "") if date_col else "")
        description = (row.get(desc_col, "") if desc_col else "").strip()
        amount_cents, amount_error, direction = _row_amount(row, mapping)
        errors = [err for err in (date_error, amount_error, None if description else "Missing description") if err]
        category = _suggest_category(db, user, description) if not errors else None
        duplicates = _find_duplicates(db, user, account_id, tx_date, amount_cents or 0, description) if tx_date and amount_cents is not None else []
        matches = _matches(db, user, tx_date, amount_cents or 0, description, category) if tx_date and amount_cents is not None else []
        row_status = "invalid" if errors else duplicates[0]["status"] if duplicates else "potential_match" if matches else "new"
        rows.append({"row_number": index, "date": tx_date.isoformat() if tx_date else None, "description": description, "merchant": _normalise_text(row.get(mapping.get("merchant", ""), description)), "amount": cents_to_decimal(amount_cents) if amount_cents is not None else None, "amount_cents": amount_cents, "transaction_type": direction, "category": category, "status": row_status, "errors": errors, "duplicates": duplicates, "matches": matches, "fingerprint": _fingerprint(account_id, tx_date, amount_cents or 0, description) if tx_date and amount_cents is not None else None})
    return rows


def _record_edit(db: DbSession, user: User, record_type: str, record_id: int, original: dict, updated: dict, source: str = "ui") -> None:
    db.execute(text("INSERT INTO edit_history (user_id, record_type, record_id, original_json, updated_json, source, created_at) VALUES (:user_id, :record_type, :record_id, :original, :updated, :source, :now)"), {"user_id": user.id, "record_type": record_type, "record_id": record_id, "original": str(original), "updated": str(updated), "source": source, "now": utcnow()})


def _update_table_record(db: DbSession, user: User, table: str, record_id: int, allowed: set[str], payload: dict[str, Any], amount_fields: dict[str, str] | None = None) -> Any:
    existing = db.execute(text(f"SELECT * FROM {table} WHERE id=:id AND user_id=:user_id"), {"id": record_id, "user_id": user.id}).mappings().first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    data = {k: v for k, v in payload.items() if k in allowed}
    for api_name, column in (amount_fields or {}).items():
        if api_name in payload:
            data[column] = parse_money(payload[api_name]) if payload[api_name] not in (None, "") else None
    if not data:
        return _obj(existing)
    values = {"id": record_id, "user_id": user.id, "now": utcnow()}
    assignments = []
    for key, value in data.items():
        assignments.append(f"{key} = :{key}")
        values[key] = value
    assignments.append("updated_at = :now")
    db.execute(text(f"UPDATE {table} SET {', '.join(assignments)} WHERE id=:id AND user_id=:user_id"), values)
    updated = db.execute(text(f"SELECT * FROM {table} WHERE id=:id AND user_id=:user_id"), {"id": record_id, "user_id": user.id}).mappings().first()
    _record_edit(db, user, table, record_id, dict(existing), dict(updated))
    return _obj(updated)


@router.put("/income/{income_id}")
def edit_income(income_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    if payload.get("frequency") and payload["frequency"] not in {"weekly", "fortnightly", "monthly", "quarterly", "yearly", "custom", "one_off"}:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    effective_from = payload.pop("effective_from", None)
    row = _update_table_record(db, current_user, "income_sources", income_id, {"name", "frequency", "interval_count", "next_payment_date", "destination_account_id", "payer", "category", "owner_group", "is_active", "start_date", "end_date", "notes"}, payload, {"amount": "amount_cents"})
    if effective_from and payload.get("amount") not in (None, ""):
        db.execute(text("INSERT INTO effective_amount_changes (user_id, record_type, record_id, new_amount_cents, effective_from, source, notes, created_at, updated_at) VALUES (:user_id, 'income', :record_id, :amount, :effective_from, 'edit', :notes, :now, :now)"), {"user_id": current_user.id, "record_id": income_id, "amount": parse_money(payload["amount"]), "effective_from": _as_date(effective_from), "notes": payload.get("edit_mode", "Change going forward"), "now": utcnow()})
    db.commit()
    return income_response(row)


@router.put("/recurring-expenses/{expense_id}")
def edit_recurring(expense_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    if payload.get("frequency") and payload["frequency"] not in {"weekly", "fortnightly", "every_28_days", "every_4_weeks", "monthly", "quarterly", "yearly", "custom", "one_off"}:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    effective_from = payload.pop("effective_from", None)
    row = _update_table_record(db, current_user, "recurring_expenses", expense_id, {"name", "frequency", "interval_count", "next_due_date", "direct_debit", "account_id", "source_account_text", "category", "expense_type", "owner_group", "is_active", "variable_amount", "aliases", "notes", "last_paid_date"}, payload, {"amount": "amount_cents"})
    if effective_from and payload.get("amount") not in (None, ""):
        db.execute(text("INSERT INTO effective_amount_changes (user_id, record_type, record_id, new_amount_cents, effective_from, source, notes, created_at, updated_at) VALUES (:user_id, 'recurring_expense', :record_id, :amount, :effective_from, 'edit', :notes, :now, :now)"), {"user_id": current_user.id, "record_id": expense_id, "amount": parse_money(payload["amount"]), "effective_from": _as_date(effective_from), "notes": payload.get("edit_mode", "Change going forward"), "now": utcnow()})
    db.commit()
    return recurring_response(row)


@router.put("/bills/{bill_id}")
def edit_bill(bill_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    status_value = payload.pop("status", None)
    row = _update_table_record(db, current_user, "bills", bill_id, {"recurring_expense_id", "name", "provider", "bill_type", "priority", "original_status", "due_date", "pay_cycle_date", "account_id", "source_account_text", "paid_through_date", "notes", "is_active"}, payload, {"amount": "remaining_amount_cents", "original_amount": "original_amount_cents"})
    if status_value in {"paid", "resolved"}:
        now = utcnow()
        db.execute(text("UPDATE bills SET paid_at=:paid, resolved_at=:resolved, remaining_amount_cents=0, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": bill_id, "user_id": current_user.id, "paid": now if status_value == "paid" else None, "resolved": now, "now": now})
        row = _obj(db.execute(text("SELECT * FROM bills WHERE id=:id AND user_id=:user_id"), {"id": bill_id, "user_id": current_user.id}).mappings().first())
    db.commit()
    return bill_response(row)


@router.get("/categories")
def categories(current_user: User = USER, db: DbSession = DB):
    return list_categories(db, current_user)


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def add_category(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    return create_category(db, current_user, payload)


@router.put("/categories/{category_id}")
def edit_category(category_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    return update_category(db, current_user, category_id, payload)


@router.get("/budgets")
def budgets(include_inactive: bool = False, current_user: User = USER, db: DbSession = DB):
    return list_budgets(db, current_user, include_inactive)


@router.get("/budgets/analysis")
def budget_analysis(start: date | None = None, end: date | None = None, mode: str = "native", current_user: User = USER, db: DbSession = DB):
    day = utcnow().date()
    return analyse_budgets(db, current_user, start or date(day.year, day.month, 1), end or day, mode)


@router.post("/budgets", status_code=status.HTTP_201_CREATED)
def add_budget(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    return create_budget(db, current_user, payload)


@router.put("/budgets/{budget_id}")
def edit_budget(budget_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    return update_budget(db, current_user, budget_id, payload)


@router.post("/budgets/{budget_id}/deactivate")
def archive_budget(budget_id: int, current_user: User = USER, db: DbSession = DB):
    return deactivate_budget(db, current_user, budget_id)


@router.get("/saved-views/{screen}")
def saved_views(screen: str, current_user: User = USER, db: DbSession = DB):
    return list_views(db, current_user, screen)


@router.post("/saved-views")
def store_view(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    return save_view(db, current_user, payload)


@router.post("/saved-views/{screen}/reset")
def reset_saved_view(screen: str, current_user: User = USER, db: DbSession = DB):
    return reset_view(db, current_user, screen)


@router.post("/imports/preview")
def import_preview(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    account_id = int(payload.get("account_id") or 0)
    if not account_id:
        raise HTTPException(status_code=400, detail="Destination account is required")
    mapping = payload.get("mapping") or {}
    csv_text = payload.get("csv_text") or ""
    rows = _preview_rows(db, current_user, csv_text, mapping, account_id)
    db.execute(text("INSERT OR REPLACE INTO import_profiles (user_id, source_name, mapping_json, updated_at) VALUES (:user_id, :source, :mapping, :now)"), {"user_id": current_user.id, "source": payload.get("source_name") or "Latest CSV", "mapping": str(mapping), "now": utcnow()})
    db.commit()
    valid_dates = [_as_date(row["date"]) for row in rows if not row["errors"] and row.get("date")]
    return {
        "headers": list(csv.DictReader(io.StringIO(csv_text.strip())).fieldnames or []),
        "rows": [{k: v for k, v in row.items() if k != "amount_cents"} for row in rows],
        "summary": {
            "row_count": len(rows),
            "new": len([r for r in rows if r["status"] == "new"]),
            "duplicates": len([r for r in rows if "duplicate" in r["status"]]),
            "matches": len([r for r in rows if r["matches"]]),
            "invalid": len([r for r in rows if r["errors"]]),
            "transaction_span_start": min(valid_dates).isoformat() if valid_dates else None,
            "transaction_span_end": max(valid_dates).isoformat() if valid_dates else None,
        },
    }


@router.post("/imports/commit")
def import_commit(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    account_id = int(payload.get("account_id") or 0)
    if not account_id:
        raise HTTPException(status_code=400, detail="Destination account is required")
    rows = _preview_rows(db, current_user, payload.get("csv_text") or "", payload.get("mapping") or {}, account_id)
    now = utcnow()
    filename = re.sub(r"[^A-Za-z0-9_. -]", "_", payload.get("filename") or "bank-import.csv")[:180]
    source_type = str(payload.get("source_type") or "csv")[:40]
    source_institution = str(payload.get("source_institution") or "")[:140] or None
    parser_profile = str(payload.get("source_name") or "Australian bank CSV")[:180]
    db.execute(text("""
        INSERT INTO import_batches (
            user_id, filename, account_id, row_count, imported_count, skipped_count,
            duplicate_count, matched_count, failed_count, status, source_type,
            source_institution, parser_profile, coverage_status, created_at, updated_at
        )
        VALUES (
            :user_id, :filename, :account_id, :row_count, 0, 0, 0, 0, 0,
            'processing', :source_type, :source_institution, :parser_profile,
            'unknown', :now, :now
        )
    """), {"user_id": current_user.id, "filename": filename, "account_id": account_id, "row_count": len(rows), "source_type": source_type, "source_institution": source_institution, "parser_profile": parser_profile, "now": now})
    batch_id = db.execute(text("SELECT last_insert_rowid()")).scalar()
    imported = skipped = duplicates = matched = failed = 0
    imported_rows = []
    imported_dates: list[date] = []
    for row in rows:
        if row["errors"]:
            failed += 1
            continue
        if "duplicate" in row["status"] and not payload.get("import_duplicates", False):
            duplicates += 1
            skipped += 1
            continue
        tx_date = _as_date(row["date"])
        signed_amount = row["amount"] if row["transaction_type"] == "income" else f"-{row['amount']}"
        created = create_transaction(db, current_user, TransactionCreate(account_id=account_id, date=tx_date, amount=signed_amount, transaction_type=row["transaction_type"], description=row["description"], merchant=row["merchant"], category=row["category"], source="csv", status="cleared", raw_description=row["description"]))
        db.execute(text("UPDATE transactions SET import_batch_id=:batch_id, external_id=:external_id, import_date=:now, reconciliation_state=:state WHERE id=:id AND user_id=:user_id"), {"batch_id": str(batch_id), "external_id": row["fingerprint"], "now": now, "state": "suggested_match" if row["matches"] else "unmatched", "id": created["id"], "user_id": current_user.id})
        if row["matches"]:
            best = row["matches"][0]
            db.execute(text("INSERT INTO reconciliation_links (user_id, transaction_id, source_type, source_id, expected_amount_cents, actual_amount_cents, variance_cents, status, confidence, created_at, updated_at) VALUES (:user_id, :transaction_id, :source_type, :source_id, :expected, :actual, :variance, 'suggested_match', :confidence, :now, :now)"), {"user_id": current_user.id, "transaction_id": created["id"], "source_type": best["source_type"], "source_id": best["source_id"], "expected": parse_money(best["expected_amount"]), "actual": row["amount_cents"], "variance": parse_money(best["variance"]), "confidence": best["confidence"], "now": now})
            matched += 1
        imported += 1
        imported_dates.append(tx_date)
        imported_rows.append(created)
    span_start = min(imported_dates) if imported_dates else None
    span_end = max(imported_dates) if imported_dates else None
    db.execute(text("""
        UPDATE import_batches
        SET imported_count=:imported, skipped_count=:skipped,
            duplicate_count=:duplicates, matched_count=:matched,
            failed_count=:failed, status='complete',
            transaction_span_start=:span_start,
            transaction_span_end=:span_end,
            updated_at=:now
        WHERE id=:id AND user_id=:user_id
    """), {"id": batch_id, "user_id": current_user.id, "imported": imported, "skipped": skipped, "duplicates": duplicates, "matched": matched, "failed": failed, "span_start": span_start, "span_end": span_end, "now": now})
    db.commit()
    return {"batch_id": batch_id, "rows_processed": len(rows), "new_transactions": imported, "duplicates_skipped": duplicates, "matched": matched, "failed": failed, "transaction_span_start": span_start.isoformat() if span_start else None, "transaction_span_end": span_end.isoformat() if span_end else None, "coverage_status": "unknown", "transactions": imported_rows}


@router.get("/imports/history")
def import_history(current_user: User = USER, db: DbSession = DB):
    rows = db.execute(text("SELECT * FROM import_batches WHERE user_id=:user_id ORDER BY created_at DESC"), {"user_id": current_user.id}).mappings().all()
    return [{"id": row["id"], "filename": row["filename"], "account_id": row["account_id"], "row_count": row["row_count"], "imported_count": row["imported_count"], "skipped_count": row["skipped_count"], "duplicate_count": row["duplicate_count"], "matched_count": row["matched_count"], "failed_count": row["failed_count"], "status": row["status"], "source_type": row.get("source_type") or "csv", "transaction_span_start": str(row.get("transaction_span_start")) if row.get("transaction_span_start") else None, "transaction_span_end": str(row.get("transaction_span_end")) if row.get("transaction_span_end") else None, "coverage_status": row.get("coverage_status") or "unknown", "coverage_start": str(row.get("coverage_start")) if row.get("coverage_start") else None, "coverage_end": str(row.get("coverage_end")) if row.get("coverage_end") else None, "created_at": str(row["created_at"])} for row in rows]


@router.get("/reconciliation/review-queue")
def review_queue(current_user: User = USER, db: DbSession = DB):
    rows = db.execute(text("""
        SELECT rl.*, t.description, t.transaction_date, t.amount_cents, t.category
        FROM reconciliation_links rl
        JOIN transactions t ON t.id = rl.transaction_id
        WHERE rl.user_id=:user_id AND rl.status IN ('suggested_match','needs_review')
        ORDER BY rl.confidence DESC, t.transaction_date DESC
    """), {"user_id": current_user.id}).mappings().all()
    return [{**dict(row), "amount": cents_to_decimal(row["amount_cents"]), "expected_amount": cents_to_decimal(row["expected_amount_cents"]), "actual_amount": cents_to_decimal(row["actual_amount_cents"]), "variance": cents_to_decimal(row["variance_cents"])} for row in rows]


@router.post("/reconciliation/{link_id}/accept")
def accept_match(link_id: int, current_user: User = USER, db: DbSession = DB):
    link = db.execute(text("SELECT * FROM reconciliation_links WHERE id=:id AND user_id=:user_id"), {"id": link_id, "user_id": current_user.id}).mappings().first()
    if not link:
        raise HTTPException(status_code=404, detail="Reconciliation link not found")
    existing = db.execute(text("SELECT id FROM reconciliation_links WHERE user_id=:uid AND transaction_id=:tx AND status='matched' AND id<>:id"), {"uid":current_user.id,"tx":link["transaction_id"],"id":link_id}).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="Transaction already settles another obligation")
    now = utcnow()
    claimed = db.execute(text("UPDATE reconciliation_links SET status='matched', updated_at=:now WHERE id=:id AND user_id=:user_id AND NOT EXISTS (SELECT 1 FROM reconciliation_links other WHERE other.user_id=:user_id AND other.transaction_id=:tx AND other.status='matched' AND other.id<>:id)"), {"id": link_id, "user_id": current_user.id, "tx": link["transaction_id"], "now": now})
    if claimed.rowcount != 1:
        raise HTTPException(status_code=409, detail="Transaction already settles another obligation")
    db.execute(text("UPDATE transactions SET reconciliation_state='matched', updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": link["transaction_id"], "user_id": current_user.id, "now": now})
    if link["source_type"] == "bill":
        db.execute(text("UPDATE bills SET paid_at=:now, resolved_at=:now, remaining_amount_cents=0, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": link["source_id"], "user_id": current_user.id, "now": now})
    if link["source_type"] == "planned_spending":
        db.execute(text("UPDATE planned_spending SET status='purchased', purchased_at=:now, include_in_forecast=0, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": link["source_id"], "user_id": current_user.id, "now": now})
    db.commit()
    return {"status": "matched", "link_id": link_id}


@router.put("/transactions/{transaction_id}/reconcile")
def set_transaction_reconciliation(transaction_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    state = payload.get("state") or "unmatched"
    if state not in RECONCILIATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid reconciliation state")
    db.execute(text("UPDATE transactions SET reconciliation_state=:state, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"state": state, "id": transaction_id, "user_id": current_user.id, "now": utcnow()})
    db.commit()
    rows = list_transactions(db, current_user, None, None, None, None, None, 500)
    return next(row for row in rows if row["id"] == transaction_id)
