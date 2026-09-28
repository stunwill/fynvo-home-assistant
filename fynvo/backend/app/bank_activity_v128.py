"""Provider-independent transaction evidence and reversible category memory."""

from sqlalchemy import text

from .database import get_engine

SCHEMA_VERSION = 17


def ensure_bank_activity_schema(engine=None):
    engine = engine or get_engine()
    with engine.begin() as connection:
        columns = {row["name"] for row in connection.execute(text("PRAGMA table_info(transactions)")).mappings()}
        if "provider_category" not in columns:
            connection.execute(text("ALTER TABLE transactions ADD COLUMN provider_category VARCHAR(180)"))
        # v1.26/v1.27 imported Redbark categories into the display category
        # without assigning a Fynvo category ID. Preserve that evidence while
        # removing the misleading authoritative categorisation.
        connection.execute(text("""
            UPDATE transactions SET provider_category=category,category=NULL
            WHERE source='bank_sync' AND category_id IS NULL
              AND category IS NOT NULL AND provider_category IS NULL
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS transaction_category_memory (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                merchant_key VARCHAR(240) NOT NULL, category_id INTEGER NOT NULL,
                confirmed_count INTEGER NOT NULL DEFAULT 1, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(category_id) REFERENCES categories(id),
                UNIQUE(user_id, merchant_key)
            )
        """))
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (:version)"), {"version": SCHEMA_VERSION})
        elif int(current) < SCHEMA_VERSION:
            connection.execute(text("UPDATE schema_version SET version=:version"), {"version": SCHEMA_VERSION})


def merchant_key(row):
    return " ".join(str(row.get("merchant") or row.get("description") or "").strip().lower().split())[:240]
