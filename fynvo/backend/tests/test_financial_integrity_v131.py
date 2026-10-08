from datetime import date

import pytest
from app import finance, forecast, payment_planning
from app.balance_evidence import ensure_schema, observe, resolve
from app.database import get_engine, get_session_factory
from app.financial_projection import project_events
from app.models import Account
from sqlalchemy import text

TODAY = date(2026, 9, 15)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(finance, "today_local", lambda: TODAY)
    monkeypatch.setattr(payment_planning, "today_local", lambda: TODAY)
    monkeypatch.setattr(forecast, "today_local", lambda: TODAY)


def setup(client):
    assert (
        client.post(
            "/api/auth/setup",
            json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
        ).status_code
        == 201
    )


def account(client, name="Bills", balance="100", kind="transaction"):
    response = client.post(
        "/api/accounts",
        json={"name": name, "account_type": kind, "opening_balance": balance},
    )
    assert response.status_code == 201, response.text
    return response.json()


def salary(client, aid):
    response = client.post(
        "/api/income",
        json={
            "name": "Salary",
            "amount": "2000",
            "frequency": "fortnightly",
            "next_payment_date": "2026-09-20",
            "destination_account_id": aid,
        },
    )
    assert response.status_code == 201, response.text


def bill(client, aid, amount="200", **extra):
    response = client.post(
        "/api/bills",
        json={
            "name": "Electricity",
            "amount": amount,
            "due_date": "2026-09-18",
            "account_id": aid,
            "payment_method": "bpay",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def tx(client, aid, day="2026-09-16", amount="20"):
    response = client.post(
        "/api/transactions",
        json={
            "account_id": aid,
            "date": day,
            "amount": amount,
            "transaction_type": "expense",
            "description": "Dated expense",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_positive_household_capacity_requires_destination_funding(client):
    setup(client)
    bills = account(client)
    savings = account(client, "Savings", "1000", "savings")
    salary(client, savings["id"])
    bill(client, bills["id"])
    client.put(f"/api/accounts/{bills['id']}/preferred-buffer", json={"amount": "50"})
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    assert safe["safe_to_spend"] is None
    assert safe["transferable_capacity"] == "850.00"
    assert safe["payment_readiness"] == "needs_transfer"
    assert safe["protected_buffer"] == "50.00"
    transfer = safe["recommended_transfers"][0]
    assert transfer["amount"] == "150.00"
    assert transfer["required_by"] == "2026-09-18"
    assert transfer["applied"] is False
    assert transfer["from_account_id"] == savings["id"]
    assert transfer["to_account_name"] == "Bills"
    forecast = client.get("/api/forecast?horizon=7d").json()
    assert forecast["reconciles"] is True
    projected = next(a for a in forecast["accounts"] if a["account_id"] == bills["id"])
    assert projected["lowest_balance"] == "-100.00"
    assert projected["first_negative_date"] == "2026-09-18"


def test_future_transaction_does_not_reduce_actual_twice(client):
    setup(client)
    a = account(client)
    tx(client, a["id"])
    assert client.get("/api/accounts").json()[0]["current_balance"] == "100.00"
    forecast = client.get("/api/forecast?horizon=7d").json()
    assert forecast["starting_balance"] == "100.00"
    assert forecast["final_balance"] == "80.00"
    assert (
        len([e for e in forecast["events"] if e["source_type"] == "transaction"]) == 1
    )


def test_rescheduled_occurrence_bill_has_one_remaining_cash_effect(client):
    setup(client)
    a = account(client, balance="500")
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Power",
            "amount": "100",
            "frequency": "monthly",
            "next_due_date": "2026-09-18",
            "account_id": a["id"],
        },
    ).json()
    scheduled = next(
        r
        for r in client.get("/api/scheduled-payments").json()
        if r["recurring_expense_id"] == recurring["id"]
    )
    b = bill(
        client,
        a["id"],
        "120",
        recurring_expense_id=recurring["id"],
        scheduled_payment_id=scheduled["id"],
    )
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "UPDATE scheduled_payments SET expected_date='2026-09-19' WHERE id=:id"
            ),
            {"id": scheduled["id"]},
        )
        connection.execute(
            text("UPDATE bills SET remaining_amount_cents=4000 WHERE id=:id"),
            {"id": b["id"]},
        )
    forecast = client.get("/api/forecast?horizon=7d").json()
    obligations = [
        e
        for e in forecast["events"]
        if e["source_type"] in {"bill", "recurring_expense"}
    ]
    assert len(obligations) == 1
    assert obligations[0]["amount"] == "-40.00"
    assert obligations[0]["scheduled_payment_id"] == scheduled["id"]
    assert forecast["final_balance"] == "460.00"


def test_provider_observation_remains_authoritative_over_history(client):
    setup(client)
    a = account(client)
    tx(client, a["id"], "2026-09-14")
    with get_session_factory()() as db:
        obj = db.get(Account, a["id"])
        observe(db, obj, 12500, source="redbark", available=11000)
        db.commit()
    tx(client, a["id"], "2026-09-13", "50")
    row = client.get("/api/accounts").json()[0]
    assert row["current_balance"] == "125.00"
    assert row["accessible_balance"] == "110.00"
    assert row["balance_source"] == "redbark"
    with get_engine().begin() as connection:
        connection.execute(
            text("UPDATE accounts SET connection_status='error' WHERE id=:id"),
            {"id": a["id"]},
        )
    row = client.get("/api/accounts").json()[0]
    assert row["current_balance"] == "125.00"
    assert row["balance_verified"] is False


def test_manual_confirmation_preserves_history_and_late_import_requires_review(client):
    setup(client)
    a = account(client)
    assert (
        client.post(
            f"/api/accounts/{a['id']}/confirm-balance", json={"amount": "100"}
        ).status_code
        == 200
    )
    with get_engine().connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM transactions")).scalar() == 0
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM balance_observations")
            ).scalar()
            == 2
        )
    t = tx(client, a["id"], "2026-09-13")
    with get_engine().begin() as connection:
        connection.execute(
            text("UPDATE transactions SET source='csv' WHERE id=:id"), {"id": t["id"]}
        )
    row = client.get("/api/accounts").json()[0]
    assert row["current_balance"] == "100.00"
    assert row["balance_freshness"] == "needs_confirmation"


def test_edit_covered_transaction_requires_confirmation(client):
    setup(client)
    a = account(client)
    t = tx(client, a["id"], "2026-09-14")
    client.post(f"/api/accounts/{a['id']}/confirm-balance", json={"amount": "80"})
    with get_engine().begin() as connection:
        connection.execute(
            text("UPDATE transactions SET transaction_date='2026-09-17' WHERE id=:id"),
            {"id": t["id"]},
        )
    row = client.get("/api/accounts").json()[0]
    assert row["current_balance"] == "80.00"
    assert row["balance_freshness"] == "needs_confirmation"


def test_donor_capacity_not_reused_for_multiple_shortfalls(client):
    setup(client)
    first = account(client, "Bills A", "0")
    second = account(client, "Bills B", "0")
    donor = account(client, "Savings", "100", "savings")
    salary(client, donor["id"])
    bill(client, first["id"], "80")
    bill(client, second["id"], "80")
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    assert safe["safe_to_spend"] == "-60.00"
    assert sum(float(t["amount"]) for t in safe["recommended_transfers"]) == 100


def event(key, day, amount, aid=1, direction="expense", **extra):
    return {
        "event_key": key,
        "date": day,
        "name": key,
        "amount_cents": amount,
        "account_id": aid,
        "direction": direction,
        **extra,
    }


def test_chronology_preserves_shortfall_before_later_income_and_deduplicates_identity():
    events = [
        event("rent", "2026-09-16", -20000),
        event("rent", "2026-09-16", -20000),
        event("pay", "2026-09-17", 30000, direction="income"),
    ]
    result = project_events(
        events,
        {1: 10000},
        {1: {"name": "Bills", "minimum_balance_cents": 5000}},
        TODAY,
        date(2026, 9, 20),
    )
    assert result["final_balance"] == "200.00"
    assert result["accounts"][0]["funding_shortfall"] == "150.00"
    assert result["accounts"][0]["first_buffer_breach"] == "2026-09-16"
    assert len(result["events"]) == 2


@pytest.mark.parametrize("to_id,expected", [(2, "150.00"), (3, "100.00")])
def test_transfer_conserves_cash_only_inside_eligible_perimeter(to_id, expected):
    transfer = event(
        "move",
        "2026-09-16",
        0,
        direction="transfer",
        transfer_amount_cents=5000,
        from_account_id=1,
        to_account_id=to_id,
    )
    result = project_events(
        [transfer],
        {1: 10000, 2: 5000},
        {1: {"name": "Bills"}, 2: {"name": "Savings"}},
        TODAY,
        date(2026, 9, 20),
    )
    assert result["final_balance"] == expected
    assert result["reconciles"] is True


def test_migration_idempotent_and_backup_preserves_preupgrade_records(client):
    import sqlite3
    from pathlib import Path

    setup(client)
    a = account(client)
    tx(client, a["id"], "2026-09-14")
    engine = get_engine()
    # Recreate the actual v18 schema around existing financial records.
    backup = Path(str(engine.url.database) + ".pre-v19.sqlite3")
    backup.unlink()
    with engine.begin() as connection:
        connection.execute(text("DROP TRIGGER bill_occurrence_update_guard"))
        connection.execute(text("DROP TRIGGER bill_occurrence_insert_guard"))
        connection.execute(text("DROP TABLE balance_observations"))
        connection.execute(text("DROP INDEX idx_bill_occurrence_link"))
        connection.execute(text("ALTER TABLE bills DROP COLUMN scheduled_payment_id"))
        connection.execute(text("UPDATE schema_version SET version=18"))
    ensure_schema(engine)
    ensure_schema(engine)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
            == 19
        )
        assert (
            connection.execute(text("SELECT count(*) FROM transactions")).scalar() == 1
        )
    backup = Path(str(engine.url.database) + ".pre-v19.sqlite3")
    assert backup.is_file()
    with sqlite3.connect(backup) as old:
        assert old.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (
            old.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 18
        )


def test_available_balance_caps_cash_without_including_credit_limit(client):
    setup(client)
    a = account(client)
    with get_session_factory()() as db:
        obj = db.get(Account, a["id"])
        observe(db, obj, 10000, source="redbark", available=50000)
        db.commit()
        assert resolve(db, obj)["accessible_cents"] == 10000
    account(client, "Credit", "10000", "credit_card")
    assert client.get("/api/forecast?horizon=7d").json()["starting_balance"] == "100.00"


def test_fingerprints_match_across_cash_scopes_and_change_with_balance(client):
    setup(client)
    a = account(client, balance="500")
    salary(client, a["id"])
    bill(client, a["id"])
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    forecast = client.get("/api/forecast?horizon=365d").json()
    assert safe["input_fingerprint"] == forecast["input_fingerprint"]
    assert safe["rules_version"] == forecast["rules_version"]
    client.post(f"/api/accounts/{a['id']}/confirm-balance", json={"amount": "600"})
    assert (
        client.get("/api/payment-planning/safe-to-spend").json()["input_fingerprint"]
        != safe["input_fingerprint"]
    )


def test_unknown_obligation_amount_never_claims_positive_safe_cash(client):
    setup(client)
    a = account(client, balance="500")
    salary(client, a["id"])
    bill(client, a["id"], None)
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    assert safe["safe_to_spend"] is None
    assert safe["incomplete"] is True
    assert any(
        issue.get("code") == "incomplete_obligation"
        for issue in safe["integrity_issues"]
    )


def test_explicit_duplicate_bill_link_rejected_without_deleting_first(client):
    setup(client)
    a = account(client)
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Power",
            "amount": "100",
            "frequency": "monthly",
            "next_due_date": "2026-09-18",
            "account_id": a["id"],
        },
    ).json()
    occurrence = next(
        r
        for r in client.get("/api/scheduled-payments").json()
        if r["recurring_expense_id"] == recurring["id"]
    )
    first = bill(client, a["id"], scheduled_payment_id=occurrence["id"])
    duplicate = client.post(
        "/api/bills",
        json={
            "name": "Duplicate",
            "amount": "200",
            "due_date": "2026-09-18",
            "account_id": a["id"],
            "scheduled_payment_id": occurrence["id"],
        },
    )
    assert duplicate.status_code == 409
    assert client.get(f"/api/bills/{first['id']}").status_code == 200


def test_stale_bank_cash_cannot_become_positive_safe_to_spend(client):
    setup(client)
    a = account(client, balance="500")
    salary(client, a["id"])
    with get_session_factory()() as db:
        observe(
            db,
            db.get(Account, a["id"]),
            50000,
            source="redbark",
            observed_at="2026-01-01T00:00:00",
        )
        db.commit()
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    assert safe["safe_to_spend"] is None
    assert safe["payment_readiness"] == "needs_information"
    assert safe["available_cash"] == "500.00"


def test_negative_opening_cash_is_first_shortfall_even_without_events():
    result = project_events([], {1: -1000}, {1: {"name": "Bills"}}, TODAY, TODAY)
    assert result["shortfall"]["date"] == TODAY.isoformat()
    assert result["accounts"][0]["first_negative_date"] == TODAY.isoformat()


def test_accepted_past_income_receipt_does_not_retire_next_weekly_income(client):
    setup(client)
    a = account(client)
    income = client.post(
        "/api/income",
        json={
            "name": "Weekly",
            "amount": "100",
            "frequency": "weekly",
            "next_payment_date": "2026-09-14",
            "destination_account_id": a["id"],
        },
    ).json()
    received = client.post(
        "/api/transactions",
        json={
            "account_id": a["id"],
            "date": "2026-09-14",
            "amount": "100",
            "transaction_type": "income",
            "description": "Weekly received",
        },
    ).json()
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO reconciliation_links(user_id,transaction_id,source_type,source_id,status,confidence,created_at,updated_at) SELECT user_id,id,'income',:iid,'matched','confirmed',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM transactions WHERE id=:txid"
            ),
            {"iid": income["id"], "txid": received["id"]},
        )
    result = client.get("/api/forecast?horizon=7d").json()
    assert any(
        e["source_type"] == "income" and e["date"] == "2026-09-21"
        for e in result["events"]
    )


def test_large_history_365_day_forecast_remains_bounded(client):
    from time import perf_counter

    setup(client)
    a = account(client, balance="10000")
    salary(client, a["id"])
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO transactions(user_id,account_id,transaction_date,amount_cents,transaction_type,description,source,status,reconciliation_state,created_at,updated_at) VALUES(1,:aid,'2026-09-01',-1,'expense','Historical expense','csv','posted','unmatched',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            ),
            [{"aid": a["id"]} for _ in range(10000)],
        )
    started = perf_counter()
    result = client.get("/api/forecast?horizon=365d")
    assert result.status_code == 200, result.text
    assert result.json()["reconciles"] is True
    assert perf_counter() - started < 5


def test_database_guards_observation_mutation(client):
    from sqlalchemy.exc import IntegrityError

    setup(client)
    a = account(client)
    with get_engine().begin() as connection, pytest.raises(IntegrityError, match="immutable"):
        connection.execute(text("UPDATE balance_observations SET current_cents=0 WHERE account_id=:id"), {"id": a["id"]})
    assert client.get("/api/accounts").json()[0]["current_balance"] == "100.00"
