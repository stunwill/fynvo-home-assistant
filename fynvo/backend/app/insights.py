from __future__ import annotations

import hashlib
import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .banking import ensure_banking_schema
from .budget import analyse_budgets
from .database import get_db
from .finance import list_recurring, schedule_summary, today_local
from .forecast import generate_forecast
from .goals import ensure_goals_schema, list_goals
from .intelligence import ensure_intelligence_schema
from .models import User
from .money import cents_to_decimal, parse_money
from .scenarios import _comparison, ensure_scenario_schema
from .security import utcnow

router = APIRouter(prefix="/api/insights")
DB = Depends(get_db)
USER = Depends(get_current_user)
INSIGHT_SCHEMA_VERSION = 12
IMPORTANCE_ORDER = {"warning": 0, "attention": 1, "opportunity": 2, "information": 3}
ACTIVE_STATUSES = {"new", "reviewed"}
VALID_STATUSES = ACTIVE_STATUSES | {"dismissed", "resolved"}
LOW_BALANCE_DEFAULT_CENTS = 100_000


def _table_exists(db: DbSession, table_name: str) -> bool:
    return bool(db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table_name}).scalar())


def ensure_insights_schema(db: DbSession) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            insight_type VARCHAR(80) NOT NULL,
            category VARCHAR(40) NOT NULL,
            title VARCHAR(220) NOT NULL,
            summary TEXT NOT NULL,
            importance VARCHAR(20) NOT NULL,
            period_start DATE,
            period_end DATE,
            related_entity_type VARCHAR(60),
            related_entity_id INTEGER,
            evidence_json TEXT NOT NULL,
            supporting_refs_json TEXT,
            confidence VARCHAR(20),
            action_label VARCHAR(120),
            action_target VARCHAR(180),
            status VARCHAR(20) NOT NULL DEFAULT 'new',
            fingerprint VARCHAR(64) NOT NULL,
            generated_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            reviewed_at DATETIME,
            dismissed_at DATETIME,
            resolved_at DATETIME,
            reviewed_by_user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(reviewed_by_user_id) REFERENCES users(id),
            UNIQUE(user_id, fingerprint)
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_insights_user_status ON insights(user_id,status,importance,updated_at)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_insights_user_category ON insights(user_id,category,insight_type)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"))
    current = db.execute(text("SELECT max(version) FROM schema_version")).scalar()
    if current is None:
        db.execute(text("INSERT INTO schema_version (version) VALUES (:version)"), {"version": INSIGHT_SCHEMA_VERSION})
    elif int(current) < INSIGHT_SCHEMA_VERSION:
        db.execute(text("UPDATE schema_version SET version=:version"), {"version": INSIGHT_SCHEMA_VERSION})
    db.commit()


def _json(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _load_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _money_cents(value: Any) -> int:
    if value in (None, ""):
        return 0
    return parse_money(str(value))


def _fingerprint(insight_type: str, entity_type: str | None, entity_id: int | None, material: Any) -> str:
    body = _json({"type": insight_type, "entity_type": entity_type, "entity_id": entity_id, "material": material})
    return hashlib.sha256(body.encode()).hexdigest()[:64]


def _serialize(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["evidence"] = _load_json(item.pop("evidence_json", None), {})
    item["supporting_refs"] = _load_json(item.pop("supporting_refs_json", None), [])
    item["importance_rank"] = IMPORTANCE_ORDER.get(item.get("importance"), 9)
    return item


def _upsert(db: DbSession, user: User, *, insight_type: str, category: str, title: str, summary: str, importance: str, evidence: dict[str, Any], supporting_refs: list[dict[str, Any]] | None = None, period_start: date | None = None, period_end: date | None = None, entity_type: str | None = None, entity_id: int | None = None, confidence: str | None = None, action_label: str | None = None, action_target: str | None = None, material: Any | None = None) -> str:
    if importance not in IMPORTANCE_ORDER:
        raise ValueError(f"Unsupported insight importance: {importance}")
    fingerprint = _fingerprint(insight_type, entity_type, entity_id, evidence if material is None else material)
    existing = db.execute(text("SELECT id,status FROM insights WHERE user_id=:user_id AND fingerprint=:fingerprint"), {"user_id": user.id, "fingerprint": fingerprint}).mappings().first()
    now = utcnow()
    params = {"user_id": user.id, "insight_type": insight_type, "category": category, "title": title, "summary": summary, "importance": importance, "period_start": period_start, "period_end": period_end, "entity_type": entity_type, "entity_id": entity_id, "evidence": _json(evidence), "refs": _json(supporting_refs or []), "confidence": confidence, "action_label": action_label, "action_target": action_target, "fingerprint": fingerprint, "now": now}
    if existing:
        db.execute(text("""
            UPDATE insights SET title=:title,summary=:summary,importance=:importance,period_start=:period_start,
                period_end=:period_end,evidence_json=:evidence,supporting_refs_json=:refs,confidence=:confidence,
                action_label=:action_label,action_target=:action_target,updated_at=:now,
                resolved_at=CASE WHEN status='resolved' THEN NULL ELSE resolved_at END,
                status=CASE WHEN status='resolved' THEN 'new' ELSE status END
            WHERE id=:id AND user_id=:user_id
        """), {**params, "id": existing["id"]})
    else:
        db.execute(text("""
            INSERT INTO insights (
                user_id,insight_type,category,title,summary,importance,period_start,period_end,
                related_entity_type,related_entity_id,evidence_json,supporting_refs_json,confidence,
                action_label,action_target,status,fingerprint,generated_at,updated_at
            ) VALUES (
                :user_id,:insight_type,:category,:title,:summary,:importance,:period_start,:period_end,
                :entity_type,:entity_id,:evidence,:refs,:confidence,:action_label,:action_target,
                'new',:fingerprint,:now,:now
            )
        """), params)
    return fingerprint


def _resolve_stale(db: DbSession, user: User, seen: set[str]) -> None:
    rows = db.execute(text("SELECT id,fingerprint FROM insights WHERE user_id=:user_id AND status IN ('new','reviewed')"), {"user_id": user.id}).mappings().all()
    now = utcnow()
    for row in rows:
        if row["fingerprint"] not in seen:
            db.execute(text("UPDATE insights SET status='resolved',resolved_at=:now,updated_at=:now WHERE id=:id"), {"id": row["id"], "now": now})


def _forecast_insights(db: DbSession, user: User, horizon_days: int, seen: set[str]) -> None:
    horizon = f"{horizon_days}d"
    forecast = generate_forecast(db, user, horizon, "expected")
    start = today_local()
    end = start + timedelta(days=horizon_days)
    low = forecast.get("lowest_balance") or {}
    low_cents = int(low.get("balance_cents") or _money_cents(low.get("balance")))
    shortfall = forecast.get("shortfall")
    events = forecast.get("events") or []
    if shortfall:
        when = _as_date(shortfall.get("date"))
        nearby = [event for event in events if when and _as_date(event.get("date")) and abs((_as_date(event.get("date")) - when).days) <= 5][:8]
        evidence = {"shortfall_balance": shortfall.get("balance"), "shortfall_date": shortfall.get("date"), "forecast_horizon_days": horizon_days, "key_nearby_events": nearby}
        seen.add(_upsert(db, user, insight_type="cash_shortfall", category="cash_flow", title="Projected cash shortfall", summary=f"Available cash is forecast to fall below zero around {shortfall.get('date')}, reaching approximately {shortfall.get('balance')}.", importance="warning", evidence=evidence, supporting_refs=[{"type": "forecast_event", "date": item.get("date"), "name": item.get("name"), "amount": item.get("amount")} for item in nearby], period_start=start, period_end=end, action_label="View Cash Flow", action_target="Cash Flow", material={"date": shortfall.get("date"), "balance": shortfall.get("balance")}))
    elif low_cents < LOW_BALANCE_DEFAULT_CENTS:
        evidence = {"lowest_balance": low.get("balance"), "lowest_balance_date": low.get("date"), "threshold": cents_to_decimal(LOW_BALANCE_DEFAULT_CENTS), "forecast_horizon_days": horizon_days}
        seen.add(_upsert(db, user, insight_type="low_balance", category="cash_flow", title="Projected balance falls below the low-balance threshold", summary=f"The lowest projected balance is {low.get('balance')} on {low.get('date')}, below the current {cents_to_decimal(LOW_BALANCE_DEFAULT_CENTS)} review threshold.", importance="attention", evidence=evidence, period_start=start, period_end=end, action_label="View Cash Flow", action_target="Cash Flow", material={"date": low.get("date"), "balance": low.get("balance"), "threshold": LOW_BALANCE_DEFAULT_CENTS}))
    schedule = schedule_summary(db, user, start, end)
    outgoing = [item for item in schedule.get("events", []) if item.get("kind") != "income" and item.get("status") not in {"paid", "resolved", "cancelled", "purchased"}]
    next_14_end = start + timedelta(days=13)
    next_14 = [item for item in outgoing if _as_date(item.get("date")) and start <= _as_date(item.get("date")) <= next_14_end]
    next_14_total = sum(abs(_money_cents(item.get("amount"))) for item in next_14)
    all_total = sum(abs(_money_cents(item.get("amount"))) for item in outgoing)
    comparison_periods = max(horizon_days / 14, 1)
    typical_14 = round(all_total / comparison_periods)
    if next_14_total >= max(round(typical_14 * 1.35), 100_000) and next_14:
        evidence = {"next_14_days": cents_to_decimal(next_14_total), "typical_14_days": cents_to_decimal(typical_14), "difference": cents_to_decimal(next_14_total - typical_14), "commitments": next_14[:10]}
        seen.add(_upsert(db, user, insight_type="upcoming_financial_pressure", category="cash_flow", title="Higher commitment period approaching", summary=f"The next 14 days contain {cents_to_decimal(next_14_total)} of scheduled outgoings, compared with about {cents_to_decimal(typical_14)} for a typical 14-day period in this forecast.", importance="attention", evidence=evidence, supporting_refs=[{"type": item.get("kind"), "date": item.get("date"), "name": item.get("name"), "amount": item.get("amount")} for item in next_14[:10]], period_start=start, period_end=next_14_end, action_label="View Calendar", action_target="Calendar", material={"next_14": next_14_total, "typical_14": typical_14}))


def _budget_insights(db: DbSession, user: User, seen: set[str]) -> None:
    analysis = analyse_budgets(db, user)
    for budget in analysis.get("budgets", []):
        available = _money_cents(budget.get("available_budget")); actual = _money_cents(budget.get("actual")); forecast = _money_cents(budget.get("forecast")); variance = forecast - available
        utilisation = int(budget.get("utilisation_percent") or 0); elapsed = int(budget.get("period_elapsed_percent") or 0)
        common = {"budget": budget.get("available_budget"), "actual": budget.get("actual"), "committed": budget.get("committed"), "planned": budget.get("planned"), "forecast": budget.get("forecast"), "projected_variance": budget.get("projected_variance"), "utilisation_percent": utilisation, "period_elapsed_percent": elapsed, "period_start": budget.get("period_start"), "period_end": budget.get("period_end"), "relationship_mode": budget.get("relationship_mode"), "counts": budget.get("counts")}
        if variance > 0:
            importance = "warning" if available > 0 and variance / available >= 0.2 else "attention"
            seen.add(_upsert(db, user, insight_type="budget_projected_over", category="budgets", title=f"{budget['name']} is projected over budget", summary=f"{budget['name']} is forecast to finish approximately {cents_to_decimal(variance)} over its {budget.get('period')} budget.", importance=importance, evidence=common, period_start=_as_date(budget.get("period_start")), period_end=_as_date(budget.get("period_end")), entity_type="budget", entity_id=int(budget["id"]), action_label="View Budget", action_target="Budgeting", material={"budget_id": budget["id"], "variance": variance, "forecast": forecast, "available": available}))
        elif elapsed > 0 and utilisation >= elapsed + 20 and actual > 0:
            seen.add(_upsert(db, user, insight_type="budget_pace", category="budgets", title=f"{budget['name']} is being used faster than the period is progressing", summary=f"{budget['name']} has used {utilisation}% of its budget while {elapsed}% of the period has elapsed.", importance="attention", evidence=common, period_start=_as_date(budget.get("period_start")), period_end=_as_date(budget.get("period_end")), entity_type="budget", entity_id=int(budget["id"]), action_label="View Budget", action_target="Budgeting", material={"budget_id": budget["id"], "utilisation": utilisation, "elapsed": elapsed}))
        elif elapsed >= 50 and available > 0 and forecast <= round(available * 0.85):
            remaining = max(available - forecast, 0)
            seen.add(_upsert(db, user, insight_type="budget_positive", category="budgets", title=f"{budget['name']} is tracking below budget", summary=f"Current records forecast {budget['name']} to finish about {cents_to_decimal(remaining)} below its available budget.", importance="opportunity", evidence=common, period_start=_as_date(budget.get("period_start")), period_end=_as_date(budget.get("period_end")), entity_type="budget", entity_id=int(budget["id"]), action_label="View Budget", action_target="Budgeting", material={"budget_id": budget["id"], "remaining": remaining, "period_end": budget.get("period_end")}))
    unbudgeted = analysis.get("unbudgeted_categories", [])
    if unbudgeted:
        total = sum(_money_cents(item.get("actual")) for item in unbudgeted)
        evidence = {"count": len(unbudgeted), "amount": cents_to_decimal(total), "categories": unbudgeted[:12]}
        seen.add(_upsert(db, user, insight_type="unbudgeted_spending", category="budgets", title="Spending exists in categories without an active budget", summary=f"{len(unbudgeted)} categories contain {cents_to_decimal(total)} of activity in the analysis period without an active budget.", importance="information", evidence=evidence, action_label="Review Budgets", action_target="Budgeting", material={"categories": [(item.get("category"), item.get("actual")) for item in unbudgeted[:20]]}))


def _spending_insights(db: DbSession, user: User, seen: set[str]) -> None:
    ensure_intelligence_schema(db)
    today = today_local(); current_start = today - timedelta(days=55); previous_start = today - timedelta(days=111)
    rows = db.execute(text("""
        SELECT t.category,
               SUM(CASE WHEN t.transaction_date BETWEEN :current_start AND :today THEN ABS(t.amount_cents) ELSE 0 END) AS current_total,
               SUM(CASE WHEN t.transaction_date BETWEEN :previous_start AND :previous_end THEN ABS(t.amount_cents) ELSE 0 END) AS previous_total,
               SUM(CASE WHEN t.transaction_date BETWEEN :current_start AND :today THEN 1 ELSE 0 END) AS current_count,
               SUM(CASE WHEN t.transaction_date BETWEEN :previous_start AND :previous_end THEN 1 ELSE 0 END) AS previous_count
        FROM transactions t LEFT JOIN transaction_intelligence ti ON ti.transaction_id=t.id AND ti.user_id=t.user_id
        WHERE t.user_id=:user_id AND t.transaction_type='expense' AND t.category IS NOT NULL AND t.category!=''
          AND t.transaction_date BETWEEN :previous_start AND :today AND COALESCE(ti.exclude_from_baseline,0)=0
        GROUP BY t.category
    """), {"user_id": user.id, "current_start": current_start, "today": today, "previous_start": previous_start, "previous_end": current_start - timedelta(days=1)}).mappings().all()
    for row in rows:
        current = int(row["current_total"] or 0); previous = int(row["previous_total"] or 0); current_count = int(row["current_count"] or 0); previous_count = int(row["previous_count"] or 0)
        if current_count < 3 or previous_count < 3 or previous <= 0: continue
        pct = round(((current - previous) / previous) * 100, 1)
        if abs(pct) < 15: continue
        weekly_current = round(current / 8); weekly_previous = round(previous / 8); direction = "higher" if pct > 0 else "lower"
        evidence = {"category": row["category"], "current_8_weeks": cents_to_decimal(current), "previous_8_weeks": cents_to_decimal(previous), "current_weekly_average": cents_to_decimal(weekly_current), "previous_weekly_average": cents_to_decimal(weekly_previous), "difference_weekly": cents_to_decimal(weekly_current - weekly_previous), "percent_change": pct, "current_transactions": current_count, "previous_transactions": previous_count, "one_off_exclusions_respected": True}
        seen.add(_upsert(db, user, insight_type="category_spending_trend", category="spending", title=f"{row['category']} spending is trending {direction}", summary=f"The rolling 8-week average is {cents_to_decimal(weekly_current)}/week, compared with {cents_to_decimal(weekly_previous)}/week in the previous 8 weeks ({pct:+.1f}%).", importance="attention" if pct >= 20 else "opportunity" if pct <= -15 else "information", evidence=evidence, supporting_refs=[{"type": "category", "name": row["category"], "date_from": current_start.isoformat(), "date_to": today.isoformat()}], period_start=previous_start, period_end=today, entity_type="category", action_label="Review Transactions", action_target="Transactions", material={"category": row["category"], "current": current, "previous": previous}))
    suggestions = db.execute(text("""
        SELECT id,suggestion_type,title,description,confidence,evidence_json FROM intelligence_suggestions
        WHERE user_id=:user_id AND status='new' AND suggestion_type IN ('unusual_spending','spending_trend','recurring_amount_change','recurring_expense_detected','recurring_income_detected')
        ORDER BY updated_at DESC LIMIT 20
    """), {"user_id": user.id}).mappings().all()
    for row in suggestions:
        evidence = _load_json(row["evidence_json"], {}); suggestion_type = row["suggestion_type"]; category = "recurring_costs" if suggestion_type.startswith("recurring_") else "spending"; importance = "attention" if suggestion_type in {"unusual_spending", "recurring_amount_change"} else "information"
        seen.add(_upsert(db, user, insight_type=suggestion_type, category=category, title=row["title"], summary=row["description"], importance=importance, evidence={"source": "Spending Intelligence", **evidence}, confidence=row["confidence"], entity_type="intelligence_suggestion", entity_id=int(row["id"]), action_label="Review Suggestion", action_target="Spending Intelligence", material={"suggestion_id": row["id"], "evidence": evidence}))


def _monthly_equivalent_cents(amount_cents: int, frequency: str) -> int:
    if frequency == "weekly": return round(amount_cents * 52 / 12)
    if frequency == "fortnightly": return round(amount_cents * 26 / 12)
    if frequency in {"every_4_weeks", "every_28_days"}: return round(amount_cents * 13 / 12)
    if frequency == "quarterly": return round(amount_cents / 3)
    if frequency in {"annual", "yearly"}: return round(amount_cents / 12)
    return amount_cents


def _recurring_health(db: DbSession, user: User, seen: set[str]) -> dict[str, Any]:
    rows = [item for item in list_recurring(db, user) if item.get("is_active") and item.get("amount") not in (None, "")]
    monthly = 0; detail = []
    for item in rows:
        amount = abs(_money_cents(item.get("amount"))); equivalent = _monthly_equivalent_cents(amount, str(item.get("frequency") or "monthly")); monthly += equivalent
        detail.append({"id": item.get("id"), "name": item.get("name"), "frequency": item.get("frequency"), "amount": item.get("amount"), "monthly_equivalent": cents_to_decimal(equivalent), "annual_equivalent": cents_to_decimal(equivalent * 12)})
    return {"monthly_equivalent": cents_to_decimal(monthly), "annual_equivalent": cents_to_decimal(monthly * 12), "count": len(detail), "items": sorted(detail, key=lambda item: _money_cents(item["monthly_equivalent"]), reverse=True)}


def _income_and_savings_insights(db: DbSession, user: User, seen: set[str]) -> dict[str, Any]:
    """Report actual savings evidence without treating unconfirmed planned income as missing.

    Scheduled income is authoritative planning data in Fynvo. Imported transaction income is
    useful for historical savings calculations, but users are not required to confirm every
    planned income occurrence by matching it to a bank transaction. Consequently this service
    deliberately does not create an `income_vs_expected` warning.
    """
    today = today_local(); month_start = today.replace(day=1); month_end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    expected = _money_cents(schedule_summary(db, user, month_start, month_end).get("income"))
    actual_income = db.execute(text("SELECT COALESCE(SUM(ABS(amount_cents)),0) FROM transactions WHERE user_id=:user_id AND transaction_type='income' AND transaction_date BETWEEN :start AND :end AND lower(COALESCE(description,'')) NOT LIKE '%refund%'"), {"user_id": user.id, "start": month_start, "end": today}).scalar() or 0
    actual_expense = db.execute(text("SELECT COALESCE(SUM(ABS(amount_cents)),0) FROM transactions WHERE user_id=:user_id AND transaction_type='expense' AND transaction_date BETWEEN :start AND :end"), {"user_id": user.id, "start": month_start, "end": today}).scalar() or 0
    uncategorised = db.execute(text("SELECT COUNT(*) FROM transactions WHERE user_id=:user_id AND transaction_type='expense' AND transaction_date BETWEEN :start AND :end AND (category IS NULL OR category='')"), {"user_id": user.id, "start": month_start, "end": today}).scalar() or 0
    savings_rate = None
    data_quality_ok = actual_income > 0 and int(uncategorised) <= 5
    if data_quality_ok:
        net = int(actual_income) - int(actual_expense); savings_rate = round((net / int(actual_income)) * 100, 1)
    return {"planned_income": cents_to_decimal(expected), "actual_income": cents_to_decimal(actual_income), "actual_expense": cents_to_decimal(actual_expense), "net_savings": cents_to_decimal(int(actual_income) - int(actual_expense)), "savings_rate_percent": savings_rate, "formula": "(actual income - actual expense) / actual income", "reliable": data_quality_ok}


def _goal_insights(db: DbSession, user: User, horizon_days: int, seen: set[str]) -> None:
    ensure_goals_schema(db); goals = list_goals(False, db, user); required_monthly = 0
    for goal in goals:
        progress = goal.get("progress") or {}; status_name = progress.get("status") or goal.get("calculated_status"); required = _money_cents(progress.get("required_contribution")); current = _money_cents(progress.get("current_contribution")); frequency = progress.get("contribution_frequency") or goal.get("contribution_frequency") or "monthly"; required_monthly += _monthly_equivalent_cents(required, frequency)
        if status_name == "behind":
            evidence = {"target": progress.get("target"), "current": progress.get("current"), "remaining": progress.get("remaining"), "required_contribution": progress.get("required_contribution"), "current_contribution": progress.get("current_contribution"), "contribution_frequency": frequency, "target_date": goal.get("target_date"), "forecast_completion_date": progress.get("forecast_completion_date")}
            seen.add(_upsert(db, user, insight_type="goal_behind", category="goals", title=f"{goal['name']} is behind its target schedule", summary=f"The current contribution is {progress.get('current_contribution')} {frequency}, compared with about {progress.get('required_contribution')} required for the target date.", importance="attention", evidence=evidence, entity_type="goal", entity_id=int(goal["id"]), action_label="Open Goal", action_target="Goals", material={"goal_id": goal["id"], "required": required, "current": current, "forecast_completion": progress.get("forecast_completion_date")}))
        elif status_name == "ahead" and _money_cents(progress.get("remaining")) > 0:
            seen.add(_upsert(db, user, insight_type="goal_ahead", category="goals", title=f"{goal['name']} is ahead of its target schedule", summary=f"{goal['name']} is currently ahead of the contribution schedule implied by its target date.", importance="opportunity", evidence={"target": progress.get("target"), "current": progress.get("current"), "target_date": goal.get("target_date"), "forecast_completion_date": progress.get("forecast_completion_date"), "status": status_name}, entity_type="goal", entity_id=int(goal["id"]), action_label="Open Goal", action_target="Goals", material={"goal_id": goal["id"], "status": "ahead", "current": progress.get("current")}))
    if goals and required_monthly > 0:
        forecast = generate_forecast(db, user, f"{horizon_days}d", "expected"); start_balance = _money_cents(forecast.get("starting_balance")); end_balance = _money_cents(forecast.get("final_balance")); months = max(horizon_days / 30.4375, 1); monthly_surplus = round((end_balance - start_balance) / months)
        if required_monthly > max(monthly_surplus, 0):
            gap = required_monthly - max(monthly_surplus, 0)
            seen.add(_upsert(db, user, insight_type="goal_competition", category="goals", title="Goal contribution requirements exceed the current forecast surplus", summary=f"Active Goals require about {cents_to_decimal(required_monthly)}/month, while the selected forecast implies about {cents_to_decimal(max(monthly_surplus, 0))}/month of net surplus. The difference is {cents_to_decimal(gap)}/month.", importance="attention", evidence={"required_goal_contributions_monthly": cents_to_decimal(required_monthly), "forecast_surplus_monthly": cents_to_decimal(max(monthly_surplus, 0)), "difference_monthly": cents_to_decimal(gap), "horizon_days": horizon_days}, action_label="Review Goals", action_target="Goals", material={"required_monthly": required_monthly, "forecast_surplus_monthly": monthly_surplus}))


def _scenario_insights(db: DbSession, user: User, seen: set[str]) -> None:
    ensure_scenario_schema(db)
    rows = db.execute(text("SELECT * FROM scenarios WHERE user_id=:user_id AND status='active' ORDER BY updated_at DESC LIMIT 5"), {"user_id": user.id}).mappings().all()
    for row in rows:
        scenario = dict(row); adjustment_rows = db.execute(text("SELECT * FROM scenario_adjustments WHERE scenario_id=:id AND user_id=:user_id ORDER BY id"), {"id": row["id"], "user_id": user.id}).mappings().all(); scenario["adjustments"] = []
        for adjustment in adjustment_rows:
            item = dict(adjustment); item["amount"] = cents_to_decimal(item["amount_cents"]) if item.get("amount_cents") is not None else None; scenario["adjustments"].append(item)
        comparison = _comparison(db, user, scenario, scenario.get("forecast_horizon") or "90d"); delta = _money_cents(comparison.get("difference")); low_delta = _money_cents(comparison.get("lowest_balance_difference"))
        if delta == 0 and low_delta == 0 and not comparison.get("shortfall_created"): continue
        if comparison.get("shortfall_created"): importance = "warning"; title = f"{scenario['name']} creates a projected cash shortfall"
        elif delta > 0: importance = "opportunity"; title = f"{scenario['name']} improves the projected balance"
        else: importance = "attention"; title = f"{scenario['name']} reduces the projected balance"
        seen.add(_upsert(db, user, insight_type="scenario_impact", category="scenarios", title=title, summary=f"Compared with baseline, this Scenario changes the end balance by {comparison.get('difference')} and the lowest projected balance by {comparison.get('lowest_balance_difference')}.", importance=importance, evidence={"end_balance_difference": comparison.get("difference"), "lowest_balance_difference": comparison.get("lowest_balance_difference"), "shortfall_created": comparison.get("shortfall_created"), "horizon": comparison.get("horizon"), "isolated": comparison.get("isolated")}, entity_type="scenario", entity_id=int(row["id"]), action_label="Open Scenario", action_target="Scenarios", material={"scenario_id": row["id"], "end_delta": delta, "low_delta": low_delta, "shortfall_created": comparison.get("shortfall_created")}))


def _data_quality_insights(db: DbSession, user: User, seen: set[str]) -> dict[str, Any]:
    today = today_local(); start = today - timedelta(days=90)
    uncategorised = db.execute(text("SELECT COUNT(*) AS count,COALESCE(SUM(ABS(amount_cents)),0) AS total FROM transactions WHERE user_id=:user_id AND transaction_type='expense' AND transaction_date BETWEEN :start AND :end AND (category IS NULL OR category='')"), {"user_id": user.id, "start": start, "end": today}).mappings().first(); uncategorised_count = int(uncategorised["count"] or 0); uncategorised_total = int(uncategorised["total"] or 0)
    if uncategorised_count:
        evidence = {"transaction_count": uncategorised_count, "amount": cents_to_decimal(uncategorised_total), "period_days": 90}
        seen.add(_upsert(db, user, insight_type="uncategorised_transactions", category="data_quality", title="Uncategorised transactions may reduce Insight accuracy", summary=f"{uncategorised_count} transactions worth {cents_to_decimal(uncategorised_total)} are uncategorised in the last 90 days.", importance="attention" if uncategorised_count >= 10 else "information", evidence=evidence, period_start=start, period_end=today, action_label="Review Transactions", action_target="Transactions", material=evidence))
    backlog = 0
    if _table_exists(db, "reconciliation_links"):
        backlog = db.execute(text("SELECT COUNT(*) FROM reconciliation_links WHERE user_id=:user_id AND status IN ('unmatched','suggested_match','needs_review')"), {"user_id": user.id}).scalar() or 0
    if backlog:
        evidence = {"review_queue_count": int(backlog)}
        seen.add(_upsert(db, user, insight_type="reconciliation_backlog", category="data_quality", title="Reconciliation items still need review", summary=f"{int(backlog)} imported or synchronised transactions remain in the reconciliation review queue.", importance="information" if int(backlog) < 10 else "attention", evidence=evidence, action_label="Open Review Queue", action_target="Review Queue", material=evidence))
    ensure_banking_schema(db)
    stale_rows = db.execute(text("SELECT id,institution_name,last_successful_sync FROM bank_connections WHERE user_id=:user_id AND status IN ('connected','syncing')"), {"user_id": user.id}).mappings().all(); stale = []
    for row in stale_rows:
        last = row["last_successful_sync"]
        if not last: stale.append({"id": row["id"], "institution": row["institution_name"], "last_successful_sync": None}); continue
        last_dt = last if isinstance(last, datetime) else datetime.fromisoformat(str(last))
        if last_dt.date() < today - timedelta(days=2): stale.append({"id": row["id"], "institution": row["institution_name"], "last_successful_sync": str(last)})
    if stale:
        seen.add(_upsert(db, user, insight_type="stale_bank_data", category="data_quality", title="Connected bank data may be stale", summary=f"{len(stale)} connected bank source{'s have' if len(stale) != 1 else ' has'} not synchronised successfully within the last 2 days.", importance="attention", evidence={"connections": stale, "stale_after_days": 2}, action_label="Review Bank Connections", action_target="Accounts", material=stale))
    return {"uncategorised_count": uncategorised_count, "reconciliation_backlog": int(backlog), "stale_connections": len(stale)}


def generate_insights(db: DbSession, user: User, horizon_days: int = 90) -> dict[str, Any]:
    ensure_insights_schema(db); ensure_intelligence_schema(db); ensure_goals_schema(db); ensure_scenario_schema(db); ensure_banking_schema(db); seen: set[str] = set()
    _forecast_insights(db, user, horizon_days, seen); _budget_insights(db, user, seen); _spending_insights(db, user, seen); recurring = _recurring_health(db, user, seen); savings = _income_and_savings_insights(db, user, seen); _goal_insights(db, user, horizon_days, seen); _scenario_insights(db, user, seen); data_quality = _data_quality_insights(db, user, seen); _resolve_stale(db, user, seen); db.commit()
    active_count = db.execute(text("SELECT COUNT(*) FROM insights WHERE user_id=:user_id AND status IN ('new','reviewed')"), {"user_id": user.id}).scalar() or 0
    return {"generated": len(seen), "active": int(active_count), "horizon_days": horizon_days, "generated_at": utcnow().isoformat(), "recurring_commitments": recurring, "savings": savings, "data_quality": data_quality}


def _dimension_status(rows: list[dict[str, Any]], category: str, fallback: str = "stable") -> str:
    matching = [row for row in rows if row["category"] == category and row["status"] in ACTIVE_STATUSES]
    if any(row["importance"] == "warning" for row in matching): return "warning"
    if any(row["importance"] == "attention" for row in matching): return "needs_attention"
    if any(row["importance"] == "opportunity" for row in matching): return "improving"
    return fallback


def financial_health(db: DbSession, user: User, horizon_days: int = 90, refresh: bool = True) -> dict[str, Any]:
    generation = generate_insights(db, user, horizon_days) if refresh else None
    if not refresh: ensure_insights_schema(db)
    rows = [_serialize(row) for row in db.execute(text("SELECT * FROM insights WHERE user_id=:user_id AND status IN ('new','reviewed')"), {"user_id": user.id}).mappings().all()]
    warning_count = sum(1 for row in rows if row["importance"] == "warning"); attention_count = sum(1 for row in rows if row["importance"] == "attention"); opportunity_count = sum(1 for row in rows if row["importance"] == "opportunity")
    goals = list_goals(False, db, user); on_track_goals = sum(1 for goal in goals if (goal.get("progress") or {}).get("status") in {"on_track", "ahead", "completed"}); budgets = analyse_budgets(db, user); on_track_budgets = sum(1 for item in budgets.get("budgets", []) if item.get("status") == "on_track")
    dimensions = {"cash_flow": {"label": "Cash Flow", "status": _dimension_status(rows, "cash_flow", "healthy")}, "budgets": {"label": "Budget Health", "status": _dimension_status(rows, "budgets", "on_track")}, "spending": {"label": "Spending Stability", "status": _dimension_status(rows, "spending", "stable")}, "recurring_costs": {"label": "Recurring Commitments", "status": _dimension_status(rows, "recurring_costs", "stable")}, "income": {"label": "Income", "status": _dimension_status(rows, "income", "stable")}, "goals": {"label": "Goals", "status": _dimension_status(rows, "goals", "on_track")}, "data_quality": {"label": "Data Quality", "status": _dimension_status(rows, "data_quality", "healthy")}}
    return {"headline": f"{warning_count + attention_count} item{'s' if warning_count + attention_count != 1 else ''} need attention" if warning_count + attention_count else "No major financial-health issues detected", "warning_count": warning_count, "attention_count": attention_count, "opportunity_count": opportunity_count, "active_insight_count": len(rows), "budgets_on_track": {"count": on_track_budgets, "total": len(budgets.get("budgets", []))}, "goals_on_track": {"count": on_track_goals, "total": len(goals)}, "dimensions": dimensions, "calculation": "Financial Health is a transparent set of component statuses. Fynvo does not calculate an opaque overall score.", "generated": generation}


@router.post("/refresh")
def refresh_insights(horizon_days: int = Query(90, ge=7, le=365), db: DbSession = DB, current_user: User = USER): return generate_insights(db, current_user, horizon_days)


@router.get("")
def list_insights(insight_status: str = Query("current", alias="status"), importance: str | None = None, category: str | None = None, horizon_days: int = Query(90, ge=7, le=365), refresh: bool = True, db: DbSession = DB, current_user: User = USER):
    if refresh: generate_insights(db, current_user, horizon_days)
    ensure_insights_schema(db); sql = "SELECT * FROM insights WHERE user_id=:user_id"; params: dict[str, Any] = {"user_id": current_user.id}
    if insight_status == "current": sql += " AND status IN ('new','reviewed')"
    elif insight_status != "all":
        if insight_status not in VALID_STATUSES: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Insight status")
        sql += " AND status=:status"; params["status"] = insight_status
    if importance:
        if importance not in IMPORTANCE_ORDER: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Insight importance")
        sql += " AND importance=:importance"; params["importance"] = importance
    if category: sql += " AND category=:category"; params["category"] = category
    rows = [_serialize(row) for row in db.execute(text(sql + " ORDER BY updated_at DESC"), params).mappings().all()]; rows.sort(key=lambda item: (IMPORTANCE_ORDER.get(item["importance"], 9), str(item.get("period_end") or ""), item["id"])); return rows


@router.get("/financial-health")
def get_financial_health(horizon_days: int = Query(90, ge=7, le=365), db: DbSession = DB, current_user: User = USER): return financial_health(db, current_user, horizon_days, True)


@router.get("/{insight_id}")
def insight_detail(insight_id: int, db: DbSession = DB, current_user: User = USER):
    ensure_insights_schema(db); row = db.execute(text("SELECT * FROM insights WHERE id=:id AND user_id=:user_id"), {"id": insight_id, "user_id": current_user.id}).mappings().first()
    if not row: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found")
    return _serialize(row)


def _set_status(db: DbSession, user: User, insight_id: int, new_status: str) -> dict[str, Any]:
    ensure_insights_schema(db)
    if new_status not in VALID_STATUSES: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Insight status")
    row = db.execute(text("SELECT id FROM insights WHERE id=:id AND user_id=:user_id"), {"id": insight_id, "user_id": user.id}).first()
    if not row: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found")
    now = utcnow(); reviewed_at = now if new_status == "reviewed" else None; dismissed_at = now if new_status == "dismissed" else None; resolved_at = now if new_status == "resolved" else None
    db.execute(text("UPDATE insights SET status=:status,reviewed_at=COALESCE(:reviewed_at,reviewed_at),dismissed_at=COALESCE(:dismissed_at,dismissed_at),resolved_at=COALESCE(:resolved_at,resolved_at),reviewed_by_user_id=:user_id,updated_at=:now WHERE id=:id AND user_id=:user_id"), {"status": new_status, "reviewed_at": reviewed_at, "dismissed_at": dismissed_at, "resolved_at": resolved_at, "user_id": user.id, "now": now, "id": insight_id}); db.commit(); return insight_detail(insight_id, db, user)


@router.post("/{insight_id}/reviewed")
def mark_reviewed(insight_id: int, db: DbSession = DB, current_user: User = USER): return _set_status(db, current_user, insight_id, "reviewed")


@router.post("/{insight_id}/dismiss")
def dismiss_insight(insight_id: int, db: DbSession = DB, current_user: User = USER): return _set_status(db, current_user, insight_id, "dismissed")
