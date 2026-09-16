from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

PLANNING_EXCEPTIONS = (SQLAlchemyError, ValueError, KeyError, TypeError, AttributeError)


class PlanningStageError(ValueError):
    """Structured, user-safe wrapper for optional pay-cycle planning failures."""

    def __init__(self, reason: dict[str, Any]):
        super().__init__(str(reason.get("message") or "Planning data is unavailable."))
        self.reason = reason


def reason_for_stage(stage: str) -> dict[str, Any]:
    reasons = {
        "income": {
            "code": "income_schedule_unavailable",
            "message": "Your income schedule could not be read. Review Income or retry the plan.",
            "action": "income",
            "stage": "income",
        },
        "planned_spending": {
            "code": "planned_spending_unavailable",
            "message": "Planned spending could not be read. Retry the plan.",
            "action": "retry",
            "stage": "planned_spending",
        },
        "accounts": {
            "code": "account_balances_unavailable",
            "message": "Account balances could not be read. Review Accounts or retry the plan.",
            "action": "accounts",
            "stage": "accounts",
        },
        "funding": {
            "code": "account_funding_unavailable",
            "message": "Account funding could not be calculated. Review payment funding accounts or retry.",
            "action": "payments",
            "stage": "funding",
        },
        "pay_cycle": {
            "code": "pay_cycle_unavailable",
            "message": "Pay-cycle planning could not be calculated. Retry the plan.",
            "action": "retry",
            "stage": "pay_cycle",
        },
    }
    return dict(reasons.get(stage, reasons["pay_cycle"]))


def run_stage(stage: str, user_id: int, operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except PlanningStageError:
        raise
    except PLANNING_EXCEPTIONS as exc:
        reason = reason_for_stage(stage)
        logger.exception("Pay-cycle planning stage %s failed for user_id=%s", stage, user_id)
        raise PlanningStageError(reason) from exc


def exception_reason(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, PlanningStageError):
        return dict(exc.reason)
    return reason_for_stage("pay_cycle")


def known_commitment_scope(current: date, planning_end: date | None) -> dict[str, Any]:
    if planning_end is not None:
        return {
            "code": "before_next_pay",
            "complete": True,
            "start_date": current.isoformat(),
            "end_date": planning_end.isoformat(),
            "label": "Committed before next pay",
        }
    horizon_end = current + timedelta(days=120)
    return {
        "code": "generated_horizon",
        "complete": False,
        "start_date": current.isoformat(),
        "end_date": horizon_end.isoformat(),
        "label": f"Known commitments to {horizon_end.isoformat()}",
    }
