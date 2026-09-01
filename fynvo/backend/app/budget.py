from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .forecast import generate_forecast, historical_run_rates
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

BUDGET_PERIODS = {"weekly", "fortnightly", "monthly", "quarterly", "annual"}
BUDGET_DIRECTIONS = {"expense", "income"}
RELATIONSHIP_MODES = {"independent", "shared_parent_pool", "sum_of_children"}
ALLOCATION_STRATEGIES = {"spend_during_period", "spread_weekly", "spread_fortnightly", "spread_monthly", "specific_dates"}


def _as_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _today() -> date:
    return utcnow().date()


def _round_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def period_bounds(period: str, anchor: date | None = None, today: date | None = None) -> tuple[date, date]:
    current = today or _today()
    anchor = anchor or current
    if period == "weekly":
        start = current - timedelta(days=current.weekday())
        return start, start + timedelta(days=6)
    if period == "fortnightly":
        delta = (current - anchor).days
        index = delta // 14 if delta >= 0 else -((-delta + 13) // 14)
        start = anchor + timedelta(days=index * 14)
        if start > current:
            start -= timedelta(days=14)
        return start, start + timedelta(days=13)
    if period == "quarterly":
        month = ((current.month - 1) // 3) * 3 + 1
        end_month = month + 2
        return date(current.year, month, 1), date(current.year, end_month, monthrange(current.year, end_month)[1])
    if period == "annual":
        return date(current.year, 1, 1), date(current.year, 12, 31)
    return date(current.year, current.month, 1), date(current.year, current.month, monthrange(current.year, current.month)[1])


def _period_elapsed_percent(start: date, end: date, today: date | None = None) -> int:
    current = min(max(today or _today(), start), end)
    return round((((current - start).days + 1) / max((end - start).days + 1, 1)) * 100)


def _proportion_budget(amount_cents: int, native_start: date, native_end: date, start: date, end: date) -> int:
    overlap_start = max(native_start, start)
    overlap_end = min(native_end, end)
    if overlap_end < overlap_start:
        return 0
    native_days = Decimal((native_end - native_start).days + 1)
    overlap_days = Decimal((overlap_end - overlap_start).days + 1)
    return _round_cents(Decimal(amount_cents) * overlap_days / native_days)


def list_categories(db: DbSession, user: User) -> list[dict]:
    rows = db.execute(text("SELECT * FROM categories WHERE user_id=:user_id ORDER BY COALESCE(parent_id, id), name"), {"user_id": user.id}).mappings().all()
    by_id = {row["id"]: dict(row) for row in rows}
    result = []
    for row in rows:
        item = dict(row)
        path = [item["name"]]
        parent_id = item.get("parent_id")
        seen = {item["id"]}
        while parent_id and parent_id in by_id and parent_id not in seen:
            seen.add(parent_id)
            parent = by_id[parent_id]
            path.insert(0, parent["name"])
            parent_id = parent.get("parent_id")
        item["path"] = " > ".join(path)
        item["is_active"] = bool(item.get("is_active"))
        result.append(item)
    return result


def _category_exists(db: DbSession, user: User, category_id: int | None) -> bool:
    if category_id is None:
        return True
    return bool(db.execute(text("SELECT id FROM categories WHERE user_id=:user_id AND id=:id"), {"user_id": user.id, "id": category_id}).scalar())


def _would_cycle(db: DbSession, user: User, category_id: int, parent_id: int | None) -> bool:
    seen = {category_id}
    current = parent_id
    while current:
        if current in seen:
            return True
        seen.add(current)
        current = db.execute(text("SELECT parent_id FROM categories WHERE user_id=:user_id AND id=:id"), {"user_id": user.id, "id": current}).scalar()
    return False


def create_category(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name is required")
    parent_id = payload.get("parent_id")
    if parent_id is not None and not _category_exists(db, user, int(parent_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")
    now = utcnow()
    db.execute(text("""
        INSERT INTO categories (user_id, name, parent_id, icon, color, category_type, budget_relationship, is_active, notes, created_at, updated_at)
        VALUES (:user_id, :name, :parent_id, :icon, :color, :category_type, :budget_relationship, 1, :notes, :now, :now)
    """), {"user_id": user.id, "name": name, "parent_id": parent_id, "icon": payload.get("icon"), "color": payload.get("color"), "category_type": payload.get("category_type") or "expense", "budget_relationship": payload.get("budget_relationship") or "independent", "notes": payload.get("notes"), "now": now})
    row = db.execute(text("SELECT * FROM categories WHERE id=last_insert_rowid()")).mappings().first()
    db.commit()
    return dict(row)


def update_category(db: DbSession, user: User, category_id: int, payload: dict[str, Any]) -> dict:
    row = db.execute(text("SELECT * FROM categories WHERE user_id=:user_id AND id=:id"), {"user_id": user.id, "id": category_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    parent_id = payload.get("parent_id", row["parent_id"])
    if parent_id is not None:
        parent_id = int(parent_id)
        if not _category_exists(db, user, parent_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")
        if _would_cycle(db, user, category_id, parent_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category hierarchy cannot contain cycles")
    relationship = payload.get("budget_relationship", row["budget_relationship"] or "independent")
    if relationship not in RELATIONSHIP_MODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid budget relationship")
    db.execute(text("""
        UPDATE categories SET name=:name, parent_id=:parent_id, icon=:icon, color=:color, category_type=:category_type,
        budget_relationship=:budget_relationship, is_active=:is_active, notes=:notes, updated_at=:now
        WHERE user_id=:user_id AND id=:id
    """), {"user_id": user.id, "id": category_id, "name": payload.get("name", row["name"]), "parent_id": parent_id, "icon": payload.get("icon", row["icon"]), "color": payload.get("color", row["color"]), "category_type": payload.get("category_type", row["category_type"]), "budget_relationship": relationship, "is_active": payload.get("is_active", row["is_active"]), "notes": payload.get("notes", row["notes"]), "now": utcnow()})
    db.commit()
    return next(item for item in list_categories(db, user) if item["id"] == category_id)


def _category_names(db: DbSession, user: User, category_id: int, descendants: bool = True) -> set[str]:
    categories = list_categories(db, user)
    by_parent: dict[int, list[dict]] = {}
    by_id = {item["id"]: item for item in categories}
    for item in categories:
        if item.get("parent_id"):
            by_parent.setdefault(item["parent_id"], []).append(item)
    ids = {category_id}
    if descendants:
        stack = [category_id]
        while stack:
            parent = stack.pop()
            for child in by_parent.get(parent, []):
                ids.add(child["id"])
                stack.append(child["id"])
    return {by_id[item_id]["name"] for item_id in ids if item_id in by_id}


def list_budgets(db: DbSession, user: User, include_inactive: bool = False) -> list[dict]:
    rows = db.execute(text("SELECT * FROM budgets WHERE user_id=:user_id ORDER BY is_active DESC, name"), {"user_id": user.id}).mappings().all()
    categories = {item["id"]: item for item in list_categories(db, user)}
    result = []
    for row in rows:
        if not include_inactive and not row["is_active"]:
            continue
        item = dict(row)
        item["amount"] = cents_to_decimal(item["amount_cents"])
        item["rollover_enabled"] = bool(item["rollover_enabled"])
        item["negative_rollover_enabled"] = bool(item["negative_rollover_enabled"])
        item["is_income_budget"] = item["direction"] == "income"
        item["is_active"] = bool(item["is_active"])
        category = categories.get(item.get("category_id"))
        item["category_path"] = category["path"] if category else item.get("category_name")
        result.append(item)
    return result


def create_budget(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    name = (payload.get("name") or payload.get("category_name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Budget name is required")
    period = payload.get("period") or "monthly"
    if period not in BUDGET_PERIODS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid budget period")
    direction = payload.get("direction") or "expense"
    if direction not in BUDGET_DIRECTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid budget direction")
    category_id = payload.get("category_id")
    if category_id is not None and not _category_exists(db, user, int(category_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    relationship = payload.get("relationship_mode") or "independent"
    allocation = payload.get("allocation_strategy") or "spend_during_period"
    if relationship not in RELATIONSHIP_MODES or allocation not in ALLOCATION_STRATEGIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid budget mode")
    anchor = _as_date(payload.get("anchor_date")) or _today()
    start_date = _as_date(payload.get("start_date")) or anchor
    amount = parse_money(payload.get("amount"))
    now = utcnow()
    db.execute(text("""
        INSERT INTO budgets (user_id, name, category_id, category_name, direction, period, amount_cents, allocation_strategy,
        relationship_mode, anchor_date, start_date, end_date, rollover_enabled, negative_rollover_enabled, notes, is_active, created_at, updated_at)
        VALUES (:user_id, :name, :category_id, :category_name, :direction, :period, :amount, :allocation, :relationship,
        :anchor, :start_date, :end_date, :rollover, :negative_rollover, :notes, 1, :now, :now)
    """), {"user_id": user.id, "name": name, "category_id": category_id, "category_name": payload.get("category_name") or name, "direction": direction, "period": period, "amount": amount, "allocation": allocation, "relationship": relationship, "anchor": anchor, "start_date": start_date, "end_date": _as_date(payload.get("end_date")), "rollover": bool(payload.get("rollover_enabled", False)), "negative_rollover": bool(payload.get("negative_rollover_enabled", False)), "notes": payload.get("notes"), "now": now})
    row = db.execute(text("SELECT * FROM budgets WHERE id=last_insert_rowid()")).mappings().first()
    db.execute(text("INSERT INTO budget_versions (budget_id, user_id, amount_cents, period, allocation_strategy, effective_from, created_at) VALUES (:budget_id, :user_id, :amount, :period, :allocation, :effective_from, :now)"), {"budget_id": row["id"], "user_id": user.id, "amount": amount, "period": period, "allocation": allocation, "effective_from": start_date, "now": now})
    db.commit()
    return next(item for item in list_budgets(db, user, True) if item["id"] == row["id"])


def update_budget(db: DbSession, user: User, budget_id: int, payload: dict[str, Any]) -> dict:
    row = db.execute(text("SELECT * FROM budgets WHERE user_id=:user_id AND id=:id"), {"user_id": user.id, "id": budget_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    amount = parse_money(payload.get("amount")) if payload.get("amount") is not None else row["amount_cents"]
    period = payload.get("period", row["period"])
    allocation = payload.get("allocation_strategy", row["allocation_strategy"])
    db.execute(text("""
        UPDATE budgets SET name=:name, category_id=:category_id, category_name=:category_name, direction=:direction,
        period=:period, amount_cents=:amount, allocation_strategy=:allocation, relationship_mode=:relationship,
        anchor_date=:anchor, start_date=:start_date, end_date=:end_date, rollover_enabled=:rollover,
        negative_rollover_enabled=:negative_rollover, notes=:notes, is_active=:is_active, updated_at=:now
        WHERE user_id=:user_id AND id=:id
    """), {"user_id": user.id, "id": budget_id, "name": payload.get("name", row["name"]), "category_id": payload.get("category_id", row["category_id"]), "category_name": payload.get("category_name", row["category_name"]), "direction": payload.get("direction", row["direction"]), "period": period, "amount": amount, "allocation": allocation, "relationship": payload.get("relationship_mode", row["relationship_mode"]), "anchor": _as_date(payload.get("anchor_date")) or row["anchor_date"], "start_date": _as_date(payload.get("start_date")) or row["start_date"], "end_date": _as_date(payload.get("end_date")) or row["end_date"], "rollover": payload.get("rollover_enabled", row["rollover_enabled"]), "negative_rollover": payload.get("negative_rollover_enabled", row["negative_rollover_enabled"]), "notes": payload.get("notes", row["notes"]), "is_active": payload.get("is_active", row["is_active"]), "now": utcnow()})
    effective_from = _as_date(payload.get("effective_from"))
    if effective_from:
        db.execute(text("INSERT INTO budget_versions (budget_id, user_id, amount_cents, period, allocation_strategy, effective_from, created_at) VALUES (:budget_id, :user_id, :amount, :period, :allocation, :effective_from, :now)"), {"budget_id": budget_id, "user_id": user.id, "amount": amount, "period": period, "allocation": allocation, "effective_from": effective_from, "now": utcnow()})
    db.commit()
    return next(item for item in list_budgets(db, user, True) if item["id"] == budget_id)


def deactivate_budget(db: DbSession, user: User, budget_id: int) -> dict:
    return update_budget(db, user, budget_id, {"is_active": False})


def _actual_for_categories(db: DbSession, user: User, names: set[str], start: date, end: date, direction: str) -> tuple[int, int]:
    if not names:
        return 0, 0
    placeholders = {f"c{i}": name for i, name in enumerate(names)}
    row = db.execute(text(f"SELECT COUNT(*) AS count, COALESCE(SUM(amount_cents),0) AS total FROM transactions WHERE user_id=:user_id AND transaction_type=:type AND transaction_date BETWEEN :start AND :end AND category IN ({','.join(':'+k for k in placeholders)})"), {"user_id": user.id, "start": start, "end": end, "type": "income" if direction == "income" else "expense", **placeholders}).mappings().first()
    return int(abs(row["total"] or 0)), int(row["count"] or 0)


def _scheduled_for_categories(db: DbSession, user: User, names: set[str], start: date, end: date, source_type: str | None = None) -> tuple[int, int]:
    forecast = generate_forecast(db, user, f"{(end - start).days + 1}d", "expected", start)
    rows = [item for item in forecast.get("timeline", []) if item.get("direction") == "expense" and item.get("category") in names and (source_type is None or item.get("source_type") == source_type)]
    return sum(abs(parse_money(item["amount"])) for item in rows), len(rows)


def analyse_budgets(db: DbSession, user: User, start: date | None = None, end: date | None = None, category_id: int | None = None, account_ids: list[int] | None = None, mode: str = "native") -> dict:
    del account_ids
    current_day = _today()
    rows = []
    total_budget = total_actual = total_committed = total_planned = total_forecast = 0
    for budget in [b for b in list_budgets(db, user) if not category_id or b.get("category_id") == category_id]:
        # Explicit historical/custom ranges must be normalised against the budget
        # period containing that requested range, not the wall-clock current period.
        reference_day = start or current_day
        native_start, native_end = period_bounds(budget["period"], _as_date(budget.get("anchor_date")), reference_day)
        period_start = start or native_start
        period_end = end or native_end
        base_budget = parse_money(budget["amount"])
        applicable = base_budget if mode == "native" else _proportion_budget(base_budget, native_start, native_end, period_start, period_end)
        if budget.get("allocation_strategy") == "spread_weekly" and budget["period"] == "annual" and mode == "native" and not start:
            applicable = _round_cents(Decimal(base_budget) / Decimal(52))
        elif budget.get("allocation_strategy") == "spread_fortnightly" and budget["period"] == "annual" and mode == "native" and not start:
            applicable = _round_cents(Decimal(base_budget) / Decimal(26))
        elif budget.get("allocation_strategy") == "spread_monthly" and budget["period"] == "annual" and mode == "native" and not start:
            applicable = _round_cents(Decimal(base_budget) / Decimal(12))
        names = _category_names(db, user, budget["category_id"], True) if budget.get("category_id") else {budget.get("category_name") or budget["name"]}
        actual, actual_count = _actual_for_categories(db, user, names, period_start, period_end, budget["direction"])
        committed, committed_count = _scheduled_for_categories(db, user, names, period_start, period_end)
        planned, planned_count = _scheduled_for_categories(db, user, names, period_start, period_end, "planned_spending")
        if budget["direction"] == "income":
            committed = planned = 0
        forecast_total = max(actual + committed + planned, actual)
        rollover = int(budget.get("rollover_cents") or 0)
        available = applicable + rollover
        current_remaining = available - actual
        projected_remaining = available - forecast_total
        variance = forecast_total - available
        utilisation = round((actual / available) * 100) if available else 0
        status_name = "over_budget" if actual > available else "projected_over_budget" if forecast_total > available else "approaching_limit" if utilisation >= 85 else "on_track"
        rows.append({"id": budget["id"], "name": budget["name"], "category": budget.get("category_path") or budget.get("category_name"), "period": budget["period"], "direction": budget["direction"], "relationship_mode": budget["relationship_mode"], "allocation_strategy": budget["allocation_strategy"], "period_start": period_start.isoformat(), "period_end": period_end.isoformat(), "base_budget": cents_to_decimal(applicable), "rollover": cents_to_decimal(rollover), "available_budget": cents_to_decimal(available), "actual": cents_to_decimal(actual), "committed": cents_to_decimal(committed), "planned": cents_to_decimal(planned), "forecast": cents_to_decimal(forecast_total), "current_remaining": cents_to_decimal(current_remaining), "projected_remaining": cents_to_decimal(projected_remaining), "projected_variance": cents_to_decimal(variance), "utilisation_percent": utilisation, "period_elapsed_percent": _period_elapsed_percent(period_start, period_end, current_day), "status": status_name, "counts": {"actual": actual_count, "committed": committed_count, "planned": planned_count, "forecast": committed_count + planned_count}, "explanation": f"Actual is based on {actual_count} transactions. Forecast combines actual, committed and planned items."})
        total_budget += available
        total_actual += actual
        total_committed += committed
        total_planned += planned
        total_forecast += forecast_total
    unbudgeted = find_unbudgeted_categories(db, user, start or current_day.replace(day=1), end or current_day)
    return {"mode": mode, "start": (start or current_day).isoformat(), "end": (end or current_day).isoformat(), "summary": {"base_budget": cents_to_decimal(total_budget), "actual": cents_to_decimal(total_actual), "committed": cents_to_decimal(total_committed), "planned": cents_to_decimal(total_planned), "forecast": cents_to_decimal(total_forecast), "projected_variance": cents_to_decimal(total_forecast - total_budget), "budgeted_surplus_deficit": cents_to_decimal(total_budget - total_forecast)}, "budgets": rows, "unbudgeted_categories": unbudgeted}


def find_unbudgeted_categories(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    budgeted = {row[0] for row in db.execute(text("SELECT category_name FROM budgets WHERE user_id=:user_id AND is_active=1 AND category_name IS NOT NULL"), {"user_id": user.id}).all()}
    rows = db.execute(text("SELECT category, COUNT(*) AS count, COALESCE(SUM(amount_cents),0) AS total FROM transactions WHERE user_id=:user_id AND transaction_type='expense' AND transaction_date BETWEEN :start AND :end AND category IS NOT NULL AND category!='' GROUP BY category ORDER BY ABS(total) DESC"), {"user_id": user.id, "start": start, "end": end}).mappings().all()
    rates = {row["category"]: row for row in historical_run_rates(db, user, 8, end + timedelta(days=1))}
    return [{"category": row["category"], "actual": cents_to_decimal(abs(row["total"] or 0)), "transaction_count": int(row["count"] or 0), "historical_average_weekly": rates.get(row["category"], {}).get("weekly_amount"), "action": "create_budget"} for row in rows if row["category"] not in budgeted]


def save_view(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    screen = (payload.get("screen") or "").strip()
    name = (payload.get("name") or "Default").strip()
    if not screen:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="screen is required")
    body = json.dumps(payload.get("settings") or {}, sort_keys=True)
    existing = db.execute(text("SELECT id FROM saved_views WHERE user_id=:user_id AND screen=:screen AND name=:name"), {"user_id": user.id, "screen": screen, "name": name}).scalar()
    if existing:
        db.execute(text("UPDATE saved_views SET settings_json=:settings, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": existing, "user_id": user.id, "settings": body, "now": utcnow()})
    else:
        db.execute(text("INSERT INTO saved_views (user_id, screen, name, settings_json, is_default, created_at, updated_at) VALUES (:user_id, :screen, :name, :settings, :is_default, :now, :now)"), {"user_id": user.id, "screen": screen, "name": name, "settings": body, "is_default": bool(payload.get("is_default", False)), "now": utcnow()})
    db.commit()
    return {"status": "ok", "screen": screen, "name": name, "settings": payload.get("settings") or {}}


def list_views(db: DbSession, user: User, screen: str | None = None) -> list[dict]:
    sql = "SELECT * FROM saved_views WHERE user_id=:user_id"
    params: dict[str, Any] = {"user_id": user.id}
    if screen:
        sql += " AND screen=:screen"
        params["screen"] = screen
    rows = db.execute(text(sql + " ORDER BY screen, is_default DESC, name"), params).mappings().all()
    return [{"id": row["id"], "screen": row["screen"], "name": row["name"], "settings": json.loads(row["settings_json"] or "{}"), "is_default": bool(row["is_default"])} for row in rows]


def reset_view(db: DbSession, user: User, screen: str) -> dict:
    db.execute(text("DELETE FROM saved_views WHERE user_id=:user_id AND screen=:screen AND name='Default'"), {"user_id": user.id, "screen": screen})
    db.commit()
    return {"status": "ok", "screen": screen, "reset": True}
