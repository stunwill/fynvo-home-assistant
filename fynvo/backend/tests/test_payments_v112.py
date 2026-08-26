from datetime import date, timedelta

from sqlalchemy import text

from app.database import get_engine


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def create_account(client, name="Shared ING"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": "transaction", "opening_balance": "5000.00", "institution": "ING"},
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


def bill_payload(**overrides):
    payload = {
        "name": "Council Rates",
        "amount": "420.00",
        "due_date": (date.today() + timedelta(days=5)).isoformat(),
        "provider": "MRCC",
        "payee_merchant": "MRCC",
        "bill_type": "Rates",
        "priority": "high",
        "payment_handling": "manual",
        "payment_method": "bpay",
        "auto_payment_grace_days": 3,
        "notes": "Quarterly notice",
    }
    payload.update(overrides)
    return payload


def test_bill_crud_mark_paid_and_forecast_resolution(client):
    setup_user(client)
    created = client.post("/api/bills", json=bill_payload())
    assert created.status_code == 201
    bill = created.json()
    assert bill["name"] == "Council Rates"
    assert bill["payment_method"] == "bpay"
    assert bill["payment_handling"] == "manual"
    assert bill["expected_amount"] == "420.00"

    centre = client.get("/api/payment-centre?date_range=next_30_days")
    assert centre.status_code == 200
    matching = [row for row in centre.json()["rows"] if row["source_type"] == "bill" and row["id"] == bill["id"]]
    assert len(matching) == 1

    calendar = client.get("/api/dashboard/command-centre?range_days=30")
    assert calendar.status_code == 200
    assert any(row.get("kind") == "bill" and row.get("name") == "Council Rates" for row in calendar.json()["upcoming_commitments"])

    forecast = client.get("/api/forecast?horizon=30d")
    assert forecast.status_code == 200
    assert any(row.get("source_type") == "bill" and row.get("source_id") == bill["id"] for row in forecast.json()["events"])

    updated_payload = bill_payload(amount="425.00", version=bill["version"], notes="Updated notice")
    updated = client.put(f"/api/bills/{bill['id']}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["expected_amount"] == "425.00"
    assert updated.json()["notes"] == "Updated notice"

    paid = client.post(
        f"/api/bills/{bill['id']}/mark-paid",
        json={"paid_date": date.today().isoformat(), "paid_amount": "431.25", "version": updated.json()["version"]},
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert paid.json()["expected_amount"] == "425.00"
    assert paid.json()["actual_amount"] == "431.25"
    assert paid.json()["difference"] == "6.25"

    duplicate = client.post(f"/api/bills/{bill['id']}/mark-paid", json={"paid_amount": "431.25"})
    assert duplicate.status_code == 409

    fresh = client.get(f"/api/bills/{bill['id']}")
    assert fresh.status_code == 200
    assert fresh.json()["status"] == "paid"
    assert fresh.json()["history"][-1]["to_status"] == "paid"

    after = client.get("/api/forecast?horizon=30d").json()
    assert not any(row.get("source_type") == "bill" and row.get("source_id") == bill["id"] for row in after["events"])


def test_overdue_bill_is_actionable_and_resolves(client):
    setup_user(client)
    overdue = client.post(
        "/api/bills",
        json=bill_payload(name="Overdue Water", amount="237.00", due_date=(date.today() - timedelta(days=4)).isoformat()),
    ).json()
    centre = client.get("/api/payment-centre?date_range=overdue")
    assert centre.status_code == 200
    row = next(item for item in centre.json()["rows"] if item["source_type"] == "bill" and item["id"] == overdue["id"])
    assert row["status"] == "overdue"
    assert row["days_overdue"] == 4
    assert row["requires_action"] is True
    assert centre.json()["summary"]["overdue"]["amount"] == "237.00"

    paid = client.post(f"/api/bills/{overdue['id']}/mark-paid", json={"paid_amount": "237.00"})
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert not any(item["id"] == overdue["id"] and item["source_type"] == "bill" for item in client.get("/api/payment-centre?date_range=overdue").json()["rows"])


def test_direct_debit_and_card_bill_sources_are_validated_and_card_derives_account(client):
    setup_user(client)
    account = create_account(client)
    card = create_card(client, account["id"])

    no_account = client.post(
        "/api/bills",
        json=bill_payload(name="Telstra", amount="120.00", payment_handling="automatic", payment_method="direct_debit"),
    )
    assert no_account.status_code == 400
    assert no_account.json()["detail"] == "Direct Debit requires an Account"

    direct = client.post(
        "/api/bills",
        json=bill_payload(name="Telstra", amount="120.00", payment_handling="automatic", payment_method="direct_debit", account_id=account["id"]),
    )
    assert direct.status_code == 201
    assert direct.json()["account_id"] == account["id"]
    assert direct.json()["payment_handling"] == "automatic"

    card_bill = client.post(
        "/api/bills",
        json=bill_payload(name="Netflix", amount="29.00", payment_handling="automatic", payment_method="automatic_card_payment", card_id=card["id"]),
    )
    assert card_bill.status_code == 201
    row = card_bill.json()
    assert row["card_id"] == card["id"]
    assert row["card_name"] == "Shared ING Card ••••6100"
    assert row["account_id"] == account["id"]
    assert row["linked_account_name"] == "Shared ING"


def test_automatic_bill_confirmation_period_never_marks_paid_without_evidence(client):
    setup_user(client)
    account = create_account(client)
    created = client.post(
        "/api/bills",
        json=bill_payload(
            name="Telstra",
            amount="120.00",
            due_date=(date.today() - timedelta(days=4)).isoformat(),
            payment_handling="automatic",
            payment_method="direct_debit",
            account_id=account["id"],
            auto_payment_grace_days=3,
        ),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "auto_payment_unconfirmed"
    assert created.json()["actual_amount"] is None


def test_payment_centre_search_filters_and_mutually_exclusive_summary(client):
    setup_user(client)
    account = create_account(client)
    manual = client.post("/api/bills", json=bill_payload(account_id=account["id"])).json()
    client.post(
        "/api/recurring-expenses",
        json={
            "name": "Netflix",
            "amount": "29.00",
            "frequency": "monthly",
            "next_due_date": (date.today() + timedelta(days=3)).isoformat(),
            "payment_method": "automatic_card_payment",
            "payment_handling": "automatic",
            "card_id": create_card(client, account["id"])["id"],
            "payee_merchant": "Netflix",
        },
    )
    centre = client.get("/api/payment-centre?date_range=next_30_days")
    assert centre.status_code == 200
    data = centre.json()
    assert any(row["source_type"] == "bill" and row["id"] == manual["id"] for row in data["rows"])
    assert any(row["source_type"] == "scheduled_payment" and row["name"] == "Netflix" for row in data["rows"])
    bucket_total = sum(
        int(round(float(data["summary"][key]["amount"]) * 100))
        for key in ("overdue", "requires_payment", "expected_automatically", "awaiting_confirmation", "paid", "skipped", "cancelled")
    )
    total = int(round(float(data["summary"]["total_scheduled"]["amount"]) * 100))
    assert bucket_total <= total

    searched = client.get("/api/payment-centre?date_range=next_30_days&search=Netflix")
    assert searched.status_code == 200
    assert searched.json()["rows"]
    assert all("netflix" in str(row["name"]).lower() for row in searched.json()["rows"])

    manual_only = client.get("/api/payment-centre?date_range=next_30_days&payment_handling=manual")
    assert all(row["payment_handling"] == "manual" for row in manual_only.json()["rows"])


def test_skip_is_idempotency_protected_and_schedule_regeneration_does_not_duplicate(client):
    setup_user(client)
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Gym",
            "amount": "59.00",
            "frequency": "monthly",
            "next_due_date": (date.today() + timedelta(days=2)).isoformat(),
            "payment_method": "manual_payment",
        },
    ).json()
    first = client.get("/api/scheduled-payments").json()
    payment = next(row for row in first if row["recurring_expense_id"] == recurring["id"])
    assert client.post(f"/api/scheduled-payments/{payment['id']}/skip", json={"note": "Paused"}).status_code == 200
    repeated = client.post(f"/api/scheduled-payments/{payment['id']}/skip", json={"note": "Repeated"})
    assert repeated.status_code == 409

    for _ in range(3):
        client.get("/api/scheduled-payments")
        client.get("/api/payment-centre?date_range=next_90_days")
    with get_engine().connect() as connection:
        duplicates = connection.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT recurring_expense_id,expected_date,COUNT(*) n
                FROM scheduled_payments GROUP BY user_id,recurring_expense_id,expected_date HAVING n>1
            )
        """)).scalar()
    assert duplicates == 0


def test_cancel_bill_preserves_history_and_blocks_paid_cancellation(client):
    setup_user(client)
    future = client.post("/api/bills", json=bill_payload(name="Future invoice")).json()
    cancelled = client.post(f"/api/bills/{future['id']}/cancel", json={"note": "No longer payable"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.get(f"/api/bills/{future['id']}").json()["history"][-1]["to_status"] == "cancelled"

    paid = client.post("/api/bills", json=bill_payload(name="Paid invoice")).json()
    assert client.post(f"/api/bills/{paid['id']}/mark-paid", json={"paid_amount": "420.00"}).status_code == 200
    blocked = client.post(f"/api/bills/{paid['id']}/cancel", json={})
    assert blocked.status_code == 409


def test_migration_is_additive_idempotent_and_schema_reaches_15(client):
    setup_user(client)
    from app.payments_v112 import ensure_v112_schema

    engine = get_engine()
    ensure_v112_schema(engine)
    ensure_v112_schema(engine)
    with engine.connect() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(bills)")).all()}
        version = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
    assert int(version) == 15
    assert {"payment_method", "payment_handling", "card_id", "actual_amount_cents", "version"}.issubset(columns)
