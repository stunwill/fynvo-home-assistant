from datetime import date, timedelta

from sqlalchemy import text

from app.database import get_engine
from app.payments_v114 import ensure_v114_schema


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def create_account(client):
    response = client.post(
        "/api/accounts",
        json={"name": "ING Everyday", "account_type": "transaction", "opening_balance": "5000.00", "institution": "ING"},
    )
    assert response.status_code == 201
    return response.json()


def create_recurring(client, *, name="Car Insurance", start=None, automatic=True):
    account = create_account(client)
    response = client.post(
        "/api/recurring-expenses",
        json={
            "name": name,
            "amount": "134.00",
            "frequency": "monthly",
            "next_due_date": (start or (date.today() + timedelta(days=3))).isoformat(),
            "payment_method": "direct_debit" if automatic else "manual_payment",
            "payment_handling": "automatic" if automatic else "manual",
            "account_id": account["id"],
            "payee_merchant": "Budget Direct",
            "auto_payment_grace_days": 3,
        },
    )
    assert response.status_code == 201
    return response.json(), account


def payments_for(client, recurring_id):
    response = client.get("/api/scheduled-payments")
    assert response.status_code == 200
    return [row for row in response.json() if row["recurring_expense_id"] == recurring_id]


def test_future_monthly_override_preserves_occurrence_identity_and_future_dates(client):
    setup_user(client)
    start = date.today() + timedelta(days=5)
    recurring, _ = create_recurring(client, start=start)
    rows = payments_for(client, recurring["id"])
    first = next(row for row in rows if str(row["expected_date"])[:10] == start.isoformat())
    moved = start + timedelta(days=3)

    response = client.post(
        f"/api/scheduled-payments/{first['id']}/reschedule",
        json={"expected_date": moved.isoformat(), "reason": "Payment date changed by provider", "version": first["version"]},
    )
    assert response.status_code == 200

    for _ in range(3):
        rows = payments_for(client, recurring["id"])

    same = next(row for row in rows if row["id"] == first["id"])
    assert str(same["original_expected_date"])[:10] == start.isoformat()
    assert str(same["expected_date"])[:10] == moved.isoformat()
    assert same["is_date_overridden"] is True
    assert not any(row["id"] != first["id"] and str(row["expected_date"])[:10] == start.isoformat() for row in rows)

    original_future = sorted(str(row["original_expected_date"])[:10] for row in rows)
    expected_future = sorted(str(row["expected_date"])[:10] for row in rows)
    assert original_future[0] == start.isoformat()
    assert expected_future[0] == moved.isoformat()
    if len(rows) > 1:
        assert str(rows[1]["original_expected_date"])[:10] == str(rows[1]["expected_date"])[:10]

    with get_engine().connect() as connection:
        logical_count = connection.execute(text("SELECT COUNT(*) FROM scheduled_payments WHERE recurring_expense_id=:rid"), {"rid": recurring["id"]}).scalar()
        duplicate_count = connection.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT occurrence_date,COUNT(*) n FROM scheduled_payments
                WHERE recurring_expense_id=:rid GROUP BY occurrence_date HAVING n>1
            )
        """), {"rid": recurring["id"]}).scalar()
    assert logical_count == len(rows)
    assert duplicate_count == 0


def test_failed_automatic_payment_can_move_to_future_without_becoming_paid(client):
    setup_user(client)
    original = date.today() - timedelta(days=5)
    recurring, _ = create_recurring(client, start=original)
    payment = min(payments_for(client, recurring["id"]), key=lambda row: str(row["original_expected_date"]))
    assert payment["status"] == "auto_payment_unconfirmed"

    retry = date.today() + timedelta(days=2)
    response = client.post(
        f"/api/scheduled-payments/{payment['id']}/reschedule",
        json={"expected_date": retry.isoformat(), "reason": "Insufficient funds", "version": payment["version"]},
    )
    assert response.status_code == 200
    updated = next(row for row in payments_for(client, recurring["id"]) if row["id"] == payment["id"])
    assert updated["status"] == "expected_automatically"
    assert updated["actual_date"] is None
    assert updated["matched_transaction_id"] is None
    assert str(updated["original_expected_date"])[:10] == original.isoformat()
    assert str(updated["expected_date"])[:10] == retry.isoformat()

    recurring_fresh = next(row for row in client.get("/api/recurring-expenses").json() if row["id"] == recurring["id"])
    assert recurring_fresh["frequency"] == "monthly"
    assert str(recurring_fresh["next_due_date"])[:10] == original.isoformat()


def test_restore_original_date_reuses_same_scheduled_payment(client):
    setup_user(client)
    start = date.today() + timedelta(days=4)
    recurring, _ = create_recurring(client, start=start, automatic=False)
    payment = payments_for(client, recurring["id"])[0]
    moved = start + timedelta(days=2)
    changed = client.post(f"/api/scheduled-payments/{payment['id']}/reschedule", json={"expected_date": moved.isoformat(), "version": payment["version"]})
    assert changed.status_code == 200
    version = changed.json()["version"]

    restored = client.post(f"/api/scheduled-payments/{payment['id']}/restore-original-date", json={"version": version})
    assert restored.status_code == 200
    rows = payments_for(client, recurring["id"])
    same = next(row for row in rows if row["id"] == payment["id"])
    assert str(same["expected_date"])[:10] == start.isoformat()
    assert str(same["original_expected_date"])[:10] == start.isoformat()
    assert same["is_date_overridden"] is False
    assert len([row for row in rows if str(row["original_expected_date"])[:10] == start.isoformat()]) == 1


def test_override_audit_records_previous_new_reason_source_and_timestamp(client):
    setup_user(client)
    start = date.today() + timedelta(days=6)
    recurring, _ = create_recurring(client, start=start)
    payment = payments_for(client, recurring["id"])[0]
    moved = start + timedelta(days=2)
    response = client.post(
        f"/api/scheduled-payments/{payment['id']}/reschedule",
        json={"expected_date": moved.isoformat(), "reason": "Payment deferred", "note": "Provider confirmed retry", "version": payment["version"]},
    )
    assert response.status_code == 200
    with get_engine().connect() as connection:
        history = connection.execute(text("""
            SELECT previous_expected_date,new_expected_date,reason,source,note,created_at
            FROM scheduled_payment_history WHERE scheduled_payment_id=:id
            ORDER BY id DESC LIMIT 1
        """), {"id": payment["id"]}).mappings().one()
    assert str(history["previous_expected_date"])[:10] == start.isoformat()
    assert str(history["new_expected_date"])[:10] == moved.isoformat()
    assert history["reason"] == "Payment deferred"
    assert history["source"] == "ui"
    assert "Provider confirmed retry" in history["note"]
    assert history["created_at"] is not None


def test_completed_or_matched_payment_date_change_is_rejected(client):
    setup_user(client)
    recurring, _ = create_recurring(client, automatic=False)
    payment = payments_for(client, recurring["id"])[0]
    paid = client.post(f"/api/scheduled-payments/{payment['id']}/mark-paid", json={"paid_amount": "134.00"})
    assert paid.status_code == 200
    blocked = client.post(
        f"/api/scheduled-payments/{payment['id']}/reschedule",
        json={"expected_date": (date.today() + timedelta(days=10)).isoformat(), "version": payment["version"]},
    )
    assert blocked.status_code == 409


def test_reconciliation_and_cross_screen_events_use_effective_expected_date(client):
    setup_user(client)
    start = date.today() + timedelta(days=4)
    recurring, account = create_recurring(client, start=start, automatic=False)
    payment = payments_for(client, recurring["id"])[0]
    moved = start + timedelta(days=3)
    response = client.post(f"/api/scheduled-payments/{payment['id']}/reschedule", json={"expected_date": moved.isoformat(), "version": payment["version"]})
    assert response.status_code == 200

    tx = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"], "date": (moved + timedelta(days=1)).isoformat(), "amount": "134.00",
            "transaction_type": "expense", "description": "Budget Direct", "merchant": "Budget Direct",
        },
    )
    assert tx.status_code == 201
    candidates = client.get("/api/payments/match-candidates?date_tolerance_days=7")
    assert candidates.status_code == 200
    candidate = next(row for row in candidates.json() if row["scheduled_payment_id"] == payment["id"])
    assert str(candidate["expected_date"])[:10] == moved.isoformat()
    assert candidate["day_delta"] == 1

    command = client.get("/api/dashboard/command-centre?range_days=30")
    assert command.status_code == 200
    events = command.json()["forecast"]["expected"]["events"]
    matching = [row for row in events if row.get("source_type") == "recurring_expense" and row.get("source_id") == recurring["id"]]
    assert any(row["date"] == moved.isoformat() for row in matching)
    assert not any(row["date"] == start.isoformat() for row in matching)

    centre = client.get("/api/payment-centre?date_range=next_30_days")
    assert centre.status_code == 200
    row = next(row for row in centre.json()["rows"] if row["source_type"] == "scheduled_payment" and row["id"] == payment["id"])
    assert str(row["expected_date"])[:10] == moved.isoformat()


def test_v114_migration_is_additive_and_idempotent(client):
    setup_user(client)
    engine = get_engine()
    ensure_v114_schema(engine)
    ensure_v114_schema(engine)
    with engine.connect() as connection:
        scheduled_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(scheduled_payments)")).all()}
        history_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(scheduled_payment_history)")).all()}
        version = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
    assert int(version) == 14
    assert {"occurrence_date", "override_reason", "override_note", "override_at", "override_by_user_id", "version"}.issubset(scheduled_columns)
    assert {"previous_expected_date", "new_expected_date", "reason"}.issubset(history_columns)
