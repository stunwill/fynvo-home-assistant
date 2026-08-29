from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import payments_v112, payments_v114
from .models import User
from .money import cents_to_decimal, parse_money

FUNDING_STATUSES = {
    "upcoming",
    "due",
    "due_today",
    "overdue",
    "expected_automatically",
    "auto_payment_unconfirmed",
    "unknown",
}
TERMINAL_STATUSES = {"paid", "skipped", "cancelled"}
PLANNING_PERIODS = (
    ("today", "Today", 0),
    ("next_7_days", "Next 7 Days", 7),
    ("next_14_days", "Next 14 Days", 14),
    ("next_30_days", "Next 30 Days", 30),
)


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _amount_cents(row: dict[str, Any]) -> int:
    value = row.get("expected_amount")
    if value in (None, ""):
        value = row.get("amount")
    return abs(parse_money(value or "0"))


def _bill_suppression_keys(bills: list[dict[str, Any]]) -> set[tuple[int, str]]:
    keys: set[tuple[int, str]] = set()
    for row in bills:
        recurring_id = row.get("recurring_expense_id")
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if recurring_id and when and row.get("status") != "cancelled":
            keys.add((int(recurring_id), when.isoformat()))
    return keys


def canonical_payment_rows(db: DbSession, user: User) -> list[dict[str, Any]]:
    """Return one authoritative planning row per household obligation.

    Bills explicitly linked to a Recurring Expense suppress the matching Scheduled
    Payment occurrence for the same effective date. This avoids counting both the
    expected recurrence and its first-class Bill representation.
    """
    scheduled = payments_v112._scheduled_payment_rows(db, user)
    bills = payments_v112._bill_rows(db, user)
    suppression = _bill_suppression_keys(bills)
    rows = [
        row
        for row in scheduled
        if (
            int(row.get("recurring_expense_id") or 0),
            (_as_date(row.get("expected_date")) or date.min).isoformat(),
        )
        not in suppression
    ]
    rows.extend(bills)
    rows.sort(key=payments_v112._sort_key)
    return rows


def _period_contains(row: dict[str, Any], today: date, days: int) -> bool:
    when = _as_date(row.get("expected_date") or row.get("due_date"))
    if row.get("status") == "overdue":
        return True
    if when is None:
        return False
    if days == 0:
        return when == today
    return today <= when <= today + timedelta(days=days)


def _period_summary(rows: list[dict[str, Any]], today: date, days: int) -> dict[str, Any]:
    relevant = [row for row in rows if _period_contains(row, today, days)]
    outstanding = [row for row in relevant if row.get("status") in FUNDING_STATUSES]
    paid = [row for row in relevant if row.get("status") == "paid"]
    manual = [row for row in outstanding if row.get("payment_handling") != "automatic"]
    automatic = [row for row in outstanding if row.get("payment_handling") == "automatic"]
    overdue = [row for row in outstanding if row.get("status") == "overdue"]
    unresolved_auto = [row for row in outstanding if row.get("status") == "auto_payment_unconfirmed"]
    total = sum(_amount_cents(row) for row in relevant if row.get("status") not in {"skipped", "cancelled"})
    remaining = sum(_amount_cents(row) for row in outstanding)
    return {
        "total_amount": cents_to_decimal(total),
        "payment_count": len(relevant),
        "manual_amount": cents_to_decimal(sum(_amount_cents(row) for row in manual)),
        "manual_count": len(manual),
        "automatic_amount": cents_to_decimal(sum(_amount_cents(row) for row in automatic)),
        "automatic_count": len(automatic),
        "overdue_amount": cents_to_decimal(sum(_amount_cents(row) for row in overdue)),
        "overdue_count": len(overdue),
        "unresolved_automatic_amount": cents_to_decimal(sum(_amount_cents(row) for row in unresolved_auto)),
        "unresolved_automatic_count": len(unresolved_auto),
        "paid_amount": cents_to_decimal(sum(_amount_cents(row) for row in paid)),
        "paid_count": len(paid),
        "remaining_funding": cents_to_decimal(remaining),
        "remaining_count": len(outstanding),
    }


def _account_balances(db: DbSession, user: User) -> dict[int, int]:
    rows = db.execute(
        text(
            """
            SELECT a.id,a.opening_balance_cents,
                   COALESCE(SUM(t.amount_cents),0) AS transaction_total
            FROM accounts a
            LEFT JOIN transactions t ON t.account_id=a.id AND t.user_id=a.user_id
            WHERE a.user_id=:uid AND a.archived_at IS NULL AND a.is_active=1
            GROUP BY a.id,a.opening_balance_cents
            """
        ),
        {"uid": user.id},
    ).mappings().all()
    return {
        int(row["id"]): int(row["opening_balance_cents"] or 0) + int(row["transaction_total"] or 0)
        for row in rows
    }


def _funding_requirements(
    rows: list[dict[str, Any]], db: DbSession, user: User, today: date, days: int = 7
) -> list[dict[str, Any]]:
    balances = _account_balances(db, user)
    names = {
        int(row["id"]): row["name"]
        for row in db.execute(
            text("SELECT id,name FROM accounts WHERE user_id=:uid"), {"uid": user.id}
        ).mappings().all()
    }
    grouped: dict[int | None, dict[str, Any]] = defaultdict(lambda: {"amount_cents": 0, "payments": 0})
    for row in rows:
        if row.get("status") not in FUNDING_STATUSES or not _period_contains(row, today, days):
            continue
        account_id = row.get("account_id")
        if account_id is None and row.get("card_id"):
            account_id = db.execute(
                text("SELECT account_id FROM cards WHERE id=:id AND user_id=:uid"),
                {"id": row["card_id"], "uid": user.id},
            ).scalar()
        key = int(account_id) if account_id is not None else None
        grouped[key]["amount_cents"] += _amount_cents(row)
        grouped[key]["payments"] += 1
    result = []
    for account_id, values in sorted(
        grouped.items(), key=lambda item: (item[0] is None, names.get(item[0], "Account not specified"))
    ):
        required = int(values["amount_cents"])
        available = balances.get(account_id) if account_id is not None else None
        shortfall = max(required - available, 0) if available is not None else None
        result.append(
            {
                "account_id": account_id,
                "account_name": names.get(account_id, "Account not specified")
                if account_id is not None
                else "Account not specified",
                "required": cents_to_decimal(required),
                "payment_count": int(values["payments"]),
                "available": cents_to_decimal(available) if available is not None else None,
                "remaining_after_commitments": cents_to_decimal(available - required)
                if available is not None
                else None,
                "shortfall": cents_to_decimal(shortfall) if shortfall is not None else None,
                "has_shortfall": bool(shortfall) if shortfall is not None else False,
                "balance_known": available is not None,
            }
        )
    return result


def _attention_reason(row: dict[str, Any]) -> str | None:
    if row.get("match_review_available"):
        return "Reconciliation ambiguity"
    if row.get("status") == "auto_payment_unconfirmed":
        return "Automatic payment not confirmed"
    if row.get("status") == "overdue":
        return "Overdue manual payment" if row.get("payment_handling") != "automatic" else "Automatic payment overdue"
    if row.get("status") in {"due", "due_today"} and row.get("payment_handling") != "automatic":
        return "Manual payment due"
    if row.get("payment_method") in {None, "", "not_set"}:
        return "Missing payment method"
    if row.get("payment_method") == "direct_debit" and row.get("account_id") is None:
        return "Missing funding account"
    if row.get("payment_method") == "automatic_card_payment" and row.get("card_id") is None:
        return "Missing funding card"
    if row.get("status") == "unknown":
        return "Unresolved payment"
    return None


def _timeline(rows: list[dict[str, Any]], today: date, horizon_days: int = 30) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("status") in TERMINAL_STATUSES:
            continue
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if when is None:
            continue
        if row.get("status") != "overdue" and not (today <= when <= today + timedelta(days=horizon_days)):
            continue
        enriched = dict(row)
        enriched["attention_reason"] = _attention_reason(row)
        enriched["requires_action"] = bool(enriched["attention_reason"])
        groups[when.isoformat()].append(enriched)
    return [
        {"date": when, "rows": sorted(group, key=payments_v112._sort_key)}
        for when, group in sorted(groups.items())
    ]


def build_payment_planning(db: DbSession, user: User, today: date | None = None) -> dict[str, Any]:
    current = today or date.today()
    payments_v114.ensure_scheduled_payments(db, user, horizon_days=120, today=current)
    rows = canonical_payment_rows(db, user)
    periods = {
        key: {"label": label, **_period_summary(rows, current, days)}
        for key, label, days in PLANNING_PERIODS
    }
    funding = _funding_requirements(rows, db, user, current, 7)
    known = [row for row in funding if row["balance_known"]]
    available_total = sum(parse_money(row["available"]) for row in known)
    required_known = sum(parse_money(row["required"]) for row in known)
    household = {
        "available": cents_to_decimal(available_total) if known else None,
        "upcoming_commitments": periods["next_7_days"]["remaining_funding"],
        "remaining_after_commitments": cents_to_decimal(available_total - required_known) if known else None,
        "shortfall": cents_to_decimal(max(required_known - available_total, 0)) if known else None,
        "balance_known": bool(known),
    }
    attention = []
    for row in rows:
        reason = _attention_reason(row)
        if reason:
            attention.append({**row, "attention_reason": reason, "requires_action": True})
    next_payment = next(
        (
            row
            for row in rows
            if row.get("status") in FUNDING_STATUSES
            and _as_date(row.get("expected_date") or row.get("due_date")) is not None
        ),
        None,
    )
    return {
        "as_of": current.isoformat(),
        "rules": {
            "included_statuses": sorted(FUNDING_STATUSES),
            "excluded_statuses": sorted(TERMINAL_STATUSES),
            "automatic_payments_require_funding": True,
            "bill_suppression": "A Bill linked to the same Recurring Expense and effective date replaces the matching Scheduled Payment in planning totals.",
        },
        "periods": periods,
        "money_needed_soon": {
            "next_7_days": periods["next_7_days"]["remaining_funding"],
            "next_14_days": periods["next_14_days"]["remaining_funding"],
            "next_30_days": periods["next_30_days"]["remaining_funding"],
        },
        "funding_requirements": funding,
        "household_funding": household,
        "attention_count": len(attention),
        "attention": attention,
        "next_payment": next_payment,
        "timeline": _timeline(rows, current, 30),
    }
