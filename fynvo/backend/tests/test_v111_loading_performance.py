from datetime import date
from time import perf_counter


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code in {200, 201}


def test_recurring_rules_remain_fast_and_scheduled_generation_is_idempotent(client):
    setup_user(client)
    account = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "5000"},
    ).json()

    today = date.today().isoformat()
    for index in range(25):
        created = client.post(
            "/api/recurring-expenses",
            json={
                "name": f"Recurring {index + 1}",
                "amount": f"{25 + index}.00",
                "frequency": "monthly",
                "next_due_date": today,
                "account_id": account["id"],
                "category": "Utilities",
                "payee_merchant": f"Merchant {index + 1}",
            },
        )
        assert created.status_code in {200, 201}, created.text

    recurring_started = perf_counter()
    recurring = client.get("/api/recurring-expenses")
    recurring_elapsed = perf_counter() - recurring_started
    assert recurring.status_code == 200
    assert len(recurring.json()) >= 25
    assert recurring_elapsed < 2.0

    first_started = perf_counter()
    first = client.get("/api/scheduled-payments")
    first_elapsed = perf_counter() - first_started
    assert first.status_code == 200, first.text
    first_rows = first.json()
    first_ids = {row["id"] for row in first_rows}
    assert first_ids

    second_started = perf_counter()
    second = client.get("/api/scheduled-payments")
    second_elapsed = perf_counter() - second_started
    assert second.status_code == 200, second.text
    second_rows = second.json()
    second_ids = {row["id"] for row in second_rows}

    print(
        "v1.11 loading timings: "
        f"recurring={recurring_elapsed:.4f}s, "
        f"scheduled_initial={first_elapsed:.4f}s, "
        f"scheduled_unchanged={second_elapsed:.4f}s, "
        f"scheduled_rows={len(first_rows)}"
    )

    assert second_ids == first_ids
    assert len(second_rows) == len(first_rows)
    assert first_elapsed < 2.0
    assert second_elapsed < 1.0
