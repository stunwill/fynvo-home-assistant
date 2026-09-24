from datetime import date

from app.database import get_engine
from sqlalchemy import text


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def account(client, name="Kristy ING"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": "transaction", "opening_balance": "2000.00", "institution": "ING"},
    )
    assert response.status_code == 201
    return response.json()


def category_by_path(client, path):
    rows = client.get("/api/categories").json()
    return next(row for row in rows if row["path"] == path)


def expense_type_by_name(client, name):
    return next(row for row in client.get("/api/expense-types").json() if row["name"] == name)


def test_v1_schema_and_reference_data_seed_are_idempotent(client):
    setup_user(client)
    first = client.get("/api/reference-data")
    assert first.status_code == 200
    payload = first.json()
    assert len(payload["categories"]) == 110
    assert len(payload["expense_types"]) == 10
    assert category_by_path(client, "Entertainment → Streaming")["is_active"] is True
    assert category_by_path(client, "Transport → Vehicle Registration")["is_active"] is True
    assert expense_type_by_name(client, "Subscription")["description"] == "Netflix, Spotify, iCloud"

    second = client.get("/api/reference-data").json()
    assert len(second["categories"]) == 110
    assert len(second["expense_types"]) == 10
    integrity = client.get("/api/v1/acceptance/data-integrity").json()
    assert integrity == {
        "schema_version": 15,
        "orphan_cards": 0,
        "orphan_category_references": 0,
        "status": "ok",
    }


def test_category_create_move_rename_archive_and_id_reference_survives(client):
    setup_user(client)
    entertainment = category_by_path(client, "Entertainment")
    utilities = category_by_path(client, "Utilities")
    created = client.post(
        "/api/categories",
        json={"name": "Podcasts", "parent_id": entertainment["id"], "category_type": "expense"},
    )
    assert created.status_code == 201
    podcasts = created.json()
    assert podcasts["path"] == "Entertainment → Podcasts"

    account_row = account(client)
    subscription = expense_type_by_name(client, "Subscription")
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Podcast membership",
            "amount": "12.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "payment_method": "direct_debit",
            "account_id": account_row["id"],
            "category_id": podcasts["id"],
            "expense_type_id": subscription["id"],
        },
    ).json()
    assert recurring["category_id"] == podcasts["id"]

    moved = client.put(
        f"/api/categories/{podcasts['id']}",
        json={"name": "Audio Services", "parent_id": utilities["id"]},
    )
    assert moved.status_code == 200
    assert moved.json()["path"] == "Utilities → Audio Services"
    reloaded = next(row for row in client.get("/api/recurring-expenses").json() if row["id"] == recurring["id"])
    assert reloaded["category_id"] == podcasts["id"]
    assert reloaded["category"] == "Utilities → Audio Services"

    archived = client.put(f"/api/categories/{podcasts['id']}", json={"is_active": False})
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False
    still_historical = next(row for row in client.get("/api/recurring-expenses").json() if row["id"] == recurring["id"])
    assert still_historical["category_id"] == podcasts["id"]


def test_category_cycle_is_rejected(client):
    setup_user(client)
    parent = client.post("/api/categories", json={"name": "Custom Parent"}).json()
    child = client.post("/api/categories", json={"name": "Custom Child", "parent_id": parent["id"]}).json()
    response = client.put(f"/api/categories/{parent['id']}", json={"parent_id": child["id"]})
    assert response.status_code == 400


def test_expense_type_create_edit_archive_preserves_recurring_reference(client):
    setup_user(client)
    account_row = account(client)
    custom = client.post(
        "/api/expense-types",
        json={"name": "School Arrangement", "description": "Regular school payment"},
    )
    assert custom.status_code == 201
    custom = custom.json()
    school = category_by_path(client, "Children & Family → School")
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "School instalment",
            "amount": "50.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "payment_method": "direct_debit",
            "account_id": account_row["id"],
            "category_id": school["id"],
            "expense_type_id": custom["id"],
        },
    ).json()
    renamed = client.put(
        f"/api/expense-types/{custom['id']}",
        json={"name": "Education Arrangement", "description": "School and training payment"},
    )
    assert renamed.status_code == 200
    row = next(item for item in client.get("/api/recurring-expenses").json() if item["id"] == recurring["id"])
    assert row["expense_type_id"] == custom["id"]
    assert row["expense_type"] == "Education Arrangement"
    archived = client.put(f"/api/expense-types/{custom['id']}", json={"is_active": False})
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False
    row = next(item for item in client.get("/api/recurring-expenses").json() if item["id"] == recurring["id"])
    assert row["expense_type_id"] == custom["id"]


def test_cards_support_multiple_per_account_deactivation_and_last_four_validation(client):
    setup_user(client)
    acct = account(client)
    first = client.post(
        "/api/cards",
        json={"account_id": acct["id"], "name": "Kristy ING Card", "card_type": "debit", "last_four": "1234"},
    )
    assert first.status_code == 201
    assert first.json()["display_name"] == "Kristy ING Card ••••1234"
    second = client.post(
        "/api/cards",
        json={"account_id": acct["id"], "name": "Spare ING Card", "card_type": "debit", "last_four": "5678"},
    )
    assert second.status_code == 201
    assert len(client.get("/api/cards").json()) == 2

    invalid = client.post(
        "/api/cards",
        json={"account_id": acct["id"], "name": "Unsafe", "card_type": "debit", "last_four": "12345"},
    )
    assert invalid.status_code == 400

    archived = client.put(f"/api/cards/{first.json()['id']}", json={"is_active": False})
    assert archived.status_code == 200
    assert len(client.get("/api/cards").json()) == 1
    all_cards = client.get("/api/cards?include_inactive=true").json()
    assert len(all_cards) == 2
    assert next(row for row in all_cards if row["id"] == first.json()["id"])["last_four"] == "1234"


def test_netflix_automatic_card_payment_derives_account_and_cost(client):
    setup_user(client)
    acct = account(client)
    card = client.post(
        "/api/cards",
        json={"account_id": acct["id"], "name": "Kristy ING Card", "card_type": "debit", "last_four": "1234"},
    ).json()
    category = category_by_path(client, "Entertainment → Streaming")
    expense_type = expense_type_by_name(client, "Subscription")
    response = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Netflix",
            "payee_merchant": "Netflix",
            "amount": "20.00",
            "amount_type": "fixed",
            "next_due_date": "2026-09-17",
            "frequency": "monthly",
            "expense_type_id": expense_type["id"],
            "category_id": category["id"],
            "payment_method": "automatic_card_payment",
            "card_id": card["id"],
        },
    )
    assert response.status_code == 201
    row = response.json()
    assert row["payment_method_label"] == "Automatic Card Payment"
    assert row["card"]["display_name"] == "Kristy ING Card ••••1234"
    assert row["derived_account_id"] == acct["id"]
    assert row["derived_account_name"] == "Kristy ING"
    assert row["account_id"] == acct["id"]
    assert row["calculated_cost"] == {"monthly": "20.00", "annual": "240.00", "show_monthly": True}
    assert row["category"] == "Entertainment → Streaming"
    assert row["expense_type"] == "Subscription"


def test_automatic_card_payment_requires_card_but_not_separate_account(client):
    setup_user(client)
    account(client)
    category = category_by_path(client, "Entertainment → Streaming")
    expense_type = expense_type_by_name(client, "Subscription")
    response = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Netflix",
            "amount": "20",
            "frequency": "monthly",
            "next_due_date": "2026-09-17",
            "payment_method": "automatic_card_payment",
            "category_id": category["id"],
            "expense_type_id": expense_type["id"],
        },
    )
    assert response.status_code == 400
    assert "Card" in response.json()["detail"]


def test_electricity_variable_direct_debit_and_not_set_are_valid(client):
    setup_user(client)
    acct = account(client)
    category = category_by_path(client, "Utilities → Electricity")
    expense_type = expense_type_by_name(client, "Bill")
    electricity = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Electricity",
            "payee_merchant": "Powershop",
            "amount": "250.00",
            "amount_type": "variable_estimated",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "expense_type_id": expense_type["id"],
            "category_id": category["id"],
            "payment_method": "direct_debit",
            "account_id": acct["id"],
        },
    )
    assert electricity.status_code == 201
    row = electricity.json()
    assert row["amount_type_label"] == "Variable / Estimated"
    assert row["calculated_cost"]["monthly"] == "250.00"
    assert row["calculated_cost"]["annual"] == "3000.00"

    unknown = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Imported unknown payment source",
            "amount": "40.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-05",
            "payment_method": "not_set",
        },
    )
    assert unknown.status_code == 201
    assert unknown.json()["completeness"] == "complete"


def test_annual_registration_has_no_artificial_monthly_cost(client):
    setup_user(client)
    registration = category_by_path(client, "Transport → Vehicle Registration")
    government = expense_type_by_name(client, "Tax / Government")
    response = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Car Registration",
            "amount": "900.00",
            "frequency": "yearly",
            "next_due_date": "2026-12-01",
            "expense_type_id": government["id"],
            "category_id": registration["id"],
            "payment_method": "manual_payment",
        },
    )
    assert response.status_code == 201
    assert response.json()["calculated_cost"] == {"monthly": None, "annual": "900.00", "show_monthly": False}


def test_recurrence_cost_acceptance_rules(client):
    setup_user(client)
    cases = [
        ("weekly", None, "86.67", "1040.00", True),
        ("fortnightly", None, "43.33", "520.00", True),
        ("every_4_weeks", None, "21.67", "260.00", True),
        ("monthly", None, "20.00", "240.00", True),
        ("quarterly", None, None, "80.00", False),
        ("yearly", None, None, "20.00", False),
    ]
    for frequency, interval, monthly, annual, show_monthly in cases:
        url = f"/api/recurring-expenses/cost?amount=20.00&frequency={frequency}"
        if interval:
            url += f"&interval_count={interval}"
        response = client.get(url)
        assert response.status_code == 200
        assert response.json() == {"monthly": monthly, "annual": annual, "show_monthly": show_monthly}

    quarterly = client.get("/api/recurring-expenses/cost?amount=300.00&frequency=quarterly").json()
    assert quarterly == {"monthly": None, "annual": "1200.00", "show_monthly": False}


def test_legacy_account_relationship_migrates_without_inventing_direct_debit(client):
    setup_user(client)
    acct = account(client)
    now = "2026-08-19 00:00:00"
    with get_engine().begin() as connection:
        connection.execute(text("""
            INSERT INTO recurring_expenses(
                user_id,name,amount_cents,frequency,next_due_date,direct_debit,account_id,
                is_active,variable_amount,source,created_at,updated_at
            ) VALUES(1,'Legacy Account Expense',5000,'monthly','2026-09-01',0,:account,1,0,'legacy',:now,:now)
        """), {"account": acct["id"], "now": now})
    row = next(item for item in client.get("/api/recurring-expenses").json() if item["name"] == "Legacy Account Expense")
    assert row["account_id"] == acct["id"]
    assert row["payment_method"] == "not_set"


def test_future_effective_amount_change_preserves_base_and_forecast_history(client):
    setup_user(client)
    acct = account(client)
    internet = category_by_path(client, "Utilities → Internet")
    bill = expense_type_by_name(client, "Bill")
    created = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Internet",
            "payee_merchant": "Telstra",
            "amount": "140.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "payment_method": "direct_debit",
            "account_id": acct["id"],
            "category_id": internet["id"],
            "expense_type_id": bill["id"],
        },
    ).json()
    changed = client.put(
        f"/api/recurring-expenses/{created['id']}",
        json={"amount": "80.00", "effective_from": "2026-10-01"},
    )
    assert changed.status_code == 200
    assert changed.json()["amount"] == "140.00"

    forecast = client.get("/api/forecast?horizon=120d&start=2026-09-01").json()
    internet_events = [event for event in forecast["events"] if event["source_type"] == "recurring_expense" and event["source_id"] == created["id"]]
    assert internet_events[0]["date"] == "2026-09-01"
    assert internet_events[0]["amount"] == "-140.00"
    assert internet_events[1]["date"] == "2026-10-01"
    assert internet_events[1]["amount"] == "-80.00"


def test_end_date_stops_schedule_and_twelve_month_forecast(client):
    setup_user(client)
    acct = account(client)
    created = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Three Month Plan",
            "amount": "100.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "end_date": "2026-11-01",
            "payment_method": "direct_debit",
            "account_id": acct["id"],
        },
    ).json()
    forecast = client.get("/api/forecast?horizon=12m&start=2026-09-01").json()
    events = [event for event in forecast["events"] if event["source_type"] == "recurring_expense" and event["source_id"] == created["id"]]
    assert [event["date"] for event in events] == ["2026-09-01", "2026-10-01", "2026-11-01"]

    schedule = client.get("/api/schedule?start=2026-09-01&end=2027-08-31").json()
    rows = [event for event in schedule["events"] if event["kind"] == "recurring_expense" and event["name"] == "Three Month Plan"]
    assert [event["date"] for event in rows] == ["2026-09-01", "2026-10-01", "2026-11-01"]


def test_linked_bill_suppresses_duplicate_recurring_occurrence(client):
    setup_user(client)
    acct = account(client)
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Water",
            "amount": "100.00",
            "frequency": "quarterly",
            "next_due_date": "2026-10-15",
            "payment_method": "direct_debit",
            "account_id": acct["id"],
        },
    ).json()
    bill = client.post(
        "/api/bills",
        json={
            "name": "Water",
            "amount": "100.00",
            "due_date": "2026-10-15",
            "account_id": acct["id"],
            "recurring_expense_id": recurring["id"],
        },
    )
    assert bill.status_code == 201
    schedule = client.get("/api/schedule?start=2026-10-01&end=2026-10-31").json()
    same = [row for row in schedule["events"] if row["name"] == "Water" and row["date"] == "2026-10-15"]
    assert len(same) == 1
    assert same[0]["kind"] == "bill"
