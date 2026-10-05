from __future__ import annotations

from typing import ClassVar

from app import banking_v126
from app.database import get_engine
from app.redbark import RedbarkError
from sqlalchemy import text


class HouseholdProvider:
    names: ClassVar[dict[str, str]] = {"stu-1": "Orange Everyday", "stu-2": "Orange Everyday", "kri-1": "Orange Everyday"}
    missing_balance = False
    fail_connection = None
    shared_transaction_id = False
    wrong_account = None
    missing_connection = None

    def __init__(self, _key):
        pass

    def validate(self):
        return {"connection_count": 2}

    def connections(self):
        return [row for row in [
            {"id": "stu", "institution_id": "ing", "institution_name": "ING BANK (Australia) Ltd", "status": "connected"},
            {"id": "kri", "institution_id": "ing", "institution_name": "ING BANK (Australia) Ltd", "status": "connected"},
        ] if row["id"] != self.missing_connection]

    def accounts(self):
        return [
            {"provider_account_id": account_id, "connection_id": "stu" if account_id.startswith("stu") else "kri",
             "name": name, "account_type": "transaction", "institution": "ING BANK (Australia) Ltd",
             "masked_identifier": f"•••• {suffix}"}
            for account_id, name in self.names.items()
            if ("stu" if account_id.startswith("stu") else "kri") != self.missing_connection
            for suffix in [{"stu-1": "2656", "stu-2": "4094", "kri-1": "1234"}[account_id]]
        ]

    def balances(self, ids):
        if self.missing_balance:
            return {}
        return {account_id: {"current_balance": "105.00", "available_balance": "90.00"} for account_id in ids}

    def transactions(self, connection_id, account_id, _from_date):
        if self.fail_connection == connection_id:
            raise RedbarkError("temporary failure", status_code=503)
        return [{"id": "same-transaction-id" if self.shared_transaction_id else f"txn-{account_id}",
                 "account_id": self.wrong_account or account_id, "date": "2026-09-30", "amount": "-5.00",
                 "direction": "debit", "description": "Coffee"}]


def prepared(client, monkeypatch, tmp_path, *, missing_balance=False):
    monkeypatch.setenv("FYNVO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(banking_v126, "RedbarkProvider", HouseholdProvider)
    monkeypatch.setattr(HouseholdProvider, "names", {"stu-1": "Orange Everyday", "stu-2": "Orange Everyday", "kri-1": "Orange Everyday"})
    monkeypatch.setattr(HouseholdProvider, "missing_balance", missing_balance)
    monkeypatch.setattr(HouseholdProvider, "fail_connection", None)
    monkeypatch.setattr(HouseholdProvider, "shared_transaction_id", False)
    monkeypatch.setattr(HouseholdProvider, "wrong_account", None)
    monkeypatch.setattr(HouseholdProvider, "missing_connection", None)
    client.post("/api/auth/setup", json={"username": "stuart", "display_name": "Stuart", "password": "Password123!"})
    response = client.put("/api/bank-connections/redbark/credentials", json={"api_key": "testing-key-123"})
    assert response.status_code == 200, response.text
    return client.get("/api/bank-connections/redbark/status").json()


def mapping_url(connection, account):
    return f"/api/bank-connections/{connection['id']}/accounts/{account['id']}/mapping"


def test_same_institution_and_names_are_isolated_by_stable_ids(client, monkeypatch, tmp_path):
    state = prepared(client, monkeypatch, tmp_path)
    first, second = sorted(state["connections"], key=lambda row: len(row["accounts"]))
    assert first["institution_id"] == second["institution_id"]
    assert first["id"] != second["id"]
    assert len(first["accounts"]) == 1
    assert len(second["accounts"]) == 2
    assert len(state["required_actions"]) == 3
    assert len({action["id"] for action in state["required_actions"]}) == 3
    mapped = {}
    for connection in state["connections"]:
        for account in connection["accounts"]:
            response = client.post(mapping_url(connection, account), json={"action": "create", "name": f"Fynvo {account['masked_identifier']}"})
            assert response.status_code == 200, response.text
            mapped[account["masked_identifier"]] = response.json()["fynvo_account_id"]
    assert len(set(mapped.values())) == 3
    for connection in state["connections"]:
        assert client.post(f"/api/bank-connections/{connection['id']}/sync").status_code == 200
    transactions = [row for row in client.get("/api/transactions").json() if row["source"] == "bank_sync"]
    assert len(transactions) == 3
    assert {row["account_id"] for row in transactions} == set(mapped.values())
    client.post("/api/bank-connections/redbark/discover")
    assert client.get("/api/bank-connections/redbark/status").json()["required_actions"] == []
    banking_v126.ensure_banking_v126_schema(get_engine())
    banking_v126.ensure_banking_v126_schema(get_engine())
    with get_engine().begin() as db:
        assert db.execute(text("SELECT COUNT(*) FROM banking_provider_configurations")).scalar() == 1
        assert db.execute(text("SELECT COUNT(DISTINCT provider_configuration_id) FROM bank_connections")).scalar() == 1
        assert db.execute(text("SELECT MAX(version) FROM schema_version")).scalar() >= 18


def test_connection_context_is_independent_of_provider_identity(client, monkeypatch, tmp_path):
    state = prepared(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    member = client.post("/api/household/members", json={"username": "kristy", "display_name": "Kristy", "role": "household_member"})
    assert member.status_code == 201, member.text
    owner_id = member.json()["user_id"]
    response = client.patch(f"/api/bank-connections/{connection['id']}/context", json={"label": "Kristy's ING", "owner_user_id": owner_id})
    assert response.status_code == 200, response.text
    assert response.json()["display_label"] == "Kristy's ING"
    assert response.json()["owner_name"] == "Kristy"
    assert response.json()["institution_id"] == "ing"
    assert client.patch(f"/api/bank-connections/{connection['id']}/context", json={"owner_user_id": 999999}).status_code == 422
    created = client.post(mapping_url(connection, connection["accounts"][0]), json={"action": "create"})
    assert created.status_code == 200, created.text
    account_id = created.json()["fynvo_account_id"]
    with get_engine().begin() as db:
        assert db.execute(text("SELECT owner_user_id FROM record_ownership WHERE record_type='account' AND record_id=:id"), {"id": account_id}).scalar() == owner_id
    client.post("/api/bank-connections/redbark/discover")
    after = client.get("/api/bank-connections/redbark/status").json()
    assert next(row for row in after["connections"] if row["id"] == connection["id"])["display_label"] == "Kristy's ING"
    assert after["account_owners"][str(account_id)] == "Kristy"


def test_missing_balance_has_no_false_timestamp_and_transactions_can_sync(client, monkeypatch, tmp_path):
    state = prepared(client, monkeypatch, tmp_path, missing_balance=True)
    connection = next(row for row in state["connections"] if len(row["accounts"]) == 1)
    account = connection["accounts"][0]
    assert account["balance_timestamp"] is None
    assert client.post(mapping_url(connection, account), json={"action": "create"}).status_code == 422
    result = client.post(mapping_url(connection, account), json={"action": "create", "opening_balance": "50.00"})
    assert result.status_code == 200
    mapped_id = result.json()["fynvo_account_id"]
    result = client.post(f"/api/bank-connections/{connection['id']}/sync")
    assert result.status_code == 200
    assert result.json()["accounts_failed"] == 1
    assert len([row for row in client.get("/api/transactions").json() if row["source"] == "bank_sync"]) == 1
    assert next(row for row in client.get("/api/accounts").json() if row["id"] == mapped_id)["current_balance"] == "45.00"
    refreshed = client.get("/api/bank-connections/redbark/status").json()
    assert next(row for row in refreshed["connections"] if row["id"] == connection["id"])["accounts"][0]["balance_timestamp"] is None


def test_partial_failure_does_not_reset_other_connection_health(client, monkeypatch, tmp_path):
    state = prepared(client, monkeypatch, tmp_path)
    for connection in state["connections"]:
        for account in connection["accounts"]:
            client.post(mapping_url(connection, account), json={"action": "create"})
    monkeypatch.setattr(HouseholdProvider, "fail_connection", "kri")
    failing = next(row for row in state["connections"] if len(row["accounts"]) == 1)
    healthy = next(row for row in state["connections"] if len(row["accounts"]) == 2)
    assert client.post(f"/api/bank-connections/{failing['id']}/sync").json()["accounts_failed"] == 1
    assert client.post(f"/api/bank-connections/{healthy['id']}/sync").json()["accounts_synced"] == 2
    status = {row["id"]: row for row in client.get("/api/bank-connections/redbark/status").json()["connections"]}
    assert status[failing["id"]]["status"] == "partial"
    assert status[healthy["id"]]["status"] == "connected"
    assert status[failing["id"]]["accounts"][0]["state"] == "needs_attention"


def test_identical_transaction_ids_on_different_bank_accounts_do_not_cross_route(client, monkeypatch, tmp_path):
    state = prepared(client, monkeypatch, tmp_path)
    monkeypatch.setattr(HouseholdProvider, "shared_transaction_id", True)
    for connection in state["connections"]:
        for account in connection["accounts"]:
            assert client.post(mapping_url(connection, account), json={"action": "create"}).status_code == 200
        assert client.post(f"/api/bank-connections/{connection['id']}/sync").status_code == 200
    imported = [row for row in client.get("/api/transactions").json() if row["source"] == "bank_sync"]
    assert len(imported) == 3
    assert len({row["account_id"] for row in imported}) == 3
    with get_engine().begin() as db:
        assert db.execute(text("SELECT COUNT(*) FROM bank_transaction_identities WHERE provider_transaction_id='same-transaction-id'")).scalar() == 3
    for connection in state["connections"]:
        assert client.post(f"/api/bank-connections/{connection['id']}/sync").json()["added"] == 0


def test_provider_row_for_another_account_is_quarantined(client, monkeypatch, tmp_path):
    state = prepared(client, monkeypatch, tmp_path)
    connection = next(row for row in state["connections"] if len(row["accounts"]) == 1)
    assert client.post(mapping_url(connection, connection["accounts"][0]), json={"action": "create"}).status_code == 200
    monkeypatch.setattr(HouseholdProvider, "wrong_account", "stu-1")
    result = client.post(f"/api/bank-connections/{connection['id']}/sync").json()
    assert result["accounts_failed"] == 1
    assert [row for row in client.get("/api/transactions").json() if row["source"] == "bank_sync"] == []


def test_disappearing_connection_requires_review_without_blocking_other_one(client, monkeypatch, tmp_path):
    state = prepared(client, monkeypatch, tmp_path)
    missing = next(row for row in state["connections"] if len(row["accounts"]) == 1)
    healthy = next(row for row in state["connections"] if len(row["accounts"]) == 2)
    mapped = client.post(mapping_url(missing, missing["accounts"][0]), json={"action": "create"}).json()["fynvo_account_id"]
    client.post(f"/api/bank-connections/{missing['id']}/sync")
    before = next(row["current_balance"] for row in client.get("/api/accounts").json() if row["id"] == mapped)
    monkeypatch.setattr(HouseholdProvider, "missing_connection", "kri")
    assert client.post(f"/api/bank-connections/{missing['id']}/sync").status_code == 409
    assert client.post(f"/api/bank-connections/{healthy['id']}/sync").status_code == 200
    after = client.get("/api/bank-connections/redbark/status").json()
    assert any(action["id"] == f"bank-connection:{missing['id']}" for action in after["required_actions"])
    assert next(row["current_balance"] for row in client.get("/api/accounts").json() if row["id"] == mapped) == before
