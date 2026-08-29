from datetime import date, timedelta

from app.database import get_engine
from sqlalchemy import text


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def create_account(client, name="Shared ING", balance="5000.00"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": "transaction", "opening_balance": balance, "institution": "ING"},
    )
    assert response.status_code == 201
    return response.json()


def create_card(client, account_id):
    response = client.post(
        "/api/cards",
        json={"account_id": account_id, "name": "Shared ING Card", "card_type": "debit", "last_four": "6100"},
    )
    assert response.status_code == 201
    return response.json()


def create_recurring(client, name, amount, days, *, account_id=None, card_id=None, automatic=False):
    method = "automatic_card_payment" if card_id else "direct_debit" if automatic else "manual_payment"
    payload = {
        "name": name,
        "amount": amount,
        "frequency": "monthly",
        "next_due_date": (date.today() + timedelta(days=days)).isoformat(),
        "payment_method": method,
        "payment_handling": "automatic" if automatic or card_id else "manual",
        "payee_merchant": name,
    }
    if account_id is not None:
        payload["account_id"] = account_id
    if card_id is not None:
        payload["card_id"] = card_id
    response = client.post("/api/recurring-expenses", json=payload)
    assert response.status_code == 201
    return response.json()


def planning(client):
    response = client.get("/api/payment-planning")
    assert response.status_code == 200
    return response.json()


def first_payment(client, recurring_id):
    response = client.get("/api/scheduled-payments")
    assert response.status_code == 200
    return next(row for row in response.json() if row["recurring_expense_id"] == recurring_id)


def test_money_needed_periods_and_automatic_funding(client):
    setup_user(client)
    account = create_account(client)
    create_recurring(client, "Manual 7", "100.00", 5, account_id=account["id"])
    create_recurring(client, "Direct Debit 14", "200.00", 10, account_id=account["id"], automatic=True)
    create_recurring(client, "Manual 30", "300.00", 20, account_id=account["id"])

    data = planning(client)
    assert data["money_needed_soon"]["next_7_days"] == "100.00"
    assert data["money_needed_soon"]["next_14_days"] == "300.00"
    assert data["money_needed_soon"]["next_30_days"] == "600.00"
    assert data["periods"]["next_14_days"]["automatic_amount"] == "200.00"
    assert data["rules"]["automatic_payments_require_funding"] is True


def test_paid_skipped_and_cancelled_are_excluded_and_restore_returns(client):
    setup_user(client)
    account = create_account(client)
    paid_rule = create_recurring(client, "Paid", "80.00", 2, account_id=account["id"])
    skipped_rule = create_recurring(client, "Skipped", "90.00", 3, account_id=account["id"])
    bill = client.post(
        "/api/bills",
        json={
            "name": "Cancelled Bill", "amount": "70.00",
            "due_date": (date.today() + timedelta(days=4)).isoformat(),
            "payment_method": "bpay", "payment_handling": "manual", "account_id": account["id"],
        },
    ).json()
    paid = first_payment(client, paid_rule["id"])
    skipped = first_payment(client, skipped_rule["id"])
    assert client.post(f"/api/scheduled-payments/{paid['id']}/mark-paid", json={"paid_amount": "80.00"}).status_code == 200
    skipped_response = client.post(
        f"/api/scheduled-payments/{skipped['id']}/skip", json={"version": skipped["version"]}
    )
    assert skipped_response.status_code == 200
    assert client.post(f"/api/bills/{bill['id']}/cancel", json={}).status_code == 200
    assert planning(client)["money_needed_soon"]["next_7_days"] == "0.00"

    restored = client.post(
        f"/api/scheduled-payments/{skipped['id']}/restore",
        json={"version": skipped_response.json()["version"]},
    )
    assert restored.status_code == 200
    assert planning(client)["money_needed_soon"]["next_7_days"] == "90.00"


def test_reschedule_moves_payment_between_periods_without_changing_identity(client):
    setup_user(client)
    account = create_account(client)
    recurring = create_recurring(client, "Move Me", "125.00", 5, account_id=account["id"])
    payment = first_payment(client, recurring["id"])
    original_id = payment["id"]
    original_occurrence = str(payment["occurrence_date"])[:10]
    assert planning(client)["money_needed_soon"]["next_7_days"] == "125.00"

    moved = client.post(
        f"/api/scheduled-payments/{payment['id']}/reschedule",
        json={"expected_date": (date.today() + timedelta(days=18)).isoformat(), "version": payment["version"]},
    )
    assert moved.status_code == 200
    data = planning(client)
    assert data["money_needed_soon"]["next_7_days"] == "0.00"
    assert data["money_needed_soon"]["next_30_days"] == "125.00"
    same = first_payment(client, recurring["id"])
    assert same["id"] == original_id
    assert str(same["occurrence_date"])[:10] == original_occurrence


def test_account_funding_card_derivation_unknown_group_and_shortfall(client):
    setup_user(client)
    funded = create_account(client, "Bills Account", "100.00")
    card_account = create_account(client, "Card Account", "500.00")
    card = create_card(client, card_account["id"])
    create_recurring(client, "Short Bill", "150.00", 2, account_id=funded["id"], automatic=True)
    create_recurring(client, "Card Charge", "29.00", 3, card_id=card["id"])
    create_recurring(client, "Unknown Account", "40.00", 4)

    data = planning(client)
    by_name = {row["account_name"]: row for row in data["funding_requirements"]}
    assert by_name["Bills Account"]["required"] == "150.00"
    assert by_name["Bills Account"]["shortfall"] == "50.00"
    assert by_name["Bills Account"]["has_shortfall"] is True
    assert by_name["Card Account"]["required"] == "29.00"
    assert by_name["Account not specified"]["required"] == "40.00"
    assert by_name["Account not specified"]["available"] is None
    assert by_name["Account not specified"]["balance_known"] is False


def test_overdue_is_included_and_attention_reason_is_explicit(client):
    setup_user(client)
    account = create_account(client)
    response = client.post(
        "/api/bills",
        json={
            "name": "Overdue Water", "amount": "237.00",
            "due_date": (date.today() - timedelta(days=4)).isoformat(),
            "payment_method": "bpay", "payment_handling": "manual", "account_id": account["id"],
        },
    )
    assert response.status_code == 201
    data = planning(client)
    assert data["money_needed_soon"]["next_7_days"] == "237.00"
    item = next(row for row in data["attention"] if row["name"] == "Overdue Water")
    assert item["attention_reason"] == "Overdue manual payment"


def test_linked_bill_suppresses_matching_scheduled_payment(client):
    setup_user(client)
    account = create_account(client)
    recurring = create_recurring(client, "Electricity", "220.00", 4, account_id=account["id"])
    client.get("/api/scheduled-payments")
    created = client.post(
        "/api/bills",
        json={
            "name": "Electricity Bill", "amount": "237.00",
            "due_date": (date.today() + timedelta(days=4)).isoformat(),
            "payment_method": "bpay", "payment_handling": "manual", "account_id": account["id"],
            "recurring_expense_id": recurring["id"],
        },
    )
    assert created.status_code == 201
    data = planning(client)
    assert data["money_needed_soon"]["next_7_days"] == "237.00"
    visible = client.get("/api/payment-centre?date_range=next_7_days").json()["rows"]
    assert len([row for row in visible if row.get("recurring_expense_id") == recurring["id"]]) == 1
    assert next(row for row in visible if row.get("recurring_expense_id") == recurring["id"])["source_type"] == "bill"


def test_reconciliation_removes_unpaid_requirement_and_materialisation_does_not_duplicate(client):
    setup_user(client)
    account = create_account(client)
    recurring = create_recurring(client, "Netflix", "29.00", 2, account_id=account["id"])
    payment = first_payment(client, recurring["id"])
    tx = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"], "date": payment["expected_date"], "amount": "29.00",
            "transaction_type": "expense", "description": "Netflix", "merchant": "Netflix",
        },
    )
    assert tx.status_code == 201
    candidates = client.get("/api/payments/match-candidates?date_tolerance_days=7").json()
    candidate = next(row for row in candidates if row["scheduled_payment_id"] == payment["id"])
    matched = client.post(
        "/api/payments/match",
        json={"transaction_id": candidate["transaction_id"], "scheduled_payment_id": payment["id"]},
    )
    assert matched.status_code == 200
    assert planning(client)["money_needed_soon"]["next_7_days"] == "0.00"

    for _ in range(3):
        client.get("/api/scheduled-payments")
        planning(client)
    with get_engine().connect() as connection:
        duplicates = connection.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT user_id,recurring_expense_id,COALESCE(occurrence_date,expected_date),COUNT(*) n
                FROM scheduled_payments
                GROUP BY user_id,recurring_expense_id,COALESCE(occurrence_date,expected_date)
                HAVING n>1
            )
        """)).scalar()
    assert duplicates == 0


def test_payment_centre_and_planning_totals_agree_and_skip_route_is_unique(client):
    setup_user(client)
    account = create_account(client)
    create_recurring(client, "One", "100.00", 3, account_id=account["id"])
    create_recurring(client, "Two", "200.00", 6, account_id=account["id"], automatic=True)
    centre = client.get("/api/payment-centre?date_range=next_7_days").json()
    plan = planning(client)
    active_total = sum(
        float(row.get("expected_amount") or row.get("amount") or 0)
        for row in centre["rows"] if row["status"] not in {"paid", "skipped", "cancelled"}
    )
    assert f"{active_total:.2f}" == plan["money_needed_soon"]["next_7_days"]

    import app.main as main_module

    skip_routes = [
        route for route in main_module.app.routes
        if getattr(route, "path", None) == "/api/scheduled-payments/{payment_id}/skip"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(skip_routes) == 1
