from __future__ import annotations

from datetime import date
from typing import ClassVar

from sqlalchemy import text

from app import banking_v126
from app.database import get_engine
from app.redbark import RedbarkProvider


def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


class FakeRedbarkProvider:
    provider = "redbark"
    name = "Redbark Open Banking"

    def validate(self):
        return {"status": "ok", "connection_count": 1}

    def connections(self):
        return [{"id": "conn-1", "provider": "fiskil", "category": "banking", "institution_id": "bank-1", "institution_name": "Example Bank", "status": "connected", "last_refreshed_at": None, "created_at": "2026-09-17T00:00:00Z"}]

    def accounts(self):
        return [{"provider_account_id": "acct-1", "connection_id": "conn-1", "name": "Everyday", "account_type": "transaction", "institution": "Example Bank", "masked_identifier": "•••• 1234", "currency": "AUD"}]

    def balances(self, account_ids):
        assert account_ids == ["acct-1"]
        return {"acct-1": {"current_balance": "1250.00", "available_balance": "1200.00", "currency": "AUD"}}

    def transactions(self, connection_id, account_id=None, date_from=None, date_to=None, **kwargs):
        assert connection_id == "conn-1"
        assert account_id == "acct-1"
        return [{"id": "tx-1", "account_id": "acct-1", "date": "2026-09-17", "posted_date": "2026-09-17", "amount": "-29.00", "direction": "debit", "description": "NETFLIX.COM", "merchant": "Netflix", "category": "entertainment", "status": "posted"}]


def test_redbark_provider_normalises_official_contract():
    class Response:
        status_code = 200
        headers: ClassVar[dict[str, str]] = {}
        def json(self):
            return {"data": [{"id": "t1", "accountId": "a1", "accountName": "Everyday", "status": "POSTED", "date": "2026-09-17", "datetime": None, "postDate": "2026-09-17", "postDatetime": None, "valueDate": None, "valueDatetime": None, "description": "Coffee", "amount": "-5.50", "direction": "DEBIT", "category": "dining", "customCategory": None, "customCategoryGroup": None, "merchantName": "Cafe", "merchantCategoryCode": "5812"}], "pagination": {"total": 1, "limit": 200, "offset": 0, "hasMore": False}}

    class Client:
        def get(self, url, params=None, headers=None):
            assert headers["Authorization"] == "Bearer secret-key"
            assert params["includePending"] == "false"
            return Response()

    provider = RedbarkProvider("secret-key", client=Client())
    rows = provider.transactions("c1", "a1", date(2026, 9, 1))
    assert rows[0]["id"] == "t1"
    assert rows[0]["direction"] == "debit"
    assert rows[0]["status"] == "posted"
    assert rows[0]["merchant"] == "Cafe"


def test_configure_discover_map_sync_is_idempotent_and_updates_actual_balance(client, monkeypatch, tmp_path):
    setup_user(client)
    monkeypatch.setenv("FYNVO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(banking_v126, "RedbarkProvider", lambda api_key: FakeRedbarkProvider())
    configured = client.put("/api/bank-connections/redbark/credentials", json={"api_key": "redbark-test-key"})
    assert configured.status_code == 200
    assert configured.json()["credential_configured"] is True
    status = client.get("/api/bank-connections/redbark/status").json()
    assert status["configured"] is True
    external = status["connections"][0]["accounts"][0]
    mapped = client.post(f"/api/bank-connections/{status['connections'][0]['id']}/accounts/{external['id']}/mapping", json={"action": "create"})
    assert mapped.status_code == 200
    account_id = mapped.json()["fynvo_account_id"]

    first = client.post(f"/api/bank-connections/{status['connections'][0]['id']}/sync")
    assert first.status_code == 200
    assert first.json()["added"] == 1
    second = client.post(f"/api/bank-connections/{status['connections'][0]['id']}/sync")
    assert second.status_code == 200
    assert second.json()["added"] == 0
    assert second.json()["duplicates_ignored"] >= 1

    account = next(item for item in client.get("/api/accounts").json() if item["id"] == account_id)
    assert account["current_balance"] == "1250.00"
    assert account["balance_update_source"] == "redbark"
    rows = client.get("/api/transactions").json()
    assert len([row for row in rows if row["source"] == "bank_sync"]) == 1

    with get_engine().begin() as connection:
        assert connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar() >= 15
        assert connection.execute(text("SELECT COUNT(*) FROM bank_transaction_identities WHERE provider='redbark'")).scalar() == 1


def test_disconnect_and_credential_removal_preserve_history(client, monkeypatch, tmp_path):
    setup_user(client)
    monkeypatch.setenv("FYNVO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(banking_v126, "RedbarkProvider", lambda api_key: FakeRedbarkProvider())
    client.put("/api/bank-connections/redbark/credentials", json={"api_key": "redbark-test-key"})
    state = client.get("/api/bank-connections/redbark/status").json()
    connection = state["connections"][0]
    external = connection["accounts"][0]
    client.post(f"/api/bank-connections/{connection['id']}/accounts/{external['id']}/mapping", json={"action": "create"})
    client.post(f"/api/bank-connections/{connection['id']}/sync")
    before = len(client.get("/api/transactions").json())
    disconnected = client.post(f"/api/bank-connections/{connection['id']}/disconnect")
    assert disconnected.status_code == 200
    removed = client.delete("/api/bank-connections/redbark/credentials")
    assert removed.status_code == 200
    assert removed.json()["history_preserved"] is True
    assert len(client.get("/api/transactions").json()) == before


def test_secret_file_is_backend_only_and_mode_0600(monkeypatch, tmp_path):
    monkeypatch.setenv("FYNVO_DATA_DIR", str(tmp_path))
    banking_v126._set_redbark_key("secret-redbark-key")
    path = tmp_path / "banking-secrets.json"
    assert path.exists()
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert banking_v126._redbark_key() == "secret-redbark-key"
