from app.config import APP_VERSION
from app.database import get_engine, run_migrations
from app.money import parse_money
from sqlalchemy import text


def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_account_creation_regression_kristy_main_account(client):
    setup_user(client)
    payload = {
        "name": "Kristy - Main AC",
        "opening_balance": "2000.00",
        "account_type": "transaction",
        "institution": "ING",
        "description": "Kristy's main account",
    }
    created = client.post("/api/accounts", json=payload)
    assert created.status_code == 201
    account = created.json()
    assert isinstance(account["id"], int)
    assert account["name"] == "Kristy - Main AC"
    assert account["current_balance"] == "2000.00"
    assert account["account_class"] == "asset"
    accounts = client.get("/api/accounts").json()
    assert [row["name"] for row in accounts] == ["Kristy - Main AC"]

    updated = client.put(
        f"/api/accounts/{account['id']}",
        json={"description": "Kristy's primary ING account"},
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == account["id"]
    assert updated.json()["description"] == "Kristy's primary ING account"
    assert len(client.get("/api/accounts").json()) == 1


def test_accounts_transactions_balances_and_running_balance(client):
    assert client.get("/api/accounts").status_code == 401
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    assert account["current_balance"] == "1000.00"
    income = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "2850.00", "transaction_type": "income", "description": "Salary"}).json()
    assert income["amount"] == "2850.00"
    expense = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-18", "amount": "142.36", "transaction_type": "expense", "description": "Woolworths"}).json()
    assert expense["amount"] == "-142.36"
    detail = client.get(f"/api/accounts/{account['id']}").json()
    assert detail["account"]["current_balance"] == "3707.64"
    assert detail["transactions"][-1]["running_balance"] == "3707.64"


def test_account_balance_regression_from_two_thousand(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Kristy - Main AC", "account_type": "transaction", "opening_balance": "2000.00"}).json()
    client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-19", "amount": "500.25", "transaction_type": "income", "description": "Credit"})
    client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-19", "amount": "125.10", "transaction_type": "expense", "description": "Debit"})
    assert client.get(f"/api/accounts/{account['id']}").json()["account"]["current_balance"] == "2375.15"


def test_historical_insert_and_edit_recalculate_balance(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "100.00"}).json()
    client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-20", "amount": "50.00", "transaction_type": "expense", "description": "Later"})
    tx = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "20.00", "transaction_type": "income", "description": "Earlier"}).json()
    assert client.get(f"/api/accounts/{account['id']}").json()["account"]["current_balance"] == "70.00"
    client.put(f"/api/transactions/{tx['id']}", json={"amount": "40.00"})
    assert client.get(f"/api/accounts/{account['id']}").json()["account"]["current_balance"] == "90.00"


def test_transfers_update_both_accounts_without_income_or_expense(client):
    setup_user(client)
    everyday = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    savings = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "100.00"}).json()
    transfer = client.post("/api/transfers", json={"from_account_id": everyday["id"], "to_account_id": savings["id"], "date": "2026-08-17", "amount": "500.00", "description": "Move to savings"}).json()
    assert client.get(f"/api/accounts/{everyday['id']}").json()["account"]["current_balance"] == "500.00"
    assert client.get(f"/api/accounts/{savings['id']}").json()["account"]["current_balance"] == "600.00"
    client.put(f"/api/transfers/{transfer['id']}", json={"amount": "200.00"})
    assert client.get(f"/api/accounts/{everyday['id']}").json()["account"]["current_balance"] == "800.00"
    assert client.get(f"/api/accounts/{savings['id']}").json()["account"]["current_balance"] == "300.00"
    txs = client.get("/api/transactions").json()
    assert {tx["transaction_type"] for tx in txs} == {"transfer"}
    client.delete(f"/api/transfers/{transfer['id']}")
    assert client.get(f"/api/accounts/{everyday['id']}").json()["account"]["current_balance"] == "1000.00"


def test_transfer_to_liability_reduces_amount_owing(client):
    setup_user(client)
    everyday = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    card = client.post("/api/accounts", json={"name": "Credit Card", "account_type": "credit_card", "opening_balance": "500.00"}).json()
    response = client.post("/api/transfers", json={"from_account_id": everyday["id"], "to_account_id": card["id"], "date": "2026-08-19", "amount": "200.00", "description": "Card payment"})
    assert response.status_code == 201
    assert client.get(f"/api/accounts/{everyday['id']}").json()["account"]["current_balance"] == "800.00"
    assert client.get(f"/api/accounts/{card['id']}").json()["account"]["current_balance"] == "300.00"


def test_available_cash_excludes_non_liquid_assets_and_liabilities(client):
    setup_user(client)
    client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"})
    client.post("/api/accounts", json={"name": "Offset", "account_type": "offset", "opening_balance": "2000.00"})
    client.post("/api/accounts", json={"name": "Shares", "account_type": "investment", "opening_balance": "5000.00"})
    client.post("/api/accounts", json={"name": "Super", "account_type": "superannuation", "opening_balance": "10000.00"})
    client.post("/api/accounts", json={"name": "Mortgage", "account_type": "mortgage", "opening_balance": "300000.00"})
    position = client.get("/api/dashboard/overview").json()["summary"]
    assert position["available_cash"] == "3000.00"
    assert position["assets"] == "18000.00"
    assert position["liabilities"] == "300000.00"


def test_archive_account_and_decimal_precision(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Cash", "account_type": "cash", "opening_balance": "0.10"}).json()
    client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "0.20", "transaction_type": "income", "description": "Coins"})
    assert parse_money("0.10") + parse_money("0.20") == 30
    assert client.get(f"/api/accounts/{account['id']}").json()["account"]["current_balance"] == "0.30"
    client.post(f"/api/accounts/{account['id']}/archive")
    assert client.get("/api/accounts").json() == []
    assert client.get("/api/accounts?include_archived=true").json()[0]["id"] == account["id"]


def test_archived_account_cannot_receive_new_transaction(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Old account", "account_type": "transaction", "opening_balance": "10.00"}).json()
    client.post(f"/api/accounts/{account['id']}/archive")
    response = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-19", "amount": "1.00", "transaction_type": "expense", "description": "Should fail"})
    assert response.status_code == 409


def test_liability_account_semantics(client):
    setup_user(client)
    card = client.post("/api/accounts", json={"name": "Credit Card", "account_type": "credit_card", "opening_balance": "0.00"}).json()
    assert card["account_class"] == "liability"
    client.post("/api/transactions", json={"account_id": card["id"], "date": "2026-08-17", "amount": "100.00", "transaction_type": "expense", "description": "Purchase"})
    assert client.get(f"/api/accounts/{card['id']}").json()["account"]["current_balance"] == "100.00"


def test_account_meta_exposes_pre_v1_supported_types(client):
    setup_user(client)
    types = set(client.get("/api/accounts/meta").json()["account_types"])
    assert {"transaction", "savings", "offset", "credit_card", "cash", "mortgage", "personal_loan", "car_loan", "line_of_credit", "investment", "superannuation", "other_asset", "other_liability"}.issubset(types)


def test_migration_schema_version_thirteen(client):
    run_migrations()
    with get_engine().begin() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 15


def test_home_assistant_spa_routes_and_api_protection(client):
    assert client.get("/api/health").json()["version"] == APP_VERSION
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/accounts").status_code == 200
    assert client.get("/api/accounts").status_code == 401
