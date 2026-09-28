from __future__ import annotations

from typing import ClassVar

from app import banking_v126
from app.database import get_engine
from sqlalchemy import text


class Provider:
    accounts_list: ClassVar[list[dict]] = [
        {"provider_account_id": "a1", "connection_id": "c1", "name": "Everyday", "account_type": "transaction", "institution": "Bank", "masked_identifier": "••1234"},
        {"provider_account_id": "a2", "connection_id": "c1", "name": "Savings", "account_type": "savings", "institution": "Bank", "masked_identifier": "••5678"},
    ]
    failed: ClassVar[set[str]] = set()

    def __init__(self, _key):
        pass

    def validate(self):
        return {"status": "ok", "connection_count": 1}

    def connections(self):
        return [{"id": "c1", "institution_id": "bank", "institution_name": "Bank", "status": "connected"}]

    def accounts(self):
        return self.accounts_list

    def balances(self, ids):
        return {item: {"current_balance": "100.00", "available_balance": "90.00"} for item in ids}

    def transactions(self, _connection, account_id, _from_date):
        if account_id in self.failed:
            from app.redbark import RedbarkError
            raise RedbarkError("Unavailable", status_code=503)
        return [{"id": f"tx-{account_id}", "date": "2026-09-20", "amount": "-5.00", "direction": "debit", "description": "Coffee"}]


def setup(client, monkeypatch, tmp_path):
    monkeypatch.setattr(Provider, "accounts_list", [dict(item) for item in Provider.accounts_list[:2]])
    monkeypatch.setenv("FYNVO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(banking_v126, "RedbarkProvider", Provider)
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})
    assert client.put("/api/bank-connections/redbark/credentials", json={"api_key": "example-key-123"}).status_code == 200
    return client.get("/api/bank-connections/redbark/status").json()


def map_url(connection, account):
    return f"/api/bank-connections/{connection['id']}/accounts/{account['id']}/mapping"


def test_partial_setup_deduplicates_actions_and_preserves_manual_accounts(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    first, second = connection["accounts"]
    assert len(state["required_actions"]) == 2
    account_id = client.post(map_url(connection, first), json={"action": "create", "name": "Our everyday"}).json()["fynvo_account_id"]
    assert client.post(map_url(connection, second), json={"action": "ignore"}).status_code == 200
    for _ in range(2):
        assert client.post("/api/bank-connections/redbark/discover").status_code == 200
        state = client.get("/api/bank-connections/redbark/status").json()
        assert state["required_actions"] == []
        assert [item["state"] for item in state["connections"][0]["accounts"]] == ["connected", "ignored"]
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").json()["added"] == 1
    assert len([row for row in client.get("/api/transactions").json() if row["source"] == "bank_sync"]) == 1
    assert client.post(map_url(connection, second), json={"action": "restore"}).status_code == 200
    assert len(client.get("/api/bank-connections/redbark/status").json()["required_actions"]) == 1
    assert client.post(map_url(connection, second), json={"action": "link", "fynvo_account_id": account_id}).status_code == 409


def test_missing_provider_account_retains_balance_history_and_recovers(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    first = connection["accounts"][0]
    account_id = client.post(map_url(connection, first), json={"action": "create"}).json()["fynvo_account_id"]
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").status_code == 200
    balance = next(a for a in client.get("/api/accounts").json() if a["id"] == account_id)["current_balance"]
    tx_count = len(client.get("/api/transactions").json())
    monkeypatch.setattr(Provider, "accounts_list", Provider.accounts_list[1:])
    result = client.post(f"/api/bank-connections/{connection['id']}/sync")
    assert result.status_code == 200
    assert result.json()["accounts_failed"] == 1
    state = client.get("/api/bank-connections/redbark/status").json()
    assert any(action["state"] == "needs_attention" for action in state["required_actions"])
    assert next(a for a in client.get("/api/accounts").json() if a["id"] == account_id)["current_balance"] == balance
    assert len(client.get("/api/transactions").json()) == tx_count
    monkeypatch.setattr(Provider, "accounts_list", [
        {"provider_account_id": "a1", "connection_id": "c1", "name": "Renamed at bank", "account_type": "transaction", "institution": "Bank", "masked_identifier": "••1234"},
        *Provider.accounts_list,
    ])
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").status_code == 200
    assert not any(action["state"] == "needs_attention" for action in client.get("/api/bank-connections/redbark/status").json()["required_actions"])
    with get_engine().begin() as db:
        assert db.execute(text("SELECT fynvo_account_id FROM external_accounts WHERE provider_account_id='a1'")).scalar() == account_id


def test_new_account_later_and_unlink_preserve_financial_history(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    first = connection["accounts"][0]
    account_id = client.post(map_url(connection, first), json={"action": "create"}).json()["fynvo_account_id"]
    client.post(f"/api/bank-connections/{connection['id']}/sync")
    Provider.accounts_list.append({"provider_account_id": "a3", "connection_id": "c1", "name": "New account", "account_type": "savings", "institution": "Bank", "masked_identifier": "••9999"})
    client.post(f"/api/bank-connections/{connection['id']}/sync")
    actions = client.get("/api/bank-connections/redbark/status").json()["required_actions"]
    assert len(actions) == 2  # a2 and the newly opened a3
    assert len({action["id"] for action in actions}) == 2
    assert client.post(map_url(connection, first), json={"action": "unlink"}).status_code == 200
    assert next(a for a in client.get("/api/accounts").json() if a["id"] == account_id)["current_balance"] == "100.00"
    assert len(client.get("/api/transactions").json()) == 1
    assert client.delete("/api/bank-connections/redbark/credentials").json()["history_preserved"]
    assert len(client.get("/api/transactions").json()) == 1


def test_link_existing_updates_actual_balance_without_changing_manual_account(client, monkeypatch, tmp_path):
    monkeypatch.setenv("FYNVO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(banking_v126, "RedbarkProvider", Provider)
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})
    bank = client.post("/api/accounts", json={"name": "Shared Bank", "account_type": "transaction", "opening_balance": "25.00"}).json()
    manual = client.post("/api/accounts", json={"name": "Cash", "account_type": "transaction", "opening_balance": "50.00"}).json()
    assert client.put("/api/bank-connections/redbark/credentials", json={"api_key": "example-key-123"}).status_code == 200
    state = client.get("/api/bank-connections/redbark/status").json()
    connection = state["connections"][0]
    first, second = connection["accounts"][:2]
    assert client.post(map_url(connection, first), json={"action": "link", "fynvo_account_id": bank["id"]}).status_code == 200
    assert client.post(map_url(connection, second), json={"action": "link", "fynvo_account_id": bank["id"]}).status_code == 409
    assert client.post(map_url(connection, second), json={"action": "ignore"}).status_code == 200
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").json()["accounts_synced"] == 1
    rows = {row["id"]: row for row in client.get("/api/accounts").json()}
    assert rows[bank["id"]]["name"] == "Shared Bank"
    assert rows[bank["id"]]["current_balance"] == "100.00"
    assert rows[manual["id"]]["current_balance"] == "50.00"
    assert rows[manual["id"]]["balance_update_source"] == "manual"
    assert len(client.get("/api/bank-connections/redbark/status").json()["required_actions"]) == 0
    with get_engine().begin() as db:
        assert db.execute(text("SELECT COUNT(*) FROM bank_transaction_identities")).scalar() == 1
        assert db.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 2


def test_legacy_duplicate_mappings_require_review_without_blocking_migration(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    first, second = connection["accounts"]
    linked = client.post(map_url(connection, first), json={"action": "create"}).json()["fynvo_account_id"]
    with get_engine().begin() as db:
        db.execute(text("DROP INDEX idx_external_accounts_active_mapping"))
        db.execute(text("UPDATE external_accounts SET fynvo_account_id=:account,status='linked' WHERE id=:id"), {"account": linked, "id": second["id"]})
    state = client.get("/api/bank-connections/redbark/status").json()
    assert len([action for action in state["required_actions"] if action["state"] == "needs_attention"]) == 2
    result = client.post(f"/api/bank-connections/{connection['id']}/sync").json()
    assert result["accounts_failed"] == 2
    assert result["accounts_synced"] == 0
    assert client.post(map_url(connection, second), json={"action": "unlink"}).status_code == 200
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").json()["accounts_synced"] == 1


def test_missing_balance_does_not_shift_last_known_actual(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    first = connection["accounts"][0]
    account_id = client.post(map_url(connection, first), json={"action": "create"}).json()["fynvo_account_id"]
    client.post(f"/api/bank-connections/{connection['id']}/sync")
    before = next(row["current_balance"] for row in client.get("/api/accounts").json() if row["id"] == account_id)
    monkeypatch.setattr(Provider, "balances", lambda _self, _ids: {})
    result = client.post(f"/api/bank-connections/{connection['id']}/sync")
    assert result.status_code == 200
    assert result.json()["accounts_failed"] == 1
    assert next(row["current_balance"] for row in client.get("/api/accounts").json() if row["id"] == account_id) == before
    assert len(client.get("/api/transactions").json()) == 1
