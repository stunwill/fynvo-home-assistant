from datetime import timedelta

from app.finance import today_local


def setup(client):
    response = client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})
    assert response.status_code == 201


def account(client, balance="1000.00"):
    response = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": balance})
    assert response.status_code == 201
    return response.json()


def income(client, account_id, days=5):
    response = client.post("/api/income", json={"name": "Salary", "amount": "2000.00", "frequency": "fortnightly", "next_payment_date": (today_local() + timedelta(days=days)).isoformat(), "destination_account_id": account_id, "is_active": True})
    assert response.status_code == 201


def bill(client, account_id, amount="200.00", days=2):
    response = client.post("/api/bills", json={"name": "Electricity", "amount": amount, "due_date": (today_local() + timedelta(days=days)).isoformat(), "payment_method": "bpay", "payment_handling": "manual", "account_id": account_id})
    assert response.status_code == 201


def test_safe_to_spend_exposes_explainable_breakdown_and_reserves_commitments(client):
    setup(client)
    everyday = account(client)
    income(client, everyday["id"])
    bill(client, everyday["id"])
    response = client.get("/api/payment-planning/safe-to-spend")
    assert response.status_code == 200
    data = response.json()
    assert data["available_cash"] == "1000.00"
    assert data["committed_outgoings"] == "200.00"
    assert data["safe_to_spend"] == "800.00"
    assert data["payment_readiness"] == "covered"
    assert data["reserved_payments"][0]["name"] == "Electricity"


def test_cash_buffer_persists_and_reduces_safe_to_spend_without_floating_point_drift(client):
    setup(client)
    everyday = account(client)
    income(client, everyday["id"])
    assert client.put("/api/payment-planning/cash-buffer", json={"amount": "125.55"}).status_code == 200
    data = client.get("/api/payment-planning/safe-to-spend").json()
    assert data["protected_buffer"] == "125.55"
    assert data["safe_to_spend"] == "874.45"


def test_safe_to_spend_keeps_negative_shortfall_and_rejects_negative_buffer(client):
    setup(client)
    everyday = account(client, "100.00")
    income(client, everyday["id"])
    bill(client, everyday["id"], "250.00")
    assert client.put("/api/payment-planning/cash-buffer", json={"amount": "50.00"}).status_code == 200
    data = client.get("/api/payment-planning/safe-to-spend").json()
    assert data["safe_to_spend"] == "-200.00"
    assert data["payment_readiness"] == "at_risk"
    assert client.put("/api/payment-planning/cash-buffer", json={"amount": "-1.00"}).status_code == 400


def test_payment_planning_remains_available_without_pay_cycle_or_safe_to_spend(client):
    setup(client)
    everyday = account(client)
    bill(client, everyday["id"])
    response = client.get("/api/payment-planning")
    assert response.status_code == 200
    data = response.json()
    assert data["periods"]["next_30_days"]["remaining_funding"] == "200.00"
    assert data["pay_cycle"]["next_income"] is None
    assert data["pay_cycle"]["completeness"]["complete"] is False
    assert data["pay_cycle_error"] is None


def test_payment_centre_core_list_does_not_depend_on_pay_cycle_configuration(client):
    setup(client)
    everyday = account(client)
    bill(client, everyday["id"], "250.00")
    response = client.get("/api/payment-centre?date_range=next_30_days")
    assert response.status_code == 200
    assert response.json()["rows"][0]["name"] == "Electricity"
