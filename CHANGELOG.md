# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.25.1 - Post-v1.25.0 Production Corrections

- Replaces generic pay-cycle failure messaging with structured, actionable diagnostics for income, balances, funding assignments and transient planning errors while preserving independently known cash and commitment values.
- Labels fallback commitment totals with their actual generated horizon instead of implying that they are necessarily limited to the next payday.
- Keeps Account Funding visible when pay-cycle planning is incomplete or unavailable, and corrects Plan Calendar date handling for real JavaScript Date values.
- Refines Update Balances with clearer currency entry, change review and immediate refresh events for dependent planning surfaces.
- Hardens release-image automation so a tested source ref can be built and verified before version metadata is exposed to Home Assistant, while retaining anonymous GHCR verification and all supported architectures.
- Preserves canonical Bill/Scheduled Payment suppression, recurring occurrence identity, terminal-state exclusions, cards, reconciliation, ingress and `/data` persistence. No database migration is required.

## v1.25.0 - Account Funding, Payday Allocation & Balance Management

- Adds one authoritative account-funding calculation for the current cycle and the next payday-to-payday cycle, with explicit dates and traceable canonical commitments.
- Adds fast, atomic bulk balance updates with negative and cent-precision support, freshness timestamps, retained input on errors and immediate planning refresh.
- Completes preferred per-account buffers using the existing minimum-balance model and exposes funding status, breakdowns and monthly context in Accounts and Account Detail.
- Adds Payday Allocation to Plan and a compact Overview summary, including projected payday balances, per-account transfer recommendations and actionable unassigned commitments.
- Preserves same-day income-before-payment ordering, Bill/Scheduled Payment suppression, terminal-state exclusions, planned spending, card-derived funding accounts, Safe-to-Spend and Home Assistant ingress.
- Adds a safe schema v14 forward migration for balance freshness fields while preserving existing accounts and balances.

## v1.24.3 - Post-v1.24.1 Production Corrections

- Corrects Payments Attention so badges, summaries, totals and rows share one source of truth.
- Prevents Accounts Activity from being held in a skeleton by parent background refreshes, while preserving reconciliation.
- Keeps selected Plan Calendar dates valid and distinct from missing planning configuration.
- Adds structured Safe to Spend unavailable reasons and actionable setup guidance.
- Preserves the v1.24 architecture, Home Assistant ingress, `/data`, routes and financial data.

## v1.24.1 - Core UX Redesign Production Corrections

- Corrects Accounts and Activity loading so primary data reaches explicit loading, populated, empty or error states without waiting on slow supporting requests.
- Improves scoped retry and empty-state handling while preserving cards, transactions, reconciliation, historical data and API contracts.
- Removes the obsolete mobile Payment Centre outer shell, clarifies Safe to Spend configuration-unavailable states and keeps legitimate recurring occurrences distinct.
- Tightens mobile shell cleanup and safe-area presentation. No database migration is required.

## v1.24.0 - Core UX Redesign

- Reorganises the mobile product around Overview, Payments, Plan, Accounts and More.
- Refocuses Overview on Safe to Spend, Needs attention, Coming up and Your plan.
- Consolidates Payments into Upcoming, Attention, Timeline and Manage, preserving Bills and recurring schedule workflows.
- Consolidates Plan into Overview, Forecast and Calendar, preserving authoritative planning and forecast calculations.
- Consolidates Accounts into Accounts, Activity and Cards, preserving transaction history, reconciliation, account details and card management.
- Extends shared mobile navigation, financial-event rows, summary surfaces, statuses, forms and action-sheet behavior across the redesign.
- Preserves Home Assistant ingress, direct routes, existing APIs, financial data and historical lifecycle semantics. No database migration is required.

## v1.23.0 - Mobile Decision UX, Cash Plan Reliability & Information Hierarchy

- Makes Cash Plan resilient when optional pay-cycle or planning inputs are unavailable, preserving known planning data and returning structured availability diagnostics.
- Refocuses the mobile Overview around Safe to Spend, a concise Money requiring action list and a compact cash outlook while keeping deeper financial workspaces available.
- Organises mobile More navigation into Planning, Payments and Money & accounts groups and improves narrow-screen safe-area spacing without changing financial semantics.
- Preserves the v1.22.2 Home Assistant distribution contract, including prebuilt GHCR images, anonymous image resolution, ingress, port 8097 and `/data` persistence.
- Requires no database migration.
