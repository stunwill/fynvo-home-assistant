from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session as DbSession

from .models import User
from .planning_resilience import run_stage


def install(base) -> None:
    """Install v1.25.1 resilience wrappers without creating a second planning engine."""
    original_income_events = base._income_events
    original_planned_spending_rows = base._planned_spending_rows
    original_active_liquid_cash = base._active_liquid_cash
    original_account_pay_cycle_requirements = base._account_pay_cycle_requirements

    def income_events(db: DbSession, user: User, start: date, end: date):
        return run_stage("income", user.id, lambda: original_income_events(db, user, start, end))

    def planned_spending_rows(db: DbSession, user: User):
        return run_stage("planned_spending", user.id, lambda: original_planned_spending_rows(db, user))

    def active_liquid_cash(db: DbSession, user: User):
        return run_stage("accounts", user.id, lambda: original_active_liquid_cash(db, user))

    def account_pay_cycle_requirements(commitments, db: DbSession, user: User, **kwargs):
        return run_stage(
            "funding",
            user.id,
            lambda: original_account_pay_cycle_requirements(commitments, db, user, **kwargs),
        )

    base._income_events = income_events
    base._planned_spending_rows = planned_spending_rows
    base._active_liquid_cash = active_liquid_cash
    base._account_pay_cycle_requirements = account_pay_cycle_requirements

    from . import payment_planning_v1251

    base.build_safe_to_spend = lambda db, user, today=None: payment_planning_v1251.build_safe_to_spend(
        base, db, user, today
    )
    base.build_payment_planning = lambda db, user, today=None: payment_planning_v1251.build_payment_planning(
        base, db, user, today
    )
