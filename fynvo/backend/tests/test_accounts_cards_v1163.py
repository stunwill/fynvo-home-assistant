def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def create_account(client, name, opening_balance="0.00", account_type="transaction"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": account_type, "opening_balance": opening_balance},
    )
    assert response.status_code == 201
    return response.json()


def test_archive_restore_and_archived_filter(client):
    setup_user(client)
    account = create_account(client, "Everyday")

    archived = client.post(f"/api/accounts/{account['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False

    active_ids = {row["id"] for row in client.get("/api/accounts").json()}
    all_rows = client.get("/api/accounts?include_archived=true").json()
    assert account["id"] not in active_ids
    assert any(row["id"] == account["id"] and row["is_active"] is False for row in all_rows)

    restored = client.post(f"/api/accounts/{account['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True
    assert account["id"] in {row["id"] for row in client.get("/api/accounts").json()}


def test_dependency_preview_and_bulk_transaction_move_are_safe(client):
    setup_user(client)
    source = create_account(client, "Duplicate")
    destination = create_account(client, "Everyday")

    transaction = client.post(
        "/api/transactions",
        json={
            "account_id": source["id"],
            "date": "2026-09-01",
            "amount": "25.00",
            "transaction_type": "expense",
            "description": "Groceries",
            "status": "cleared",
        },
    )
    assert transaction.status_code == 201

    preview = client.get(f"/api/accounts/{source['id']}/dependencies")
    assert preview.status_code == 200
    dependencies = {item["type"]: item for item in preview.json()["dependencies"]}
    assert dependencies["transactions"]["count"] == 1
    assert dependencies["transactions"]["action"] == "move"

    moved = client.post(
        f"/api/accounts/{source['id']}/move-and-archive",
        json={"destination_account_id": destination["id"]},
    )
    assert moved.status_code == 200
    assert moved.json()["account"]["is_active"] is False

    rows = client.get(f"/api/transactions?account_id={destination['id']}").json()
    assert any(row["description"] == "Groceries" for row in rows)


def test_opening_balance_preserves_transactions_during_consolidation(client):
    setup_user(client)
    source = create_account(client, "Legacy", opening_balance="500.00")
    destination = create_account(client, "Current")
    transaction = client.post(
        "/api/transactions",
        json={
            "account_id": source["id"],
            "date": "2026-09-01",
            "amount": "40.00",
            "transaction_type": "expense",
            "description": "Historical purchase",
            "status": "cleared",
        },
    )
    assert transaction.status_code == 201

    preview = client.get(f"/api/accounts/{source['id']}/dependencies").json()
    assert preview["transaction_move_blocked"] is True
    assert any("opening balance" in warning.lower() for warning in preview["warnings"])

    moved = client.post(
        f"/api/accounts/{source['id']}/move-and-archive",
        json={"destination_account_id": destination["id"]},
    )
    assert moved.status_code == 200
    assert "transactions" in moved.json()["preserved_historical_relationships"]
    source_rows = client.get(f"/api/transactions?account_id={source['id']}").json()
    assert any(row["description"] == "Historical purchase" for row in source_rows)


def test_destination_validation_and_safe_permanent_delete(client):
    setup_user(client)
    source = create_account(client, "Source")
    destination = create_account(client, "Archived Destination")

    same = client.post(
        f"/api/accounts/{source['id']}/move-and-archive",
        json={"destination_account_id": source["id"]},
    )
    assert same.status_code == 400

    client.post(f"/api/accounts/{destination['id']}/archive")
    archived_destination = client.post(
        f"/api/accounts/{source['id']}/move-and-archive",
        json={"destination_account_id": destination["id"]},
    )
    assert archived_destination.status_code == 409

    disposable = create_account(client, "Disposable")
    deleted = client.delete(f"/api/accounts/{disposable['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "ok"
