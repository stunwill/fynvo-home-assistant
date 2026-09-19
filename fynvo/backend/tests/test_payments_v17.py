from datetime import date, timedelta

from app.database import get_engine
from app.payments_v17 import (
    _status_for,
    default_payment_handling,
    ensure_payment_schema,
)
from sqlalchemy import text


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def create_account(client, name="Kristy ING"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": "transaction", "opening_balance": "2000.00", "institution": "ING"},
    )
    assert response.status_code == 201
    return response.json()


def create_card(client, account_id):
    response = client.post(
        "/api/cards",
        json={"account_id": account_id, "name": "Kristy ING Card", "card_type": "debit", "last_four": "1234"},
    )
    assert response.status_code == 201
    return response.json()


def test_payment_handling_defaults_and_grace_status_rules():
    assert default_payment_handling("direct_debit") == "automatic"
    assert default_payment_handling("automatic_card_payment") == "automatic"
    assert default_payment_handling("bpay") == "manual"
    today = date(2026, 8, 22)
    assert _status_for(today, "manual", 3, today) == "due"
    assert _status_for(today - timedelta(days=1), "manual", 3, today) == "overdue"
    assert _status_for(today, "automatic", 3, today) == "expected_automatically"
    assert _status_for(today - timedelta(days=3), "automatic", 3, today) == "expected_automatically"
    assert _status_for(today - timedelta(days=4), "automatic", 3, today) == "auto_payment_unconfirmed"


def test_card_payment_derives_account_and_generates_scheduled_payments(client):
    setup_user(client)
    account = create_account(client)
    card = create_card(client, account["id"])
    response = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Netflix",
            "amount": "20.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-17",
            "payment_method": "automatic_card_payment",
            "payment_handling": "automatic",
            "card_id": card["id"],
            "payee_merchant": "Netflix",
            "auto_payment_grace_days": 3,
        },
    )
    assert response.status_code == 201
    row = response.json()
    assert row["card_id"] == card["id"]
    assert row["derived_account_id"] == account["id"]
    assert row["derived_account_name"] == "Kristy ING"
    assert row["payment_handling"] == "automatic"
    assert row["auto_payment_grace_days"] == 3

    scheduled = client.get("/api/scheduled-payments")
    assert scheduled.status_code == 200
    netflix = [item for item in scheduled.json() if item["recurring_expense_id"] == row["id"]]
    assert len(netflix) >= 3
    assert netflix[0]["card_id"] == card["id"]
    assert netflix[0]["account_id"] == account["id"]
    assert netflix[0]["payment_method"] == "automatic_card_payment"


def test_direct_debit_and_manual_payment_sources(client):
    setup_user(client)
    account = create_account(client)
    direct = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Insurance",
            "amount": "116.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-21",
            "payment_method": "direct_debit",
            "account_id": account["id"],
        },
    )
    assert direct.status_code == 201
    assert direct.json()["payment_handling"] == "automatic"
    assert direct.json()["account_id"] == account["id"]
    assert direct.json()["card_id"] is None

    manual = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Council Rates",
            "amount": "450.00",
            "frequency": "quarterly",
            "next_due_date": "2026-09-24",
            "payment_method": "bpay",
        },
    )
    assert manual.status_code == 201
    assert manual.json()["payment_handling"] == "manual"
    assert manual.json()["account_id"] is None
    assert manual.json()["card_id"] is None


def test_mark_paid_preserves_expected_amount_and_skip_is_distinct(client):
    setup_user(client)
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Electricity",
            "amount": "250.00",
            "frequency": "monthly",
            "next_due_date": "2026-08-20",
            "payment_method": "bpay",
            "amount_type": "variable_estimated",
        },
    ).json()
    scheduled = client.get("/api/scheduled-payments").json()
    payment = next(item for item in scheduled if item["recurring_expense_id"] == recurring["id"])
    marked = client.post(
        f"/api/scheduled-payments/{payment['id']}/mark-paid",
        json={"paid_date": "2026-08-22", "paid_amount": "263.42", "note": "Paid via BPAY"},
    )
    assert marked.status_code == 200
    refreshed = next(item for item in client.get("/api/scheduled-payments").json() if item["id"] == payment["id"])
    assert refreshed["status"] == "paid"
    assert refreshed["expected_amount"] == "250.00"
    assert refreshed["actual_amount"] == "263.42"
    assert refreshed["actual_date"] == "2026-08-22"

    gym = client.post(
        "/api/recurring-expenses",
        json={"name": "Gym", "amount": "59.00", "frequency": "monthly", "next_due_date": "2026-09-05", "payment_method": "manual_payment"},
    ).json()
    gym_payment = next(item for item in client.get("/api/scheduled-payments").json() if item["recurring_expense_id"] == gym["id"])
    skipped = client.post(f"/api/scheduled-payments/{gym_payment['id']}/skip", json={"note": "Membership paused"})
    assert skipped.status_code == 200
    skipped_row = next(item for item in client.get("/api/scheduled-payments").json() if item["id"] == gym_payment["id"])
    assert skipped_row["status"] == "skipped"
    assert skipped_row["actual_amount"] is None


def test_transaction_match_is_one_to_one_and_preserves_variance(client):
    setup_user(client)
    account = create_account(client)
    recurring = client.post(
        "/api/recurring-expenses",
        json={"name": "Electricity", "amount": "250.00", "frequency": "monthly", "next_due_date": "2026-08-20", "payment_method": "direct_debit", "account_id": account["id"], "payee_merchant": "AGL"},
    ).json()
    transaction = client.post(
        "/api/transactions",
        json={"account_id": account["id"], "date": "2026-08-20", "amount": "263.42", "transaction_type": "expense", "description": "AGL Electricity", "merchant": "AGL"},
    )
    assert transaction.status_code == 201
    tx = transaction.json()
    payment = next(item for item in client.get("/api/scheduled-payments").json() if item["recurring_expense_id"] == recurring["id"])
    matched = client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": tx["id"], "confidence": "high"})
    assert matched.status_code == 200
    refreshed = next(item for item in client.get("/api/scheduled-payments").json() if item["id"] == payment["id"])
    assert refreshed["expected_amount"] == "250.00"
    assert refreshed["actual_amount"] == "263.42"
    assert refreshed["matched_transaction_id"] == tx["id"]

    second = client.post(
        "/api/recurring-expenses",
        json={"name": "Other AGL", "amount": "263.42", "frequency": "monthly", "next_due_date": "2026-08-20", "payment_method": "bpay"},
    ).json()
    second_payment = next(item for item in client.get("/api/scheduled-payments").json() if item["recurring_expense_id"] == second["id"])
    duplicate = client.post(f"/api/scheduled-payments/{second_payment['id']}/match", json={"transaction_id": tx["id"], "confidence": "high"})
    assert duplicate.status_code == 409


def test_rejected_and_ignored_candidates_are_not_suggested_again(client):
    setup_user(client)
    account = create_account(client)
    recurring = client.post(
        "/api/recurring-expenses",
        json={"name": "Insurance", "amount": "116.00", "frequency": "monthly", "next_due_date": "2026-08-21", "payment_method": "direct_debit", "account_id": account["id"], "payee_merchant": "Budget Direct"},
    ).json()
    first_tx = client.post(
        "/api/transactions",
        json={"account_id": account["id"], "date": "2026-08-21", "amount": "116.00", "transaction_type": "expense", "description": "BUDGET DIRECT", "merchant": "Budget Direct"},
    ).json()
    payment = next(item for item in client.get("/api/scheduled-payments").json() if item["recurring_expense_id"] == recurring["id"])
    candidates = client.get("/api/payments/match-candidates").json()
    assert any(item["transaction_id"] == first_tx["id"] and item["scheduled_payment_id"] == payment["id"] for item in candidates)
    rejected = client.post(f"/api/scheduled-payments/{payment['id']}/reject-match", json={"transaction_id": first_tx["id"]})
    assert rejected.status_code == 200
    after_reject = client.get("/api/payments/match-candidates").json()
    assert not any(item["transaction_id"] == first_tx["id"] and item["scheduled_payment_id"] == payment["id"] for item in after_reject)

    second_tx = client.post(
        "/api/transactions",
        json={"account_id": account["id"], "date": "2026-08-22", "amount": "116.00", "transaction_type": "expense", "description": "BUDGET DIRECT", "merchant": "Budget Direct"},
    ).json()
    ignored = client.post(f"/api/payments/transactions/{second_tx['id']}/ignore")
    assert ignored.status_code == 200
    after_ignore = client.get("/api/payments/match-candidates").json()
    assert not any(item["transaction_id"] == second_tx["id"] for item in after_ignore)


def test_confirmed_mapping_is_remembered(client):
    setup_user(client)
    account = create_account(client)
    recurring = client.post(
        "/api/recurring-expenses",
        json={"name": "Netflix", "amount": "20.00", "frequency": "monthly", "next_due_date": "2026-08-20", "payment_method": "direct_debit", "account_id": account["id"], "payee_merchant": "Netflix"},
    ).json()
    tx = client.post(
        "/api/transactions",
        json={"account_id": account["id"], "date": "2026-08-20", "amount": "20.00", "transaction_type": "expense", "description": "NETFLIX.COM", "merchant": "Netflix"},
    ).json()
    payment = next(item for item in client.get("/api/scheduled-payments").json() if item["recurring_expense_id"] == recurring["id"])
    assert client.post(f"/api/scheduled-payments/{payment['id']}/match", json={"transaction_id": tx["id"], "confidence": "high"}).status_code == 200
    with get_engine().connect() as connection:
        count = connection.execute(text("SELECT confirmed_count FROM recurring_match_mappings WHERE recurring_expense_id=:rid"), {"rid": recurring["id"]}).scalar()
    assert count == 1


def test_payment_migration_is_idempotent_and_preserves_cards(client):
    setup_user(client)
    account = create_account(client)
    card = create_card(client, account["id"])
    engine = get_engine()
    ensure_payment_schema(engine)
    ensure_payment_schema(engine)
    with engine.connect() as connection:
        card_count = connection.execute(text("SELECT COUNT(*) FROM cards WHERE id=:id"), {"id": card["id"]}).scalar()
        schema_version = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(recurring_expenses)")).all()}
    assert card_count == 1
    assert int(schema_version) == 15
    assert "payment_handling" in columns
    assert "auto_payment_grace_days" in columns
