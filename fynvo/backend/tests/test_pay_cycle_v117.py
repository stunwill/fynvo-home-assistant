from datetime import date, timedelta

from app.database import get_engine
from sqlalchemy import text


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def create_account(client, name="Everyday", balance="2000.00", account_type="transaction"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": account_type, "opening_balance": balance},
    )
    assert response.status_code == 201
    return response.json()


def create_income(client, name, amount, days, frequency="fortnightly", account_id=None):
    payload = {
        "name": name,
        "amount": amount,
        "frequency": frequency,
        "next_payment_date": (date.today() + timedelta(days=days)).isoformat(),
        "is_active": True,
    }
    if account_id is not None:
        payload["destination_account_id"] = account_id
    response = client.post("/api/income", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_recurring(client, name, amount, days, *, frequency="monthly", account_id=None, card_id=None, automatic=False):
    payload = {
        "name": name,
        "amount": amount,
        "frequency": frequency,
        "next_due_date": (date.today() + timedelta(days=days)).isoformat(),
        "payment_method": "automatic_card_payment" if card_id else "direct_debit" if automatic else "manual_payment",
        "payment_handling": "automatic" if automatic or card_id else "manual",
    }
    if account_id is not None:
        payload["account_id"] = account_id
    if card_id is not None:
        payload["card_id"] = card_id
    response = client.post("/api/recurring-expenses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_bill(client, name, amount, days, account_id=None, automatic=False, recurring_expense_id=None):
    payload = {
        "name": name,
        "amount": amount,
        "due_date": (date.today() + timedelta(days=days)).isoformat(),
        "payment_method": "direct_debit" if automatic else "bpay",
        "payment_handling": "automatic" if automatic else "manual",
    }
    if account_id is not None:
        payload["account_id"] = account_id
    if recurring_expense_id is not None:
        payload["recurring_expense_id"] = recurring_expense_id
    response = client.post("/api/bills", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def pay_cycle(client):
    response = client.get("/api/payment-planning/pay-cycle")
    assert response.status_code == 200, response.text
    return response.json()


def first_payment(client, recurring_id):
    response = client.get("/api/scheduled-payments")
    assert response.status_code == 200
    return next(row for row in response.json() if row["recurring_expense_id"] == recurring_id)


def test_weekly_fortnightly_monthly_and_multiple_income_select_next_event(client):
    setup_user(client)
    account = create_account(client)
    create_income(client, "Monthly Salary", "4000.00", 12, "monthly", account["id"])
    create_income(client, "Weekly Pay", "900.00", 3, "weekly", account["id"])
    create_income(client, "Fortnightly Pay", "1800.00", 5, "fortnightly", account["id"])

    data = pay_cycle(client)
    assert data["next_income"]["name"] == "Weekly Pay"
    assert data["next_income"]["days_until"] == 3
    assert [row["name"] for row in data["upcoming_income_events"]][:3] == ["Weekly Pay", "Fortnightly Pay", "Weekly Pay"]


def test_no_income_is_unknown_not_zero(client):
    setup_user(client)
    create_account(client)
    create_bill(client, "Electricity", "237.00", 7)
    data = pay_cycle(client)
    assert data["status"] == "unknown"
    assert data["next_income"] is None
    assert data["before_next_income"] is None
    assert data["completeness"]["next_income_known"] is False
    assert float(data["fallback_upcoming_commitments"]["next_30_days"]) >= 237


def test_income_today_excludes_same_day_commitments_from_before_pay(client):
    setup_user(client)
    account = create_account(client, balance="1000.00")
    create_income(client, "Salary", "2500.00", 0, "fortnightly", account["id"])
    create_bill(client, "Same-day bill", "300.00", 0, account["id"])

    data = pay_cycle(client)
    assert data["next_income"]["days_until"] == 0
    assert data["before_next_income"]["commitments_total"] == "0.00"
    assert data["before_next_income"]["projected_cash"] == "1000.00"
    assert data["after_next_income"]["projected_cash"] == "3500.00"
    assert data["planning_window"]["before_pay_excludes_next_income"] is True
    assert "Income is applied before commitments" in data["planning_window"]["same_day_ordering"]


def test_due_today_and_day_before_income_are_required(client):
    setup_user(client)
    account = create_account(client, balance="1000.00")
    create_income(client, "Salary", "2000.00", 3, account_id=account["id"])
    create_bill(client, "Today", "100.00", 0, account["id"])
    create_bill(client, "Day before", "250.00", 2, account["id"])
    data = pay_cycle(client)
    assert data["before_next_income"]["commitment_count"] == 2
    assert data["before_next_income"]["commitments_total"] == "350.00"
    assert data["before_next_income"]["projected_cash"] == "650.00"


def test_overdue_automatic_paid_skipped_and_reconciled_lifecycle(client):
    setup_user(client)
    account = create_account(client, balance="1500.00")
    create_income(client, "Salary", "2000.00", 8, account_id=account["id"])
    create_bill(client, "Overdue", "100.00", -2, account["id"])
    create_bill(client, "Automatic", "200.00", 2, account["id"], automatic=True)
    paid_rule = create_recurring(client, "Paid", "80.00", 3, account_id=account["id"])
    skipped_rule = create_recurring(client, "Skipped", "90.00", 4, account_id=account["id"])
    reconciled_rule = create_recurring(client, "Reconciled", "60.00", 5, account_id=account["id"])

    paid = first_payment(client, paid_rule["id"])
    skipped = first_payment(client, skipped_rule["id"])
    reconciled = first_payment(client, reconciled_rule["id"])
    assert client.post(f"/api/scheduled-payments/{paid['id']}/mark-paid", json={"paid_amount": "80.00"}).status_code == 200
    skipped_response = client.post(f"/api/scheduled-payments/{skipped['id']}/skip", json={"version": skipped["version"]})
    assert skipped_response.status_code == 200
    tx = client.post("/api/transactions", json={"account_id": account["id"], "date": reconciled["expected_date"], "amount": "60.00", "transaction_type": "expense", "description": "Reconciled"}).json()
    assert client.post(f"/api/scheduled-payments/{reconciled['id']}/match", json={"transaction_id": tx["id"], "confidence": "confirmed"}).status_code == 200

    data = pay_cycle(client)
    assert data["before_next_income"]["commitments_total"] == "300.00"
    assert data["before_next_income"]["overdue_total"] == "100.00"
    assert data["before_next_income"]["automatic_payment_total"] == "200.00"


def test_bill_recurring_duplicate_suppression_and_planned_spending(client):
    setup_user(client)
    account = create_account(client)
    create_income(client, "Salary", "2500.00", 10, account_id=account["id"])
    recurring = create_recurring(client, "Electricity estimate", "220.00", 5, account_id=account["id"])
    create_bill(client, "Electricity actual", "237.00", 5, account["id"], recurring_expense_id=recurring["id"])
    planned = client.post("/api/planned-spending", json={"name": "School shoes", "estimated_amount": "150.00", "planned_date": (date.today() + timedelta(days=6)).isoformat(), "account_id": account["id"], "status": "committed", "include_in_forecast": True})
    assert planned.status_code == 201, planned.text
    data = pay_cycle(client)
    assert data["before_next_income"]["commitments_total"] == "387.00"
    assert data["before_next_income"]["planned_spending_total"] == "150.00"


def test_account_card_unknown_archived_and_shortfalls(client):
    setup_user(client)
    bills = create_account(client, "Bills", "600.00")
    card_account = create_account(client, "Everyday", "500.00")
    unknown_type = create_account(client, "Mortgage", "9999.00", "mortgage")
    card = client.post("/api/cards", json={"account_id": card_account["id"], "name": "Debit", "card_type": "debit", "last_four": "1234"}).json()
    create_income(client, "Salary", "2500.00", 7, account_id=bills["id"])
    create_recurring(client, "Bills debit", "700.00", 2, account_id=bills["id"], automatic=True)
    create_recurring(client, "Card debit", "200.00", 3, card_id=card["id"])
    create_recurring(client, "Unknown", "50.00", 4)
    create_recurring(client, "Liability destination", "100.00", 5, account_id=unknown_type["id"])

    data = pay_cycle(client)
    by_name = {row["account_name"]: row for row in data["accounts"]}
    assert by_name["Bills"]["status"] == "shortfall"
    assert by_name["Bills"]["funding_shortfall"] == "100.00"
    assert by_name["Everyday"]["required_before_pay"] == "200.00"
    assert by_name["Everyday"]["status"] == "funded"
    assert by_name["Account not specified"]["status"] == "unknown"
    assert by_name["Mortgage"]["status"] == "unknown"
    assert data["unassigned"]["required"] == "50.00"
    assert data["status"] == "unknown"


def test_archived_account_is_not_future_funding(client):
    setup_user(client)
    account = create_account(client, "Old Everyday", "500.00")
    create_income(client, "Salary", "2000.00", 7)
    recurring = create_recurring(client, "Old debit", "100.00", 2, account_id=account["id"])
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE accounts SET is_active=0, archived_at=CURRENT_TIMESTAMP WHERE id=:id"), {"id": account["id"]})
    data = pay_cycle(client)
    row = next(item for item in data["accounts"] if item["account_id"] == account["id"])
    assert row["status"] == "unknown"
    assert row["current_balance"] is None
    assert row["archived"] is True
    assert recurring["id"]


def test_household_shortfall_and_no_invented_buffer(client):
    setup_user(client)
    account = create_account(client, balance="400.00")
    create_income(client, "Salary", "1000.00", 5, account_id=account["id"])
    create_bill(client, "Rates", "600.00", 2, account["id"])
    data = pay_cycle(client)
    assert data["status"] == "shortfall"
    assert data["before_next_income"]["funding_shortfall"] == "200.00"
    assert data["accounts"][0]["preferred_buffer"] is None
    assert data["completeness"]["buffer_supported"] is False


def test_true_fortnightly_month_end_and_effective_income_change(client):
    setup_user(client)
    account = create_account(client)
    monthly = create_income(client, "Month end", "3000.00", 0, "monthly", account["id"])
    fortnightly = create_income(client, "Fortnightly", "1500.00", 14, "fortnightly", account["id"])
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE income_sources SET next_payment_date='2026-01-31' WHERE id=:id"), {"id": monthly["id"]})
        connection.execute(text("UPDATE income_sources SET next_payment_date='2026-02-14' WHERE id=:id"), {"id": fortnightly["id"]})
        connection.execute(text("INSERT INTO effective_amount_changes(user_id,record_type,record_id,new_amount_cents,effective_from,source,created_at,updated_at) SELECT user_id,'income',id,175000,'2026-02-14','test',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM income_sources WHERE id=:id"), {"id": fortnightly["id"]})
    from app.database import SessionLocal
    from app.models import User
    from app.payment_planning import _income_events

    with SessionLocal() as db:
        user = db.query(User).first()
        events = _income_events(db, user, date(2026, 1, 31), date(2026, 3, 5))
    month_dates = [row["date"] for row in events if row["name"] == "Month end"]
    fortnight_dates = [row["date"] for row in events if row["name"] == "Fortnightly"]
    assert month_dates[:2] == ["2026-01-31", "2026-02-28"]
    assert fortnight_dates[:2] == ["2026-02-14", "2026-02-28"]
    assert next(row for row in events if row["name"] == "Fortnightly")["amount"] == "1750.00"


def test_multiple_commitments_same_day_and_cycles_do_not_repeat_overdue(client):
    setup_user(client)
    account = create_account(client, balance="2000.00")
    create_income(client, "Pay A", "1000.00", 5, "weekly", account["id"])
    create_bill(client, "Overdue", "100.00", -1, account["id"])
    create_bill(client, "One", "200.00", 2, account["id"])
    create_bill(client, "Two", "300.00", 2, account["id"])
    data = pay_cycle(client)
    assert data["before_next_income"]["commitments_total"] == "600.00"
    assert data["cycles"][0]["commitments_before"] == "600.00"
    assert data["cycles"][1]["commitments_before"] == "0.00"


def test_cross_screen_reconciliation_for_income_commitments_calendar_and_forecast(client):
    setup_user(client)
    account = create_account(client, balance="1000.00")
    create_income(client, "Salary", "2000.00", 5, account_id=account["id"])
    create_recurring(client, "Internet", "100.00", 2, account_id=account["id"])
    create_bill(client, "Water", "150.00", 3, account["id"])

    plan = pay_cycle(client)
    centre = client.get("/api/payment-centre?date_range=next_7_days").json()
    forecast = client.get("/api/forecast?mode=baseline&horizon=7d").json()
    dashboard = client.get("/api/dashboard/command-centre?range_days=7").json()

    centre_total = sum(float(row.get("expected_amount") or row.get("amount") or 0) for row in centre["rows"] if row["status"] not in {"paid", "skipped", "cancelled"})
    forecast_before_pay = [row for row in forecast["events"] if row["date"] < plan["next_income"]["date"] and row["direction"] == "expense"]
    assert f"{centre_total:.2f}" == plan["before_next_income"]["commitments_total"]
    assert f"{sum(abs(float(row['amount'])) for row in forecast_before_pay):.2f}" == plan["before_next_income"]["commitments_total"]
    income_event = next(row for row in forecast["events"] if row["direction"] == "income")
    assert income_event["date"] == plan["next_income"]["date"]
    calendar_signature = {(row["date"], row["name"], row["amount"]) for row in dashboard["calendar"]}
    forecast_signature = {(row["date"], row["name"], row["amount"]) for row in dashboard["forecast"]["baseline"]["events"]}
    assert calendar_signature == forecast_signature
    assert plan["before_next_income"]["projected_cash"] == "750.00"


def test_skipped_and_rescheduled_occurrences_reconcile_with_forecast(client):
    setup_user(client)
    account = create_account(client)
    create_income(client, "Salary", "2000.00", 10, account_id=account["id"])
    skipped_rule = create_recurring(client, "Skip me", "100.00", 2, account_id=account["id"])
    moved_rule = create_recurring(client, "Move me", "200.00", 3, account_id=account["id"])
    skipped = first_payment(client, skipped_rule["id"])
    moved = first_payment(client, moved_rule["id"])
    assert client.post(f"/api/scheduled-payments/{skipped['id']}/skip", json={"version": skipped["version"]}).status_code == 200
    moved_date = (date.today() + timedelta(days=7)).isoformat()
    assert client.post(f"/api/scheduled-payments/{moved['id']}/reschedule", json={"expected_date": moved_date, "version": moved["version"]}).status_code == 200

    plan = pay_cycle(client)
    forecast = client.get("/api/forecast?mode=baseline&horizon=14d").json()
    names = [(row["name"], row["date"]) for row in forecast["events"] if row["direction"] == "expense"]
    assert not any(name == "Skip me" for name, _ in names)
    assert ("Move me", moved_date) in names
    assert plan["before_next_income"]["commitments_total"] == "200.00"
