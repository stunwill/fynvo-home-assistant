# Fynvo Add-on Changelog

## v1.25.1 - Post-v1.25.0 Production Corrections

- Makes Safe to Spend and Payday Allocation failures specific and actionable instead of collapsing them into generic pay-cycle unavailable messaging.
- Keeps known cash and commitment data visible when planning is incomplete, with the actual fallback commitment horizon shown explicitly.
- Keeps account funding status visible in Accounts even when a pay-cycle dependency fails, and corrects valid Plan Calendar dates that previously rendered as Date unavailable.
- Refines Update Balances with a clear currency affordance, balance-change review and immediate refresh of dependent planning views.
- Hardens release-image/release-source handling while preserving anonymous GHCR verification, supported architectures, ingress, port 8097 and `/data` persistence.
- Preserves canonical recurring occurrence identity and Bill/Scheduled Payment suppression. No database migration is required.

## v1.25.0 - Account Funding, Payday Allocation & Balance Management

- Shows whether every active liquid Account is covered until the next payday and identifies the exact amount to add where it is not.
- Adds mobile-first Update Balances with one atomic save, negative balances, cents, change review and unsaved-change protection.
- Adds Account Detail funding breakdowns, preferred buffers, balance freshness and monthly scheduled-payment context.
- Adds next-cycle Payday Allocation using projected payday balances and canonical payments across calendar-month boundaries.
- Integrates one shared funding result into Accounts, Plan and Overview, with actionable incomplete and unassigned states.
- Migrates existing installations safely to schema v14 without changing stored balances or deleting records.

## v1.24.3 - Post-v1.24.1 Production Corrections

- Aligns Payments Attention counts, badges, totals and displayed rows from the same canonical payment set.
- Ensures Accounts Activity reaches a populated, empty or error state without indefinite loading.
- Corrects Plan Calendar selected-date labelling and exposes actionable Safe to Spend configuration reasons.
- Preserves payment, account, transaction, reconciliation, ingress and `/data` behaviour. No database migration is required.

## v1.24.1 - Core UX Redesign Production Corrections

- Corrects Accounts and Activity loading and terminal states, with scoped errors, retry and deliberate empty states.
- Removes the obsolete mobile Payment Centre presentation around the redesigned Payments workspace.
- Improves Safe to Spend unavailable explanations and configuration follow-up while preserving financial semantics and data.
- Preserves Home Assistant ingress, existing routes, reconciliation and `/data` persistence. No database migration is required.
