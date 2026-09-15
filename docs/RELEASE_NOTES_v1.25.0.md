# Fynvo v1.25.0

## Account Funding, Payday Allocation & Balance Management

Fynvo can now answer two separate household cash-flow questions from the same authoritative payment-planning data:

1. Are my accounts covered from today until the next payday?
2. When that payday arrives, how much should I allocate to each account until the following payday?

### What is new

- Accounts shows current-cycle requirements, preferred buffers, shortfalls, coverage and no-payment states.
- Update Balances lets you confirm several real-world account balances and save them atomically in one mobile-first workflow.
- Account Detail explains every canonical commitment behind its target balance and shows balance freshness and monthly context.
- Plan includes Payday Allocation with projected payday balances and exact recommended transfers per account.
- Overview includes a compact payday action summary.
- Unassigned commitments remain visible and actionable instead of being guessed or silently omitted.

### Calculation integrity

- Same-day income is available before same-day commitments, so a payment on payday belongs to the new cycle.
- Current-cycle commitments reduce the projected balance available at payday before next-cycle transfers are recommended.
- Income deposited directly into an account is included at the payday boundary.
- Bill and Scheduled Payment duplicates remain suppressed, and paid, skipped and cancelled commitments remain excluded.
- All stored and calculated money continues to use integer cents.

### Upgrade safety

Schema v14 adds preferred-buffer and balance-freshness support without replacing existing accounts, balances or transactions. Existing account buffers default safely to zero. Home Assistant ingress, `/data` persistence, health endpoints and the prebuilt-image release contract are unchanged.
