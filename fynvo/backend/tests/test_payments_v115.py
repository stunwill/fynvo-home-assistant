from datetime import date, timedelta

from app.database import get_engine
from app.payments_v115 import ensure_v115_schema
from sqlalchemy import text


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


def create_recurring(client, *, start=None, automatic=False):
    account = create_account(client)
    response = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Car Insurance",
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


def test_monthly_skip_preserves_occurrence_identity_and_future_schedule(client):
    setup_user(client)
    start = date.today() + timedelta(days=5)
    recurring, _ = create_recurring(client, start=start)
    rows = payments_for(client, recurring["id"])
    first = rows[0]
    future_occurrences = [str(row["original_expected_date"])[:10] for row in rows[1:3]]

    skipped = client.post(
        f"/api/scheduled-payments/{first['id']}/skip",
        json={"reason": "Payment paused", "note": "One month only", "version": first["version"]},
    )
    assert skipped.status_code == 200
    assert skipped.json()["status"] == "skipped"
    assert skipped.json()["skip_reason"] == "Payment paused"

    for _ in range(3):
        rows = payments_for(client, recurring["id"])

    same = next(row for row in rows if row["id"] == first["id"])
    assert same["status"] == "skipped"
    assert str(same["original_expected_date"])[:10] == start.isoformat()
    assert [str(row["original_expected_date"])[:10] for row in rows[1:3]] == future_occurrences
    assert len([row for row in rows if str(row["original_expected_date"])[:10] == start.isoformat()]) == 1


def test_restore_reuses_same_payment_and_preserves_date_override(client):
    setup_user(client)
    start = date.today() + timedelta(days=4)
    recurring, _ = create_recurring(client, start=start)
    payment = payments_for(client, recurring["id"])[0]
    moved = start + timedelta(days=3)
    changed = client.post(
        f"/api/scheduled-payments/{payment['id']}/reschedule",
        json={"expected_date": moved.isoformat(), "version": payment["version"]},
    )
    assert changed.status_code == 200

    skipped = client.post(
        f"/api/scheduled-payments/{payment['id']}/skip",
        json={"reason": "User requested skip", "version": changed.json()["version"]},
    )
    assert skipped.status_code == 200
    restored = client.post(
        f"/api/scheduled-payments/{payment['id']}/restore",
        json={"note": "Accidental skip", "version": skipped.json()["version"]},
    )
    assert restored.status_code == 200
    result = restored.json()
    assert result["id"] == payment["id"]
    assert str(result["original_expected_date"])[:10] == start.isoformat()
    assert str(result["expected_date"])[:10] == moved.isoformat()
    assert result["is_date_overridden"] is True
    assert result["status"] == "upcoming"


def test_skip_audit_and_payment_centre_detail_retain_reason(client):
    setup_user(client)
    recurring, _ = create_recurring(client)
    payment = payments_for(client, recurring["id"])[0]
    response = client.post(
        f"/api/scheduled-payments/{payment['id']}/skip",
        json={"reason": "Provider waived payment", "note": "Provider confirmed waiver", "version": payment["version"]},
    )
    assert response.status_code == 200

    detail = client.get(f"/api/scheduled-payments/{payment['id']}/detail")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "skipped"
    assert payload["skip_reason"] == "Provider waived payment"
    assert payload["skip_note"] == "Provider confirmed waiver"
    assert payload["history"][-1]["reason"] == "Provider waived payment"
    assert payload["history"][-1]["source"] == "ui"
    assert payload["history"][-1]["created_at"] is not None


def test_skipped_occurrence_is_excluded_from_forecast_and_match_candidates(client):
    setup_user(client)
    start = date.today() + timedelta(days=3)
    recurring, account = create_recurring(client, start=start)
    payment = payments_for(client, recurring["id"])[0]
    skipped = client.post(
        f"/api/scheduled-payments/{payment['id']}/skip",
        json={"version": payment["version"]},
    )
    assert skipped.status_code == 200

    command = client.get("/api/dashboard/command-centre?range_days=30")
    assert command.status_code == 200
    events = command.json()["forecast"]["expected"]["events"]
    assert not any(row.get("scheduled_payment_id") == payment["id"] for row in events)

    tx = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"], "date": start.isoformat(), "amount": "134.00",
            "transaction_type": "expense", "description": "Budget Direct", "merchant": "Budget Direct",
        },
    )
    assert tx.status_code == 201
    candidates = client.get("/api/payments/match-candidates?date_tolerance_days=7")
    assert candidates.status_code == 200
    assert not any(row["scheduled_payment_id"] == payment["id"] for row in candidates.json())


def test_paid_payment_cannot_be_skipped_or_restored(client):
    setup_user(client)
    recurring, _ = create_recurring(client)
    payment = payments_for(client, recurring["id"])[0]
    paid = client.post(
        f"/api/scheduled-payments/{payment['id']}/mark-paid",
        json={"paid_amount": "134.00"},
    )
    assert paid.status_code == 200
    blocked = client.post(
        f"/api/scheduled-payments/{payment['id']}/skip",
        json={"version": payment["version"]},
    )
    assert blocked.status_code == 409
    restore = client.post(
        f"/api/scheduled-payments/{payment['id']}/restore",
        json={},
    )
    assert restore.status_code == 409


def test_v115_migration_is_additive_and_idempotent(client):
    setup_user(client)
    engine = get_engine()
    ensure_v115_schema(engine)
    ensure_v115_schema(engine)
    with engine.connect() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(scheduled_payments)")).all()}
        version = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
    assert {"skip_reason", "skip_note", "skipped_at", "skipped_by_user_id"}.issubset(columns)
    assert int(version) == 13
