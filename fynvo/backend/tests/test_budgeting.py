from datetime import date

import pytest
from app.budget import (
    analyse_budgets,
    create_budget,
    create_category,
    list_views,
    period_bounds,
    reset_view,
    save_view,
    update_budget,
    update_category,
)
from app.database import get_engine, get_session_factory, run_migrations
from fastapi import HTTPException
from sqlalchemy import text


def setup_user(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})
    db = get_session_factory()()
    try:
        user_id = db.execute(text("SELECT id FROM users WHERE username='stu'")).scalar()
        user = db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id}).first()
        return db, user
    except RuntimeError:
        db.close()
        raise


def test_budget_migration_schema_version_thirteen(client):
    run_migrations()
    with get_engine().begin() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 13
        tables = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars().all()
    assert "budgets" in tables
    assert "categories" in tables
    assert "saved_views" in tables
    assert "import_batches" in tables


def test_weekly_monthly_quarterly_annual_and_true_fortnight_periods():
    assert period_bounds("weekly", today=date(2026, 8, 19)) == (date(2026, 8, 17), date(2026, 8, 23))
    assert period_bounds("fortnightly", anchor=date(2026, 10, 1), today=date(2026, 10, 29)) == (date(2026, 10, 29), date(2026, 11, 11))
    assert period_bounds("monthly", today=date(2028, 2, 12)) == (date(2028, 2, 1), date(2028, 2, 29))
    assert period_bounds("quarterly", today=date(2026, 5, 5)) == (date(2026, 4, 1), date(2026, 6, 30))
    assert period_bounds("annual", today=date(2026, 8, 16)) == (date(2026, 1, 1), date(2026, 12, 31))


def test_category_hierarchy_reparent_and_cycle_prevention(client):
    db, user = setup_user(client)
    try:
        utilities = create_category(db, user, {"name": "Utilities", "budget_relationship": "shared_parent_pool"})
        electricity = create_category(db, user, {"name": "Electricity", "parent_id": utilities["id"]})
        assert update_category(db, user, electricity["id"], {"name": "Power", "parent_id": utilities["id"]})["path"] == "Utilities → Power"
        with pytest.raises(HTTPException):
            update_category(db, user, utilities["id"], {"parent_id": electricity["id"]})
    finally:
        db.close()


def test_budget_create_update_history_and_analysis(client):
    db, user = setup_user(client)
    try:
        groceries = create_category(db, user, {"name": "Groceries"})
        budget = create_budget(db, user, {"name": "Groceries", "category_id": groceries["id"], "category_name": "Groceries", "amount": "1000", "period": "monthly", "rollover_enabled": True, "anchor_date": "2026-08-01", "start_date": "2026-08-01"})
        assert budget["amount"] == "1000.00"
        updated = update_budget(db, user, budget["id"], {"amount": "1100", "effective_from": "2026-10-01"})
        assert updated["amount"] == "1100.00"
        db.execute(text("INSERT INTO accounts (user_id,name,account_type,opening_balance_cents,is_active,created_at,updated_at) VALUES (:user_id,'Everyday','transaction',0,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"user_id": user.id})
        account_id = db.execute(text("SELECT id FROM accounts WHERE user_id=:user_id AND name='Everyday'"), {"user_id": user.id}).scalar()
        db.execute(text("INSERT INTO transactions (user_id,account_id,transaction_date,amount_cents,transaction_type,description,category,source,status,reconciliation_state,created_at,updated_at) VALUES (:user_id,:account_id,'2026-08-10',68400,'expense','Supermarket','Groceries','manual','cleared','unmatched',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"user_id": user.id, "account_id": account_id})
        db.commit()
        analysis = analyse_budgets(db, user, start=date(2026, 8, 1), end=date(2026, 8, 31), mode="normalised")
        row = analysis["budgets"][0]
        assert row["actual"] == "684.00"
        assert row["current_remaining"] == "416.00"
        assert row["counts"]["actual"] == 1
        assert row["status"] in {"on_track", "approaching_limit", "projected_over_budget", "over_budget"}
        versions = db.execute(text("SELECT COUNT(*) FROM budget_versions WHERE budget_id=:budget_id"), {"budget_id": budget["id"]}).scalar()
        assert versions == 2
    finally:
        db.close()


def test_saved_view_preferences_persist_and_reset(client):
    db, user = setup_user(client)
    try:
        view = save_view(db, user, {"screen": "budgets", "name": "Monthly Household", "settings": {"sort": {"column": "utilisation", "direction": "desc"}, "columns": ["category", "budget", "actual"]}})
        assert view["settings"]["sort"]["direction"] == "desc"
        assert list_views(db, user, "budgets")[0]["name"] == "Monthly Household"
        save_view(db, user, {"screen": "budgets", "name": "Default", "settings": {"columns": ["category"]}})
        assert reset_view(db, user, "budgets")["reset"] is True
    finally:
        db.close()


def test_unbudgeted_category_detection(client):
    db, user = setup_user(client)
    try:
        db.execute(text("INSERT INTO accounts (user_id,name,account_type,opening_balance_cents,is_active,created_at,updated_at) VALUES (:user_id,'Everyday','transaction',0,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"user_id": user.id})
        account_id = db.execute(text("SELECT id FROM accounts WHERE user_id=:user_id AND name='Everyday'"), {"user_id": user.id}).scalar()
        db.execute(text("INSERT INTO transactions (user_id,account_id,transaction_date,amount_cents,transaction_type,description,category,source,status,reconciliation_state,created_at,updated_at) VALUES (:user_id,:account_id,'2026-08-10',19600,'expense','Cafe','Dining Out','manual','cleared','unmatched',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"user_id": user.id, "account_id": account_id})
        db.commit()
        analysis = analyse_budgets(db, user, start=date(2026, 8, 1), end=date(2026, 8, 31))
        assert analysis["unbudgeted_categories"][0]["category"] == "Dining Out"
        assert analysis["unbudgeted_categories"][0]["action"] == "create_budget"
    finally:
        db.close()