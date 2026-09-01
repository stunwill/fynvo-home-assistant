from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .finance import add_period, bill_status, today_local
from .ledger import LIQUID_ASSET_TYPES
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

HORIZONS = {"7d": 7, "next_7_days": 7, "30d": 30, "next_30_days": 30, "3m": 92, "next_3_months": 92, "6m": 184, "next_6_months": 184, "12m": 365, "next_12_months": 365}


def _as_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def resolve_horizon(horizon: str | None, start: date | None = None) -> tuple[date, date, str]:
    start_date = start or today_local()
    key = (horizon or "30d").lower()
    if key == "year_end":
        return start_date, date(start_date.year, 12, 31), key
    if key in HORIZONS:
        return start_date, start_date + timedelta(days=HORIZONS[key]), key
    try:
        days = int(key.rstrip("d"))
        if days < 1 or days > 730:
            raise ValueError
        return start_date, start_date + timedelta(days=days), f"{days}d"
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported forecast horizon") from exc


def household_starting_balance(db: DbSession, user: User) -> tuple[int, dict[int, int]]:
    placeholders = ",".join(f":type_{index}" for index, _ in enumerate(sorted(LIQUID_ASSET_TYPES)))
    params: dict[str, Any] = {"user_id": user.id}
    params.update({f"type_{index}": value for index, value in enumerate(sorted(LIQUID_ASSET_TYPES))})
    rows = db.execute(text(f"SELECT id, opening_balance_cents FROM accounts WHERE user_id=:user_id AND is_active=1 AND archived_at IS NULL AND account_type IN ({placeholders})"), params).all()
    by_account = {row.id: int(row.opening_balance_cents or 0) for row in rows}
    if not by_account:
        return 0, {}
    account_ids = tuple(by_account)
    id_placeholders = ",".join(f":account_{index}" for index, _ in enumerate(account_ids))
    tx_params: dict[str, Any] = {"user_id": user.id}
    tx_params.update({f"account_{index}": value for index, value in enumerate(account_ids)})
    tx_rows = db.execute(text(f"SELECT account_id, COALESCE(SUM(amount_cents),0) AS total FROM transactions WHERE user_id=:user_id AND account_id IN ({id_placeholders}) GROUP BY account_id"), tx_params).all()
    for row in tx_rows:
        by_account[row.account_id] = by_account.get(row.account_id, 0) + int(row.total or 0)
    return sum(by_account.values()), by_account


def _changes(db: DbSession, user: User, record_type: str, record_id: int):
    return db.execute(text("SELECT * FROM effective_amount_changes WHERE user_id=:user_id AND record_type=:record_type AND record_id=:record_id ORDER BY effective_from ASC, id ASC"), {"user_id": user.id, "record_type": record_type, "record_id": record_id}).mappings().all()


def amount_at(db: DbSession, user: User, record_type: str, record_id: int, base_amount: int | None, when: date) -> tuple[int | None, dict | None]:
    amount = base_amount
    applied = None
    for change in _changes(db, user, record_type, record_id):
        start = _as_date(change["effective_from"])
        end = _as_date(change["effective_to"])
        if start and start <= when and (end is None or when <= end):
            amount = int(change["new_amount_cents"])
            applied = dict(change)
    return amount, applied


def create_effective_change(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    record_type = payload.get("record_type")
    if record_type not in {"income", "recurring_expense"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="record_type must be income or recurring_expense")
    record_id = int(payload.get("record_id") or 0)
    table = "income_sources" if record_type == "income" else "recurring_expenses"
    found = db.execute(text(f"SELECT id FROM {table} WHERE id=:id AND user_id=:user_id"), {"id": record_id, "user_id": user.id}).scalar()
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring record not found")
    effective_from = _as_date(payload.get("effective_from"))
    if effective_from is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="effective_from is required")
    amount = parse_money(payload.get("new_amount"))
    now = utcnow()
    db.execute(text("INSERT INTO effective_amount_changes (user_id,record_type,record_id,new_amount_cents,effective_from,effective_to,source,notes,created_at,updated_at) VALUES (:user_id,:record_type,:record_id,:amount,:effective_from,:effective_to,:source,:notes,:now,:now)"), {"user_id": user.id, "record_type": record_type, "record_id": record_id, "amount": amount, "effective_from": effective_from, "effective_to": _as_date(payload.get("effective_to")), "source": payload.get("source") or "manual", "notes": payload.get("notes"), "now": now})
    db.commit()
    return {"status": "ok", "record_type": record_type, "record_id": record_id, "new_amount": cents_to_decimal(amount), "effective_from": effective_from.isoformat()}


def list_effective_changes(db: DbSession, user: User) -> list[dict]:
    rows = db.execute(text("SELECT * FROM effective_amount_changes WHERE user_id=:user_id ORDER BY effective_from,id"), {"user_id": user.id}).mappings().all()
    return [{**dict(row), "new_amount": cents_to_decimal(row["new_amount_cents"]), "effective_from": _as_date(row["effective_from"]).isoformat() if row["effective_from"] else None, "effective_to": _as_date(row["effective_to"]).isoformat() if row["effective_to"] else None} for row in rows]


def _event(when: date, name: str, amount: int, direction: str, source_type: str, source_id: int | None, category: str | None, account_id: int | None, confidence: str, layer: str, explanation: str, estimated: bool = False) -> dict:
    signed = amount if direction == "income" else -amount
    return {"date": when.isoformat(), "name": name, "amount_cents": signed, "amount": cents_to_decimal(signed), "direction": direction, "source_type": source_type, "source_id": source_id, "category": category or "Uncategorised", "account_id": account_id, "confidence": confidence, "financial_layer": layer, "estimated": estimated, "explanation": explanation}


def _recurring_events(db: DbSession, user: User, start: date, end: date, scenario: dict | None = None) -> list[dict]:
    events = []
    scenario = scenario or {}
    removed = set(scenario.get("remove_recurring_ids", []))
    virtual_changes = scenario.get("amount_changes", {})
    for record_type, table, date_col, account_col, direction, source_type in [("income", "income_sources", "next_payment_date", "destination_account_id", "income", "income"), ("recurring_expense", "recurring_expenses", "next_due_date", "account_id", "expense", "recurring_expense")]:
        rows = db.execute(text(f"SELECT * FROM {table} WHERE user_id=:user_id AND is_active=1 AND {date_col} IS NOT NULL AND amount_cents IS NOT NULL"), {"user_id": user.id}).mappings().all()
        for row in rows:
            if record_type == "recurring_expense" and row["id"] in removed:
                continue
            current = _as_date(row[date_col])
            while current and current < start:
                nxt = add_period(current, row["frequency"], row["interval_count"])
                if not nxt or nxt <= current:
                    break
                current = nxt
            while current and current <= end:
                amount, change = amount_at(db, user, record_type, row["id"], row["amount_cents"], current)
                amount = virtual_changes.get(f"{record_type}:{row['id']}:{current.isoformat()}", amount)
                if amount is not None:
                    explanation = "Recurring income" if direction == "income" else "Recurring expense"
                    if change:
                        explanation += f"; effective amount from {change['effective_from']}"
                    events.append(_event(current, row["name"], int(amount), direction, source_type, row["id"], row["category"], row[account_col], "confirmed", "committed", explanation))
                current = add_period(current, row["frequency"], row["interval_count"])
    return events


def _authoritative_scheduled_events(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    """Project recurring expenses from their authoritative Scheduled Payment lifecycle."""
    from . import payments_v114
    from .payment_planning import FUNDING_STATUSES, canonical_payment_rows

    payments_v114.ensure_scheduled_payments(db, user, horizon_days=max((end - start).days + 2, 30), today=start)
    events: list[dict] = []
    for row in canonical_payment_rows(db, user):
        if row.get("source_type") != "scheduled_payment" or row.get("status") not in FUNDING_STATUSES:
            continue
        when = _as_date(row.get("expected_date") or row.get("due_date"))
        if when is None or not (start <= when <= end):
            continue
        recurring_id = row.get("recurring_expense_id")
        base_amount = abs(parse_money(row.get("expected_amount") or row.get("amount") or "0"))
        amount = base_amount
        change = None
        if recurring_id is not None:
            amount, change = amount_at(db, user, "recurring_expense", int(recurring_id), base_amount, when)
        explanation = f"Scheduled Payment lifecycle; status {row.get('status') or 'upcoming'}"
        if change:
            explanation += f"; effective amount from {change['effective_from']}"
        events.append(_event(when, row.get("name") or "Recurring payment", int(amount or 0), "expense", "recurring_expense", recurring_id or row.get("id"), row.get("category"), row.get("account_id"), "confirmed", "committed", explanation))
    return events


def _bill_events(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    rows = db.execute(text("SELECT * FROM bills WHERE user_id=:user_id AND is_active=1 AND paid_at IS NULL AND resolved_at IS NULL AND due_date IS NOT NULL AND remaining_amount_cents IS NOT NULL AND due_date BETWEEN :start AND :end"), {"user_id": user.id, "start": start, "end": end}).mappings().all()
    events = []
    for row in rows:
        when = _as_date(row["due_date"])
        if when:
            status_name = bill_status(when, row["paid_at"], row["resolved_at"], row["remaining_amount_cents"], row["original_status"], start)
            events.append(_event(when, row["name"], int(row["remaining_amount_cents"]), "expense", "bill", row["id"], row["bill_type"], row["account_id"], "confirmed", "committed", f"Bill or obligation; status {status_name}"))
    return events


def _planned_events(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    rows = db.execute(text("SELECT * FROM planned_spending WHERE user_id=:user_id AND archived_at IS NULL AND include_in_forecast=1 AND status IN ('planned','committed') AND planned_date IS NOT NULL AND estimated_amount_cents IS NOT NULL AND planned_date BETWEEN :start AND :end"), {"user_id": user.id, "start": start, "end": end}).mappings().all()
    return [_event(_as_date(row["planned_date"]), row["name"], int(row["estimated_amount_cents"]), "expense", "planned_spending", row["id"], row["category"], row["account_id"], "confirmed", "planned", "Forecast-included Planned Spending") for row in rows if _as_date(row["planned_date"])]


def historical_run_rates(db: DbSession, user: User, weeks: int = 8, forecast_start: date | None = None) -> list[dict]:
    start = forecast_start or today_local()
    history_end = start - timedelta(days=start.weekday() + 1)
    history_start = history_end - timedelta(days=(weeks * 7) - 1)
    rows = db.execute(text("SELECT category, COUNT(*) AS count, SUM(amount_cents) AS total FROM transactions WHERE user_id=:user_id AND transaction_type='expense' AND transaction_date BETWEEN :history_start AND :history_end AND (source IS NULL OR source='manual') AND category IS NOT NULL AND category!='' GROUP BY category"), {"user_id": user.id, "history_start": history_start, "history_end": history_end}).mappings().all()
    known = {r[0] for r in db.execute(text("SELECT DISTINCT category FROM recurring_expenses WHERE user_id=:user_id AND category IS NOT NULL"), {"user_id": user.id}).all()}
    known |= {r[0] for r in db.execute(text("SELECT DISTINCT bill_type FROM bills WHERE user_id=:user_id AND bill_type IS NOT NULL"), {"user_id": user.id}).all()}
    known |= {r[0] for r in db.execute(text("SELECT DISTINCT category FROM planned_spending WHERE user_id=:user_id AND category IS NOT NULL"), {"user_id": user.id}).all()}
    rates = []
    for row in rows:
        category = row["category"] or "Uncategorised"
        if category in known or int(row["count"] or 0) < 3:
            continue
        weekly = abs(round((row["total"] or 0) / weeks))
        if weekly > 0:
            rates.append({"category": category, "weekly_amount_cents": weekly, "weekly_amount": cents_to_decimal(weekly), "sample_count": int(row["count"] or 0), "period": f"{weeks} complete weeks", "history_start": history_start.isoformat(), "history_end": history_end.isoformat(), "explanation": f"Based on the previous {weeks} complete weeks."})
    return rates


def _estimated_events(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    events = []
    for rate in historical_run_rates(db, user, 8, start):
        current = start + timedelta(days=(7 - start.weekday()) % 7)
        while current <= end:
            events.append(_event(current, f"{rate['category']} estimate", rate["weekly_amount_cents"], "expense", "run_rate_estimate", None, rate["category"], None, "estimated", "forecast", rate["explanation"], True))
            current += timedelta(days=7)
    return events


def _apply_scenario(events: list[dict], scenario: dict | None, start: date, end: date) -> list[dict]:
    if not scenario:
        return events
    rows = list(events)
    for adj in scenario.get("adjustments", []):
        kind = adj.get("kind")
        name = adj.get("name") or "Scenario adjustment"
        when = _as_date(adj.get("date")) or _as_date(adj.get("start_date")) or start
        if kind in {"one_off_expense", "one_off_income"} and start <= when <= end:
            direction = "income" if kind == "one_off_income" else "expense"
            rows.append(_event(when, name, parse_money(adj.get("amount")), direction, "scenario", None, adj.get("category") or "Scenario", None, "scenario", "forecast", "Temporary scenario adjustment", True))
        elif kind == "recurring_expense":
            amount = parse_money(adj.get("amount"))
            frequency = adj.get("frequency") or "monthly"
            while when and when <= end:
                if when >= start:
                    rows.append(_event(when, name, amount, "expense", "scenario", None, adj.get("category") or "Scenario", None, "scenario", "forecast", "Temporary scenario recurring expense", True))
                when = add_period(when, frequency, adj.get("interval_count"))
    return rows


def generate_forecast(db: DbSession, user: User, horizon: str = "30d", mode: str = "baseline", start: date | None = None, scenario: dict | None = None) -> dict:
    start_date, end_date, resolved = resolve_horizon(horizon, start)
    starting_balance, account_balances = household_starting_balance(db, user)
    recurring = _recurring_events(db, user, start_date, end_date, scenario)
    if scenario:
        recurring_events = recurring
    else:
        recurring_events = [row for row in recurring if row["source_type"] == "income"] + _authoritative_scheduled_events(db, user, start_date, end_date)
    events = recurring_events + _bill_events(db, user, start_date, end_date) + _planned_events(db, user, start_date, end_date)
    if mode == "expected":
        events += _estimated_events(db, user, start_date, end_date)
    events = _apply_scenario(events, scenario, start_date, end_date)
    events.sort(key=lambda r: (r["date"], 0 if r["direction"] == "income" else 1, r["name"]))
    balance = starting_balance
    lowest = {"date": start_date.isoformat(), "balance_cents": balance, "balance": cents_to_decimal(balance)}
    shortfall = None
    totals = defaultdict(int)
    timeline = []
    for row in events:
        balance += int(row["amount_cents"])
        row = {**row, "forecast_balance_cents": balance, "forecast_balance": cents_to_decimal(balance)}
        totals[row["source_type"]] += int(row["amount_cents"])
        timeline.append(row)
        if balance < lowest["balance_cents"]:
            lowest = {"date": row["date"], "balance_cents": balance, "balance": cents_to_decimal(balance), "source": row["name"]}
        if balance < 0 and shortfall is None:
            shortfall = {"date": row["date"], "balance_cents": balance, "balance": cents_to_decimal(balance), "nearby_events": timeline[-5:]}
    income = sum(r["amount_cents"] for r in timeline if r["direction"] == "income")
    expenses = -sum(r["amount_cents"] for r in timeline if r["direction"] == "expense")
    return {"mode": mode, "horizon": resolved, "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "starting_balance": cents_to_decimal(starting_balance), "final_balance": cents_to_decimal(balance), "net_movement": cents_to_decimal(balance - starting_balance), "income_total": cents_to_decimal(income), "expense_total": cents_to_decimal(expenses), "lowest_balance": lowest, "shortfall": shortfall, "account_starting_balances": {str(k): cents_to_decimal(v) for k, v in account_balances.items()}, "events": timeline, "chart_points": [{"date": start_date.isoformat(), "balance": cents_to_decimal(starting_balance), "balance_cents": starting_balance, "kind": "actual"}] + [{"date": r["date"], "balance": r["forecast_balance"], "balance_cents": r["forecast_balance_cents"], "kind": "estimated" if r["estimated"] else "known"} for r in timeline], "totals_by_source": {k: cents_to_decimal(v) for k, v in totals.items()}, "explanations": ["Baseline uses current active liquid Account balances, Income, authoritative Scheduled Payment lifecycle occurrences, Bills and forecast-included Planned Spending."] + (["Expected forecasts add historical run-rate estimates where there is enough manual transaction history and no known commitment already covers the category."] if mode == "expected" else [])}


def compare_scenario(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    horizon = payload.get("horizon") or "30d"
    mode = payload.get("mode") or "baseline"
    baseline = generate_forecast(db, user, horizon, mode)
    scenario = generate_forecast(db, user, horizon, mode, scenario=payload.get("scenario") or payload)
    diff = parse_money(scenario["final_balance"]) - parse_money(baseline["final_balance"])
    return {"name": payload.get("name") or payload.get("scenario", {}).get("name") or "Scenario", "baseline": baseline, "scenario": scenario, "difference": cents_to_decimal(diff), "isolated": True, "explanation": "Scenario calculations are temporary and do not modify real financial records."}


def forecast_drilldown(db: DbSession, user: User, period: str, horizon: str = "30d", mode: str = "baseline") -> dict:
    forecast = generate_forecast(db, user, horizon, mode)
    groups: dict[str, dict] = {}
    for item in forecast["events"]:
        key = item["date"][:7] if period == "month" else item["date"]
        group = groups.setdefault(key, {"period": key, "total_cents": 0, "items": []})
        group["total_cents"] += item["amount_cents"]
        group["items"].append(item)
    return {"period": period, "groups": [{**v, "total": cents_to_decimal(v["total_cents"])} for v in groups.values()]}
