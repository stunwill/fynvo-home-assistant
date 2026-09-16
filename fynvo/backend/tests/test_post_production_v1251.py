from datetime import date

import pytest
from app import finance, payment_planning
from app.planning_resilience import PlanningStageError

TODAY = date(2026, 9, 16)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(finance, "today_local", lambda: TODAY)
    monkeypatch.setattr(payment_planning, "today_local", lambda: TODAY)


def setup(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def account(client, name="Everyday", balance="1000.00"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": "transaction", "opening_balance": balance},
    )
    assert response.status_code == 201
    return response.json()


def income(client, next_date="2026-09-20"):
    response = client.post(
        "/api/income",
        json={
            "name": "Salary",
            "amount": "2000.00",
            "frequency": "fortnightly",
            "next_payment_date": next_date,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def bill(client, name, amount, due, account_id=None):
    payload = {
        "name": name,
        "amount": amount,
        "due_date": due,
        "payment_method": "bpay",
        "payment_handling": "manual",
    }
    if account_id is not None:
        payload["account_id"] = account_id
    response = client.post("/api/bills", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_missing_income_labels_known_commitments_with_generated_horizon(client):
    setup(client)
    everyday = account(client)
    bill(client, "Electricity", "200.00", "2026-09-18", everyday["id"])
    response = client.get("/api/payment-planning/safe-to-spend")
    assert response.status_code == 200
    data = response.json()
    assert data["safe_to_spend"] is None
    assert data["unavailable_reason"]["code"] == "missing_next_income"
    assert data["commitment_scope"]["code"] == "generated_horizon"
    assert data["commitment_scope"]["complete"] is False
    assert data["commitment_scope"]["end_date"] == "2027-01-14"
    assert data["committed_outgoings"] == "0.00"
    assert data["known_commitments"] == "200.00"


def test_complete_safe_to_spend_labels_commitments_before_next_pay(client):
    setup(client)
    everyday = account(client)
    income(client)
    bill(client, "Electricity", "200.00", "2026-09-18", everyday["id"])
    response = client.get("/api/payment-planning/safe-to-spend")
    assert response.status_code == 200
    data = response.json()
    assert data["commitment_scope"]["code"] == "before_next_pay"
    assert data["commitment_scope"]["complete"] is True
    assert data["commitment_scope"]["end_date"] == "2026-09-20"
    assert data["committed_outgoings"] == "200.00"
    assert data["known_commitments"] == "200.00"
    assert data["safe_to_spend"] == "800.00"


def test_structured_income_failure_survives_safe_to_spend(monkeypatch, client):
    setup(client)
    account(client)

    def broken(*args, **kwargs):
        raise PlanningStageError(
            {
                "code": "income_schedule_unavailable",
                "message": "Your income schedule could not be read. Review Income or retry the plan.",
                "action": "income",
                "stage": "income",
            }
        )

    monkeypatch.setattr(payment_planning, "build_pay_cycle_planning", broken)
    response = client.get("/api/payment-planning/safe-to-spend")
    assert response.status_code == 200
    reason = response.json()["unavailable_reason"]
    assert reason["code"] == "income_schedule_unavailable"
    assert reason["action"] == "income"
    assert response.json()["planning_status"] == "unavailable"


def test_v1251_account_funding_returns_useful_unavailable_accounts(monkeypatch, client):
    setup(client)
    everyday = account(client, balance="2671.00")

    def broken(*args, **kwargs):
        raise PlanningStageError(
            {
                "code": "income_schedule_unavailable",
                "message": "Your income schedule could not be read. Review Income or retry the plan.",
                "action": "income",
                "stage": "income",
            }
        )

    monkeypatch.setattr(payment_planning, "build_pay_cycle_planning", broken)
    response = client.get("/api/payment-planning/account-funding/v1251")
    assert response.status_code == 200
    data = response.json()
    assert data["current_cycle"]["status"] == "unavailable"
    assert data["current_cycle"]["accounts"][0]["account_id"] == everyday["id"]
    assert data["current_cycle"]["accounts"][0]["current_balance"] == "2671.00"
    assert data["current_cycle"]["accounts"][0]["status"] == "unavailable"
    assert data["next_cycle"]["total_recommended_allocation"] is None
    assert data["next_cycle"]["reason"]["action"] == "income"


def test_unassigned_current_payment_keeps_payday_allocation_explicitly_incomplete(client):
    setup(client)
    account(client)
    income(client)
    bill(client, "Unassigned", "50.00", "2026-09-18")
    response = client.get("/api/payment-planning/account-funding/v1251")
    assert response.status_code == 200
    allocation = response.json()["next_cycle"]
    assert allocation["status"] == "needs_setup"
    assert allocation["planning_status"] == "unknown"
    assert allocation["total_recommended_allocation"] is None
    assert "Assign every current-cycle payment" in allocation["message"]
