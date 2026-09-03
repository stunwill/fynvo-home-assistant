# ruff: noqa: I001

import logging

from fastapi import APIRouter

# Import household migrations before v12_extra so the wrapper chain executes
# the base migrations first, then creates the v1.2 household tables, and only
# then applies the dependent v1.2 supplemental migrations.
from . import v12_household as household
from . import v12_extra as extra

logger = logging.getLogger("fynvo.startup")

router = APIRouter(prefix="/household", tags=["household"])
router.add_api_route("/current", household.current_household, methods=["GET"])
router.add_api_route("/current", household.update_household, methods=["PUT"])
router.add_api_route("/members", household.list_members, methods=["GET"])
router.add_api_route("/members", household.create_member, methods=["POST"], status_code=201)
router.add_api_route("/members/{user_id}", household.update_member, methods=["PUT"])
router.add_api_route("/members/{user_id}/deactivate", household.deactivate_member, methods=["POST"])
router.add_api_route("/members/{user_id}/reactivate", household.reactivate_member, methods=["POST"])
router.add_api_route("/members/{user_id}/password-reset", household.reset_member_password, methods=["POST"])
router.add_api_route("/members/{user_id}/mfa-reset", household.reset_member_mfa, methods=["POST"])
router.add_api_route("/members/{user_id}/sessions/revoke", household.revoke_member_sessions, methods=["POST"])
router.add_api_route("/ownership/accounts/{account_id}", household.account_ownership, methods=["GET"])
router.add_api_route("/ownership/accounts/{account_id}", household.update_account_ownership, methods=["PUT"])
router.add_api_route("/me/security", extra.my_household_security, methods=["GET"])
router.add_api_route("/me/change-temporary-password", household.change_temporary_password, methods=["POST"])


@router.post("/client-diagnostics")
def client_diagnostics(payload: dict) -> dict[str, str]:
    stage = str(payload.get("stage") or "unknown")[:80]
    detail = str(payload.get("detail") or "")[:240]
    version = str(payload.get("version") or "unknown")[:40]
    logger.warning("frontend_startup stage=%s version=%s detail=%s", stage, version, detail)
    return {"status": "ok"}
