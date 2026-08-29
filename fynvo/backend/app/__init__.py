"""Fynvo application package.

Fynvo layers forward-compatible services over the proven financial core while
preserving household records and canonical event semantics.
"""

from contextvars import ContextVar
from types import SimpleNamespace

from fastapi import Depends, HTTPException
from sqlalchemy import text

from . import budget, database, finance, forecast, schemas, v018, v1
from .auth import get_current_user
from .money import cents_to_decimal, parse_money

USER_DEPENDENCY = Depends(get_current_user)
DB_DEPENDENCY = Depends(database.get_db)

_legacy_run_migrations = database.run_migrations


def _run_v11_migrations(engine) -> None:
    with engine.begin() as connection:
        def has_column(table: str, column: str) -> bool:
            rows = connection.execute(text(f"PRAGMA table_info({table})")).mappings().all()
            return any(row["name"] == column for row in rows)

        def add_column(table: str, definition: str) -> None:
            column = definition.split()[0]
            if not has_column(table, column):
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))

        for definition in (
            "source_type VARCHAR(40) NOT NULL DEFAULT 'csv'",
            "source_institution VARCHAR(140)",
            "parser_profile VARCHAR(180)",
            "transaction_span_start DATE",
            "transaction_span_end DATE",
            "coverage_status VARCHAR(20) NOT NULL DEFAULT 'unknown'",
            "coverage_start DATE",
            "coverage_end DATE",
            "coverage_note TEXT",
            "coverage_confirmed_at DATETIME",
            "coverage_confirmed_by INTEGER",
        ):
            add_column("import_batches", definition)

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS transaction_splits (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                transaction_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                category_id INTEGER,
                category_name VARCHAR(180),
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_transaction_splits_transaction ON transaction_splits(user_id, transaction_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_import_batches_coverage ON import_batches(user_id, account_id, coverage_status, coverage_start, coverage_end)"))
        current = connection.execute(text("SELECT max(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version (version) VALUES (10)"))
        elif int(current) < 10:
            connection.execute(text("UPDATE schema_version SET version = 10"))


def _run_migrations_v1() -> None:
    _legacy_run_migrations()
    engine = database.get_engine()
    v1.run_v1_migrations(engine)
    _run_v11_migrations(engine)


database.run_migrations = _run_migrations_v1

v1.CATEGORY_SEED["Housing"] = ["Mortgage", "Rent", "Council Rates", "Body Corporate", "Home Maintenance", "Home Improvements", "Security"]

_legacy_get_card = v1._get_card


def _get_card_v0174(db, user, card_id, active_only=False):
    row = _legacy_get_card(db, user, card_id, active_only)
    if row is None:
        return None
    values = dict(row._mapping)
    values["display_name"] = f"{values['name']} ••••{values['last_four']}"
    return SimpleNamespace(**values)


v1._get_card = _get_card_v0174
_legacy_recurring_response_v1 = v1._recurring_response


def _calculated_cost_v0174(amount, frequency, interval_count=None):
    if amount in (None, ""):
        return {"monthly": None, "annual": None, "show_monthly": False}
    amount_cents = parse_money(amount)
    factor = v1._annual_factor(frequency, interval_count)
    if factor is None:
        return {"monthly": None, "annual": None, "show_monthly": False}
    annual_cents = round(amount_cents * float(factor))
    show_monthly = frequency in {"weekly", "fortnightly", "every_28_days", "every_4_weeks", "monthly", "custom"}
    monthly = cents_to_decimal(round(annual_cents / 12)) if show_monthly else None
    return {"monthly": monthly, "annual": cents_to_decimal(annual_cents), "show_monthly": show_monthly}


def _recurring_response_v0174(db, user, row):
    result = _legacy_recurring_response_v1(db, user, row)
    required_missing = [field for field in result.get("missing_fields", []) if field in {"amount", "frequency", "next_due_date", "account", "card"}]
    if not result.get("is_active"):
        result["completeness"] = "inactive_incomplete" if required_missing else "inactive"
    else:
        result["completeness"] = "incomplete" if required_missing else "complete"
    result["missing_fields"] = required_missing
    result["calculated_cost"] = _calculated_cost_v0174(result.get("amount"), result.get("frequency"), result.get("interval_count"))
    result["derived_account_id"] = result.get("account_id")
    result["derived_account_name"] = result.get("account_name")
    if result.get("card_id"):
        card = _get_card_v0174(db, user, result["card_id"])
        result["card"] = {"id": card.id, "account_id": card.account_id, "account_name": card.account_name, "name": card.name, "card_type": card.card_type, "last_four": card.last_four, "display_name": card.display_name, "is_active": bool(card.is_active)}
    else:
        result["card"] = None
    method = result.get("payment_method") or "not_set"
    handling = getattr(row, "payment_handling", None) or ("automatic" if method in {"direct_debit", "automatic_card_payment"} else "manual")
    result["payment_handling"] = handling
    result["payment_handling_label"] = "Paid automatically" if handling == "automatic" else "I pay this manually"
    result["auto_payment_grace_days"] = int(getattr(row, "auto_payment_grace_days", 3) or 3)
    return result


v1._recurring_response = _recurring_response_v0174
finance.recurring_response = v1.recurring_response

_reference_seed_sync_suppressed: ContextVar[bool] = ContextVar("fynvo_reference_seed_sync_suppressed", default=False)
_legacy_sync_category_denormalized_values = v1._sync_category_denormalized_values
_legacy_ensure_reference_data = v1.ensure_reference_data


def _sync_category_denormalized_values_v1(db, user) -> None:
    if _reference_seed_sync_suppressed.get():
        return
    _legacy_sync_category_denormalized_values(db, user)


def _ensure_reference_data_v1(db, user) -> None:
    token = _reference_seed_sync_suppressed.set(True)
    try:
        _legacy_ensure_reference_data(db, user)
    finally:
        _reference_seed_sync_suppressed.reset(token)


v1._sync_category_denormalized_values = _sync_category_denormalized_values_v1
v1.ensure_reference_data = _ensure_reference_data_v1

_legacy_ensure_seed_data = finance.ensure_seed_data


def _ensure_seed_data_v1(db, user) -> None:
    v1.ensure_reference_data(db, user)
    _legacy_ensure_seed_data(db, user)


finance.ensure_seed_data = _ensure_seed_data_v1


def _schedule_events_v1_seeded(db, user, start, end):
    _ensure_seed_data_v1(db, user)
    return v1.schedule_events_v1(db, user, start, end)


finance.schedule_events = _schedule_events_v1_seeded

_legacy_list_categories_v1 = v1.list_categories_v1


def _list_categories_v1_seeded(db, user):
    rows = _legacy_list_categories_v1(db, user)
    if not rows:
        v1.ensure_reference_data(db, user)
        rows = _legacy_list_categories_v1(db, user)
    return rows


v1.list_categories_v1 = _list_categories_v1_seeded
budget.list_categories = _list_categories_v1_seeded
_legacy_create_category_v1 = v1.create_category_v1
_legacy_update_category_v1 = v1.update_category_v1


def _normalise_parent_id(value):
    if value in (None, "", 0, "0"):
        return None
    return int(value)


def _create_category_v018(db, user, payload):
    values = dict(payload)
    values["name"] = " ".join(str(values.get("name") or "").strip().split())
    parent_id = _normalise_parent_id(values.get("parent_id"))
    values["parent_id"] = parent_id
    v018.assert_category_unique(db, user, values["name"], parent_id)
    return _legacy_create_category_v1(db, user, values)


def _update_category_v018(db, user, category_id, payload):
    existing = db.execute(text("SELECT name,parent_id FROM categories WHERE id=:id AND user_id=:uid"), {"id": category_id, "uid": user.id}).mappings().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    values = dict(payload)
    name = " ".join(str(values.get("name", existing["name"]) or "").strip().split())
    parent_id = _normalise_parent_id(values.get("parent_id", existing["parent_id"]))
    values["name"] = name
    if "parent_id" in values or parent_id != existing["parent_id"]:
        values["parent_id"] = parent_id
    v018.assert_category_unique(db, user, name, parent_id, exclude_id=category_id)
    return _legacy_update_category_v1(db, user, category_id, values)


v1.create_category_v1 = _create_category_v018
v1.update_category_v1 = _update_category_v018
budget.create_category = _create_category_v018
budget.update_category = _update_category_v018

_legacy_list_recurring_v1 = v1.list_recurring_v1


def _list_recurring_v1_seeded(db, user, filter_value="all"):
    _ensure_seed_data_v1(db, user)
    return _legacy_list_recurring_v1(db, user, filter_value)


v1.list_recurring_v1 = _list_recurring_v1_seeded
finance.list_recurring = _list_recurring_v1_seeded
forecast._recurring_events = v1.forecast_recurring_events_v1

v1.router.routes = [route for route in v1.router.routes if not (getattr(route, "path", None) == "/recurring-expenses/cost" or (getattr(route, "path", None) == "/recurring-expenses/{expense_id}" and "PUT" in getattr(route, "methods", set())))]


def _recurring_cost_endpoint_v0174(amount: str, frequency: str, interval_count: int | None = None, current_user=USER_DEPENDENCY):
    del current_user
    if frequency not in v1.SUPPORTED_FREQUENCIES:
        raise HTTPException(status_code=400, detail="Unsupported recurrence frequency")
    return _calculated_cost_v0174(amount, frequency, interval_count)


v1.router.add_api_route("/recurring-expenses/cost", _recurring_cost_endpoint_v0174, methods=["GET"])


def _data_integrity_v0174(current_user=USER_DEPENDENCY, db=DB_DEPENDENCY):
    schema_version = db.execute(text("SELECT MAX(version) FROM schema_version")).scalar() or 0
    orphan_cards = db.execute(text("SELECT COUNT(*) FROM cards c LEFT JOIN accounts a ON a.id=c.account_id AND a.user_id=c.user_id WHERE c.user_id=:uid AND a.id IS NULL"), {"uid": current_user.id}).scalar() or 0
    orphan_category_references = 0
    for table_name in ("transactions", "income_sources", "recurring_expenses", "bills", "planned_spending", "budgets"):
        orphan_category_references += db.execute(text(f"SELECT COUNT(*) FROM {table_name} r LEFT JOIN categories c ON c.id=r.category_id AND c.user_id=r.user_id WHERE r.user_id=:uid AND r.category_id IS NOT NULL AND c.id IS NULL"), {"uid": current_user.id}).scalar() or 0
    return {"schema_version": int(schema_version), "orphan_cards": int(orphan_cards), "orphan_category_references": int(orphan_category_references), "status": "ok" if not orphan_cards and not orphan_category_references else "error"}


v1.router.add_api_route("/v1/acceptance/data-integrity", _data_integrity_v0174, methods=["GET"])

from . import (
    auth_v15,
    banking_v12,
    budget_v14,
    corrective_v0174,
    dashboard_v12,
    goals,
    insights_v14,
    payments_v17,
    payments_v112,
    payments_v114,
    payments_v115,
    scenarios,
    v09,
    v11,
    v13_cashflow,
    v111,
)

schemas.RecurringExpenseCreate = payments_v17.RecurringExpenseCreateV17
schemas.BillCreate = payments_v112.BillPayload
finance.create_recurring = payments_v17.create_recurring_v17
finance.create_bill = payments_v112.create_bill_v112
finance.list_bills = payments_v112.list_bills_v112
payments_v17.ensure_scheduled_payments = v111.ensure_scheduled_payments
v111.ensure_scheduled_payments = payments_v114.ensure_scheduled_payments
payments_v17.ensure_scheduled_payments = payments_v114.ensure_scheduled_payments

v09.router.routes = [route for route in v09.router.routes if not (getattr(route, "path", None) == "/api/budgets/analysis" or (getattr(route, "path", None) == "/api/recurring-expenses/{expense_id}" and "PUT" in getattr(route, "methods", set())))]
v09.router.routes = [route for route in v09.router.routes if not (getattr(route, "path", None) == "/api/bills/{bill_id}" and "PUT" in getattr(route, "methods", set()))]
payments_v17.router.routes = [
    route for route in payments_v17.router.routes
    if getattr(route, "path", None) not in {"/scheduled-payments", "/payments/attention", "/payments/match-candidates", "/scheduled-payments/{payment_id}/skip"}
]
v09.router.routes = [
    route for route in v09.router.routes
    if not (getattr(route, "path", None) == "/api/scheduled-payments/{payment_id}/skip" and "POST" in getattr(route, "methods", set()))
]
v09.router.include_router(budget_v14.router)
v09.router.include_router(v1.router)
v09.router.include_router(auth_v15.router)
v09.router.include_router(dashboard_v12.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
v09.router.include_router(scenarios.router)
v09.router.include_router(insights_v14.router)
v09.router.include_router(corrective_v0174.router)
v09.router.include_router(v018.router)
v09.router.include_router(v11.router)
v09.router.include_router(v13_cashflow.router)
v09.router.include_router(payments_v17.router)
v09.router.include_router(v111.router)
v09.router.include_router(payments_v112.router)
v09.router.include_router(payments_v114.router)
v09.router.include_router(payments_v115.router)

_legacy_run_migrations_v12_plus = database.run_migrations


def _run_migrations_v115() -> None:
    _legacy_run_migrations_v12_plus()
    v13_cashflow.run_v13_migrations(database.get_engine())
    payments_v17.ensure_payment_schema(database.get_engine())
    payments_v112.ensure_v112_schema(database.get_engine())
    payments_v114.ensure_v114_schema(database.get_engine())
    payments_v115.ensure_v115_schema(database.get_engine())


database.run_migrations = _run_migrations_v115
