from datetime import timedelta

from app.database import get_engine
from app.finance import today_local
from sqlalchemy import text


def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_legacy_mock_provider_routes_are_retired(client):
    setup_user(client)
    providers = client.get("/api/bank-connections/providers")
    assert providers.status_code == 200
    assert providers.json()["providers"][0]["id"] == "redbark"

    legacy = client.post("/api/bank-connections/mock/connect", json={"institution_id": "mock-bank-au"})
    assert legacy.status_code == 404

def test_dashboard_upcoming_commitments_and_overdue_are_separate(client):
    setup_user(client)
    current_day = today_local()
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "5000.00"}).json()
    client.post("/api/income", json={"name": "Salary", "amount": "2100.00", "frequency": "one_off", "next_payment_date": (current_day + timedelta(days=1)).isoformat(), "destination_account_id": account["id"]})
    client.post("/api/bills", json={"name": "Old Bill", "amount": "120.00", "due_date": (current_day - timedelta(days=1)).isoformat(), "account_id": account["id"]})
    client.post("/api/bills", json={"name": "Internet", "amount": "140.00", "due_date": (current_day + timedelta(days=4)).isoformat(), "account_id": account["id"]})
    dashboard = client.get("/api/dashboard/command-centre?range_days=90")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    upcoming_names = {item["name"] for item in payload["upcoming"]}
    commitment_names = {item["name"] for item in payload["upcoming_commitments"]}
    assert "Salary" in upcoming_names
    assert "Internet" in upcoming_names
    assert "Internet" in commitment_names
    assert "Salary" not in commitment_names
    assert "Old Bill" not in upcoming_names
    assert payload["overdue"]["count"] >= 1
    assert any(item["amount"].startswith("-") for item in payload["upcoming"] if item["name"] == "Internet")
    assert any(not item["amount"].startswith("-") for item in payload["upcoming"] if item["name"] == "Salary")
