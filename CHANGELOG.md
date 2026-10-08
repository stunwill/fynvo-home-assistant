# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.31.0 - Financial Integrity & Account Cash Flow

- Uses one canonical dated cash-event stream for household and Account forecasts, current-cycle funding, Safe-to-Spend and Payday Allocation. Linked Bills replace their original recurring occurrence, including rescheduling and partial payment amounts.
- Separates observed bank cash from imported history and exposes source, observation time, accessible cash and freshness. Future transactions no longer reduce today's actual balance. Manual balance confirmation preserves transaction history and can refresh an unchanged amount.
- Shows Account forecasts, lowest balances and funding deadlines in Plan and Accounts. Internal cash transfers conserve household cash; transfers outside eligible cash Accounts reduce it.
- Protects preferred Account buffers plus the household reserve once. Positive household capacity remains provisional when payment Accounts need transfers or essential inputs require confirmation. Recommendations allocate donor headroom once and do not execute transfers.
- Adds additive schema v19, a consistent pre-upgrade SQLite backup, Bill occurrence references, immutable balance observations and regression coverage. Existing APIs, Redbark integration, history and Home Assistant ingress remain supported.

## v1.30.0 - Household Bank Connection Clarity

- Groups discovered accounts beneath their stable Redbark connection, including separate connections to the same institution and identically named accounts distinguished by masked identifiers.
- Adds editable connection labels and optional active-household-member context without changing provider IDs or Fynvo account ownership. Introduces additive provider-configuration references while retaining the verified single-credential setup workflow.
- Separates account discovery, connection sync, transaction refresh and bank balance freshness. A missing balance no longer receives a false update time or silently becomes a new account's $0 opening balance; users supply an explicit provisional starting balance when needed.
- Isolates a failed connection's health from another connection and preserves last-known actual balances, transaction history, manual accounts, required-action identities and the existing planning engines. Adds schema v18 and regressions for multi-connection routing.

## v1.29.0 - Bank Connection Integrity

- Coordinates account mapping, provider discovery, credential changes and disconnects with background sync in the add-on process. A conflicting operation asks the user to retry instead of racing the sync.
- Atomically claims an unresolved provider account when linking or creating a Fynvo account; a competing claim rolls back the newly created account instead of leaving an orphan.
- Opens the exact unresolved bank account from its Accounts required action and offers an optional, never-preselected mapping suggestion only when account name, institution and type agree.
- Clarifies Redbark's connection summary, needs-setup count and disconnected status. Account Detail labels a disconnected bank balance as no longer syncing while preserving its last value and historical transactions.
- Retains schema v17, the existing mapping uniqueness constraints, posted transaction deduplication, planning engines, Accounts → Activity and Home Assistant ingress routes. No database migration is required.

## v1.28.0 - Bank Activity Reconciliation

- Makes posted bank transactions explainable payment-match evidence in Activity and the existing Review Queue; only explicit confirmation changes a scheduled payment to paid.
- Retains deterministic, account-aware candidate matching, rejected-pair decisions and confirmed merchant aliases; protects pending, transfer, duplicate and already-completed transactions against unsafe matches.
- Separates provider categories from Fynvo categories, suggests categories from confirmed merchant history without silently applying them, and provides reversible memory and alias endpoints.
- Limits new bank-sync review suggestions to the most recent 45 days; old imported activity remains visible. Adds schema v17, mobile review containment and integration regressions while keeping actual balances and planning calculations untouched.

## v1.27.0 - Bank Account Lifecycle

- Adds deterministic bank-account actions in Accounts, explicit link/create/ignore confirmation, and connected/ignored/attention management.
- Discovers new accounts on recurring backend syncs; preserves the last known financial state if a mapped account disappears or fails.
- Enforces unique active mappings, transaction-safe account creation, and schema v16 lifecycle metadata.

## v1.26.0 - Redbark Open Banking Foundation

- Adds the first live banking-provider integration through Redbark, with secure backend-only credentials, account discovery and explicit mapping to existing or new Fynvo accounts.
- Synchronises actual current/available balances and posted transactions while keeping forecast balances, Safe-to-Spend, Account Funding and Payday Allocation as separate Fynvo planning calculations.
- Adds idempotent transaction import, provider transaction identities, incremental overlap, per-account failure handling, stale-data preservation and backend scheduled/manual synchronisation.
- Adds Settings → Bank connections for connection status, account mapping, manual sync and safe disconnect while preserving imported financial history.
- Preserves the Accounts → Activity protected transaction workspace and reconciliation flow, including safe currency/date formatter defaults and persisted Activity re-entry.
- Adds schema v15 banking metadata and keeps manual accounts and existing financial history backward compatible.

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
