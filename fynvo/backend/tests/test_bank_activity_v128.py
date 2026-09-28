"""Bank evidence stays distinct from Fynvo decisions and financial history."""

from datetime import date, timedelta

import pytest
from app import banking_v126
from app.bank_activity_v128 import ensure_bank_activity_schema
from app.database import get_engine
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError


def setup(client):
    assert client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"}).status_code == 201
    account = client.post("/api/accounts", json={"name": "Shared ING", "account_type": "transaction", "opening_balance": "100.00", "institution": "ING"}).json()
    return account


def recurring(client, account_id, name="Telstra", amount="120.00", due=None):
    due = due or date.today().isoformat()
    response = client.post("/api/recurring-expenses", json={"name": name, "amount": amount, "frequency": "monthly", "next_due_date": due, "payment_method": "direct_debit", "account_id": account_id, "payee_merchant": name})
    assert response.status_code == 201, response.text
    return next(row for row in client.get("/api/scheduled-payments").json() if row["recurring_expense_id"] == response.json()["id"])


def outgoing(client, account_id, merchant="Telstra", amount="120.00", when=None):
    response = client.post("/api/transactions", json={"account_id": account_id, "date": when or date.today().isoformat(), "amount": amount, "transaction_type": "expense", "description": merchant, "merchant": merchant})
    assert response.status_code == 201, response.text
    return response.json()


def test_suggestions_are_deterministic_and_never_pay_automatically(client):
    account = setup(client)
    payment = recurring(client, account["id"])
    tx = outgoing(client, account["id"])
    first = client.get("/api/payments/match-candidates").json()
    match = next(item for item in first if item["transaction_id"] == tx["id"] and item["scheduled_payment_id"] == payment["id"])
    assert match["review_id"] == f"payment-match:{tx['id']}:{payment['id']}"
    assert match["automatic_match_eligible"] is False
    assert "Amount matches" in match["evidence"]
    assert first == client.get("/api/payments/match-candidates").json()
    assert next(item for item in client.get("/api/scheduled-payments").json() if item["id"] == payment["id"])["status"] != "paid"
    assert client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": tx["id"]}).status_code == 200
    assert not any(item["transaction_id"] == tx["id"] for item in client.get("/api/payments/match-candidates").json())
    assert client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": tx["id"]}).status_code == 409
    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM scheduled_payment_history WHERE scheduled_payment_id=:id AND to_status='paid'"), {"id": payment["id"]}).scalar() == 1


def test_rejection_and_ambiguity_leave_payments_open(client):
    account = setup(client)
    first = recurring(client, account["id"], "Insurance", "75.00")
    second = recurring(client, account["id"], "Insurance Plus", "75.00")
    tx = outgoing(client, account["id"], "Insurance", "75.00")
    candidates = [item for item in client.get("/api/payments/match-candidates").json() if item["transaction_id"] == tx["id"]]
    assert len(candidates) >= 2
    assert all(item["review_id"] is None for item in candidates if item["confidence"] == "high")
    assert client.post(f"/api/scheduled-payments/{first['id']}/reject-match", json={"transaction_id": tx["id"]}).status_code == 200
    assert not any(item["scheduled_payment_id"] == first["id"] and item["transaction_id"] == tx["id"] for item in client.get("/api/payments/match-candidates").json())
    assert next(row for row in client.get("/api/scheduled-payments").json() if row["id"] == second["id"])["status"] != "paid"


def test_pending_transfer_and_different_account_cannot_be_confirmed(client):
    account = setup(client)
    other = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "500.00"}).json()
    payment = recurring(client, account["id"])
    wrong = outgoing(client, other["id"])
    assert client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": wrong["id"]}).status_code == 409
    tx = outgoing(client, account["id"])
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE transactions SET status='pending' WHERE id=:id"), {"id": tx["id"]})
    assert client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": tx["id"]}).status_code == 409
    assert not any(item["transaction_id"] == tx["id"] for item in client.get("/api/payments/match-candidates").json())
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE transactions SET status='cleared' WHERE id=:id"), {"id": tx["id"]})
    assert any(item["transaction_id"] == tx["id"] for item in client.get("/api/payments/match-candidates").json())


def test_provider_category_is_not_a_fynvo_category_and_sync_is_idempotent(client, monkeypatch):
    setup(client)
    from test_redbark_v126 import FakeRedbarkProvider
    monkeypatch.setattr(banking_v126, "RedbarkProvider", lambda api_key: FakeRedbarkProvider())
    assert client.put("/api/bank-connections/redbark/credentials", json={"api_key": "redbark-test-key"}).status_code == 200
    connection = client.get("/api/bank-connections/redbark/status").json()["connections"][0]
    external = connection["accounts"][0]
    assert client.post(f"/api/bank-connections/{connection['id']}/accounts/{external['id']}/mapping", json={"action": "create"}).status_code == 200
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").status_code == 200
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").status_code == 200
    imported = [row for row in client.get("/api/payments/transactions").json() if row["source"] == "bank_sync"]
    assert len(imported) == 1
    assert imported[0]["provider_category"] == "entertainment"
    assert imported[0]["category"] is None and imported[0]["category_id"] is None
    ensure_bank_activity_schema(get_engine())
    with get_engine().connect() as db:
        assert db.execute(text("SELECT MAX(version) FROM schema_version")).scalar() == 17


def test_old_bank_history_does_not_flood_review(client):
    account = setup(client)
    due = (date.today() - timedelta(days=90)).isoformat()
    payment = recurring(client, account["id"], due=due)
    tx = outgoing(client, account["id"], when=due)
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE transactions SET source='bank_sync' WHERE id=:id"), {"id": tx["id"]})
    assert not any(item["transaction_id"] == tx["id"] and item["scheduled_payment_id"] == payment["id"] for item in client.get("/api/payments/match-candidates").json())
    assert any(row["id"] == tx["id"] for row in client.get("/api/payments/transactions").json())


def test_confirmed_merchant_and_category_memory_are_reversible(client):
    account = setup(client)
    payment = recurring(client, account["id"])
    tx = outgoing(client, account["id"], merchant="TELSTRA CORP MELB AU")
    category_response = client.post("/api/categories", json={"name": "Telecom services", "category_type": "expense"})
    assert category_response.status_code == 201, category_response.text
    category_id = category_response.json()["id"]
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE transactions SET source='bank_sync',provider_category='telecom' WHERE id=:id"), {"id": tx["id"]})
    assert client.put(f"/api/payments/transactions/{tx['id']}/category", json={"category_id": category_id}).status_code == 200
    second = outgoing(client, account["id"], merchant="TELSTRA CORP MELB AU")
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE transactions SET source='bank_sync' WHERE id=:id"), {"id": second["id"]})
    suggestion = next(row for row in client.get("/api/payments/transactions").json() if row["id"] == second["id"])
    assert suggestion["category_id"] is None
    assert suggestion["category_suggestion"]["category_id"] == category_id
    assert client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": tx["id"]}).status_code == 200
    aliases = client.get("/api/payments/merchant-aliases").json()
    assert len(aliases) == 1 and aliases[0]["merchant_key"] == "telstra corp melb au"
    assert client.delete(f"/api/payments/merchant-aliases/{aliases[0]['id']}").status_code == 200
    memory = client.get("/api/payments/category-memory").json()
    assert len(memory) == 1
    assert client.delete(f"/api/payments/category-memory/{memory[0]['id']}").status_code == 200
    assert next(row for row in client.get("/api/payments/transactions").json() if row["id"] == second["id"])["category_suggestion"] is None
    assert next(row for row in client.get("/api/payments/transactions").json() if row["id"] == tx["id"])["category_id"] == category_id


def test_failed_reconciliation_rolls_back_payment_and_transaction(client):
    account = setup(client)
    payment = recurring(client, account["id"])
    tx = outgoing(client, account["id"])
    with get_engine().begin() as connection:
        connection.execute(text("""
            CREATE TRIGGER fail_match_history BEFORE INSERT ON scheduled_payment_history
            WHEN NEW.source IN ('bank_match','csv_match')
            BEGIN SELECT RAISE(FAIL, 'simulated history persistence failure'); END
        """))
    with pytest.raises(DatabaseError):
        client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": tx["id"]})
    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT matched_transaction_id FROM scheduled_payments WHERE id=:id"), {"id": payment["id"]}).scalar() is None
        assert connection.execute(text("SELECT reconciliation_status FROM transactions WHERE id=:id"), {"id": tx["id"]}).scalar() != "matched"


def test_existing_bank_categories_migrate_without_changing_manual_categories(client):
    account = setup(client)
    bank = outgoing(client, account["id"], "Bank merchant")
    manual = outgoing(client, account["id"], "Manual expense")
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE transactions SET source='bank_sync',category='provider-label' WHERE id=:id"), {"id": bank["id"]})
        connection.execute(text("UPDATE transactions SET category='manual-label' WHERE id=:id"), {"id": manual["id"]})
    ensure_bank_activity_schema(get_engine())
    ensure_bank_activity_schema(get_engine())
    with get_engine().connect() as connection:
        rows = connection.execute(text("SELECT id,category,provider_category FROM transactions WHERE id IN (:bank,:manual)"), {"bank": bank["id"], "manual": manual["id"]}).mappings().all()
    by_id = {row["id"]: row for row in rows}
    assert by_id[bank["id"]]["category"] is None and by_id[bank["id"]]["provider_category"] == "provider-label"
    assert by_id[manual["id"]]["category"] == "manual-label" and by_id[manual["id"]]["provider_category"] is None
