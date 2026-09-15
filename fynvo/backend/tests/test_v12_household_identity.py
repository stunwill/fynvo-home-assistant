from app.database import get_engine
from sqlalchemy import text


def _setup_admin(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201
    return response.json()


def _create_member(client, username="kristy", role="household_member"):
    response = client.post(
        "/api/household/members",
        json={
            "username": username,
            "display_name": username.title(),
            "role": role,
            "temporary_password": "Temporary123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_setup_admin_gets_initial_household_membership_and_schema_13(client):
    _setup_admin(client)
    household = client.get("/api/household/current")
    assert household.status_code == 200
    payload = household.json()
    assert payload["role"] == "administrator"
    assert payload["member_count"] == 1
    assert payload["currency"] == "AUD"

    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar() == 14
        membership = connection.execute(text("""
            SELECT hm.role, hm.status, u.username
            FROM household_memberships hm JOIN users u ON u.id=hm.user_id
        """)).mappings().one()
        assert membership["role"] == "administrator"
        assert membership["status"] == "active"
        assert membership["username"] == "stu"


def test_admin_can_create_and_manage_household_members_without_exposing_secrets(client):
    _setup_admin(client)
    created = _create_member(client)
    assert created["must_change_password"] is True
    assert created["temporary_password"] == "Temporary123!"

    members = client.get("/api/household/members")
    assert members.status_code == 200
    rows = members.json()
    kristy = next(row for row in rows if row["username"] == "kristy")
    assert kristy["role"] == "household_member"
    assert kristy["status"] == "active"
    assert "password_hash" not in kristy
    assert "temporary_password" not in kristy
    assert "session_token" not in kristy
    assert "mfa_secret" not in kristy

    updated = client.put(
        f"/api/household/members/{created['user_id']}",
        json={"display_name": "Kristy Williams", "role": "read_only"},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "read_only"

    reset = client.post(
        f"/api/household/members/{created['user_id']}/password-reset",
        json={"temporary_password": "Replacement123!"},
    )
    assert reset.status_code == 200
    assert reset.json()["user_id"] == created["user_id"]
    assert reset.json()["temporary_password"] == "Replacement123!"

    deactivated = client.post(f"/api/household/members/{created['user_id']}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"

    reactivated = client.post(f"/api/household/members/{created['user_id']}/reactivate")
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


def test_username_uniqueness_is_case_and_whitespace_safe(client):
    _setup_admin(client)
    _create_member(client, "kristy")
    response = client.post(
        "/api/household/members",
        json={
            "username": "  KRISTY  ",
            "display_name": "Duplicate Kristy",
            "role": "household_member",
            "temporary_password": "Temporary123!",
        },
    )
    assert response.status_code == 409
    assert "already in use" in response.json()["detail"]


def test_only_active_administrator_cannot_be_demoted_or_deactivated(client):
    _setup_admin(client)
    current = client.get("/api/household/current").json()
    user_id = current["user"]["id"]

    demote = client.put(
        f"/api/household/members/{user_id}",
        json={"display_name": "Stu", "role": "household_member"},
    )
    assert demote.status_code == 409

    deactivate = client.post(f"/api/household/members/{user_id}/deactivate")
    assert deactivate.status_code == 409


def test_second_administrator_allows_first_administrator_role_change(client):
    _setup_admin(client)
    first_admin_id = client.get("/api/household/current").json()["user"]["id"]
    _create_member(client, "secondadmin", "administrator")

    response = client.put(
        f"/api/household/members/{first_admin_id}",
        json={"display_name": "Stu", "role": "household_member"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "household_member"


def test_household_rename_keeps_stable_identity(client):
    _setup_admin(client)
    before = client.get("/api/household/current").json()
    response = client.put("/api/household/current", json={"name": "Williams Household"})
    assert response.status_code == 200
    after = response.json()
    assert after["id"] == before["id"]
    assert after["name"] == "Williams Household"


def test_new_accounts_receive_household_ownership_metadata(client):
    _setup_admin(client)
    account = client.post(
        "/api/accounts",
        json={
            "name": "Kristy ING",
            "account_type": "transaction",
            "institution": "ING",
            "opening_balance": "100.00",
        },
    )
    assert account.status_code == 201
    account_id = account.json()["id"]

    ownership = client.get(f"/api/household/ownership/accounts/{account_id}")
    assert ownership.status_code == 200
    assert ownership.json()["visibility"] == "household_shared"
    assert ownership.json()["record_type"] == "account"


def test_account_ownership_distinguishes_owner_from_actor(client):
    _setup_admin(client)
    member = _create_member(client)
    account = client.post(
        "/api/accounts",
        json={
            "name": "Shared Savings",
            "account_type": "savings",
            "institution": "ING",
            "opening_balance": "0.00",
        },
    ).json()

    response = client.put(
        f"/api/household/ownership/accounts/{account['id']}",
        json={"owner_user_id": member["user_id"], "visibility": "household_shared"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["owner_user_id"] == member["user_id"]
    assert payload["updated_by_user_id"] != member["user_id"]


def test_household_security_state_uses_authenticated_identity(client):
    _setup_admin(client)
    response = client.get("/api/household/me/security")
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "administrator"
    assert payload["membership_status"] == "active"
    assert payload["must_change_password"] is False
    assert isinstance(payload["active_session_count"], int)
