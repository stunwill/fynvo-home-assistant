from app.database import get_engine
from sqlalchemy import text


def login(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def account(client):
    return client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "0"}).json()


def add_tx(client, acc, date, amount, description, category=None, tx_type="expense"):
    payload = {"account_id": acc["id"], "date": date, "amount": amount, "transaction_type": tx_type, "description": description}
    if category:
        payload["category"] = category
    return client.post("/api/transactions", json=payload).json()


def test_intelligence_schema_rules_and_merchant_normalisation(client):
    login(client)
    acc = account(client)
    add_tx(client, acc, "2026-05-01", "50", "WOOLWORTHS 1234 MILDURA", "Groceries > Supermarket")
    add_tx(client, acc, "2026-05-08", "61", "WOOLWORTHS MILDURA VIC", "Groceries > Supermarket")

    rule = client.post("/api/intelligence/rules", json={"rule_type": "merchant", "name": "Woolworths", "match_type": "contains", "pattern": "WOOL", "normalised_merchant": "Woolworths", "priority": 10})
    assert rule.status_code == 201
    edited = client.put(f"/api/intelligence/rules/{rule.json()['id']}", json={"pattern": "WOOLWORTHS", "priority": 5})
    assert edited.status_code == 200
    preview = client.post(f"/api/intelligence/rules/{rule.json()['id']}/preview").json()
    assert preview["match_count"] == 2

    result = client.post("/api/intelligence/process")
    assert result.status_code == 200
    merchants = client.get("/api/intelligence/merchants").json()
    assert merchants[0]["merchant"] == "Woolworths"
    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 15


def test_category_suggestions_and_dismissal_suppression(client):
    login(client)
    acc = account(client)
    for day in [1, 8, 15, 22, 29]:
        add_tx(client, acc, f"2026-06-{day:02d}", "45", "WOOLWORTHS MILDURA", "Groceries > Supermarket")
    target = add_tx(client, acc, "2026-07-06", "52", "WOOLWORTHS 9999 MILDURA")

    client.post("/api/intelligence/process")
    suggestions = client.get("/api/intelligence/suggestions").json()
    category = next(item for item in suggestions if item["suggestion_type"] == "category_suggestion" and item["action_payload"].get("transaction_id") == target["id"])
    assert category["confidence"] in {"high", "medium"}
    assert "previous" in category["description"].lower() or category["evidence"]
    assert client.post(f"/api/intelligence/suggestions/{category['id']}/dismiss").status_code == 200
    client.post("/api/intelligence/process")
    remaining = client.get("/api/intelligence/suggestions").json()
    assert all(item["id"] != category["id"] for item in remaining)


def test_recurring_expense_income_and_amount_change_suggestions(client):
    login(client)
    acc = account(client)
    for month, amount in [(1, "140"), (2, "140"), (3, "140"), (4, "140"), (5, "80"), (6, "80")]:
        add_tx(client, acc, f"2026-{month:02d}-01", amount, "TELSTRA SERVICES", "Utilities > Internet")
    for month in [1, 2, 3, 4]:
        add_tx(client, acc, f"2026-{month:02d}-12", "2500", "PAYROLL ACME", "Income > Salary", "income")

    client.post("/api/intelligence/process")
    suggestions = client.get("/api/intelligence/suggestions").json()
    assert any(item["suggestion_type"] == "recurring_expense_detected" for item in suggestions)
    assert any(item["suggestion_type"] == "recurring_income_detected" for item in suggestions)
    assert any(item["suggestion_type"] == "recurring_amount_change" for item in suggestions)

    recurring = next(item for item in suggestions if item["suggestion_type"] == "recurring_expense_detected")
    accepted = client.post(f"/api/intelligence/suggestions/{recurring['id']}/accept")
    assert accepted.status_code == 200
    assert any(row["name"] == recurring["action_payload"]["merchant"] for row in client.get("/api/recurring-expenses").json())


def test_trends_anomalies_and_one_off_exclusion(client):
    login(client)
    acc = account(client)
    for week in range(1, 9):
        add_tx(client, acc, f"2026-06-{week + 1:02d}", "120", "COLES MILDURA", "Groceries > Supermarket")
    for week in range(1, 9):
        add_tx(client, acc, f"2026-08-{week + 1:02d}", "200", "COLES MILDURA", "Groceries > Supermarket")
    high = add_tx(client, acc, "2026-08-15", "610", "POWERSHOP", "Utilities > Electricity")
    for day in [1, 15, 28, 42, 56]:
        month = 1 + (day // 28)
        add_tx(client, acc, f"2026-{month:02d}-10", "280", "POWERSHOP", "Utilities > Electricity")

    client.post("/api/intelligence/process")
    trends = client.get("/api/intelligence/trends").json()
    assert any(item["category"] == "Groceries > Supermarket" and item["state"] == "increasing" for item in trends)
    suggestions = client.get("/api/intelligence/suggestions").json()
    assert any(item["suggestion_type"] == "unusual_spending" for item in suggestions)
    assert client.post(f"/api/intelligence/transactions/{high['id']}/exclude-baseline").status_code == 200
