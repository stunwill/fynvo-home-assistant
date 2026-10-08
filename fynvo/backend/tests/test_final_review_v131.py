from datetime import date

import pytest
from app import finance, forecast, payment_planning
from app.balance_evidence import ensure_schema
from app.database import get_engine
from sqlalchemy import event, text

TODAY = date(2026, 12, 28)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    for module in (finance, forecast, payment_planning):
        monkeypatch.setattr(module, "today_local", lambda: TODAY)


def setup(client, balance="500"):
    assert (
        client.post(
            "/api/auth/setup",
            json={
                "username": "reviewer",
                "display_name": "Reviewer",
                "password": "Password123!",
            },
        ).status_code
        == 201
    )
    return client.post(
        "/api/accounts",
        json={
            "name": "Bills",
            "account_type": "transaction",
            "opening_balance": balance,
        },
    ).json()["id"]


def income(client, aid, day="2026-12-28", frequency="weekly"):
    response = client.post(
        "/api/income",
        json={
            "name": "Salary",
            "amount": "1000",
            "frequency": frequency,
            "next_payment_date": day,
            "destination_account_id": aid,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def bill(client, aid, amount="600", day="2026-12-28", **extra):
    response = client.post(
        "/api/bills",
        json={
            "name": "Mortgage",
            "amount": amount,
            "due_date": day,
            "account_id": aid,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_today_payday_cannot_hide_today_obligation(client):
    aid = setup(client)
    income(client, aid)
    bill(client, aid)
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    assert safe["safe_to_spend"] is None or float(safe["safe_to_spend"]) <= 0, safe


def test_received_today_income_is_not_next_payday_again(client):
    aid = setup(client)
    iid = income(client, aid)
    tx = client.post(
        "/api/transactions",
        json={
            "account_id": aid,
            "date": TODAY.isoformat(),
            "amount": "1000",
            "transaction_type": "income",
            "description": "Received salary",
        },
    ).json()
    with get_engine().begin() as c:
        c.execute(
            text(
                "INSERT INTO reconciliation_links(user_id,transaction_id,source_type,source_id,status,confidence,created_at,updated_at) SELECT user_id,id,'income',:iid,'matched','confirmed',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM transactions WHERE id=:tid"
            ),
            {"iid": iid, "tid": tx["id"]},
        )
    bill(client, aid, "600", "2026-12-30")
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    assert safe["planning_end"] == "2027-01-04", safe
    assert safe["safe_to_spend"] == "900.00", safe


def downgrade_to_v18():
    engine = get_engine()
    with engine.begin() as c:
        c.execute(text("DROP TRIGGER bill_occurrence_update_guard"))
        c.execute(text("DROP TRIGGER bill_occurrence_insert_guard"))
        c.execute(text("DROP TABLE balance_observations"))
        c.execute(text("DROP INDEX idx_bill_occurrence_link"))
        c.execute(text("ALTER TABLE bills DROP COLUMN scheduled_payment_id"))
        c.execute(text("UPDATE schema_version SET version=18"))
    return engine


def test_failed_migration_rolls_back_all_schema_changes(client):
    setup(client)
    engine = downgrade_to_v18()

    def fail_late(connection, cursor, statement, parameters, context, executemany):
        if "CREATE INDEX IF NOT EXISTS idx_balance_observation_account" in statement:
            raise RuntimeError("Injected migration failure")

    event.listen(engine, "before_cursor_execute", fail_late)
    try:
        with pytest.raises(RuntimeError, match="Injected migration failure"):
            ensure_schema(engine)
    finally:
        event.remove(engine, "before_cursor_execute", fail_late)
    with engine.connect() as c:
        assert c.execute(text("SELECT MAX(version) FROM schema_version")).scalar() == 18
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='balance_observations'"
                )
            ).scalar()
            == 0
        )
        assert c.execute(text("SELECT count(*) FROM accounts")).scalar() == 1
    ensure_schema(engine)


def test_late_historical_manual_income_cannot_inflate_confirmed_cash(client):
    aid = setup(client)
    client.post(f"/api/accounts/{aid}/confirm-balance", json={"amount": "500"})
    client.post(
        "/api/transactions",
        json={
            "account_id": aid,
            "date": "2026-12-27",
            "amount": "100",
            "transaction_type": "income",
            "description": "Old income entered late",
        },
    )
    row = client.get("/api/accounts").json()[0]
    assert row["current_balance"] == "500.00", row
    assert row["balance_verified"] is False, row


@pytest.mark.parametrize("kind", ["recurring", "planned"])
def test_active_obligation_without_date_blocks_positive_spendable_cash(client, kind):
    aid = setup(client)
    income(client, aid, "2027-01-04")
    if kind == "recurring":
        created = client.post(
            "/api/recurring-expenses",
            json={
                "name": "Unknown due date",
                "amount": "100",
                "frequency": "monthly",
                "account_id": aid,
            },
        )
    else:
        created = client.post(
            "/api/planned-spending",
            json={
                "name": "Unknown due date",
                "estimated_amount": "100",
                "status": "committed",
                "account_id": aid,
                "include_in_forecast": True,
            },
        )
    assert created.status_code == 201, created.text
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    assert safe["safe_to_spend"] is None
    assert safe["incomplete"] is True


@pytest.mark.parametrize("case", range(1, 13))
def test_controlled_financial_acceptance_scenarios(client, case):
    from app.balance_evidence import observe
    from app.database import get_session_factory
    from app.models import Account

    initial = "100" if case == 2 or case == 8 else "1000"
    aid = setup(client, initial)
    iid = income(client, aid, "2027-01-04")
    bill_id = None
    expected_safe = "400.00"
    expected_low = "400.00"
    expected_required = "0.00"
    expected_total = "400.00"
    if case in (1, 9, 10, 11):
        bill_id = bill(client, aid, "600", "2026-12-30")
    elif case in (2, 8):
        savings = client.post(
            "/api/accounts",
            json={
                "name": "Savings",
                "account_type": "savings",
                "opening_balance": "1000",
            },
        ).json()["id"]
        client.put(f"/api/accounts/{aid}/preferred-buffer", json={"amount": "50"})
        bill_id = bill(client, aid, "200", "2026-12-30")
        expected_safe = None if case == 2 else "850.00"
        expected_low = "-100.00" if case == 2 else "50.00"
        expected_required = "150.00" if case == 2 else "0.00"
        expected_total = "900.00"
        if case == 8:
            response = client.post(
                "/api/transfers",
                json={
                    "from_account_id": savings,
                    "to_account_id": aid,
                    "amount": "150",
                    "date": "2026-12-29",
                    "description": "Fund Bills",
                },
            )
            assert response.status_code == 201, response.text
    elif case in (3, 5):
        recurring = client.post(
            "/api/recurring-expenses",
            json={
                "name": "Mortgage",
                "amount": "600",
                "frequency": "monthly",
                "next_due_date": "2026-12-30",
                "account_id": aid,
            },
        ).json()["id"]
        sid = next(
            r["id"]
            for r in client.get("/api/scheduled-payments").json()
            if r["recurring_expense_id"] == recurring
        )
        bill_id = bill(
            client,
            aid,
            "600",
            "2026-12-30",
            recurring_expense_id=recurring,
            scheduled_payment_id=sid,
        )
        if case == 5:
            with get_engine().begin() as c:
                c.execute(
                    text(
                        "UPDATE scheduled_payments SET expected_date='2027-01-01' WHERE id=:id"
                    ),
                    {"id": sid},
                )
            response = client.put(
                f"/api/bills/{bill_id}", json={"due_date": "2027-01-01"}
            )
            assert response.status_code == 200, response.text
    elif case == 4:
        bill_id = bill(client, aid, "600", "2026-12-30")
        with get_engine().begin() as c:
            c.execute(
                text("UPDATE bills SET remaining_amount_cents=20000 WHERE id=:id"),
                {"id": bill_id},
            )
        expected_safe = expected_low = expected_total = "800.00"
    elif case == 6:
        response = client.post(
            "/api/planned-spending",
            json={
                "name": "Plumber",
                "estimated_amount": "600",
                "planned_date": "2026-12-30",
                "status": "committed",
                "account_id": aid,
                "include_in_forecast": True,
            },
        )
        assert response.status_code == 201, response.text
    elif case == 7:
        bill_id = bill(client, aid, "600", "2026-12-30")
        with get_engine().begin() as c:
            c.execute(
                text("UPDATE bills SET original_status='estimated' WHERE id=:id"),
                {"id": bill_id},
            )
    elif case == 12:
        second = client.post(
            "/api/accounts",
            json={
                "name": "Savings",
                "account_type": "savings",
                "opening_balance": "500",
            },
        ).json()["id"]
        client.put(f"/api/accounts/{aid}/preferred-buffer", json={"amount": "100"})
        client.put(f"/api/accounts/{second}/preferred-buffer", json={"amount": "200"})
        bill_id = bill(client, aid, "600", "2026-12-30")
        expected_safe = "600.00"
        expected_total = "900.00"
    if case == 9:
        assert (
            client.put(
                f"/api/income/{iid}", json={"next_payment_date": "2027-01-08"}
            ).status_code
            == 200
        )
    if case == 10:
        with get_session_factory()() as db:
            observe(db, db.get(Account, aid), 100000, source="redbark")
            db.commit()
        with get_engine().begin() as c:
            c.execute(
                text("UPDATE accounts SET connection_status='error' WHERE id=:id"),
                {"id": aid},
            )
        expected_safe = None
    if case == 11:
        before = client.get("/api/accounts").json()[0]["balance_observation_id"]
        assert (
            client.post(
                f"/api/accounts/{aid}/confirm-balance", json={"amount": "1000"}
            ).status_code
            == 200
        )
        assert client.get("/api/accounts").json()[0]["balance_observation_id"] > before
        with get_engine().connect() as c:
            assert c.execute(text("SELECT count(*) FROM transactions")).scalar() == 0
    safe = client.get("/api/payment-planning/safe-to-spend").json()
    projection = client.get("/api/forecast?horizon=7d").json()
    account_projection = next(
        a for a in projection["accounts"] if a["account_id"] == aid
    )
    assert (
        client.get("/api/accounts").json()[0]["current_balance"]
        == f"{float(initial):.2f}"
    )
    assert account_projection["lowest_balance"] == expected_low
    assert account_projection["funding_shortfall"] == expected_required
    # The existing 7d API horizon includes Jan 4; Safe-to-Spend excludes payday.
    forecast_total = float(expected_total) + (0 if case == 9 else 1000)
    assert projection["final_balance"] == f"{forecast_total:.2f}"
    assert projection["reconciles"] is True
    assert safe["safe_to_spend"] == expected_safe
    if case == 7:
        assert (
            next(e for e in projection["events"] if e["source_type"] == "bill")[
                "confidence"
            ]
            == "estimated"
        )
    if case == 9:
        assert safe["planning_end"] == "2027-01-08"


@pytest.mark.parametrize(
    "frequency,dates",
    [
        ("weekly", ["2026-12-31", "2027-01-07", "2027-01-14"]),
        ("fortnightly", ["2026-12-31", "2027-01-14", "2027-01-28"]),
        ("every_28_days", ["2026-12-31", "2027-01-28", "2027-02-25"]),
        ("monthly", ["2026-12-31", "2027-01-31", "2027-02-28"]),
    ],
)
def test_income_frequency_year_and_short_month_boundaries(client, frequency, dates):
    aid = setup(client)
    income(client, aid, "2026-12-31", frequency)
    results = {}
    for horizon in ("7d", "30d", "90d", "365d"):
        result = client.get(f"/api/forecast?horizon={horizon}").json()
        assert result["reconciles"] is True
        results[horizon] = [
            e["date"] for e in result["events"] if e["source_type"] == "income"
        ]
    assert results["365d"][:3] == dates
    assert results["7d"] == [dates[0]]
    assert results["90d"] == results["365d"][: len(results["90d"])]
