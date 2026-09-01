from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .banking import ensure_banking_schema
from .budget import analyse_budgets
from .database import get_db
from .finance import (
    list_bills,
    list_income,
    list_planned,
    list_recurring,
    schedule_summary,
    today_local,
)
from .forecast import generate_forecast
from .goals import ensure_goals_schema, list_goals
from .insights import financial_health
from .intelligence import ensure_intelligence_schema
from .ledger import dashboard_position
from .models import User
from .money import cents_to_decimal, parse_money

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)
OUTGOING_KINDS = {"bill", "recurring_expense", "planned_spending"}


def _monthly(value_cents: int, range_days: int) -> str:
    return cents_to_decimal(round(value_cents * 30 / max(range_days, 1)))


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _direction(item: dict[str, Any]) -> str:
    return "in" if item.get("kind") == "income" else "out"


def _signed_event(item: dict[str, Any]) -> dict[str, Any]:
    amount = parse_money(item.get("amount") or "0.00")
    direction = _direction(item)
    signed = amount if direction == "in" else -abs(amount)
    return {**item, "direction": direction, "amount": cents_to_decimal(signed), "absolute_amount": cents_to_decimal(abs(amount))}


def _future_events(events: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    rows = []
    for item in events:
        item_date = _as_date(item.get("date"))
        if item_date and start <= item_date <= end and item.get("status") not in {"paid", "purchased", "cancelled", "resolved"}:
            rows.append(_signed_event(item))
    return rows


def _overdue(bills: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    rows = []
    for item in bills:
        due = _as_date(item.get("due_date"))
        if item.get("status") == "overdue" or (due and due < today and item.get("status") not in {"paid", "resolved"}):
            amount = parse_money(item.get("amount") or item.get("remaining_amount") or "0.00")
            rows.append({"date": item.get("due_date"), "name": item.get("name"), "provider": item.get("provider"), "category": item.get("bill_type") or "Bill", "kind": "bill", "status": "overdue", "direction": "out", "amount": cents_to_decimal(-abs(amount)), "absolute_amount": cents_to_decimal(abs(amount))})
    return rows


def _top_insights(db: DbSession, user: User) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT id,title,summary,importance,category,action_label,action_target,updated_at
            FROM insights
            WHERE user_id=:user_id AND status IN ('new','reviewed')
            ORDER BY CASE importance
                WHEN 'warning' THEN 0
                WHEN 'attention' THEN 1
                WHEN 'opportunity' THEN 2
                ELSE 3 END,
                updated_at DESC
            LIMIT 3
            """
        ),
        {"user_id": user.id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/dashboard/command-centre")
def command_centre_dashboard_v12(
    range_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    ensure_goals_schema(db)
    ensure_intelligence_schema(db)
    ensure_banking_schema(db)
    start = today_local()
    end = start + timedelta(days=range_days)
    upcoming_end = start + timedelta(days=7)
    position = dashboard_position(db, current_user)
    scheduled = schedule_summary(db, current_user, start, end)
    upcoming_scheduled = schedule_summary(db, current_user, start, upcoming_end)
    forecast = generate_forecast(db, current_user, f"{range_days}d", "baseline", start)
    expected_forecast = generate_forecast(db, current_user, f"{range_days}d", "expected", start)
    bills = list_bills(db, current_user)
    recurring = list_recurring(db, current_user)
    planned = list_planned(db, current_user)
    income = list_income(db, current_user)
    budgets = analyse_budgets(db, current_user)
    goals = list_goals(False, db, current_user)
    # The dashboard range selector should not regenerate the entire Insights engine.
    # Insights are refreshed by their own endpoint/page; this call reuses current state.
    health = financial_health(db, current_user, range_days, False)
    top_insights = _top_insights(db, current_user)
    overdue = _overdue(bills, start)
    future_events = _future_events(scheduled["events"], start, end)
    upcoming = _future_events(upcoming_scheduled["events"], start, upcoming_end)[:8]
    commitments = [item for item in future_events if item.get("kind") in OUTGOING_KINDS and item.get("direction") == "out"]
    commitment_source_totals: dict[str, int] = {"bill": 0, "recurring_expense": 0, "planned_spending": 0}
    for item in commitments:
        commitment_source_totals[item["kind"]] += abs(parse_money(item.get("amount") or "0.00"))
    planned_period = [item for item in planned if item.get("status") not in {"cancelled", "purchased"} and item.get("include_in_forecast")]
    planned_cents = sum(parse_money(item["estimated_amount"]) for item in planned_period if item.get("estimated_amount"))
    income_cents = parse_money(scheduled["income"])
    commitments_cents = sum(commitment_source_totals.values())
    bank_freshness = db.execute(text("SELECT max(last_successful_sync) FROM bank_connections WHERE user_id=:user_id AND status IN ('connected','syncing')"), {"user_id": current_user.id}).scalar()
    average_net = _monthly(income_cents - commitments_cents - planned_cents, range_days)
    return {
        "range_days": range_days,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "bank_data_updated_at": str(bank_freshness) if bank_freshness else None,
        "kpis": {
            "available_cash": position["available_cash"],
            "expected_income": scheduled["income"],
            "scheduled_commitments": cents_to_decimal(commitments_cents),
            "planned_spending": cents_to_decimal(planned_cents),
            "projected_balance": forecast["final_balance"],
        },
        "forecast": {
            "baseline": forecast,
            "expected": expected_forecast,
            "summary": {"baseline": forecast["final_balance"], "expected": expected_forecast["final_balance"], "lowest_balance": forecast.get("lowest_balance"), "shortfall": forecast.get("shortfall")},
        },
        "calendar": forecast["events"],
        "upcoming_label": "Upcoming, Next 7 Days",
        "upcoming": upcoming,
        "upcoming_commitments_label": f"Upcoming Commitments, Next {range_days} Days",
        "upcoming_commitments": commitments[:8],
        "upcoming_commitments_summary": {
            "bills": cents_to_decimal(commitment_source_totals["bill"]),
            "recurring_expenses": cents_to_decimal(commitment_source_totals["recurring_expense"]),
            "committed_planned_spending": cents_to_decimal(commitment_source_totals["planned_spending"]),
            "total": cents_to_decimal(commitments_cents),
        },
        "overdue": {"count": len(overdue), "total": cents_to_decimal(sum(abs(parse_money(item["amount"])) for item in overdue)), "items": overdue[:6]},
        "top_planned_spending": planned_period[:5],
        "quick_stats": {
            "average_monthly_income": _monthly(income_cents, range_days),
            "average_monthly_commitments": _monthly(commitments_cents, range_days),
            "average_monthly_planned": _monthly(planned_cents, range_days),
            "average_monthly_net_forecast": average_net,
            "average_monthly_balance": average_net,
        },
        "budget_overview": budgets.get("budgets", [])[:5] if isinstance(budgets, dict) else [],
        "goals": goals[:4],
        "attention": {
            "headline": health["headline"],
            "insights": health["active_insight_count"],
            "warnings": health["warning_count"],
            "attention_count": health["attention_count"],
            "opportunities": health["opportunity_count"],
            "top": top_insights,
        },
        "financial_health": health,
        "counts": {"bills": len(bills), "recurring": len(recurring), "income": len(income), "goals": len(goals)},
    }