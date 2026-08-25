def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def create_account(client):
    response = client.post(
        "/api/accounts",
        json={
            "name": "Shared ING",
            "account_type": "transaction",
            "opening_balance": "2000.00",
            "institution": "ING",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_card(client, account_id):
    response = client.post(
        "/api/cards",
        json={
            "account_id": account_id,
            "name": "Shared ING Card",
            "card_type": "debit",
            "last_four": "6100",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_recurring_edit_persists_full_payment_contract_after_fresh_fetch(client):
    setup_user(client)
    account = create_account(client)
    card = create_card(client, account["id"])
    reference = client.get("/api/reference-data")
    assert reference.status_code == 200
    expense_types = reference.json()["expense_types"]
    subscription = next(row for row in expense_types if row["name"] == "Subscription")

    created = client.post(
        "/api/recurring-expenses",
        json={
            "name": "iCloud Storage",
            "amount": "4.49",
            "frequency": "monthly",
            "next_due_date": "2026-09-14",
            "expense_type_id": subscription["id"],
            "amount_type": "fixed",
            "payment_handling": "automatic",
            "payment_method": "automatic_card_payment",
            "card_id": card["id"],
            "payee_merchant": "Apple",
            "auto_payment_grace_days": 3,
            "notes": "Original note",
        },
    )
    assert created.status_code == 201
    recurring = created.json()

    update_payload = {
        "name": "iCloud Storage",
        "amount": "4.49",
        "frequency": "monthly",
        "next_due_date": "2026-09-14",
        "payment_method": "automatic_card_payment",
        "payment_handling": "automatic",
        "account_id": None,
        "card_id": card["id"],
        "category_id": recurring.get("category_id"),
        "expense_type_id": subscription["id"],
        "payee_merchant": "Apple Services",
        "amount_type": "fixed",
        "end_date": None,
        "reminder_days_before": None,
        "notes": "Updated from the edit modal",
        "is_active": True,
        "auto_payment_grace_days": 5,
    }
    updated = client.put(f"/api/recurring-expenses/{recurring['id']}", json=update_payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["payee_merchant"] == "Apple Services"
    assert updated.json()["notes"] == "Updated from the edit modal"
    assert updated.json()["payment_method"] == "automatic_card_payment"
    assert updated.json()["payment_handling"] == "automatic"
    assert updated.json()["card_id"] == card["id"]
    assert updated.json()["derived_account_id"] == account["id"]
    assert updated.json()["expense_type_id"] == subscription["id"]
    assert updated.json()["auto_payment_grace_days"] == 5

    fetched = client.get("/api/recurring-expenses")
    assert fetched.status_code == 200
    persisted = next(row for row in fetched.json() if row["id"] == recurring["id"])
    assert persisted["payee_merchant"] == "Apple Services"
    assert persisted["notes"] == "Updated from the edit modal"
    assert persisted["payment_method"] == "automatic_card_payment"
    assert persisted["payment_handling"] == "automatic"
    assert persisted["card_id"] == card["id"]
    assert persisted["derived_account_id"] == account["id"]
    assert persisted["expense_type_id"] == subscription["id"]
    assert persisted["auto_payment_grace_days"] == 5


def test_recurring_update_rejects_invalid_payment_reference_with_specific_error(client):
    setup_user(client)
    account = create_account(client)
    created = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Insurance",
            "amount": "116.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-21",
            "payment_method": "direct_debit",
            "payment_handling": "automatic",
            "account_id": account["id"],
        },
    ).json()

    payload = {
        "name": "Insurance",
        "amount": "116.00",
        "frequency": "monthly",
        "next_due_date": "2026-09-21",
        "payment_method": "automatic_card_payment",
        "payment_handling": "automatic",
        "card_id": None,
        "auto_payment_grace_days": 3,
    }
    response = client.put(f"/api/recurring-expenses/{created['id']}", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Choose a Card for Automatic Card Payment"
