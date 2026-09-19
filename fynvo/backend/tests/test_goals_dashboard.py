from app.database import get_engine
from app.money import parse_money
from sqlalchemy import text


def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_goal_creation_edit_progress_and_true_fortnightly_required_contribution(client):
    setup_user(client)
    response = client.post("/api/goals", json={
        "name": "Japan Holiday",
        "goal_type": "savings",
        "target_amount": "8000.00",
        "current_amount": "2400.00",
        "start_date": "2026-08-17",
        "target_date": "2027-10-01",
        "priority": "high",
        "contribution_frequency": "fortnightly",
        "contribution_amount": "350.00",
    })
    assert response.status_code == 201
    goal = response.json()
    assert goal["name"] == "Japan Holiday"
    assert goal["progress"]["percentage"] == 30.0
    assert goal["progress"]["remaining"] == "5600.00"
    assert goal["progress"]["contribution_frequency"] == "fortnightly"
    assert parse_money(goal["progress"]["required_contribution"]) > 0
    assert "fortnightly" in goal["progress"]["explanation"]

    updated = client.put(f"/api/goals/{goal['id']}", json={**goal, "name": "Japan Trip", "contribution_amount": "400.00", "status": "active"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Japan Trip"
    assert updated.json()["contribution_amount"] == "400.00"

    with get_engine().begin() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 15


def test_goal_allocations_prevent_double_counting_and_unallocated_savings(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "10000.00"}).json()
    japan = client.post("/api/goals", json={"name": "Japan", "target_amount": "8000.00", "current_amount": "0.00", "target_date": "2027-10-01"}).json()
    car = client.post("/api/goals", json={"name": "Car", "target_amount": "5000.00", "current_amount": "0.00", "target_date": "2027-06-01"}).json()

    assert client.post(f"/api/goals/{japan['id']}/allocations", json={"account_id": account["id"], "amount": "3000.00"}).status_code == 201
    assert client.post(f"/api/goals/{car['id']}/allocations", json={"account_id": account["id"], "amount": "2000.00"}).status_code == 201
    rows = client.get("/api/goals/allocations/unallocated").json()
    assert rows[0]["allocated"] == "5000.00"
    assert rows[0]["unallocated"] == "5000.00"


def test_goal_contribution_completion_what_if_and_dashboard_summary(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "5000.00"}).json()
    client.post("/api/income", json={"name": "Salary", "amount": "2100.00", "frequency": "fortnightly", "next_payment_date": "2026-08-20", "destination_account_id": account["id"]})
    client.post("/api/recurring-expenses", json={"name": "Internet", "amount": "80.00", "frequency": "monthly", "next_due_date": "2026-08-24", "account_id": account["id"]})
    client.post("/api/planned-spending", json={"name": "New BBQ", "estimated_amount": "1200.00", "planned_date": "2026-09-20", "status": "planned", "include_in_forecast": True})
    goal = client.post("/api/goals", json={"name": "Emergency Fund", "goal_type": "target_balance", "target_amount": "15000.00", "current_amount": "6500.00", "target_date": "2027-12-01", "contribution_amount": "300.00"}).json()

    detail = client.post(f"/api/goals/{goal['id']}/contributions", json={"date": "2026-08-17", "amount": "250.00"})
    assert detail.status_code == 201
    assert detail.json()["progress"]["contributions"] == "250.00"

    what_if = client.post("/api/goals/what-if", json={"goal_id": goal["id"], "contribution_amount": "450.00", "frequency": "monthly"})
    assert what_if.status_code == 200
    assert what_if.json()["explanation"].startswith("This is a what-if")

    dashboard = client.get("/api/dashboard/command-centre?range_days=90")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert "kpis" in payload
    assert payload["goals"][0]["name"] == "Emergency Fund"
    assert payload["top_planned_spending"][0]["name"] == "New BBQ"

    complete = client.post(f"/api/goals/{goal['id']}/complete")
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
