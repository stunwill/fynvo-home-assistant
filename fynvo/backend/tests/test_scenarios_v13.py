
def setup_user(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_scenarios_are_protected(client):
    assert client.get("/api/scenarios").status_code == 401


def test_create_edit_archive_and_isolate_scenarios(client):
    setup_user(client)
    first = client.post("/api/scenarios", json={"name": "Internet Savings", "forecast_horizon": "90d"})
    assert first.status_code == 201
    scenario_id = first.json()["id"]
    updated = client.put(f"/api/scenarios/{scenario_id}", json={"description": "Cheaper internet", "status": "active"})
    assert updated.status_code == 200
    assert updated.json()["description"] == "Cheaper internet"
    second = client.post("/api/scenarios", json={"name": "New TV", "forecast_horizon": "90d"}).json()
    rows = client.get("/api/scenarios").json()
    assert {row["id"] for row in rows} == {scenario_id, second["id"]}
    assert client.post(f"/api/scenarios/{scenario_id}/archive").status_code == 200
    assert next(row for row in client.get("/api/scenarios").json() if row["id"] == scenario_id)["status"] == "archived"


def test_effective_dated_recurring_amount_change_is_scenario_only(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "5000"}).json()
    recurring = client.post("/api/recurring-expenses", json={"name": "Internet", "amount": "140", "frequency": "monthly", "next_due_date": "2026-08-01", "account_id": account["id"], "category": "Utilities"}).json()
    scenario = client.post("/api/scenarios", json={"name": "Internet Savings", "forecast_horizon": "184d"}).json()
    adjustment = client.post(f"/api/scenarios/{scenario['id']}/adjustments", json={"kind": "change_recurring_expense_amount", "source_type": "recurring_expense", "source_id": recurring["id"], "amount": "80", "effective_from": "2026-10-01"})
    assert adjustment.status_code == 201
    comparison = client.get(f"/api/scenarios/{scenario['id']}/comparison?horizon=184d").json()
    baseline = [(row["date"], row["amount"]) for row in comparison["baseline"]["events"] if row["name"] == "Internet"]
    projected = [(row["date"], row["amount"]) for row in comparison["scenario"]["events"] if row["name"] == "Internet"]
    assert ("2026-09-01", "-140.00") in baseline
    assert ("2026-10-01", "-140.00") in baseline
    assert ("2026-09-01", "-140.00") in projected
    assert ("2026-10-01", "-80.00") in projected
    assert ("2026-11-01", "-80.00") in projected

    baseline_by_date = dict(baseline)
    changed_dates = [when for when, amount in projected if when >= "2026-10-01" and amount == "-80.00"]
    assert changed_dates
    assert all(baseline_by_date[when] == "-140.00" for when in changed_dates)
    assert comparison["difference"] == f"{len(changed_dates) * 60:.2f}"


def test_multiple_scenarios_do_not_cross_contaminate(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "5000"}).json()
    recurring = client.post("/api/recurring-expenses", json={"name": "Internet", "amount": "140", "frequency": "monthly", "next_due_date": "2026-10-01", "account_id": account["id"]}).json()
    a = client.post("/api/scenarios", json={"name": "A", "forecast_horizon": "90d"}).json()
    b = client.post("/api/scenarios", json={"name": "B", "forecast_horizon": "90d"}).json()
    client.post(f"/api/scenarios/{a['id']}/adjustments", json={"kind": "change_recurring_expense_amount", "source_type": "recurring_expense", "source_id": recurring["id"], "amount": "80", "effective_from": "2026-10-01"})
    client.post(f"/api/scenarios/{b['id']}/adjustments", json={"kind": "change_recurring_expense_amount", "source_type": "recurring_expense", "source_id": recurring["id"], "amount": "120", "effective_from": "2026-10-01"})
    ca = client.get(f"/api/scenarios/{a['id']}/comparison?horizon=90d").json()
    cb = client.get(f"/api/scenarios/{b['id']}/comparison?horizon=90d").json()
    assert any(row["name"] == "Internet" and row["amount"] == "-80.00" for row in ca["scenario"]["events"])
    assert any(row["name"] == "Internet" and row["amount"] == "-120.00" for row in cb["scenario"]["events"])
    assert all(row["amount"] == "-140.00" for row in ca["baseline"]["events"] if row["name"] == "Internet")
    assert all(row["amount"] == "-140.00" for row in cb["baseline"]["events"] if row["name"] == "Internet")


def test_one_off_purchase_changes_scenario_but_not_baseline(client):
    setup_user(client)
    client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "4000"})
    scenario = client.post("/api/scenarios", json={"name": "New TV", "forecast_horizon": "365d"}).json()
    client.post(f"/api/scenarios/{scenario['id']}/adjustments", json={"kind": "one_off_expense", "name": "New TV", "amount": "3000", "effective_from": "2026-11-15", "category": "Entertainment"})
    result = client.get(f"/api/scenarios/{scenario['id']}/comparison?horizon=365d").json()
    assert not any(row["name"] == "New TV" for row in result["baseline"]["events"])
    assert any(row["name"] == "New TV" and row["amount"] == "-3000.00" for row in result["scenario"]["events"])
    assert result["difference"] == "-3000.00"
    assert result["scenario"]["lowest_balance"]["balance_cents"] <= result["baseline"]["lowest_balance"]["balance_cents"]


def test_hypothetical_income_change_only_applies_from_effective_date(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"}).json()
    income = client.post("/api/income", json={"name": "Salary", "amount": "7000", "frequency": "monthly", "next_payment_date": "2026-12-01", "destination_account_id": account["id"]}).json()
    scenario = client.post("/api/scenarios", json={"name": "Pay Rise", "forecast_horizon": "184d"}).json()
    client.post(f"/api/scenarios/{scenario['id']}/adjustments", json={"kind": "change_income_amount", "source_type": "income", "source_id": income["id"], "amount": "7500", "effective_from": "2027-01-01"})
    result = client.get(f"/api/scenarios/{scenario['id']}/comparison?horizon=184d").json()
    baseline = [(row["date"], row["amount"]) for row in result["baseline"]["events"] if row["name"] == "Salary"]
    projected = [(row["date"], row["amount"]) for row in result["scenario"]["events"] if row["name"] == "Salary"]
    assert ("2026-12-01", "7000.00") in baseline and ("2026-12-01", "7000.00") in projected
    assert ("2027-01-01", "7000.00") in baseline and ("2027-01-01", "7500.00") in projected


def test_baseline_forecast_without_scenario_is_unchanged(client):
    setup_user(client)
    client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"})
    before = client.get("/api/forecast?horizon=30d").json()
    scenario = client.post("/api/scenarios", json={"name": "Temporary", "forecast_horizon": "30d"}).json()
    client.post(f"/api/scenarios/{scenario['id']}/adjustments", json={"kind": "one_off_expense", "name": "TV", "amount": "300", "effective_from": "2026-08-20"})
    after = client.get("/api/forecast?horizon=30d").json()
    assert before["final_balance"] == after["final_balance"]
    assert before["events"] == after["events"]
