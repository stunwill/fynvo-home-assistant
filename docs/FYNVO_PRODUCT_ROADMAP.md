# Fynvo Product Roadmap

This roadmap is the canonical development queue for Fynvo. Future development should update this file rather than creating parallel release plans.

## Current baseline and next work (31 October 2026)

Latest verified published release: **v1.31.0**, merged through [PR #103](https://github.com/stunwill/fynvo-home-assistant/pull/103) on 10 October and published on 11 October Australian time. The version sections below retain historical scope; their original plans are not current release status.

The v1.31.1 corrective candidate addresses Ruff timezone findings and reproducible local/CI tooling, with aligned release documentation. It remains pending PR CI, review, merge and publication. It adds no financial features or migration. See [release evidence and outstanding acceptance](RELEASE_STATUS.md).

Current priorities, with no committed dates or assigned owners recorded:

1. Obtain green backend, frontend and Home Assistant image CI for the corrective candidate and then merged main.
2. Record installed upgrade/restart, ingress/iPhone and restore acceptance using [the retained checklist](RELEASE_VALIDATION_v1.31.0.md).
3. Reconcile live Redbark current/available balances, stale/error sync recovery and controlled financial scenarios.
4. Record acceptance results and reviewer decisions before representing installed reliability as verified.

Balance observations, dated Account/household forecasting, recurring and one-off plans, remaining Bills, accepted income, Account Funding, Payday Allocation, buffers and provisional Safe-to-Spend are implemented in v1.31.0. Publication does not establish deployment or live financial acceptance. Later production CDR/provider expansion means extending the existing Redbark integration, not adding Fynvo's first live provider.


## Product principles

1. Forecast actual dated cash flow, not just monthly averages.
2. Keep financial data local by default.
3. Separate budgeted, planned, actual and forecast financial activity.
4. Make scenario planning simple enough for everyday household use.
5. Keep financial calculations clear, auditable and explainable.
6. Support Australian household finance first while allowing later internationalisation.
7. Maintain a cohesive Fynvo visual and navigation system across future modules.
8. Make Budget, Actual, Committed, Planned, Forecast and Scenario explicit in budget analysis.
9. Make financial records maintainable after creation.
10. Feed Manual Entry, CSV Import and future CDR/Open Banking into one Actual transaction pipeline.
11. Keep spending intelligence local, explainable and user-controlled.
12. Treat Goals as forward-looking financial planning records distinct from Budgets and Planned Spending.
13. The Overview dashboard should be a household financial command centre, not a development-status page.
14. Authentication must always have a documented owner bootstrap and recovery path.
15. User activity, audit events and record change history must become explicit production-readiness capabilities before they are represented as delivered production features.
16. Financial Insights must be evidence-backed, consistent with source financial calculations and free from unsupported personal financial advice.
17. Fynvo must remain one responsive application across phone, tablet, desktop and Home Assistant ingress.
18. Stable-version work must prioritise reliability, data preservation and verifiable core workflows over new feature expansion.
19. Category identity and hierarchy must be authoritative, normalised and safe to reorganise without losing historical financial records.
20. Recurring definitions, forecast occurrences, commitments and actual transactions must remain distinguishable so future reconciliation can match records without duplicating obligations.

## Core product concepts

### Actual
Money that has already been received or spent through recorded, imported, synchronised or reconciled transactions.

### Committed
Known obligations and income sources such as recurring expenses, bills and scheduled income.

### Planned
Known or intended future spending that has not yet occurred.

### Budget
The amount the household intends or permits itself to spend for a category, period, account, person or goal.

### Goal
A desired future financial position or amount, such as a savings target, emergency fund, planned purchase, annual obligation or debt-reduction target.

### Forecast
What Fynvo calculates is likely to happen based on balances, commitments, plans, budgets where available and historical behaviour where appropriate.

### Scenario
A temporary or saved what-if view of what would happen if circumstances changed.

### Insight
An explainable signal derived from core Fynvo financial calculations. An Insight describes what changed or matters, its comparison basis, supporting evidence and a route to inspect the underlying records. Insights are not the source of financial truth.

### Audit Event
An append-only record of what action occurred, when it occurred and which user/interface caused it.

### Change History
A versioned view of what data changed on a financial record, such as amount, date, category or status.

## Release definition of done from v0.3.0 onward

Every release must include a version bump, database migrations where required, automated tests, CI validation, a CHANGELOG entry, Home Assistant-visible release notes, GitHub release notes and user-readable release notes.

Home Assistant ingress access, login, protected APIs, core create/edit persistence and safe upgrade behaviour are release blockers.

## Release plan

### v0.2.0 - Fynvo Foundation + Dashboard

Status: Completed.

Delivered scope:
- Home Assistant add-on foundation;
- SQLite persistence under `/data`;
- first-run administrator setup;
- username/password login;
- server-side session enforcement;
- responsive application shell.

### v0.3.0 - Accounts & Transactions

Status: Completed.

Delivered scope:
- account management;
- actual transactions;
- account-to-account transfers;
- dashboard financial position;
- transaction metadata fields for future CSV import and matching;
- deterministic Home Assistant ingress/root-route behaviour.

### v0.4.0 - Income, Recurring Expenses & Bills

Status: Completed.

Delivered scope:
- income source management;
- recurring expense management;
- incomplete recurring records;
- bills and financial obligations;
- overdue and due-state tracking;
- weekly, monthly, pay-cycle and annual schedule views;
- Excel-style Jan-Dec annual matrix with drill-down.

### v0.5.0 - Planned Spending & Enhanced Financial Views

Status: Completed.

Delivered scope:
- Planned Spending records;
- statuses: Idea, Wishlist, Planned, Committed, Purchased and Cancelled;
- forecast inclusion/exclusion;
- planned spending integration with Overview, Week, Month, Pay Cycle and Year views;
- canonical Fynvo branding assets.

### v0.6.0 - Cash Flow Forecasting & Financial Scenarios

Status: Completed.

Delivered scope:
- reusable cash-flow forecast engine;
- baseline and expected forecasts;
- projected balance timeline;
- lowest balance and shortfall detection;
- effective-dated amount changes;
- scenario comparisons without mutating real records.

### v0.7.0 - Financial Calendar & Category Management

Status: Completed.

Delivered scope:
- redesigned Fynvo interface;
- unified Financial Calendar;
- Cash Flow view;
- Quick Add;
- category visibility foundation.

### v0.8.0 - Advanced Budgeting

Status: Completed.

Delivered scope:
- first-class Budget domain model;
- expense budgets and income budget/target foundations;
- weekly, true fortnightly, monthly, quarterly and annual periods;
- annual allocation strategies;
- base budget, rollover and effective available budget separated;
- category hierarchy foundation;
- Independent, Shared Parent Pool and Parent Equals Sum of Children budget modes;
- Budget vs Actual vs Committed vs Planned vs Forecast analysis foundation;
- unbudgeted category detection;
- Saved Views / View Preferences foundation.

Deferred from v0.8.0 and corrected in v0.9.0:
- full edit UI for existing major financial records.

### v0.9.0 - Editing, CSV Import & Reconciliation

Status: Completed.

Delivered scope:
- full record editing for Accounts, Transactions, Categories, Bills, Recurring Expenses, Income, Planned Spending and Budgets;
- edit forms discoverable from current screens;
- persistence after reload through update APIs;
- effective-dated edit support for income, recurring expenses and budgets;
- edit-history audit foundation;
- CSV bank transaction import;
- account selection during import;
- column mapping;
- Australian date support: DD/MM/YYYY, DD/MM/YY and YYYY-MM-DD;
- import preview, invalid-row reporting and duplicate detection;
- matching suggestions against Bills, Recurring Expenses and Planned Spending;
- import batches, import history and reconciliation review queue;
- imported transactions feeding Budgeting, Cash Flow and Forecasting.

### v0.10.0 - Spending Intelligence

Status: Completed.

Delivered scope:
- source-independent spending intelligence service;
- merchant/payee normalisation and user-managed rules;
- category suggestions with confidence and evidence;
- recurring expense/income and amount-change detection;
- Spending Intelligence review queue;
- category spending trend analysis and unusual-spending detection;
- one-off baseline exclusion;
- local deterministic analysis.

### v0.11.0 - Goals & Financial Planning

Status: Completed.

Delivered scope:
- first-class Financial Goals domain;
- Goal creation, editing, completion and cancellation;
- progress, contribution and forecast-completion calculations;
- account allocations and unallocated savings reporting;
- Goal What-If calculations;
- command-centre dashboard aggregation;
- redesigned Overview dashboard with KPI row, Cash Flow Forecast, Forecast Summary, Upcoming Commitments, Quick Stats, Budget Overview and Goals.

### v0.12.0 - Australian Open Banking / CDR Foundation, Admin Bootstrap & Branding

Status: Completed.

Delivered scope:
- Home Assistant administrator bootstrap configuration and explicit recovery mode;
- provider-neutral Bank Connection architecture and mock Australian provider;
- external account discovery/linking and connected-account balance metadata;
- bank transaction ingestion through the existing Actual transaction table;
- provider transaction identity tracking, pending-to-posted matching and sync history;
- disconnect without deleting historical transactions;
- reconciliation-link suggestions;
- Fynvo branding/favicon and corrected Upcoming/Commitments definitions.

Production CDR connectivity remains future work. v0.12.0 deliberately does not fabricate live bank connectivity without provider credentials, consent infrastructure or an appropriate Australian CDR intermediary.

### v0.13.0 - Authentication, Login UX, Branding Reliability & Scenario Foundations

Status: Completed.

Delivered scope confirmed from the merged repository:
- administrator credential adoption and recovery improvements;
- authentication regression coverage;
- responsive login/authentication foundations;
- official Fynvo branding and bundled Galano Grotesque Medium typography;
- persistent Scenario records/adjustments;
- isolated baseline-versus-scenario comparisons;
- effective-dated recurring-income/expense Scenario changes;
- one-off Scenario income/expense changes;
- created/updated user metadata foundations.

### v0.14.0 - Insights & Financial Health

Status: Completed.

Delivered scope:
- first-class Insights lifecycle with New, Reviewed, Dismissed and Resolved states;
- deterministic fingerprinting and stale-resolution behaviour;
- Financial Health component summary;
- Cash Flow, Budget, Spending, Recurring Commitment, Income, Goal, Scenario and Data Quality Insights;
- evidence/reference retention and authenticated Insights APIs;
- responsive Insights interface and Overview Financial Health integration;
- local deterministic processing.

### v0.15.0 - Authentication Reliability & Recovery Hardening

Status: Completed and merged.

Delivered scope confirmed from the merged repository:
- deterministic administrator authentication initialisation during application startup;
- authoritative authentication lifecycle/state handling;
- safe Home Assistant option-source diagnostics;
- fresh-install administrator bootstrap;
- explicit administrator recovery mode;
- in-place, atomic administrator recovery preserving ownership relationships;
- deterministic recovery-target safety;
- recovered-session revocation and stale failed-login cleanup;
- `session_days` consistency;
- minimal public authentication state and protected administrator diagnostics;
- authentication/legacy-database regression coverage;
- Home Assistant ingress authentication boundary.

The v0.15.0 plan also proposed Home Assistant financial sensors/entities and automation actions. Those entities are not present in the actual merged repository and are therefore retained as future work rather than marked delivered.

### v0.16.0 - Mobile Experience & Responsive UI

Status: Completed and merged.

Delivered scope confirmed from the merged repository:
- shared responsive application shell;
- one authoritative navigation configuration;
- hamburger-controlled off-canvas mobile drawer closed by default;
- backdrop, close, Escape and route-selection dismissal;
- background scroll locking and independent drawer scrolling;
- iPhone safe-area and dynamic viewport handling;
- active-route, touch-target, keyboard and focus accessibility improvements;
- responsive mobile forms, tables, modals and dashboard/card layouts;
- tablet layout refinement and desktop sidebar preservation;
- responsive regression tests.

A real installed Home Assistant/iPhone acceptance run remains an operational acceptance requirement and is carried forward into v0.17.0 rather than being treated as automatically proven by source-level tests.

### v0.17.0 - Pre-v1.0 Reliability & Responsive Hardening

Status: Completed and merged.

Delivered scope:
- root-cause correction for the Accounts `+ Add` failure where the generic modal generated `PUT /api/accounts/null`;
- create/update contract separation in the shared frontend workflow, with `POST` for new records and ID-based `PUT` for persisted records;
- exact `Kristy - Main AC` Account create/edit regression coverage;
- generated Account ID, persistence and no-duplicate edit coverage;
- expanded friendly Account Types including Offset, Car Loan, Line of Credit, Investment and Superannuation, while retaining legacy `vehicle_loan` compatibility;
- explicit asset/liability Account classification;
- positive amount-owing UX for liability opening balances;
- Available Cash limited to active Transaction, Savings, Offset and Cash accounts;
- Account balance, cent-precision and transaction relationship regression coverage;
- liability-aware internal transfer semantics;
- archived-account write protection while retaining historical retrieval;
- user-facing validation messages for normal create/edit failures;
- Australian date-only display hardening;
- reinforced mobile off-canvas navigation styling and regression checks;
- compact mobile Account/page actions and safer mobile modal action placement;
- v0.15 authentication regression preservation;
- v1.0 readiness assessment in `docs/V1_READINESS_v0.17.0.md`;
- release metadata, changelog and release-note updates.

### v0.17.4-v0.17.5 - Corrective Category and Mobile Workflow Releases

Status: Completed and merged.

Delivered scope:
- corrected Categories parent/child presentation and historical duplicate consolidation;
- preserved linked financial values while duplicate Category records were deactivated;
- removed the redundant Overview `Upcoming / Next 7 days` card while retaining Upcoming Commitments;
- removed the global date-range control from the Income page;
- improved corrective mobile layout and release regression coverage.

### v0.18.0 - Financial Data Integrity, Category Management & Workflow Polish

Status: Completed and merged.

Delivered scope:
- authoritative Category-name normalisation across create and edit workflows, including case and repeated-whitespace duplicate prevention;
- user-supported Category merge preview and merge operations that reassign financial references and archive the source without deleting history;
- automatic consolidation of same-name child Categories when parent hierarchies are merged;
- Category health diagnostics covering duplicate groups, orphan children, inactive-parent relationships, cycles, orphan/inactive references, stale denormalised paths and Category-type conflicts;
- compact Category management UI with health checking, merge controls and reduced zero-entry visual noise;
- recurring-expense duplicate review based on normalised name, amount, frequency, payment source and due-date proximity, without automatic merging;
- Account/Card integrity diagnostics for orphan Cards and active Cards linked to archived Accounts;
- filtered Upcoming Commitments service foundation with explicit duplicate-suppression helper and overdue inclusion;
- continued reliance on the established linked Bill/Recurring Expense suppression in the schedule engine;
- compact mobile workflow refinements for Categories, Recurring Expenses and financial record tables;
- CI-equivalent local validation script to catch compile, Ruff, backend, frontend, metadata and Docker failures before PR creation;
- expanded regression coverage for Category duplicate prevention, merge data preservation, Category health, recurring duplicate review and commitment de-duplication;
- release metadata updated to v0.18.0.

Explicitly out of scope:
- direct ING connectivity;
- new production Open Banking/CDR provider integration;
- bank credential storage;
- standalone Cloudways migration.

Production CDR/provider work remains future scope. v0.18.0 prepares cleaner identities and data relationships without adding a bank-specific integration.

### v1.0.0 - Stable Production Release

Status: Historical readiness plan, superseded by the current v1.31.0 release baseline. The acceptance requirements below remain relevant wherever evidence has not been recorded.

Historical planned scope:
- final acceptance QA of functionality already delivered;
- final v0.18-to-v1 upgrade/migration validation and representative older-data upgrade confirmation;
- backup and restore validation/documentation;
- final database integrity and recovery checks;
- final authentication/session/security review;
- Home Assistant ingress installation/onboarding validation;
- privacy, retention and safe diagnostic documentation for the functionality actually present;
- performance validation on representative household histories;
- final defects identified during acceptance;
- known-limitations documentation;
- production packaging, release notes and stable version tagging.

v1.0.0 must not become another large feature-expansion release. Capabilities not already dependable should remain explicitly future work rather than being added solely to satisfy the version number.

### Future Home Assistant Financial Integration

Planned scope retained because it is not present in the actual merged v0.16.0 source:
- Home Assistant financial sensors/entities;
- automation-friendly numeric financial state;
- dashboard cards;
- shortfall, upcoming bill, budget-risk, Insight and Goal automation foundations;
- sensor-friendly Financial Health component states;
- useful states such as available cash, forecast balance, lowest projected balance, overdue count, budget risk and Goal progress;
- Home Assistant notifications/actions that link back to Fynvo without duplicating core calculations;
- strict authentication/privacy boundary and no sensitive detail in entity attributes.

### Future Household Production Capabilities

Historical backlog, requiring reconciliation against current source before any item is scheduled or described as absent. Redbark integration and household identity foundations have since shipped; this list must not override current implementation evidence. Remaining production acceptance is tracked above.

Originally proposed capabilities:
- household user creation, editing, deactivation/reactivation and password-reset workflows;
- Administrator, Household Member and Read Only permissions;
- household membership/profile management;
- User Activity;
- immutable Audit Logs;
- per-record Change History;
- richer Reports and export-ready services;
- production CDR/provider expansion and consent lifecycle;
- advanced bank-sync retry/backoff and provider-degraded behaviour;
- broader privacy/data-retention controls;
- per-user Insight state when multi-user support is introduced.
