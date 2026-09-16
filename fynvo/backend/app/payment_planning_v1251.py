from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession

from .models import User
from .money import cents_to_decimal
from .planning_resilience import (
    PLANNING_EXCEPTIONS,
    exception_reason,
    known_commitment_scope,
)

logger = logging.getLogger(__name__)


def _known_commitments(base, rows: list[dict[str, Any]], current: date, end: date | None) -> list[dict[str, Any]]:
    """Keep partial planning useful without pretending a missing pay boundary exists."""
    if end is not None:
        return base._safe_commitment_rows(rows, current, end)
    horizon_end = current + timedelta(days=base.PAY_CYCLE_INCOME_HORIZON_DAYS)
    result = []
    for row in rows:
        if row.get("status") not in base.FUNDING_STATUSES:
            continue
        when = base._as_date(row.get("expected_date") or row.get("due_date"))
        if row.get("status") == "overdue" or (when is not None and current <= when <= horizon_end):
            result.append(row)
    return result


def build_safe_to_spend(base, db: DbSession, user: User, today: date | None = None) -> dict[str, Any]:
    current = today or base.today_local()
    base.payments_v114.ensure_scheduled_payments(
        db,
        user,
        horizon_days=base.PAY_CYCLE_INCOME_HORIZON_DAYS,
        today=current,
    )
    rows = base.canonical_payment_rows(db, user)
    pay_cycle = None
    pay_cycle_error = None
    try:
        pay_cycle = base.build_pay_cycle_planning(db, user, current, rows)
    except PLANNING_EXCEPTIONS as exc:
        logger.exception("Safe-to-Spend pay-cycle section failed for user_id=%s", user.id)
        pay_cycle_error = exception_reason(exc)

    next_income = pay_cycle.get("next_income") if pay_cycle else None
    end = base._as_date(next_income.get("date")) if next_income else None
    commitments = _known_commitments(base, rows, current, end)
    commitment_scope = known_commitment_scope(current, end)
    balances = base._account_balances(db, user)
    available = sum(balances.values())
    balance_known = bool(balances)
    committed = sum(base._amount_cents(row) for row in commitments)
    buffer_cents = base._safe_buffer_cents(db, user)
    safe_cents = available - committed - buffer_cents if balance_known and end else None

    coverage = []
    running = available - buffer_cents
    first_insufficient_date = None
    for when, _, row in sorted(
        (
            (
                base._as_date(row.get("expected_date") or row.get("due_date")) or current,
                -base._amount_cents(row),
                row,
            )
            for row in commitments
        ),
        key=lambda item: item[0],
    ):
        running -= base._amount_cents(row)
        if first_insufficient_date is None and running < 0:
            first_insufficient_date = when.isoformat()
        coverage.append(
            {
                "date": when.isoformat(),
                "name": row.get("name"),
                "amount": cents_to_decimal(base._amount_cents(row)),
                "projected_balance": cents_to_decimal(running),
            }
        )

    incomplete = not balance_known or end is None or pay_cycle_error is not None
    covered_through = None if first_insufficient_date else (end.isoformat() if end else None)
    if pay_cycle_error:
        unavailable_reason = dict(pay_cycle_error)
    elif not balance_known:
        unavailable_reason = {
            "code": "missing_account_balance",
            "message": "Add an active liquid account balance to calculate Safe to Spend.",
            "action": "accounts",
            "stage": "accounts",
        }
    elif end is None:
        unavailable_reason = {
            "code": "missing_next_income",
            "message": "Add or complete an active income source to set the next pay-cycle boundary.",
            "action": "income",
            "stage": "income",
        }
    else:
        unavailable_reason = None

    warnings = []
    if not balance_known:
        warnings.append("No active liquid account balance is available.")
    if end is None:
        warnings.append("No next pay-cycle boundary is available.")
    if pay_cycle_error:
        warnings.append(pay_cycle_error["message"])

    return {
        "as_of": current.isoformat(),
        "planning_start": current.isoformat(),
        "planning_end": end.isoformat() if end else None,
        "next_income": next_income,
        "available_cash": cents_to_decimal(available) if balance_known else None,
        "eligible_confirmed_income": "0.00",
        "committed_outgoings": cents_to_decimal(committed),
        "commitment_scope": commitment_scope,
        "protected_buffer": cents_to_decimal(buffer_cents),
        "safe_to_spend": cents_to_decimal(safe_cents) if safe_cents is not None else None,
        "projected_shortfall": cents_to_decimal(abs(safe_cents)) if safe_cents is not None and safe_cents < 0 else "0.00",
        "payment_readiness": "needs_information" if incomplete else "covered" if safe_cents >= 0 else "at_risk",
        "incomplete": incomplete,
        "planning_status": "unavailable" if pay_cycle_error else "complete" if not incomplete else "incomplete",
        "planning_error": pay_cycle_error,
        "unavailable_reason": unavailable_reason,
        "warnings": warnings,
        "reserved_payments": commitments,
        "coverage": coverage,
        "payment_coverage": {
            "covered_through": covered_through,
            "first_insufficient_date": first_insufficient_date,
        },
        "rules": {
            "credit_limits_excluded": True,
            "paid_skipped_cancelled_excluded": True,
            "automatic_payments_reserved_until_resolved": True,
        },
    }


def build_payment_planning(base, db: DbSession, user: User, today: date | None = None) -> dict[str, Any]:
    """v1.25.1 wrapper around the authoritative planning engine with precise optional-failure diagnostics."""
    current = today or base.today_local()
    base.payments_v114.ensure_scheduled_payments(db, user, horizon_days=120, today=current)
    rows = base.canonical_payment_rows(db, user)
    periods = {
        key: {"label": label, **base._period_summary(rows, current, days)}
        for key, label, days in base.PLANNING_PERIODS
    }
    funding = base._funding_requirements(rows, db, user, current, 7)
    known = [row for row in funding if row["balance_known"]]
    complete_funding_picture = bool(funding) and len(known) == len(funding)
    available_total = sum(base.parse_money(row["available"]) for row in known)
    required_known = sum(base.parse_money(row["required"]) for row in known)
    household = {
        "available": cents_to_decimal(available_total) if complete_funding_picture else None,
        "upcoming_commitments": periods["next_7_days"]["remaining_funding"],
        "remaining_after_commitments": cents_to_decimal(available_total - required_known) if complete_funding_picture else None,
        "shortfall": cents_to_decimal(max(required_known - available_total, 0)) if complete_funding_picture else None,
        "balance_known": complete_funding_picture,
    }
    attention = []
    for row in rows:
        reason = base._attention_reason(row)
        if reason:
            attention.append({**row, "attention_reason": reason, "requires_action": True})
    dated_outstanding = [
        row
        for row in rows
        if row.get("status") in base.FUNDING_STATUSES
        and base._as_date(row.get("expected_date") or row.get("due_date")) is not None
    ]
    future = [
        row
        for row in dated_outstanding
        if (base._as_date(row.get("expected_date") or row.get("due_date")) or date.min) >= current
    ]
    next_payment = (future or dated_outstanding or [None])[0]
    pay_cycle = None
    pay_cycle_error = None
    try:
        pay_cycle = base.build_pay_cycle_planning(db, user, current, rows)
    except PLANNING_EXCEPTIONS as exc:
        logger.exception("Payment planning pay-cycle section failed for user_id=%s", user.id)
        pay_cycle_error = exception_reason(exc)
    return {
        "as_of": current.isoformat(),
        "rules": {
            "included_statuses": sorted(base.FUNDING_STATUSES),
            "excluded_statuses": sorted(base.TERMINAL_STATUSES),
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
        "timeline": base._timeline(rows, current, 30),
        "pay_cycle": pay_cycle,
        "pay_cycle_error": pay_cycle_error,
    }


def unavailable_account_funding(base, db: DbSession, user: User, exc: BaseException) -> dict[str, Any]:
    current = base.today_local()
    reason = exception_reason(exc)
    try:
        accounts = base._account_rows(db, user)
    except (SQLAlchemyError, ValueError, KeyError, TypeError, AttributeError):
        accounts = []
    rows = []
    for account in accounts:
        if (
            account.get("account_type") not in base.LIQUID_ACCOUNT_TYPES
            or not bool(account.get("is_active"))
            or account.get("archived_at") is not None
        ):
            continue
        balance = int(account.get("opening_balance_cents") or 0) + int(account.get("transaction_total") or 0)
        rows.append(
            {
                "account_id": int(account["id"]),
                "account_name": account.get("name") or "Account",
                "current_balance": cents_to_decimal(balance),
                "cycle_start_date": current.isoformat(),
                "cycle_end_date": None,
                "commitment_total": None,
                "target_balance": None,
                "funding_shortfall": None,
                "funding_surplus": None,
                "commitment_count": None,
                "status": "unavailable",
                "balance_known": True,
                "funding_destination_known": None,
                "reason": reason,
                "setup_action": reason.get("action"),
                "balance_updated_at": str(account.get("balance_updated_at")) if account.get("balance_updated_at") else None,
            }
        )
    current_cycle = {
        "status": "unavailable",
        "cycle_start_date": current.isoformat(),
        "cycle_end_date": None,
        "total_required": None,
        "total_shortfall": None,
        "accounts": rows,
        "unassigned": {"required": None, "commitment_count": None, "commitments": []},
        "reason": reason,
        "setup_action": reason.get("action"),
    }
    next_cycle = {
        "status": "unavailable",
        "cycle_start_date": None,
        "cycle_end_date": None,
        "incoming_payday": None,
        "following_payday": None,
        "total_recommended_allocation": None,
        "accounts": [],
        "unassigned": {"required": None, "commitment_count": None, "commitments": []},
        "reconciles": False,
        "message": reason["message"],
        "reason": reason,
        "setup_action": reason.get("action"),
    }
    return {
        "as_of": current.isoformat(),
        "current_cycle": current_cycle,
        "next_cycle": next_cycle,
        "completeness": {
            "next_income_known": False,
            "cash_balance_known": bool(rows),
            "funding_assignments_complete": False,
            "complete": False,
            "message": reason["message"],
            "reason": reason,
        },
    }
