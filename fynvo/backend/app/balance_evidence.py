"""Immutable observations and one actual-cash resolver, separate from history."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text

from .money import cents_to_decimal
from .security import utcnow

LIQUID_TYPES = {"transaction", "savings", "offset", "cash"}


def ensure_schema(engine):
    # SQLite's backup API gives a consistent pre-upgrade copy, including WAL.
    with engine.connect() as connection:
        version = (
            connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
            or 0
        )
    database = engine.url.database
    if (
        version < 19
        and database
        and database != ":memory:"
        and Path(database).is_file()
    ):
        backup = Path(str(database) + ".pre-v19.sqlite3")
        if not backup.exists():
            temporary = Path(str(backup) + ".tmp")
            with (
                sqlite3.connect(database) as source,
                sqlite3.connect(temporary) as target,
            ):
                source.backup(target)
            temporary.replace(backup)
    with engine.begin() as connection:
        # SQLite legacy transaction mode does not begin a transaction for DDL.
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        connection.execute(
            text("""CREATE TABLE IF NOT EXISTS balance_observations (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, account_id INTEGER NOT NULL,
            current_cents INTEGER NOT NULL, available_cents INTEGER, source VARCHAR(40) NOT NULL,
            observed_at DATETIME NOT NULL, fetched_at DATETIME NOT NULL, covered_json TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id), FOREIGN KEY(user_id) REFERENCES users(id))""")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_balance_observation_account ON balance_observations(user_id,account_id,id)"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS balance_observations_immutable BEFORE UPDATE ON balance_observations BEGIN SELECT RAISE(ABORT, 'Balance observations are immutable'); END"
            )
        )
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(bills)"))
        }
        if "scheduled_payment_id" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE bills ADD COLUMN scheduled_payment_id INTEGER REFERENCES scheduled_payments(id)"
                )
            )
        if version < 19:
            # Backfill only a unique original occurrence. Never merge/delete evidence.
            connection.execute(
                text("""UPDATE bills SET scheduled_payment_id=(
                SELECT MIN(sp.id) FROM scheduled_payments sp WHERE sp.user_id=bills.user_id
                AND sp.recurring_expense_id=bills.recurring_expense_id
                AND COALESCE(sp.occurrence_date,sp.expected_date)=bills.due_date)
                WHERE scheduled_payment_id IS NULL AND recurring_expense_id IS NOT NULL
                AND 1=(SELECT COUNT(*) FROM scheduled_payments sp WHERE sp.user_id=bills.user_id
                AND sp.recurring_expense_id=bills.recurring_expense_id
                AND COALESCE(sp.occurrence_date,sp.expected_date)=bills.due_date)""")
            )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_bill_occurrence_link ON bills(user_id,scheduled_payment_id)"
            )
        )
        # Preserve legacy conflicts, but prevent any new active Bill collision.
        connection.execute(
            text("""CREATE TRIGGER IF NOT EXISTS bill_occurrence_insert_guard BEFORE INSERT ON bills
            WHEN NEW.scheduled_payment_id IS NOT NULL AND NEW.is_active=1
            AND EXISTS (SELECT 1 FROM bills b WHERE b.user_id=NEW.user_id AND b.scheduled_payment_id=NEW.scheduled_payment_id AND b.is_active=1)
            BEGIN SELECT RAISE(ABORT, 'This occurrence already has a Bill'); END""")
        )
        connection.execute(
            text("""CREATE TRIGGER IF NOT EXISTS bill_occurrence_update_guard BEFORE UPDATE OF scheduled_payment_id,is_active ON bills
            WHEN NEW.scheduled_payment_id IS NOT NULL AND NEW.is_active=1
            AND (OLD.scheduled_payment_id IS NOT NEW.scheduled_payment_id OR OLD.is_active<>NEW.is_active)
            AND EXISTS (SELECT 1 FROM bills b WHERE b.user_id=NEW.user_id AND b.scheduled_payment_id=NEW.scheduled_payment_id AND b.is_active=1 AND b.id<>NEW.id)
            BEGIN SELECT RAISE(ABORT, 'This occurrence already has a Bill'); END""")
        )
        connection.execute(
            text("UPDATE schema_version SET version=19 WHERE version<19")
        )


def transactions(db, account):
    return (
        db.execute(
            text(
                "SELECT * FROM transactions WHERE user_id=:uid AND account_id=:aid ORDER BY id"
            ),
            {"uid": account.user_id, "aid": account.id},
        )
        .mappings()
        .all()
    )


def observe(
    db,
    account,
    amount,
    source="manual",
    available=None,
    observed_at=None,
    basis="current",
):
    now = observed_at or utcnow()
    from .finance import today_local

    covered = {
        str(row["id"]): [
            int(row["amount_cents"]),
            str(row["transaction_date"]),
            row["status"],
        ]
        for row in transactions(db, account)
        if str(row["transaction_date"])[:10] <= today_local().isoformat()
        and row["status"] not in {"pending", "cancelled", "duplicate"}
    }
    db.execute(
        text("""INSERT INTO balance_observations
        (user_id,account_id,current_cents,available_cents,source,observed_at,fetched_at,covered_json)
        VALUES(:uid,:aid,:amount,:available,:source,:observed,:fetched,:covered)"""),
        {
            "uid": account.user_id,
            "aid": account.id,
            "amount": amount,
            "available": available,
            "source": source,
            "observed": now,
            "fetched": utcnow(),
            "covered": json.dumps(
                {
                    "transactions": covered,
                    "as_of": today_local().isoformat(),
                    "basis": basis,
                },
                sort_keys=True,
            ),
        },
    )


def resolve(db, account, today: date | None = None):
    from .finance import today_local

    current = today or today_local()
    rows = transactions(db, account)
    settled = [
        row
        for row in rows
        if str(row["transaction_date"])[:10] <= current.isoformat()
        and row["status"] not in {"pending", "cancelled", "duplicate"}
    ]
    settled_ids = {str(row["id"]) for row in settled}
    ledger = int(account.opening_balance_cents or 0) + sum(
        int(row["amount_cents"]) for row in settled
    )
    observation = (
        db.execute(
            text(
                "SELECT * FROM balance_observations WHERE user_id=:uid AND account_id=:aid ORDER BY id DESC LIMIT 1"
            ),
            {"uid": account.user_id, "aid": account.id},
        )
        .mappings()
        .first()
    )
    metadata = (
        db.execute(
            text(
                "SELECT connection_status,bank_provider,available_balance_cents FROM accounts WHERE id=:aid"
            ),
            {"aid": account.id},
        )
        .mappings()
        .first()
    )
    source = (
        observation["source"]
        if observation
        else account.balance_update_source or "legacy"
    )
    timestamp = (
        observation["observed_at"] if observation else account.balance_updated_at
    )
    amount = ledger
    verification = "verified" if observation and timestamp else "needs_confirmation"
    available = None
    if observation:
        amount = int(observation["current_cents"])
        available = observation["available_cents"]
        if source == "manual":
            snapshot = json.loads(observation["covered_json"])
            covered = snapshot.get("transactions", snapshot)
            observation_day = snapshot.get("as_of", str(timestamp)[:10])
            opening_basis = snapshot.get("basis") == "opening"
            ids = {str(row["id"]) for row in rows}
            if set(covered) - ids:
                verification = "needs_confirmation"
            for row in rows:
                key = str(row["id"])
                if key in covered:
                    if covered[key] != [
                        int(row["amount_cents"]),
                        str(row["transaction_date"]),
                        row["status"],
                    ]:
                        verification = "needs_confirmation"
                elif key not in settled_ids:
                    continue
                elif row["source"] in {"manual", "transfer"}:
                    if (
                        not opening_basis
                        and str(row["transaction_date"])[:10] < observation_day
                    ):
                        verification = "needs_confirmation"
                        continue
                    amount += int(row["amount_cents"])
                else:
                    # Late imported history is not proof of a movement outside an observation.
                    verification = "needs_confirmation"
    elif source == "redbark":
        external = (
            db.execute(
                text(
                    "SELECT current_balance_cents,available_balance_cents,balance_timestamp FROM external_accounts WHERE user_id=:uid AND fynvo_account_id=:aid AND current_balance_cents IS NOT NULL ORDER BY id LIMIT 1"
                ),
                {"uid": account.user_id, "aid": account.id},
            )
            .mappings()
            .first()
        )
        if external:
            amount = int(external["current_balance_cents"])
            available = external["available_balance_cents"]
            timestamp = external["balance_timestamp"]
            verification = "verified" if timestamp else "needs_confirmation"
    if timestamp:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        hours = max(0, (datetime.now(timezone.utc) - parsed).total_seconds() / 3600)
        limit = max(
            1,
            int(
                os.getenv(
                    "FYNVO_BANK_BALANCE_MAX_AGE_HOURS"
                    if source == "redbark"
                    else "FYNVO_MANUAL_BALANCE_MAX_AGE_HOURS",
                    "24" if source == "redbark" else "168",
                )
            ),
        )
        if hours > limit:
            verification = "stale"
    if (
        source == "redbark"
        and metadata
        and metadata["connection_status"] in {"stale", "missing", "error"}
    ):
        verification = "stale"
    accessible = min(amount, int(available)) if available is not None else amount
    return {
        "current_cents": amount,
        "accessible_cents": accessible,
        "ledger_estimate_cents": ledger,
        "current_balance": cents_to_decimal(amount),
        "accessible_balance": cents_to_decimal(accessible),
        "balance_source": source,
        "balance_observed_at": str(timestamp) if timestamp else None,
        "balance_freshness": verification,
        "balance_verified": verification == "verified",
        "balance_observation_id": observation["id"] if observation else None,
        "balance_basis": "provider_observation"
        if source == "redbark"
        else "manual_observation_and_new_manual_movements"
        if observation
        else "legacy_ledger",
    }


def eligible_balances(db, user, today=None):
    from .models import Account

    return {
        account.id: resolve(db, account, today)
        for account in db.query(Account)
        .filter(
            Account.user_id == user.id,
            Account.is_active.is_(True),
            Account.archived_at.is_(None),
            Account.account_type.in_(LIQUID_TYPES),
        )
        .order_by(Account.id)
        .all()
    }
