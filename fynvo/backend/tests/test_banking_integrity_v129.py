"""Account mapping remains transactional while background banking is active."""

from app import banking_v126
from app.database import get_engine
from sqlalchemy import text
from test_banking_lifecycle_v127 import map_url, setup


def test_discovery_mapping_and_disconnect_do_not_race_sync(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    account = connection["accounts"][0]
    with banking_v126._banking_operation(1):
        for method, url, payload in (
            ("post", "/api/bank-connections/redbark/discover", None),
            ("post", map_url(connection, account), {"action": "create"}),
            ("post", f"/api/bank-connections/{connection['id']}/sync", None),
            ("post", f"/api/bank-connections/{connection['id']}/disconnect", None),
            ("delete", "/api/bank-connections/redbark/credentials", None),
        ):
            response = getattr(client, method)(url, **({"json": payload} if payload else {}))
            assert response.status_code == 409, response.text
    assert client.post(map_url(connection, account), json={"action": "create"}).status_code == 200
    with get_engine().connect() as db:
        assert db.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 1


def test_competing_mapping_claim_rolls_back_new_account(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    external = connection["accounts"][0]
    original = banking_v126._create_fynvo_account

    def simulate_competing_claim(db, user, row, payload):
        account_id = original(db, user, row, payload)
        db.execute(text("UPDATE external_accounts SET fynvo_account_id=:id WHERE id=:external"), {"id": account_id, "external": external["id"]})
        return account_id

    monkeypatch.setattr(banking_v126, "_create_fynvo_account", simulate_competing_claim)
    response = client.post(map_url(connection, external), json={"action": "create"})
    assert response.status_code == 409
    with get_engine().connect() as db:
        assert db.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 0
        assert db.execute(text("SELECT fynvo_account_id FROM external_accounts WHERE id=:id"), {"id": external["id"]}).scalar() is None
    assert len(client.get("/api/bank-connections/redbark/status").json()["required_actions"]) == 2


def test_disconnected_account_reports_sync_stopped_without_erasing_history(client, monkeypatch, tmp_path):
    state = setup(client, monkeypatch, tmp_path)
    connection = state["connections"][0]
    external = connection["accounts"][0]
    mapped = client.post(map_url(connection, external), json={"action": "create"}).json()
    assert client.post(f"/api/bank-connections/{connection['id']}/sync").status_code == 200
    before = next(row for row in client.get("/api/accounts").json() if row["id"] == mapped["fynvo_account_id"])
    assert client.post(f"/api/bank-connections/{connection['id']}/disconnect").status_code == 200
    stopped = client.get("/api/bank-connections/redbark/status").json()
    assert stopped["connections"][0]["accounts"][0]["connection_status"] == "disconnected"
    assert stopped["required_actions"] == []
    after = next(row for row in client.get("/api/accounts").json() if row["id"] == mapped["fynvo_account_id"])
    assert after["current_balance"] == before["current_balance"]
    assert len(client.get("/api/transactions").json()) == 1
