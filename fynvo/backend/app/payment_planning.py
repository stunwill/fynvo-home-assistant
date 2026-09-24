from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession

from . import payments_v112, payments_v114, v1
from .finance import today_local
from .models import User
from .money import cents_to_decimal, parse_money

FUNDING_STATUSES = {
    "upcoming",
    "due",
    "due_today",
    "due_soon",
    "overdue",
    "expected_automatically",
    "auto_payment_unconfirmed",
    "unknown",
}
TERMINAL_STATUSES = {"paid", "skipped", "cancelled"}
LIQUID_ACCOUNT_TYPES = {"transaction", "savings", "offset", "cash"}
PLANNING_PERIODS = (
    ("today", "Today", 0),
    ("next_7_days", "Next 7 Days", 7),
    ("next_14_days", "Next 14 Days", 14),
    ("next_30_days", "Next 30 Days", 30),
)
PAY_CYCLE_INCOME_HORIZON_DAYS = 120
PAY_CYCLE_SEQUENCE_LIMIT = 4
SAFE_TO_SPEND_BUFFER_KEY = "safe_to_spend.buffer"
logger = logging.getLogger(__name__)


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


def _safe_buffer_cents(db: DbSession, user: User) -> int:
    value = db.execute(text("SELECT value FROM app_config WHERE key=:key"), {"key": f"{SAFE_TO_SPEND_BUFFER_KEY}.{user.id}"}).scalar()
    return max(parse_money(value or "0"), 0)


def _safe_commitment_rows(rows: list[dict[str, Any]], current: date, end: date | None) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if row.get("status") not in FUNDING_STATUSES:
            continue
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if row.get("status") == "overdue" or (when is not None and (end is None or current <= when < end)):
            result.append(row)
    return result


def build_safe_to_spend(db: DbSession, user: User, today: date | None = None) -> dict[str, Any]:
    """Build one explainable Safe-to-Spend result for all presentation surfaces."""
    current = today or today_local()
    payments_v114.ensure_scheduled_payments(db, user, horizon_days=PAY_CYCLE_INCOME_HORIZON_DAYS, today=current)
    rows = canonical_payment_rows(db, user)
    pay_cycle = None
    pay_cycle_error = None
    try:
        pay_cycle = build_pay_cycle_planning(db, user, current, rows)
    except (SQLAlchemyError, ValueError, KeyError, TypeError, AttributeError):
        # Safe-to-Spend is an optional planning view. Keep known balances and
        # obligations usable when an incomplete pay-cycle input cannot be read.
        logger.exception("Safe-to-Spend pay-cycle section failed for user_id=%s", user.id)
        pay_cycle_error = {"code": "pay_cycle_unavailable", "message": "Pay-cycle planning is temporarily unavailable."}
    next_income = pay_cycle.get("next_income") if pay_cycle else None
    end = _as_date(next_income.get("date")) if next_income else None
    commitments = _safe_commitment_rows(rows, current, end)
    balances = _account_balances(db, user)
    available = sum(balances.values())
    balance_known = bool(balances)
    committed = sum(_amount_cents(row) for row in commitments)
    buffer_cents = _safe_buffer_cents(db, user)
    safe_cents = available - committed - buffer_cents if balance_known and end else None
    coverage = []
    running = available - buffer_cents
    first_insufficient_date = None
    for when, _, row in sorted(((_as_date(row.get("expected_date") or row.get("due_date")) or current, -_amount_cents(row), row) for row in commitments), key=lambda item: item[0]):
        running -= _amount_cents(row)
        if first_insufficient_date is None and running < 0:
            first_insufficient_date = when.isoformat()
        coverage.append({"date": when.isoformat(), "name": row.get("name"), "amount": cents_to_decimal(_amount_cents(row)), "projected_balance": cents_to_decimal(running)})
    incomplete = not balance_known or end is None or pay_cycle_error is not None
    covered_through = None if first_insufficient_date else (end.isoformat() if end else None)
    if pay_cycle_error:
        unavailable_reason = {"code": "pay_cycle_unavailable", "message": pay_cycle_error["message"], "action": "retry"}
    elif not balance_known:
        unavailable_reason = {"code": "missing_account_balance", "message": "Add an active liquid account balance to calculate Safe to Spend.", "action": "accounts"}
    elif end is None:
        unavailable_reason = {"code": "missing_next_income", "message": "Add or complete an active income source to set the next pay-cycle boundary.", "action": "income"}
    else:
        unavailable_reason = None
    return {
        "as_of": current.isoformat(), "planning_start": current.isoformat(), "planning_end": end.isoformat() if end else None,
        "next_income": next_income, "available_cash": cents_to_decimal(available) if balance_known else None,
        "eligible_confirmed_income": "0.00", "committed_outgoings": cents_to_decimal(committed),
        "protected_buffer": cents_to_decimal(buffer_cents), "safe_to_spend": cents_to_decimal(safe_cents) if safe_cents is not None else None,
        "projected_shortfall": cents_to_decimal(abs(safe_cents)) if safe_cents is not None and safe_cents < 0 else "0.00",
        "payment_readiness": "needs_information" if incomplete else "covered" if safe_cents >= 0 else "at_risk",
        "incomplete": incomplete,
        "planning_status": "unavailable" if pay_cycle_error else "complete" if not incomplete else "incomplete",
        "planning_error": pay_cycle_error, "unavailable_reason": unavailable_reason,
        "warnings": (["No active liquid account balance is available."] if not balance_known else []) + (["No next pay-cycle boundary is available."] if end is None else []) + ([pay_cycle_error["message"]] if pay_cycle_error else []),
        "reserved_payments": commitments, "coverage": coverage,
        "payment_coverage": {"covered_through": covered_through, "first_insufficient_date": first_insufficient_date},
        "rules": {"credit_limits_excluded": True, "paid_skipped_cancelled_excluded": True, "automatic_payments_reserved_until_resolved": True},
    }


def _bill_suppression_keys(bills: list[dict[str, Any]]) -> set[tuple[int, str]]:
    keys: set[tuple[int, str]] = set()
    for row in bills:
        recurring_id = row.get("recurring_expense_id")
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if recurring_id and when and row.get("status") != "cancelled":
            keys.add((int(recurring_id), when.isoformat()))
    return keys


def canonical_payment_rows(db: DbSession, user: User) -> list[dict[str, Any]]:
    """Return one authoritative planning row per household obligation."""
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


def _account_rows(db: DbSession, user: User) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT a.id,a.name,a.account_type,a.institution,a.account_suffix,
                       a.opening_balance_cents,COALESCE(a.minimum_balance_cents,0) AS minimum_balance_cents,
                       a.balance_updated_at,a.balance_update_source,a.is_active,a.archived_at,
                       COALESCE(SUM(t.amount_cents),0) AS transaction_total
                FROM accounts a
                LEFT JOIN transactions t ON t.account_id=a.id AND t.user_id=a.user_id
                WHERE a.user_id=:uid
                GROUP BY a.id,a.name,a.account_type,a.institution,a.account_suffix,
                         a.opening_balance_cents,a.minimum_balance_cents,a.balance_updated_at,
                         a.balance_update_source,a.is_active,a.archived_at
                ORDER BY a.name,a.id
                """
            ),
            {"uid": user.id},
        ).mappings().all()
    ]


def _account_balances(db: DbSession, user: User) -> dict[int, int]:
    return {
        int(row["id"]): int(row["opening_balance_cents"] or 0) + int(row["transaction_total"] or 0)
        for row in _account_rows(db, user)
        if row["account_type"] in LIQUID_ACCOUNT_TYPES and bool(row["is_active"]) and row["archived_at"] is None
    }


def _funding_requirements(
    rows: list[dict[str, Any]], db: DbSession, user: User, today: date, days: int = 7
) -> list[dict[str, Any]]:
    balances = _account_balances(db, user)
    names = {
        int(row["id"]): row["name"]
        for row in db.execute(text("SELECT id,name FROM accounts WHERE user_id=:uid"), {"uid": user.id}).mappings().all()
    }
    grouped: dict[int | None, dict[str, Any]] = defaultdict(lambda: {"amount_cents": 0, "payments": 0})
    for row in rows:
        if row.get("status") not in FUNDING_STATUSES or not _period_contains(row, today, days):
            continue
        account_id = _derived_account_id(row, db, user)
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
                "account_name": names.get(account_id, "Account not specified") if account_id is not None else "Account not specified",
                "required": cents_to_decimal(required),
                "payment_count": int(values["payments"]),
                "available": cents_to_decimal(available) if available is not None else None,
                "remaining_after_commitments": cents_to_decimal(available - required) if available is not None else None,
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


def _income_events(db: DbSession, user: User, start: date, end: date) -> list[dict[str, Any]]:
    """Use Fynvo's existing recurrence/effective-change helpers for expected income."""
    rows = db.execute(
        text(
            """
            SELECT * FROM income_sources
            WHERE user_id=:uid AND is_active=1 AND next_payment_date IS NOT NULL AND amount_cents IS NOT NULL
            ORDER BY next_payment_date,id
            """
        ),
        {"uid": user.id},
    ).mappings().all()
    events: list[dict[str, Any]] = []
    for row in rows:
        start_boundary = max(start, _as_date(row.get("start_date")) or start)
        end_boundary = min(end, _as_date(row.get("end_date")) or end)
        if end_boundary < start_boundary:
            continue
        for when in v1._occurrence_dates(
            row.get("next_payment_date"),
            start_boundary,
            end_boundary,
            row.get("frequency"),
            row.get("interval_count"),
            row.get("end_date"),
        ):
            amount = v1._effective_amount(db, user, "income", int(row["id"]), row.get("amount_cents"), when)
            if amount is None:
                continue
            events.append(
                {
                    "date": when.isoformat(),
                    "name": row.get("name"),
                    "amount": cents_to_decimal(int(amount)),
                    "amount_cents": int(amount),
                    "income_id": int(row["id"]),
                    "account_id": row.get("destination_account_id"),
                    "frequency": row.get("frequency"),
                    "complete": bool(row.get("name") and amount is not None and when),
                }
            )
    events.sort(key=lambda item: (item["date"], item["name"] or "", item["income_id"]))
    return events


def _planned_spending_rows(db: DbSession, user: User) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT id,name,planned_date,estimated_amount_cents,account_id,status,include_in_forecast
            FROM planned_spending
            WHERE user_id=:uid AND archived_at IS NULL AND include_in_forecast=1
              AND status IN ('planned','committed') AND planned_date IS NOT NULL AND estimated_amount_cents IS NOT NULL
            ORDER BY planned_date,id
            """
        ),
        {"uid": user.id},
    ).mappings().all()
    return [
        {
            "source_type": "planned_spending",
            "source_id": int(row["id"]),
            "name": row["name"],
            "expected_date": _as_date(row["planned_date"]).isoformat(),
            "expected_amount": cents_to_decimal(abs(int(row["estimated_amount_cents"]))),
            "amount": cents_to_decimal(abs(int(row["estimated_amount_cents"]))),
            "account_id": row["account_id"],
            "status": row["status"],
            "payment_handling": "manual",
            "is_planned_spending": True,
        }
        for row in rows
        if _as_date(row["planned_date"])
    ]


def _derived_account_id(row: dict[str, Any], db: DbSession, user: User) -> int | None:
    account_id = row.get("account_id")
    if account_id is None and row.get("card_id"):
        account_id = db.execute(
            text("SELECT account_id FROM cards WHERE id=:id AND user_id=:uid"),
            {"id": row["card_id"], "uid": user.id},
        ).scalar()
    return int(account_id) if account_id is not None else None


def _commitments_before_income(
    payment_rows: list[dict[str, Any]],
    planned_rows: list[dict[str, Any]],
    current: date,
    income_date: date,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in payment_rows:
        if row.get("status") not in FUNDING_STATUSES:
            continue
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if row.get("status") == "overdue" or (when is not None and current <= when < income_date):
            result.append(row)
    for row in planned_rows:
        when = _as_date(row.get("expected_date"))
        if when is not None and current <= when < income_date:
            result.append(row)
    return result


def _commitment_breakdown(row: dict[str, Any], account_id: int | None) -> dict[str, Any]:
    return {
        "source_type": row.get("source_type"),
        "source_id": row.get("source_id") or row.get("id"),
        "name": row.get("name") or row.get("merchant") or "Payment",
        "date": (_as_date(row.get("expected_date") or row.get("due_date")) or date.min).isoformat(),
        "amount": cents_to_decimal(_amount_cents(row)),
        "status": row.get("status"),
        "account_id": account_id,
        "card_id": row.get("card_id"),
        "is_planned_spending": bool(row.get("is_planned_spending")),
    }


def _monthly_requirements(
    payment_rows: list[dict[str, Any]], planned_rows: list[dict[str, Any]], db: DbSession, user: User, current: date
) -> dict[int, dict[str, Any]]:
    month_start = current.replace(day=1)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    totals: dict[int, dict[str, int]] = defaultdict(lambda: {"scheduled": 0, "remaining": 0, "count": 0})
    for row in [*payment_rows, *planned_rows]:
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if when is None or not month_start <= when < month_end:
            continue
        account_id = _derived_account_id(row, db, user)
        if account_id is None:
            continue
        status_name = row.get("status")
        if status_name not in {"skipped", "cancelled"}:
            totals[account_id]["scheduled"] += _amount_cents(row)
        if status_name in FUNDING_STATUSES:
            totals[account_id]["remaining"] += _amount_cents(row)
            totals[account_id]["count"] += 1
    return {
        account_id: {
            "month": month_start.isoformat(),
            "scheduled_total": cents_to_decimal(values["scheduled"]),
            "remaining_total": cents_to_decimal(values["remaining"]),
            "remaining_count": values["count"],
        }
        for account_id, values in totals.items()
    }


def _account_pay_cycle_requirements(
    commitments: list[dict[str, Any]],
    db: DbSession,
    user: User,
    *,
    cycle_start: date,
    cycle_end: date,
    starting_balances: dict[int, int] | None = None,
    monthly: dict[int, dict[str, Any]] | None = None,
    next_cycle: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    accounts = {int(row["id"]): row for row in _account_rows(db, user)}
    active_balances = starting_balances or {
        account_id: int(row["opening_balance_cents"] or 0) + int(row["transaction_total"] or 0)
        for account_id, row in accounts.items()
        if row["account_type"] in LIQUID_ACCOUNT_TYPES and bool(row["is_active"]) and row["archived_at"] is None
    }
    grouped: dict[int | None, dict[str, Any]] = defaultdict(lambda: {"required": 0, "count": 0, "commitments": []})
    for row in commitments:
        account_id = _derived_account_id(row, db, user)
        grouped[account_id]["required"] += _amount_cents(row)
        grouped[account_id]["count"] += 1
        grouped[account_id]["commitments"].append(_commitment_breakdown(row, account_id))

    output: list[dict[str, Any]] = []
    unassigned_required = 0
    unassigned_count = 0
    account_ids: set[int | None] = set(grouped)
    account_ids.update(active_balances)
    for account_id in account_ids:
        values = grouped[account_id]
        required = int(values["required"])
        count = int(values["count"])
        if account_id is None:
            unassigned_required += required
            unassigned_count += count
            output.append(
                {
                    "account_id": None,
                    "account_name": "Account not specified",
                    "current_balance": None,
                    "projected_starting_balance": None,
                    "cycle_start_date": cycle_start.isoformat(),
                    "cycle_end_date": cycle_end.isoformat(),
                    "required_before_pay": cents_to_decimal(required),
                    "commitment_total": cents_to_decimal(required),
                    "target_balance": None,
                    "recommended_transfer": None,
                    "preferred_buffer": "0.00",
                    "balance_after_commitments": None,
                    "projected_remaining": None,
                    "funding_surplus": None,
                    "funding_shortfall": None,
                    "commitment_count": count,
                    "status": "needs_setup",
                    "balance_known": False,
                    "funding_destination_known": False,
                    "archived": False,
                    "commitments": values["commitments"],
                    "setup_action": "payments",
                }
            )
            continue
        account = accounts.get(account_id)
        active_funding = bool(
            account
            and account["account_type"] in LIQUID_ACCOUNT_TYPES
            and account["is_active"]
            and account["archived_at"] is None
        )
        balance = active_balances.get(account_id) if active_funding else None
        buffer_cents = max(int(account["minimum_balance_cents"] or 0), 0) if account else 0
        target = required + buffer_cents
        remaining = balance - required if balance is not None else None
        shortfall = max(target - balance, 0) if balance is not None else None
        surplus = max(balance - target, 0) if balance is not None else None
        if not active_funding or balance is None:
            status_name = "needs_setup"
        elif count == 0 and buffer_cents == 0:
            status_name = "no_payments_due"
        elif shortfall:
            status_name = "transfer" if next_cycle else "add"
        else:
            status_name = "already_funded" if next_cycle else "covered"
        output.append(
            {
                "account_id": account_id,
                "account_name": account["name"] if account else "Account unavailable",
                "institution": account.get("institution") if account else None,
                "account_suffix": account.get("account_suffix") if account else None,
                "current_balance": cents_to_decimal(
                    int(account["opening_balance_cents"] or 0) + int(account["transaction_total"] or 0)
                ) if active_funding else None,
                "projected_starting_balance": cents_to_decimal(balance) if balance is not None else None,
                "cycle_start_date": cycle_start.isoformat(),
                "cycle_end_date": cycle_end.isoformat(),
                "required_before_pay": cents_to_decimal(required),
                "commitment_total": cents_to_decimal(required),
                "preferred_buffer": cents_to_decimal(buffer_cents),
                "target_balance": cents_to_decimal(target),
                "recommended_transfer": cents_to_decimal(shortfall) if shortfall is not None else None,
                "balance_after_commitments": cents_to_decimal(remaining) if remaining is not None else None,
                "projected_remaining": cents_to_decimal(remaining) if remaining is not None else None,
                "funding_surplus": cents_to_decimal(surplus) if surplus is not None else None,
                "funding_shortfall": cents_to_decimal(shortfall) if shortfall is not None else None,
                "commitment_count": count,
                "status": status_name,
                "balance_known": balance is not None,
                "funding_destination_known": active_funding,
                "archived": bool(account and (not account["is_active"] or account["archived_at"] is not None)),
                "balance_updated_at": str(account["balance_updated_at"]) if account and account["balance_updated_at"] else None,
                "balance_update_source": account.get("balance_update_source") if account else None,
                "monthly_requirement": (monthly or {}).get(
                    account_id,
                    {"month": cycle_start.replace(day=1).isoformat(), "scheduled_total": "0.00", "remaining_total": "0.00", "remaining_count": 0},
                ),
                "commitments": sorted(values["commitments"], key=lambda item: (item["date"], item["name"])),
                "setup_action": None if active_funding else "accounts",
            }
        )
    priority = {"add": 0, "transfer": 0, "needs_setup": 1, "covered": 2, "already_funded": 2, "no_payments_due": 3}
    output.sort(key=lambda row: (priority.get(row["status"], 4), row["account_name"]))
    return output, {
        "required": cents_to_decimal(unassigned_required),
        "commitment_count": unassigned_count,
        "account_funding_unknown": bool(unassigned_count),
        "commitments": sorted(grouped[None]["commitments"], key=lambda item: (item["date"], item["name"])),
        "setup_action": "payments" if unassigned_count else None,
    }


def _commitments_in_cycle(
    payment_rows: list[dict[str, Any]], planned_rows: list[dict[str, Any]], start: date, end: date
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in payment_rows:
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if row.get("status") in FUNDING_STATUSES and row.get("status") != "overdue" and when and start <= when < end:
            rows.append(row)
    for row in planned_rows:
        when = _as_date(row.get("expected_date"))
        if when and start <= when < end:
            rows.append(row)
    return rows


def _active_liquid_cash(db: DbSession, user: User) -> tuple[int, int]:
    balances = _account_balances(db, user)
    return sum(balances.values()), len(balances)


def _cycle_commitment_total(
    payment_rows: list[dict[str, Any]],
    planned_rows: list[dict[str, Any]],
    start: date,
    end: date,
    *,
    include_overdue: bool = False,
) -> int:
    total = 0
    for row in payment_rows:
        if row.get("status") not in FUNDING_STATUSES:
            continue
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if row.get("status") == "overdue":
            if include_overdue:
                total += _amount_cents(row)
        elif when is not None and start <= when < end:
            total += _amount_cents(row)
    for row in planned_rows:
        when = _as_date(row.get("expected_date"))
        if when is not None and start <= when < end:
            total += _amount_cents(row)
    return total


def build_pay_cycle_planning(
    db: DbSession,
    user: User,
    today: date | None = None,
    payment_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current = today or today_local()
    if payment_rows is None:
        payments_v114.ensure_scheduled_payments(db, user, horizon_days=PAY_CYCLE_INCOME_HORIZON_DAYS, today=current)
        payment_rows = canonical_payment_rows(db, user)
    planned_rows = _planned_spending_rows(db, user)
    income_events = _income_events(db, user, current, current + timedelta(days=PAY_CYCLE_INCOME_HORIZON_DAYS))
    current_cash_cents, liquid_account_count = _active_liquid_cash(db, user)

    if not income_events:
        next_30 = _period_summary(payment_rows, current, 30)
        planned_30 = sum(
            _amount_cents(row)
            for row in planned_rows
            if current <= (_as_date(row.get("expected_date")) or date.max) <= current + timedelta(days=30)
        )
        return {
            "as_of": current.isoformat(),
            "timezone": "Australia/Melbourne",
            "status": "unknown",
            "next_income": None,
            "planning_window": {
                "start_date": current.isoformat(),
                "next_income_date": None,
                "days_remaining": None,
                "before_pay_excludes_next_income": True,
                "same_day_ordering": "Income is applied before commitments on the same date. Same-date commitments are therefore after-pay items.",
            },
            "before_next_income": None,
            "after_next_income": None,
            "accounts": [],
            "account_funding": {
                "status": "needs_setup",
                "cycle_start_date": current.isoformat(),
                "cycle_end_date": None,
                "accounts": [],
                "unassigned": {"required": "0.00", "commitment_count": 0, "commitments": []},
            },
            "payday_allocation": {
                "status": "needs_setup",
                "cycle_start_date": None,
                "cycle_end_date": None,
                "total_recommended_allocation": None,
                "accounts": [],
                "unassigned": {"required": "0.00", "commitment_count": 0, "commitments": []},
                "message": "Add or complete an active Income schedule to calculate Payday Allocation.",
            },
            "unassigned": {"required": "0.00", "commitment_count": 0, "account_funding_unknown": False},
            "upcoming_income_events": [],
            "cycles": [],
            "fallback_upcoming_commitments": {
                "next_30_days": cents_to_decimal(parse_money(next_30["remaining_funding"]) + planned_30),
                "payment_count": int(next_30["remaining_count"]),
            },
            "completeness": {
                "next_income_known": False,
                "cash_balance_known": liquid_account_count > 0,
                "funding_assignments_complete": False,
                "complete": False,
                "message": "Next income not known. Upcoming commitments remain available, but a complete before-next-pay plan needs an active Income schedule.",
            },
        }

    next_income = income_events[0]
    next_income_date = _as_date(next_income["date"])
    commitments = _commitments_before_income(payment_rows, planned_rows, current, next_income_date)
    monthly = _monthly_requirements(payment_rows, planned_rows, db, user, current)
    funding_accounts, unassigned = _account_pay_cycle_requirements(
        commitments,
        db,
        user,
        cycle_start=current,
        cycle_end=next_income_date,
        monthly=monthly,
    )
    legacy_status = {"add": "shortfall", "covered": "funded", "no_payments_due": "funded", "needs_setup": "unknown"}
    accounts = [{**row, "status": legacy_status.get(row["status"], row["status"])} for row in funding_accounts]
    commitments_total = sum(_amount_cents(row) for row in commitments)
    overdue_total = sum(
        _amount_cents(row) for row in commitments if row.get("status") == "overdue"
    )
    automatic_total = sum(
        _amount_cents(row)
        for row in commitments
        if row.get("payment_handling") == "automatic" and not row.get("is_planned_spending")
    )
    planned_total = sum(_amount_cents(row) for row in commitments if row.get("is_planned_spending"))
    before_cents = current_cash_cents - commitments_total
    after_cents = before_cents + int(next_income["amount_cents"])
    household_shortfall = max(-before_cents, 0)
    assignments_complete = not unassigned["account_funding_unknown"] and all(
        row["funding_destination_known"] for row in funding_accounts
    )
    cash_known = liquid_account_count > 0
    account_shortfall = any(row["status"] == "add" for row in funding_accounts)
    if not cash_known or not assignments_complete:
        status_name = "unknown"
    elif household_shortfall or account_shortfall:
        status_name = "shortfall"
    else:
        status_name = "funded"

    cycles: list[dict[str, Any]] = []
    running_cash = current_cash_cents
    cycle_start = current
    for index, income in enumerate(income_events[:PAY_CYCLE_SEQUENCE_LIMIT]):
        income_date = _as_date(income["date"])
        cycle_commitments = _cycle_commitment_total(
            payment_rows,
            planned_rows,
            cycle_start,
            income_date,
            include_overdue=index == 0,
        )
        projected_before = running_cash - cycle_commitments
        projected_after = projected_before + int(income["amount_cents"])
        cycles.append(
            {
                "income": income,
                "commitments_before": cents_to_decimal(cycle_commitments),
                "projected_before": cents_to_decimal(projected_before),
                "projected_after": cents_to_decimal(projected_after),
            }
        )
        running_cash = projected_after
        cycle_start = income_date

    active_balances = _account_balances(db, user)
    current_commitments_by_account: dict[int, int] = defaultdict(int)
    for row in commitments:
        account_id = _derived_account_id(row, db, user)
        if account_id in active_balances:
            current_commitments_by_account[int(account_id)] += _amount_cents(row)
    boundary_income_by_account: dict[int, int] = defaultdict(int)
    boundary_income_events = [event for event in income_events if _as_date(event["date"]) == next_income_date]
    for event in boundary_income_events:
        account_id = event.get("account_id")
        if account_id in active_balances:
            boundary_income_by_account[int(account_id)] += int(event["amount_cents"])
    projected_at_payday = {
        account_id: balance - current_commitments_by_account[account_id] + boundary_income_by_account[account_id]
        for account_id, balance in active_balances.items()
    }
    following_event = next((event for event in income_events if _as_date(event["date"]) > next_income_date), None)
    if following_event:
        following_pay_date = _as_date(following_event["date"])
        next_commitments = _commitments_in_cycle(payment_rows, planned_rows, next_income_date, following_pay_date)
        allocation_accounts, next_unassigned = _account_pay_cycle_requirements(
            next_commitments,
            db,
            user,
            cycle_start=next_income_date,
            cycle_end=following_pay_date,
            starting_balances=projected_at_payday,
            monthly=monthly,
            next_cycle=True,
        )
        projection_complete = assignments_complete
        if not projection_complete:
            for row in allocation_accounts:
                row.update(
                    {
                        "projected_starting_balance": None,
                        "recommended_transfer": None,
                        "projected_remaining": None,
                        "funding_surplus": None,
                        "funding_shortfall": None,
                        "status": "needs_setup",
                        "balance_known": False,
                    }
                )
        allocation_total = (
            sum(
                parse_money(row["recommended_transfer"])
                for row in allocation_accounts
                if row["recommended_transfer"] is not None
            )
            if projection_complete
            else None
        )
        payday_allocation = {
            "status": "needs_setup" if not projection_complete or next_unassigned["account_funding_unknown"] or any(row["status"] == "needs_setup" for row in allocation_accounts) else "ready",
            "cycle_start_date": next_income_date.isoformat(),
            "cycle_end_date": following_pay_date.isoformat(),
            "incoming_payday": next_income_date.isoformat(),
            "following_payday": following_pay_date.isoformat(),
            "income_events": boundary_income_events,
            "total_recommended_allocation": cents_to_decimal(allocation_total) if allocation_total is not None else None,
            "accounts": allocation_accounts,
            "unassigned": next_unassigned,
            "reconciles": allocation_total is not None and allocation_total == sum(
                parse_money(row["recommended_transfer"] or "0") for row in allocation_accounts
            ),
            "message": None if projection_complete else "Assign every current-cycle payment to calculate reliable payday balances.",
        }
    else:
        payday_allocation = {
            "status": "needs_setup",
            "cycle_start_date": next_income_date.isoformat(),
            "cycle_end_date": None,
            "incoming_payday": next_income_date.isoformat(),
            "following_payday": None,
            "income_events": boundary_income_events,
            "total_recommended_allocation": None,
            "accounts": [],
            "unassigned": {"required": "0.00", "commitment_count": 0, "commitments": []},
            "reconciles": False,
            "message": "The following payday is not known. Complete the Income schedule to calculate Payday Allocation.",
        }

    current_total_required = sum(parse_money(row["target_balance"] or "0") for row in funding_accounts)
    current_total_shortfall = sum(parse_money(row["funding_shortfall"] or "0") for row in funding_accounts)
    account_funding = {
        "status": "needs_setup" if not cash_known or not assignments_complete else "add" if current_total_shortfall else "covered",
        "cycle_start_date": current.isoformat(),
        "cycle_end_date": next_income_date.isoformat(),
        "total_required": cents_to_decimal(current_total_required),
        "total_shortfall": cents_to_decimal(current_total_shortfall),
        "accounts": funding_accounts,
        "unassigned": unassigned,
    }

    return {
        "as_of": current.isoformat(),
        "timezone": "Australia/Melbourne",
        "status": status_name,
        "next_income": {
            **next_income,
            "days_until": (next_income_date - current).days,
            "reliable": bool(next_income["complete"]),
        },
        "planning_window": {
            "start_date": current.isoformat(),
            "next_income_date": next_income_date.isoformat(),
            "days_remaining": (next_income_date - current).days,
            "before_pay_excludes_next_income": True,
            "same_day_ordering": "Income is applied before commitments on the same date. Same-date commitments are therefore after-pay items.",
        },
        "before_next_income": {
            "commitment_count": len(commitments),
            "commitments_total": cents_to_decimal(commitments_total),
            "overdue_total": cents_to_decimal(overdue_total),
            "automatic_payment_total": cents_to_decimal(automatic_total),
            "planned_spending_total": cents_to_decimal(planned_total),
            "current_available_cash": cents_to_decimal(current_cash_cents) if cash_known else None,
            "projected_cash": cents_to_decimal(before_cents) if cash_known else None,
            "funding_surplus": cents_to_decimal(max(before_cents, 0)) if cash_known else None,
            "funding_shortfall": cents_to_decimal(household_shortfall) if cash_known else None,
        },
        "after_next_income": {
            "projected_cash_before_pay": cents_to_decimal(before_cents) if cash_known else None,
            "next_income_amount": next_income["amount"],
            "projected_cash": cents_to_decimal(after_cents) if cash_known else None,
        },
        "accounts": accounts,
        "account_funding": account_funding,
        "payday_allocation": payday_allocation,
        "unassigned": unassigned,
        "upcoming_income_events": income_events[:PAY_CYCLE_SEQUENCE_LIMIT],
        "cycles": cycles,
        "completeness": {
            "next_income_known": True,
            "cash_balance_known": cash_known,
            "funding_assignments_complete": assignments_complete,
            "complete": bool(next_income["complete"] and cash_known and assignments_complete),
            "buffer_supported": True,
            "message": None if next_income["complete"] and cash_known and assignments_complete else "Some Account funding information is incomplete. Unknown information is not treated as zero.",
        },
    }


def build_payment_planning(db: DbSession, user: User, today: date | None = None) -> dict[str, Any]:
    current = today or today_local()
    payments_v114.ensure_scheduled_payments(db, user, horizon_days=120, today=current)
    rows = canonical_payment_rows(db, user)
    periods = {
        key: {"label": label, **_period_summary(rows, current, days)}
        for key, label, days in PLANNING_PERIODS
    }
    funding = _funding_requirements(rows, db, user, current, 7)
    known = [row for row in funding if row["balance_known"]]
    complete_funding_picture = bool(funding) and len(known) == len(funding)
    available_total = sum(parse_money(row["available"]) for row in known)
    required_known = sum(parse_money(row["required"]) for row in known)
    household = {
        "available": cents_to_decimal(available_total) if complete_funding_picture else None,
        "upcoming_commitments": periods["next_7_days"]["remaining_funding"],
        "remaining_after_commitments": cents_to_decimal(available_total - required_known) if complete_funding_picture else None,
        "shortfall": cents_to_decimal(max(required_known - available_total, 0)) if complete_funding_picture else None,
        "balance_known": complete_funding_picture,
    }
    attention = []
    for row in rows:
        reason = _attention_reason(row)
        if reason:
            attention.append({**row, "attention_reason": reason, "requires_action": True})
    dated_outstanding = [
        row
        for row in rows
        if row.get("status") in FUNDING_STATUSES and _as_date(row.get("expected_date") or row.get("due_date")) is not None
    ]
    future = [
        row
        for row in dated_outstanding
        if (_as_date(row.get("expected_date") or row.get("due_date")) or date.min) >= current
    ]
    next_payment = (future or dated_outstanding or [None])[0]
    pay_cycle = None
    pay_cycle_error = None
    try:
        pay_cycle = build_pay_cycle_planning(db, user, current, rows)
    except (SQLAlchemyError, ValueError, KeyError, TypeError, AttributeError):
        logger.exception("Payment planning pay-cycle section failed for user_id=%s", user.id)
        pay_cycle_error = {"code": "pay_cycle_unavailable", "message": "Pay-cycle planning is temporarily unavailable."}
    return {
        "as_of": current.isoformat(),
        "rules": {
            "included_statuses": sorted(FUNDING_STATUSES),
            "excluded_statuses": sorted(TERMINAL_STATUSES),
            "automatic_payments_require_funding": True,
            "balance_comparison": "Only active liquid Account balances are treated as available funding. Unknown or liability balances are never treated as zero.",
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
        "pay_cycle": pay_cycle,
        "pay_cycle_error": pay_cycle_error,
    }
