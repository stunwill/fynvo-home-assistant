"""Funding and spending decisions derived from the canonical chronological path."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import text

from .balance_evidence import eligible_balances
from .financial_projection import (
    RULES_VERSION,
    canonical_events,
    input_fingerprint,
    project_events,
)
from .money import cents_to_decimal, parse_money


def funding_window(db, user, start, boundary, starting_balances=None):
    events, issues = canonical_events(db, user, start, boundary)
    evidence = eligible_balances(db, user)
    balances = (
        dict(starting_balances)
        if starting_balances is not None
        else {a: r["accessible_cents"] for a, r in evidence.items()}
    )
    metadata = {
        int(row["id"]): dict(row)
        for row in db.execute(
            text(
                "SELECT id,name,minimum_balance_cents FROM accounts WHERE user_id=:uid"
            ),
            {"uid": user.id},
        ).mappings()
    }
    events = [
        event
        for event in events
        if start.isoformat() <= event["date"] < boundary.isoformat()
        and not (
            starting_balances is not None
            and event["source_type"] == "income"
            and event["date"] == start.isoformat()
        )
    ]
    result = project_events(
        events,
        balances,
        metadata,
        start,
        max(start, boundary - timedelta(days=1)),
        issues,
    )
    donors, requests = [], []
    for account in result["accounts"]:
        aid = account["account_id"]
        buffer = parse_money(account["preferred_buffer"])
        amount = parse_money(account["funding_shortfall"])
        account.update(
            balance_freshness=evidence[aid]["balance_freshness"],
            balance_observed_at=evidence[aid]["balance_observed_at"],
        )
        if amount:
            requests.append(
                {
                    "account_id": aid,
                    "amount": amount,
                    "deadline": account["first_buffer_breach"] or start.isoformat(),
                }
            )
        headroom = max(0, min(balances[aid], account["lowest_balance_cents"]) - buffer)
        if headroom:
            donors.append({"account_id": aid, "remaining": headroom})
    transfers = []
    for request in sorted(requests, key=lambda r: (r["deadline"], r["account_id"])):
        remaining = request["amount"]
        for donor in donors:
            if donor["account_id"] == request["account_id"]:
                continue
            amount = min(remaining, donor["remaining"])
            if amount:
                transfers.append(
                    {
                        "from_account_id": donor["account_id"],
                        "to_account_id": request["account_id"],
                        "from_account_name": metadata[donor["account_id"]]["name"],
                        "to_account_name": metadata[request["account_id"]]["name"],
                        "amount": cents_to_decimal(amount),
                        "required_by": request["deadline"],
                        "applied": False,
                    }
                )
                donor["remaining"] -= amount
                remaining -= amount
        request["unfunded_cents"] = remaining
    result.update(
        input_fingerprint=input_fingerprint(db, user),
        rules_version=RULES_VERSION,
        transfers=transfers,
        unfunded_shortfall=cents_to_decimal(sum(r["unfunded_cents"] for r in requests)),
        balance_evidence=evidence,
        balances=balances,
        assignments_complete=not result["issues"]
        and all(
            e["direction"] == "transfer" or e.get("account_id") in balances
            for e in events
        ),
    )
    return result


def enhance_requirements(db, user, rows, start, boundary, starting_balances=None):
    window = funding_window(db, user, start, boundary, starting_balances)
    projected = {r["account_id"]: r for r in window["accounts"]}
    for row in rows:
        account = projected.get(row["account_id"])
        if not account:
            continue
        shortfall = parse_money(account["funding_shortfall"])
        surplus = max(
            0,
            account["lowest_balance_cents"] - parse_money(account["preferred_buffer"]),
        )
        row.update(
            lowest_projected_balance=account["lowest_balance"],
            lowest_projected_date=account["lowest_balance_date"],
            first_negative_date=account["first_negative_date"],
            funding_deadline=account["first_buffer_breach"],
            funding_shortfall=account["funding_shortfall"],
            recommended_transfer=account["funding_shortfall"],
            funding_surplus=cents_to_decimal(surplus),
            projected_remaining=account["final_balance"],
            balance_after_commitments=account["final_balance"],
            balance_freshness=account["balance_freshness"],
            balance_observed_at=account["balance_observed_at"],
            recommended_transfers=[
                t
                for t in window["transfers"]
                if t["to_account_id"] == row["account_id"]
            ],
            funding_status="needs_transfer" if shortfall else "covered",
        )
        if shortfall:
            row["status"] = "transfer" if starting_balances is not None else "add"
        elif row["status"] in {"add", "transfer"}:
            row["status"] = (
                "already_funded" if starting_balances is not None else "covered"
            )
    return window


def safe_to_spend(base, db, user, current, pay_cycle, error, legacy):
    end = (
        base._as_date((pay_cycle or {}).get("next_income", {}).get("date"))
        if (pay_cycle or {}).get("next_income")
        else None
    )
    if end is None or error:
        return legacy
    if end <= current:
        return {
            **legacy,
            "safe_to_spend": None,
            "incomplete": True,
            "payment_readiness": "needs_information",
            "planning_status": "incomplete",
            "unavailable_reason": {
                "code": "payday_receipt_required",
                "message": "Confirm today's expected income receipt and current balances before relying on Safe to Spend.",
                "action": "accounts",
                "stage": "income",
            },
        }
    window = funding_window(db, user, current, end)
    available = sum(window["balances"].values())
    account_buffers = sum(
        parse_money(r["preferred_buffer"]) for r in window["accounts"]
    )
    extra = base._safe_buffer_cents(db, user)
    reserve = account_buffers + extra
    capacity = min(
        available - reserve, window["lowest_balance"]["balance_cents"] - reserve
    )
    verified = bool(window["balance_evidence"]) and all(
        r["balance_verified"] for r in window["balance_evidence"].values()
    )
    transfer_needed = any(
        parse_money(r["funding_shortfall"]) > 0 for r in window["accounts"]
    )
    complete = verified and window["assignments_complete"]
    readiness = (
        "at_risk"
        if capacity < 0
        else "needs_information"
        if not complete
        else "needs_transfer"
        if transfer_needed
        else "covered"
    )
    safe = capacity if capacity < 0 or readiness == "covered" else None
    commitments = [e for e in window["events"] if e["direction"] == "expense"]
    reason = None
    if not complete:
        reason = {
            "code": "unverified_cash_inputs",
            "message": "Confirm stale balances and assign dated obligations before relying on Safe to Spend.",
            "action": "accounts" if not verified else "payments",
            "stage": "accounts" if not verified else "funding",
        }
    elif transfer_needed:
        reason = {
            "code": "account_transfer_required",
            "message": "Fund the payment Accounts before treating household capacity as available to spend.",
            "action": "accounts",
            "stage": "funding",
        }
    return {
        **legacy,
        "input_fingerprint": window["input_fingerprint"],
        "rules_version": RULES_VERSION,
        "available_cash": cents_to_decimal(available),
        "committed_outgoings": cents_to_decimal(
            -sum(e["amount_cents"] for e in commitments)
        ),
        "protected_buffer": cents_to_decimal(reserve),
        "account_buffers": cents_to_decimal(account_buffers),
        "household_extra_buffer": cents_to_decimal(extra),
        "safe_to_spend": cents_to_decimal(safe) if safe is not None else None,
        "transferable_capacity": cents_to_decimal(capacity),
        "projected_shortfall": cents_to_decimal(max(0, -capacity)),
        "payment_readiness": readiness,
        "incomplete": not complete,
        "planning_status": "complete" if complete else "incomplete",
        "unavailable_reason": reason,
        "funding_action_required": transfer_needed,
        "recommended_transfers": window["transfers"],
        "accounts": window["accounts"],
        "balance_evidence": window["balance_evidence"],
        "payment_coverage": {
            "covered_through": end.isoformat() if readiness == "covered" else None,
            "first_insufficient_date": window["shortfall"]["date"]
            if window["shortfall"]
            else None,
        },
        "reserved_payments": [
            {
                **e,
                "id": e.get("scheduled_payment_id") or e["source_id"],
                "source_type": "scheduled_payment"
                if e.get("scheduled_payment_id")
                and e["source_type"] == "recurring_expense"
                else e["source_type"],
                "due_date": e["date"],
                "expected_date": e["date"],
                "amount": cents_to_decimal(abs(e["amount_cents"])),
                "expected_amount": cents_to_decimal(abs(e["amount_cents"])),
            }
            for e in commitments
        ],
        "coverage": [
            {
                "date": e["date"],
                "name": e["name"],
                "amount": cents_to_decimal(abs(e["amount_cents"])),
                "projected_balance": cents_to_decimal(
                    e["forecast_balance_cents"] - reserve
                ),
            }
            for e in commitments
        ],
        "cash_events": window["events"],
        "integrity_issues": window["issues"] + window["warnings"],
        "warnings": [
            issue.get("code") or issue.get("kind") or "Cash input needs review"
            for issue in window["issues"] + window["warnings"]
        ],
    }
