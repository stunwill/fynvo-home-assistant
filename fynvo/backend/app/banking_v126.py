from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db, get_engine, get_session_factory
from .ledger import account_balance_cents, get_account, signed_amount_cents
from .models import Account, User
from .money import cents_to_decimal, parse_money
from .redbark import (
    REDBARK_PROVIDER_ID,
    REDBARK_PROVIDER_NAME,
    RedbarkError,
    RedbarkProvider,
)
from .security import utcnow

logger = logging.getLogger("fynvo.banking")

router = APIRouter(prefix="/bank-connections", tags=["banking"])
DB = Depends(get_db)
USER = Depends(get_current_user)
BANKING_SCHEMA_VERSION = 15
AUTOMATIC_SYNC_INTERVAL_SECONDS = 30 * 60
INCREMENTAL_OVERLAP_DAYS = 7

_SYNC_GUARD = threading.Lock()
_SYNC_KEYS: set[tuple[int, int]] = set()
_SCHEDULER_TASK: asyncio.Task | None = None


class RedbarkCredentialPayload(BaseModel):
    api_key: str = Field(min_length=8, max_length=512)


class AccountMappingPayload(BaseModel):
    action: str = Field(default="link", pattern="^(link|create|ignore|unlink)$")
    fynvo_account_id: int | None = None


def _secret_path() -> Path:
    data_dir = Path(os.getenv("FYNVO_DATA_DIR", "/data"))
    return data_dir / "banking-secrets.json"


def _read_secrets() -> dict[str, str]:
    path = _secret_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(key): str(value) for key, value in payload.items() if value}


def _write_secrets(values: dict[str, str]) -> None:
    path = _secret_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)


def _set_redbark_key(api_key: str) -> None:
    values = _read_secrets()
    values[REDBARK_PROVIDER_ID] = api_key.strip()
    _write_secrets(values)


def _redbark_key() -> str | None:
    return _read_secrets().get(REDBARK_PROVIDER_ID)


def _remove_redbark_key() -> None:
    values = _read_secrets()
    values.pop(REDBARK_PROVIDER_ID, None)
    _write_secrets(values)


def ensure_banking_v126_schema(engine=None) -> None:
    engine = engine or get_engine()
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bank_connections (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, provider VARCHAR(80) NOT NULL,
                provider_connection_id VARCHAR(180) NOT NULL, institution_id VARCHAR(180) NOT NULL,
                institution_name VARCHAR(180) NOT NULL, status VARCHAR(40) NOT NULL DEFAULT 'connected',
                consent_status VARCHAR(40) NOT NULL DEFAULT 'unknown', connected_at DATETIME NOT NULL,
                last_successful_sync DATETIME, last_attempted_sync DATETIME, consent_expiry DATE,
                error_state TEXT, sync_cursor TEXT, is_mock BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), UNIQUE(user_id, provider, provider_connection_id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS external_accounts (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, bank_connection_id INTEGER NOT NULL,
                provider VARCHAR(80) NOT NULL, provider_account_id VARCHAR(180) NOT NULL,
                fynvo_account_id INTEGER, institution_name VARCHAR(180), account_name VARCHAR(180) NOT NULL,
                account_type VARCHAR(40), masked_identifier VARCHAR(40), current_balance_cents INTEGER,
                available_balance_cents INTEGER, balance_timestamp DATETIME, status VARCHAR(40) NOT NULL DEFAULT 'discovered',
                ignored BOOLEAN NOT NULL DEFAULT 0, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(bank_connection_id) REFERENCES bank_connections(id),
                FOREIGN KEY(fynvo_account_id) REFERENCES accounts(id), UNIQUE(user_id, provider, provider_account_id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bank_transaction_identities (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, external_account_id INTEGER NOT NULL,
                transaction_id INTEGER NOT NULL, provider VARCHAR(80) NOT NULL,
                provider_transaction_id VARCHAR(180), pending_key VARCHAR(180), fingerprint VARCHAR(180) NOT NULL,
                status VARCHAR(40) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(external_account_id) REFERENCES external_accounts(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id), UNIQUE(user_id, provider, fingerprint)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bank_sync_history (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, bank_connection_id INTEGER NOT NULL,
                started_at DATETIME NOT NULL, completed_at DATETIME, status VARCHAR(40) NOT NULL,
                added_count INTEGER NOT NULL DEFAULT 0, updated_count INTEGER NOT NULL DEFAULT 0,
                duplicate_count INTEGER NOT NULL DEFAULT 0, review_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT, created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(bank_connection_id) REFERENCES bank_connections(id)
            )
        """))
        columns = lambda table: {row["name"] for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()}
        account_columns = columns("accounts")
        for definition in (
            "connection_status VARCHAR(40)",
            "available_balance_cents INTEGER",
            "balance_timestamp DATETIME",
            "bank_provider VARCHAR(80)",
        ):
            column = definition.split()[0]
            if column not in account_columns:
                connection.execute(text(f"ALTER TABLE accounts ADD COLUMN {definition}"))
                account_columns.add(column)
        tx_columns = columns("transactions")
        for definition in (
            "posted_date DATE",
            "provider VARCHAR(80)",
            "provider_account_id VARCHAR(180)",
            "provider_transaction_id VARCHAR(180)",
            "pending_key VARCHAR(180)",
            "source_fingerprint VARCHAR(180)",
        ):
            column = definition.split()[0]
            if column not in tx_columns:
                connection.execute(text(f"ALTER TABLE transactions ADD COLUMN {definition}"))
                tx_columns.add(column)
        external_columns = columns("external_accounts")
        for definition in (
            "last_transaction_sync DATETIME",
            "last_successful_sync DATETIME",
            "last_attempted_sync DATETIME",
            "error_state TEXT",
        ):
            column = definition.split()[0]
            if column not in external_columns:
                connection.execute(text(f"ALTER TABLE external_accounts ADD COLUMN {definition}"))
                external_columns.add(column)
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_external_accounts_mapping ON external_accounts(user_id, provider, fynvo_account_id)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_tx_provider_id ON bank_transaction_identities(user_id, provider, provider_transaction_id) WHERE provider_transaction_id IS NOT NULL AND provider_transaction_id != ''"))
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (:version)"), {"version": BANKING_SCHEMA_VERSION})
        elif int(current) < BANKING_SCHEMA_VERSION:
            connection.execute(text("UPDATE schema_version SET version=:version"), {"version": BANKING_SCHEMA_VERSION})


def _account_type(value: str | None) -> str:
    raw = str(value or "transaction").lower().replace(" ", "_")
    aliases = {
        "banking": "transaction", "transaction_account": "transaction", "saver": "savings",
        "creditcard": "credit_card", "loan": "personal_loan", "term_deposit": "savings",
    }
    value = aliases.get(raw, raw)
    return value if value in {"transaction", "savings", "offset", "credit_card", "mortgage", "personal_loan", "car_loan", "line_of_credit"} else "transaction"


def _connection_response(db: DbSession, row: dict[str, Any]) -> dict[str, Any]:
    accounts = db.execute(text("SELECT * FROM external_accounts WHERE bank_connection_id=:id ORDER BY account_name"), {"id": row["id"]}).mappings().all()
    return {
        "id": row["id"], "provider": row["provider"], "provider_label": REDBARK_PROVIDER_NAME,
        "institution_id": row["institution_id"], "institution_name": row["institution_name"],
        "status": row["status"], "consent_status": row["consent_status"],
        "connected_at": str(row["connected_at"]),
        "last_successful_sync": str(row["last_successful_sync"]) if row["last_successful_sync"] else None,
        "last_attempted_sync": str(row["last_attempted_sync"]) if row["last_attempted_sync"] else None,
        "error_state": row["error_state"], "is_mock": bool(row["is_mock"]),
        "accounts": [_external_response(item) for item in accounts],
    }


def _external_response(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": data["id"], "bank_connection_id": data["bank_connection_id"],
        "provider_account_id": data["provider_account_id"], "fynvo_account_id": data["fynvo_account_id"],
        "institution_name": data["institution_name"], "name": data["account_name"],
        "account_type": data["account_type"], "masked_identifier": data["masked_identifier"],
        "current_balance": cents_to_decimal(data["current_balance_cents"]) if data["current_balance_cents"] is not None else None,
        "available_balance": cents_to_decimal(data["available_balance_cents"]) if data["available_balance_cents"] is not None else None,
        "balance_timestamp": str(data["balance_timestamp"]) if data["balance_timestamp"] else None,
        "last_successful_sync": str(data.get("last_successful_sync")) if data.get("last_successful_sync") else None,
        "last_attempted_sync": str(data.get("last_attempted_sync")) if data.get("last_attempted_sync") else None,
        "error_state": data.get("error_state"), "status": data["status"], "ignored": bool(data["ignored"]),
    }


def _connection(db: DbSession, user_id: int, connection_id: int) -> dict[str, Any]:
    row = db.execute(text("SELECT * FROM bank_connections WHERE id=:id AND user_id=:user_id AND provider='redbark'"), {"id": connection_id, "user_id": user_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    return dict(row)


def _provider() -> RedbarkProvider:
    key = _redbark_key()
    if not key:
        raise HTTPException(status_code=409, detail="Redbark is not configured")
    return RedbarkProvider(key)


def _upsert_connections_and_accounts(db: DbSession, user: User, provider: RedbarkProvider) -> list[dict[str, Any]]:
    now = utcnow()
    remote_connections = provider.connections()
    remote_accounts = provider.accounts()
    balances = provider.balances([item["provider_account_id"] for item in remote_accounts])
    connection_ids: dict[str, int] = {}
    for remote in remote_connections:
        existing = db.execute(text("SELECT id FROM bank_connections WHERE user_id=:user_id AND provider='redbark' AND provider_connection_id=:remote_id"), {"user_id": user.id, "remote_id": remote["id"]}).scalar()
        values = {"user_id": user.id, "remote_id": remote["id"], "institution_id": remote["institution_id"] or remote["id"], "institution_name": remote["institution_name"], "status": remote["status"] or "connected", "now": now}
        if existing:
            connection_id = int(existing)
            db.execute(text("UPDATE bank_connections SET institution_id=:institution_id,institution_name=:institution_name,status=:status,consent_status='provider_managed',error_state=NULL,is_mock=0,updated_at=:now WHERE id=:id"), {**values, "id": connection_id})
        else:
            db.execute(text("""INSERT INTO bank_connections(user_id,provider,provider_connection_id,institution_id,institution_name,status,consent_status,connected_at,is_mock,created_at,updated_at)
                VALUES(:user_id,'redbark',:remote_id,:institution_id,:institution_name,:status,'provider_managed',:now,0,:now,:now)"""), values)
            connection_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
        connection_ids[remote["id"]] = connection_id
    for remote in remote_accounts:
        connection_id = connection_ids.get(remote["connection_id"])
        if not connection_id:
            continue
        balance = balances.get(remote["provider_account_id"], {})
        current = parse_money(str(balance["current_balance"])) if balance.get("current_balance") not in (None, "") else None
        available = parse_money(str(balance["available_balance"])) if balance.get("available_balance") not in (None, "") else None
        existing = db.execute(text("SELECT id FROM external_accounts WHERE user_id=:user_id AND provider='redbark' AND provider_account_id=:provider_account_id"), {"user_id": user.id, "provider_account_id": remote["provider_account_id"]}).scalar()
        values = {"user_id": user.id, "connection_id": connection_id, "provider_account_id": remote["provider_account_id"], "institution": remote["institution"], "name": remote["name"], "account_type": _account_type(remote["account_type"]), "masked": remote["masked_identifier"], "current": current, "available": available, "now": now}
        if existing:
            db.execute(text("""UPDATE external_accounts SET bank_connection_id=:connection_id,institution_name=:institution,account_name=:name,account_type=:account_type,masked_identifier=:masked,current_balance_cents=:current,available_balance_cents=:available,balance_timestamp=:now,updated_at=:now WHERE id=:id"""), {**values, "id": int(existing)})
        else:
            db.execute(text("""INSERT INTO external_accounts(user_id,bank_connection_id,provider,provider_account_id,institution_name,account_name,account_type,masked_identifier,current_balance_cents,available_balance_cents,balance_timestamp,status,ignored,created_at,updated_at)
                VALUES(:user_id,:connection_id,'redbark',:provider_account_id,:institution,:name,:account_type,:masked,:current,:available,:now,'discovered',0,:now,:now)"""), values)
    db.commit()
    rows = db.execute(text("SELECT * FROM bank_connections WHERE user_id=:user_id AND provider='redbark' ORDER BY institution_name"), {"user_id": user.id}).mappings().all()
    return [_connection_response(db, dict(row)) for row in rows]


def _create_fynvo_account(db: DbSession, user: User, external: dict[str, Any]) -> int:
    now = utcnow()
    db.execute(text("""INSERT INTO accounts(user_id,name,account_type,institution,opening_balance_cents,minimum_balance_cents,balance_updated_at,balance_update_source,description,account_suffix,icon,is_active,connection_status,available_balance_cents,balance_timestamp,bank_provider,created_at,updated_at)
        VALUES(:user_id,:name,:account_type,:institution,:balance,0,:now,'redbark','Connected through Redbark Open Banking.',:suffix,'bank',1,'connected',:available,:now,'redbark',:now,:now)"""), {
        "user_id": user.id, "name": external["account_name"], "account_type": _account_type(external["account_type"]),
        "institution": external["institution_name"], "balance": int(external["current_balance_cents"] or 0),
        "available": external["available_balance_cents"], "suffix": str(external["masked_identifier"] or "")[-4:], "now": now,
    })
    return int(db.execute(text("SELECT last_insert_rowid()")).scalar())


def _set_actual_balance(db: DbSession, account: Account, current_balance: int | None, available_balance: int | None, timestamp: datetime) -> None:
    if current_balance is not None:
        transaction_total = account_balance_cents(db, account) - int(account.opening_balance_cents or 0)
        account.opening_balance_cents = current_balance - transaction_total
    account.balance_updated_at = timestamp
    account.balance_update_source = "redbark"
    account.connection_status = "connected"  # type: ignore[attr-defined]
    account.available_balance_cents = available_balance  # type: ignore[attr-defined]
    account.balance_timestamp = timestamp  # type: ignore[attr-defined]
    account.bank_provider = "redbark"  # type: ignore[attr-defined]
    account.updated_at = timestamp


def _insert_transaction(db: DbSession, user: User, external: dict[str, Any], row: dict[str, Any]) -> str:
    if not external.get("fynvo_account_id"):
        return "ignored"
    provider_transaction_id = str(row.get("id") or "")
    if not provider_transaction_id:
        return "ignored"
    existing = db.execute(text("SELECT transaction_id FROM bank_transaction_identities WHERE user_id=:user_id AND provider='redbark' AND provider_transaction_id=:provider_transaction_id"), {"user_id": user.id, "provider_transaction_id": provider_transaction_id}).scalar()
    if existing:
        return "duplicate"
    account = get_account(db, user, int(external["fynvo_account_id"]))
    raw_amount = parse_money(str(row.get("amount") or "0"))
    direction = str(row.get("direction") or "").lower()
    if direction in {"credit", "in", "income"}:
        tx_type = "income"
    elif direction in {"debit", "out", "expense"}:
        tx_type = "expense"
    else:
        tx_type = "income" if raw_amount >= 0 else "expense"
    amount = abs(raw_amount)
    signed = signed_amount_cents(account, tx_type, amount)
    tx_date = date.fromisoformat(str(row.get("date"))[:10])
    posted = date.fromisoformat(str(row.get("posted_date"))[:10]) if row.get("posted_date") else tx_date
    now = utcnow()
    db.execute(text("""INSERT INTO transactions(user_id,account_id,transaction_date,posted_date,amount_cents,transaction_type,description,merchant,category,source,status,raw_description,external_id,provider,provider_account_id,provider_transaction_id,reconciliation_state,created_at,updated_at)
        VALUES(:user_id,:account_id,:date,:posted,:amount,:type,:description,:merchant,:category,'bank_sync','cleared',:raw,:external_id,'redbark',:provider_account_id,:provider_transaction_id,'unmatched',:now,:now)"""), {
        "user_id": user.id, "account_id": account.id, "date": tx_date, "posted": posted, "amount": signed, "type": tx_type,
        "description": row.get("description") or "Bank transaction", "merchant": row.get("merchant"), "category": row.get("category"),
        "raw": row.get("description"), "external_id": provider_transaction_id, "provider_account_id": external["provider_account_id"],
        "provider_transaction_id": provider_transaction_id, "now": now,
    })
    transaction_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    fingerprint = f"redbark:{external['provider_account_id']}:{provider_transaction_id}"
    db.execute(text("""INSERT INTO bank_transaction_identities(user_id,external_account_id,transaction_id,provider,provider_transaction_id,fingerprint,status,created_at,updated_at)
        VALUES(:user_id,:external_account_id,:transaction_id,'redbark',:provider_transaction_id,:fingerprint,'cleared',:now,:now)"""), {
        "user_id": user.id, "external_account_id": external["id"], "transaction_id": transaction_id,
        "provider_transaction_id": provider_transaction_id, "fingerprint": fingerprint, "now": now,
    })
    return "added"


def _sync_connection(db: DbSession, user: User, connection_id: int, *, automatic: bool = False) -> dict[str, Any]:
    key = (user.id, connection_id)
    with _SYNC_GUARD:
        if key in _SYNC_KEYS:
            raise HTTPException(status_code=409, detail="This bank connection is already synchronising")
        _SYNC_KEYS.add(key)
    started = utcnow()
    try:
        connection = _connection(db, user.id, connection_id)
        if connection["status"] == "disconnected":
            raise HTTPException(status_code=409, detail="Reconnect this bank connection before syncing")
        provider = _provider()
        db.execute(text("UPDATE bank_connections SET status='syncing',last_attempted_sync=:now,updated_at=:now WHERE id=:id"), {"id": connection_id, "now": started})
        db.commit()
        remote_accounts = {item["provider_account_id"]: item for item in provider.accounts() if item["connection_id"] == connection["provider_connection_id"]}
        balances = provider.balances(list(remote_accounts))
        external_rows = db.execute(text("SELECT * FROM external_accounts WHERE user_id=:user_id AND bank_connection_id=:connection_id AND ignored=0"), {"user_id": user.id, "connection_id": connection_id}).mappings().all()
        added = duplicates = ignored = 0
        completed_accounts = failed_accounts = 0
        for raw_external in external_rows:
            external = dict(raw_external)
            if external["provider_account_id"] not in remote_accounts:
                continue
            attempt = utcnow()
            db.execute(text("UPDATE external_accounts SET last_attempted_sync=:now,error_state=NULL WHERE id=:id"), {"id": external["id"], "now": attempt})
            db.commit()
            try:
                last_success = external.get("last_successful_sync")
                from_date = None
                if last_success:
                    parsed = datetime.fromisoformat(str(last_success).replace("Z", "+00:00")).date()
                    from_date = parsed - timedelta(days=INCREMENTAL_OVERLAP_DAYS)
                rows = provider.transactions(connection["provider_connection_id"], external["provider_account_id"], from_date)
                for row in rows:
                    result = _insert_transaction(db, user, external, row)
                    if result == "added": added += 1
                    elif result == "duplicate": duplicates += 1
                    else: ignored += 1
                balance = balances.get(external["provider_account_id"], {})
                current = parse_money(str(balance["current_balance"])) if balance.get("current_balance") not in (None, "") else None
                available = parse_money(str(balance["available_balance"])) if balance.get("available_balance") not in (None, "") else None
                now = utcnow()
                db.execute(text("UPDATE external_accounts SET current_balance_cents=:current,available_balance_cents=:available,balance_timestamp=:now,last_transaction_sync=:now,last_successful_sync=:now,error_state=NULL,status=CASE WHEN fynvo_account_id IS NULL THEN status ELSE 'linked' END,updated_at=:now WHERE id=:id"), {"id": external["id"], "current": current, "available": available, "now": now})
                if external.get("fynvo_account_id"):
                    account = get_account(db, user, int(external["fynvo_account_id"]))
                    _set_actual_balance(db, account, current, available, now)
                db.commit()
                completed_accounts += 1
            except (RedbarkError, HTTPException, SQLAlchemyError, ValueError, TypeError, LookupError) as account_exc:
                db.rollback()
                failed_accounts += 1
                db.execute(text("UPDATE external_accounts SET error_state=:error,status=CASE WHEN fynvo_account_id IS NULL THEN status ELSE 'stale' END,updated_at=:now WHERE id=:id"), {"id": external["id"], "error": "Bank data could not be refreshed. Last-known data is still available.", "now": utcnow()})
                db.commit()
                logger.warning("bank_sync_account_failed provider=redbark connection_id=%s account_id=%s error=%s", connection_id, external["id"], type(account_exc).__name__)
        completed = utcnow()
        final_status = "connected" if failed_accounts == 0 else "partial"
        message = None if failed_accounts == 0 else f"{failed_accounts} account(s) could not be refreshed. Last-known data is still available."
        db.execute(text("UPDATE bank_connections SET status=:status,last_successful_sync=CASE WHEN :completed_accounts > 0 THEN :now ELSE last_successful_sync END,error_state=:error,updated_at=:now WHERE id=:id"), {"id": connection_id, "status": final_status, "completed_accounts": completed_accounts, "error": message, "now": completed})
        db.execute(text("""INSERT INTO bank_sync_history(user_id,bank_connection_id,started_at,completed_at,status,added_count,updated_count,duplicate_count,review_count,error_message,created_at)
            VALUES(:user_id,:connection_id,:started,:completed,:status,:added,0,:duplicates,0,:error,:completed)"""), {"user_id": user.id, "connection_id": connection_id, "started": started, "completed": completed, "status": "success" if failed_accounts == 0 else "partial", "added": added, "duplicates": duplicates + ignored, "error": message})
        db.commit()
        logger.info("bank_sync_complete provider=redbark automatic=%s connection_id=%s accounts=%s failed=%s added=%s duplicates=%s", automatic, connection_id, completed_accounts, failed_accounts, added, duplicates)
        return {"status": final_status, "accounts_synced": completed_accounts, "accounts_failed": failed_accounts, "added": added, "duplicates_ignored": duplicates + ignored, "connection": _connection_response(db, _connection(db, user.id, connection_id))}
    except RedbarkError as exc:
        db.rollback()
        db.execute(text("UPDATE bank_connections SET status='error',error_state=:error,updated_at=:now WHERE id=:id"), {"id": connection_id, "error": exc.message, "now": utcnow()})
        db.commit()
        raise HTTPException(status_code=502 if exc.status_code >= 500 else exc.status_code, detail=exc.message) from exc
    finally:
        with _SYNC_GUARD:
            _SYNC_KEYS.discard(key)


@router.get("/providers")
def provider_catalog() -> dict[str, Any]:
    return {"providers": [{"id": "redbark", "name": REDBARK_PROVIDER_NAME, "mode": "live", "credential_configured": bool(_redbark_key()), "pending_transactions": False, "automatic_sync_minutes": 30}]}


@router.get("/redbark/status")
def redbark_status(db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_v126_schema()
    rows = db.execute(text("SELECT * FROM bank_connections WHERE user_id=:user_id AND provider='redbark' ORDER BY institution_name"), {"user_id": current_user.id}).mappings().all()
    return {"provider": "redbark", "configured": bool(_redbark_key()), "connections": [_connection_response(db, dict(row)) for row in rows], "automatic_sync_minutes": 30, "pending_transactions_supported": False}


@router.put("/redbark/credentials")
def configure_redbark(payload: RedbarkCredentialPayload, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_v126_schema()
    provider = RedbarkProvider(payload.api_key)
    try:
        validation = provider.validate()
    except RedbarkError as exc:
        raise HTTPException(status_code=400 if exc.status_code == 401 else 502, detail=exc.message) from exc
    _set_redbark_key(payload.api_key)
    connections = _upsert_connections_and_accounts(db, current_user, provider)
    return {"status": "configured", "credential_configured": True, "connection_count": validation["connection_count"], "connections": connections}


@router.post("/redbark/test")
def test_redbark(current_user: User = USER) -> dict[str, Any]:
    del current_user
    try:
        result = _provider().validate()
    except RedbarkError as exc:
        raise HTTPException(status_code=400 if exc.status_code == 401 else 502, detail=exc.message) from exc
    return {"status": "ok", "connection_count": result["connection_count"]}


@router.post("/redbark/discover")
def discover_redbark(db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_v126_schema()
    try:
        rows = _upsert_connections_and_accounts(db, current_user, _provider())
    except RedbarkError as exc:
        raise HTTPException(status_code=502 if exc.status_code >= 500 else exc.status_code, detail=exc.message) from exc
    return {"status": "ok", "connections": rows}


@router.post("/{connection_id}/accounts/{external_account_id}/mapping")
def map_account(connection_id: int, external_account_id: int, payload: AccountMappingPayload, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_v126_schema()
    _connection(db, current_user.id, connection_id)
    row = db.execute(text("SELECT * FROM external_accounts WHERE id=:id AND user_id=:user_id AND bank_connection_id=:connection_id AND provider='redbark'"), {"id": external_account_id, "user_id": current_user.id, "connection_id": connection_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Discovered bank account not found")
    external = dict(row)
    if payload.action == "ignore":
        db.execute(text("UPDATE external_accounts SET ignored=1,status='ignored',fynvo_account_id=NULL,updated_at=:now WHERE id=:id"), {"id": external_account_id, "now": utcnow()})
    elif payload.action == "unlink":
        db.execute(text("UPDATE external_accounts SET ignored=0,status='discovered',fynvo_account_id=NULL,updated_at=:now WHERE id=:id"), {"id": external_account_id, "now": utcnow()})
    else:
        account_id = payload.fynvo_account_id
        if payload.action == "create" or account_id is None:
            account_id = external.get("fynvo_account_id") or _create_fynvo_account(db, current_user, external)
        account = get_account(db, current_user, int(account_id))
        if not account.is_active or account.archived_at is not None:
            raise HTTPException(status_code=409, detail="Choose an active Fynvo account")
        _set_actual_balance(db, account, external.get("current_balance_cents"), external.get("available_balance_cents"), utcnow())
        db.execute(text("UPDATE external_accounts SET ignored=0,status='linked',fynvo_account_id=:account_id,updated_at=:now WHERE id=:id"), {"id": external_account_id, "account_id": account.id, "now": utcnow()})
    db.commit()
    updated = db.execute(text("SELECT * FROM external_accounts WHERE id=:id"), {"id": external_account_id}).mappings().first()
    return _external_response(updated)


@router.post("/{connection_id}/sync")
def sync_connection(connection_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_v126_schema()
    return _sync_connection(db, current_user, connection_id)


@router.post("/{connection_id}/disconnect")
def disconnect_connection(connection_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_v126_schema()
    _connection(db, current_user.id, connection_id)
    now = utcnow()
    db.execute(text("UPDATE bank_connections SET status='disconnected',error_state=NULL,updated_at=:now WHERE id=:id"), {"id": connection_id, "now": now})
    db.execute(text("UPDATE accounts SET connection_status='disconnected',updated_at=:now WHERE id IN (SELECT fynvo_account_id FROM external_accounts WHERE bank_connection_id=:id AND fynvo_account_id IS NOT NULL)"), {"id": connection_id, "now": now})
    db.commit()
    return _connection_response(db, _connection(db, current_user.id, connection_id))


@router.delete("/redbark/credentials")
def remove_redbark_credentials(db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_v126_schema()
    now = utcnow()
    db.execute(text("UPDATE bank_connections SET status='disconnected',error_state=NULL,updated_at=:now WHERE user_id=:user_id AND provider='redbark'"), {"user_id": current_user.id, "now": now})
    db.execute(text("UPDATE accounts SET connection_status='disconnected',updated_at=:now WHERE id IN (SELECT fynvo_account_id FROM external_accounts WHERE user_id=:user_id AND provider='redbark' AND fynvo_account_id IS NOT NULL)"), {"user_id": current_user.id, "now": now})
    db.commit()
    _remove_redbark_key()
    return {"status": "disconnected", "credential_configured": False, "history_preserved": True}


@router.get("/{connection_id}/sync-history")
def connection_sync_history(connection_id: int, db: DbSession = DB, current_user: User = USER) -> list[dict[str, Any]]:
    ensure_banking_v126_schema()
    _connection(db, current_user.id, connection_id)
    rows = db.execute(text("SELECT * FROM bank_sync_history WHERE user_id=:user_id AND bank_connection_id=:connection_id ORDER BY started_at DESC LIMIT 50"), {"user_id": current_user.id, "connection_id": connection_id}).mappings().all()
    return [{"id": row["id"], "started_at": str(row["started_at"]), "completed_at": str(row["completed_at"]) if row["completed_at"] else None, "status": row["status"], "added": row["added_count"], "duplicates_ignored": row["duplicate_count"], "error_message": row["error_message"]} for row in rows]


def run_automatic_sync_once() -> None:
    if not _redbark_key():
        return
    Session = get_session_factory()
    db = Session()
    try:
        ensure_banking_v126_schema()
        rows = db.execute(text("SELECT bc.id,bc.user_id FROM bank_connections bc WHERE bc.provider='redbark' AND bc.status NOT IN ('disconnected','syncing') AND EXISTS(SELECT 1 FROM external_accounts ea WHERE ea.bank_connection_id=bc.id AND ea.fynvo_account_id IS NOT NULL AND ea.ignored=0)" )).mappings().all()
        for row in rows:
            user = db.query(User).filter(User.id == row["user_id"], User.is_active.is_(True)).first()
            if not user:
                continue
            last = db.execute(text("SELECT last_successful_sync FROM bank_connections WHERE id=:id"), {"id": row["id"]}).scalar()
            if last:
                try:
                    if utcnow() - datetime.fromisoformat(str(last)) < timedelta(seconds=AUTOMATIC_SYNC_INTERVAL_SECONDS):
                        continue
                except ValueError:
                    pass
            try:
                _sync_connection(db, user, int(row["id"]), automatic=True)
            except HTTPException as exc:
                logger.warning("automatic_bank_sync_failed connection_id=%s error=%s", row["id"], type(exc).__name__)
    finally:
        db.close()


async def automatic_sync_loop() -> None:
    while True:
        await asyncio.sleep(AUTOMATIC_SYNC_INTERVAL_SECONDS)
        await asyncio.to_thread(run_automatic_sync_once)


def start_automatic_sync() -> None:
    global _SCHEDULER_TASK
    if _SCHEDULER_TASK is None or _SCHEDULER_TASK.done():
        _SCHEDULER_TASK = asyncio.create_task(automatic_sync_loop(), name="fynvo-redbark-sync")


async def stop_automatic_sync() -> None:
    global _SCHEDULER_TASK
    if _SCHEDULER_TASK is None:
        return
    _SCHEDULER_TASK.cancel()
    try:
        await _SCHEDULER_TASK
    except asyncio.CancelledError:
        pass
    _SCHEDULER_TASK = None
