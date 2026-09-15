from datetime import date

import pytest
from app import finance
from app.database import get_engine
from sqlalchemy import text

TODAY = date(2026, 9, 15)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(finance, "today_local", lambda: TODAY)


def setup(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def account(client, name, balance="0.00", account_type="transaction"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": account_type, "opening_balance": balance},
    )
    assert response.status_code == 201, response.text
    return response.json()


def income(client, name="Salary", next_date="2026-09-20", account_id=None, frequency="fortnightly"):
    payload = {
        "name": name,
        "amount": "2000.00",
        "frequency": frequency,
        "next_payment_date": next_date,
        "is_active": True,
    }
    if account_id is not None:
        payload["destination_account_id"] = account_id
    response = client.post("/api/income", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def bill(client, name, amount, due, account_id=None, card_id=None):
    payload = {
        "name": name,
        "amount": amount,
        "due_date": due,
        "payment_method": "automatic_card_payment" if card_id else "bpay",
        "payment_handling": "automatic" if card_id else "manual",
    }
    if account_id is not None:
        payload["account_id"] = account_id
    if card_id is not None:
        payload["card_id"] = card_id
    response = client.post("/api/bills", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def funding(client):
    response = client.get("/api/payment-planning/account-funding")
    assert response.status_code == 200, response.text
    return response.json()


def test_current_cycle_funding_buffer_card_derivation_no_payments_and_unassigned(client):
    setup(client)
    bills = account(client, "Bills", "1000.00")
    card_account = account(client, "Card", "100.00")
    account(client, "Quiet", "50.00")
    card = client.post(
        "/api/cards",
        json={"account_id": card_account["id"], "name": "Debit", "card_type": "debit", "last_four": "4821"},
    ).json()
    income(client)
    bill(client, "Rates", "800.00", "2026-09-18", account_id=bills["id"])
    bill(client, "Card charge", "200.00", "2026-09-19", card_id=card["id"])
    bill(client, "Unassigned", "50.00", "2026-09-17")
    assert client.put(f"/api/accounts/{bills['id']}/preferred-buffer", json={"amount": "100.00"}).status_code == 200

    data = funding(client)["current_cycle"]
    rows = {row["account_name"]: row for row in data["accounts"]}
    assert rows["Bills"]["status"] == "covered"
    assert rows["Bills"]["target_balance"] == "900.00"
    assert rows["Bills"]["funding_surplus"] == "100.00"
    assert rows["Card"]["status"] == "add"
    assert rows["Card"]["funding_shortfall"] == "100.00"
    assert rows["Quiet"]["status"] == "no_payments_due"
    assert data["unassigned"]["required"] == "50.00"
    assert data["unassigned"]["commitments"][0]["name"] == "Unassigned"
    next_cycle = funding(client)["next_cycle"]
    assert next_cycle["status"] == "needs_setup"
    assert next_cycle["total_recommended_allocation"] is None
    assert all(row["projected_starting_balance"] is None for row in next_cycle["accounts"])


def test_payday_allocation_uses_projected_balance_and_crosses_month_boundary(client):
    setup(client)
    bills = account(client, "Bills", "1000.00")
    income(client)
    bill(client, "Before payday", "700.00", "2026-09-19", account_id=bills["id"])
    bill(client, "On payday", "500.00", "2026-09-20", account_id=bills["id"])
    bill(client, "Month end", "1000.00", "2026-09-30", account_id=bills["id"])

    allocation = funding(client)["next_cycle"]
    row = allocation["accounts"][0]
    assert allocation["cycle_start_date"] == "2026-09-20"
    assert allocation["cycle_end_date"] == "2026-10-04"
    assert row["projected_starting_balance"] == "300.00"
    assert row["commitment_total"] == "1500.00"
    assert row["recommended_transfer"] == "1200.00"
    assert allocation["total_recommended_allocation"] == "1200.00"
    assert allocation["reconciles"] is True
    assert sum(int(float(item["amount"]) * 100) for item in row["commitments"]) == 150000


def test_boundary_income_is_applied_before_same_day_commitments(client):
    setup(client)
    everyday = account(client, "Everyday", "100.00")
    income(client, account_id=everyday["id"])
    bill(client, "Payday debit", "250.00", "2026-09-20", account_id=everyday["id"])

    data = funding(client)
    assert data["current_cycle"]["accounts"][0]["commitment_total"] == "0.00"
    next_row = data["next_cycle"]["accounts"][0]
    assert next_row["projected_starting_balance"] == "2100.00"
    assert next_row["commitment_total"] == "250.00"
    assert next_row["status"] == "already_funded"


def test_monthly_requirement_remains_separate_from_pay_cycle(client):
    setup(client)
    everyday = account(client, "Everyday", "1000.00")
    income(client)
    bill(client, "September", "100.00", "2026-09-18", account_id=everyday["id"])
    bill(client, "October", "200.00", "2026-10-02", account_id=everyday["id"])
    row = funding(client)["current_cycle"]["accounts"][0]
    assert row["monthly_requirement"] == {
        "month": "2026-09-01",
        "scheduled_total": "100.00",
        "remaining_total": "100.00",
        "remaining_count": 1,
    }


def test_bulk_balance_update_is_atomic_exact_and_preserves_transactions(client):
    setup(client)
    first = account(client, "Bills", "1000.00")
    second = account(client, "Loan", "0.00", "mortgage")
    created = client.post(
        "/api/transactions",
        json={"account_id": first["id"], "date": "2026-09-14", "amount": "100.00", "transaction_type": "expense", "description": "Paid"},
    )
    assert created.status_code == 201

    response = client.patch(
        "/api/accounts/balances",
        json={"balances": [{"account_id": first["id"], "balance": "1312.45"}, {"account_id": second["id"], "balance": "-283910.32"}]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["updated_count"] == 2
    rows = {row["name"]: row for row in client.get("/api/accounts").json()}
    assert rows["Bills"]["current_balance"] == "1312.45"
    assert rows["Loan"]["current_balance"] == "-283910.32"
    assert rows["Bills"]["balance_update_source"] == "manual"
    assert rows["Bills"]["balance_updated_at"]
    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM transactions WHERE account_id=:id"), {"id": first["id"]}).scalar() == 1

    failed = client.patch(
        "/api/accounts/balances",
        json={"balances": [{"account_id": first["id"], "balance": "999.00"}, {"account_id": 999999, "balance": "1.00"}]},
    )
    assert failed.status_code == 404
    assert next(row for row in client.get("/api/accounts").json() if row["id"] == first["id"])["current_balance"] == "1312.45"


@pytest.mark.parametrize("value", ["", "not-money", "12.345", "1000000000000.00"])
def test_bulk_balance_validation_rejects_blank_invalid_precision_and_extremes(client, value):
    setup(client)
    everyday = account(client, "Everyday", "100.00")
    response = client.patch("/api/accounts/balances", json={"balances": [{"account_id": everyday["id"], "balance": value}]})
    assert response.status_code in {400, 422}
    assert client.get("/api/accounts").json()[0]["current_balance"] == "100.00"


def test_unchanged_balance_avoids_write_and_archived_account_fails_whole_batch(client):
    setup(client)
    first = account(client, "First", "100.00")
    old = account(client, "Old", "20.00")
    unchanged = client.patch("/api/accounts/balances", json={"balances": [{"account_id": first["id"], "balance": "100.00"}]})
    assert unchanged.status_code == 200
    assert unchanged.json()["status"] == "unchanged"
    assert unchanged.json()["updated_count"] == 0
    assert client.post(f"/api/accounts/{old['id']}/archive").status_code == 200
    failed = client.patch("/api/accounts/balances", json={"balances": [{"account_id": first["id"], "balance": "200.00"}, {"account_id": old["id"], "balance": "30.00"}]})
    assert failed.status_code == 409
    assert next(row for row in client.get("/api/accounts").json() if row["id"] == first["id"])["current_balance"] == "100.00"


def test_balance_update_immediately_recalculates_funding_and_safe_to_spend(client):
    setup(client)
    everyday = account(client, "Everyday", "100.00")
    income(client)
    bill(client, "Electricity", "200.00", "2026-09-18", account_id=everyday["id"])
    assert funding(client)["current_cycle"]["accounts"][0]["status"] == "add"
    assert client.get("/api/payment-planning/safe-to-spend").json()["safe_to_spend"] == "-100.00"
    assert client.patch("/api/accounts/balances", json={"balances": [{"account_id": everyday["id"], "balance": "500.00"}]}).status_code == 200
    assert funding(client)["current_cycle"]["accounts"][0]["status"] == "covered"
    assert client.get("/api/payment-planning/safe-to-spend").json()["safe_to_spend"] == "300.00"


def test_missing_income_exposes_setup_instead_of_zero(client):
    setup(client)
    account(client, "Everyday", "100.00")
    data = funding(client)
    assert data["current_cycle"]["status"] == "needs_setup"
    assert data["current_cycle"]["cycle_end_date"] is None
    assert data["next_cycle"]["total_recommended_allocation"] is None
    assert data["next_cycle"]["status"] == "needs_setup"


def test_no_liquid_accounts_never_reports_funding_as_covered(client):
    setup(client)
    account(client, "Mortgage", "-283910.32", "mortgage")
    income(client)
    data = funding(client)
    assert data["current_cycle"]["status"] == "needs_setup"
    assert data["current_cycle"]["accounts"] == []
