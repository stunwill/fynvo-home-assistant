from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from . import payment_planning
from .auth import get_current_user
from .database import get_db
from .models import User
from .payment_planning_runtime_v1251 import install as install_planning_resilience
from .payment_planning_v1251 import unavailable_account_funding
from .planning_resilience import PLANNING_EXCEPTIONS

install_planning_resilience(payment_planning)

router = APIRouter(tags=["planning-resilience"])
DB = Depends(get_db)
USER = Depends(get_current_user)


@router.get("/payment-planning/v1251")
def payment_planning_v1251(current_user: User = USER, db: DbSession = DB):
    return payment_planning.build_payment_planning(db, current_user)


@router.get("/payment-planning/safe-to-spend/v1251")
def safe_to_spend_v1251(current_user: User = USER, db: DbSession = DB):
    result = payment_planning.build_safe_to_spend(db, current_user)
    if result.get("commitment_scope", {}).get("code") == "generated_horizon":
        # This versioned presentation contract deliberately surfaces reliable
        # partial commitments while the legacy field keeps its pay-cycle meaning.
        result["committed_outgoings"] = result.get("known_commitments", "0.00")
    return result


@router.get("/payment-planning/account-funding/v1251")
def account_funding_v1251(current_user: User = USER, db: DbSession = DB):
    try:
        plan = payment_planning.build_pay_cycle_planning(db, current_user)
    except PLANNING_EXCEPTIONS as exc:
        return unavailable_account_funding(payment_planning, db, current_user, exc)
    return {
        "as_of": plan["as_of"],
        "current_cycle": plan.get("account_funding"),
        "next_cycle": plan.get("payday_allocation"),
        "completeness": plan.get("completeness"),
        "reason": None,
    }
