from app.database import get_engine, run_migrations
from sqlalchemy import text


def test_database_migration_records_schema_version(client):
    run_migrations()
    with get_engine().connect() as connection:
        version = connection.execute(text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")).scalar()
        tables = connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'")).scalars().all()
    assert version == 15
    assert "income_sources" in tables
    assert "recurring_expenses" in tables
    assert "bills" in tables
    assert "planned_spending" in tables
    assert "effective_amount_changes" in tables
    assert "forecast_scenarios" in tables
    assert "categories" in tables
    assert "budgets" in tables
    assert "budget_versions" in tables
    assert "saved_views" in tables
    assert "edit_history" in tables
    assert "import_batches" in tables
    assert "import_profiles" in tables
    assert "reconciliation_links" in tables
    assert "expense_types" in tables
    assert "cards" in tables
    assert "households" in tables
    assert "household_memberships" in tables
    assert "record_ownership" in tables
    assert "forecast_occurrence_overrides" in tables
