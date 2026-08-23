# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.8.0 - Recurring Expenses Responsive UI/UX Completion

### Changed
- Completed the production Recurring Expenses responsive redesign across desktop, tablet, mobile and Home Assistant ingress-sized viewports.
- Moved List, Calendar and Summary to the real v1.7 Scheduled Payment occurrence dataset instead of presenting one recurring-rule row as a proxy for a payment occurrence.
- Added real Payment Method and Scheduled Payment Status filtering, Overdue Only and Payments Requiring Attention filtering.
- Added draft/apply mobile Filters with a real active-filter count, focus handling and safe-area padding.
- Added collapsible mobile financial Summary details, mutually exclusive payment-status totals, Largest Upcoming Expense and quick links to CSV matching and Payments Requiring Attention.
- Added grouped desktop Scheduled Payment rows and compact mobile rows with actual and relative due dates, payment source, payment state and state-aware actions.
- Added Direct Debit Account display and Automatic Card Payment Card plus derived linked Account display without exposing full Card numbers.
- Added Mark as Paid, Skip Payment, Review Payment and matched-transaction presentation through the existing v1.7 lifecycle and reconciliation APIs.
- Added a functional Recurring Expenses-specific Calendar with month navigation, adjacent-month dates, multiple payments per day, `+N more`, selected-date details, status legend and Upcoming prioritisation.
- Calendar navigation uses the selected calendar month as its temporal scope while preserving the List relative Date Range and all non-temporal filters.
- Replaced the active version-specific Recurring Expenses implementation with a durable `RecurringExpensesPage`, while keeping the historical v1.5.1 filename as a compatibility wrapper for the existing production route.

### Preserved behaviour
- Preserved v1.5.1 Search, Date Range, Frequency, Category, financial summary, sorting, mobile presentation, actions and empty states.
- Preserved v1.7 Payment Handling, Account → Card relationships, Scheduled Payment lifecycle, Payments Requiring Attention, Mark as Paid, Skip Payment, CSV matching and expected-vs-actual payment evidence.
- Recurring Expense remains the rule, Scheduled Payment remains the expected occurrence and Transaction remains the actual financial movement.

### Data safety
- No v1.8.0 database migration is required.
- Existing Accounts, Cards, Recurring Expenses, Scheduled Payments, transaction matches and historical data are not reset or recreated.

### Versioning and release gates
- Updated Home Assistant add-on, frontend and backend API release metadata to v1.8.0.
- Added focused v1.8 frontend regression coverage while retaining v1.7 lifecycle tests.
- Installed Home Assistant desktop/iPhone ingress acceptance and real implementation screenshots remain manual gates before merge.

## v1.5.1 - Recurring Expenses UI refresh

### Changed
- Redesigned the Recurring Expenses experience around upcoming household cash-flow visibility rather than administrative record cards.
- Consolidated search, date-range, frequency and Category filtering into one responsive filter workflow with Clear Filters behaviour.
- Added a compact Scheduled Total summary with payment count and average-payment visibility derived from the filtered scheduled payments.
- Added prominent Next Payment and Largest Upcoming Expense context.
- Added a period breakdown using Next 7 days, Following 7 days and Later buckets that reconcile to the filtered total without double-counting.
- Replaced desktop recurring-expense row cards with one lightweight sortable table showing relative and actual due dates, Name, Category, Amount, Frequency and accessible Actions.
- Added restrained overdue, today/tomorrow and near-term due-date urgency styling that always includes textual status.
- Added right-aligned tabular currency values and subtle frequency badges for faster scanning.
- Replaced the native-looking Edit control with an accessible per-row actions menu while preserving the existing edit workflow.
- Added compact responsive mobile rows, mobile search, a filter sheet and collapsible summary details modelled on the supplied Fynvo recurring-expense mock-ups.
- Added first-class empty states for households with no recurring expenses and filtered result sets with no matches.
- Kept recurring rules distinct from scheduled-payment rows, and reused the existing occurrence summary service rather than duplicating recurring records.

### Release scope
- This is a focused UI/usability release. No database migration is required.
- Existing recurring-expense creation, editing, persistence, recurrence generation, forecasting, authentication and Home Assistant ingress architecture remain unchanged.
- A recurring-expense List/Calendar switch is not exposed in this release because the existing general Financial Calendar does not yet provide a production-ready recurring-expense-specific calendar interaction. The recurring page remains structured so a real Calendar view can be added without replacing the List implementation.

## v1.3.0 - Cash Flow Intelligence, Financial Calendar & Smart Forecasting

### Added
- Added a dedicated v1.3 Cash Flow Intelligence experience with projected household balance, expected income and expenses, lowest projected balance and explainable event-level breakdowns.
- Added 7, 14, 30, 60 and 90 day plus 6 and 12 month forecast horizons.
- Added per-Account projected balances and optional minimum-balance safety buffers.
- Added low-balance and negative-balance warnings with expected date, projected balance, shortfall and contributing event.
- Added occurrence-level forecast overrides for amount changes, rescheduling and due/overdue/paid/skipped status without rewriting the recurring template.
- Added Financial Calendar daily income, expense and net-movement totals.
- Added grouped Upcoming money views for Overdue, Today, Tomorrow, Next 7 Days, Later This Month and Future.
- Added an isolated `Can I afford this?` future-purchase simulator showing balance before and after purchase, lowest later balance and safety-buffer/negative-balance risk.
- Added additive v1.3 migration support for `accounts.minimum_balance_cents` and `forecast_occurrence_overrides`.
- Added backend and frontend regression coverage for the new cash-flow workflows.

### Forecast integrity
- Internal Account-to-Account transfers update individual Account projections while remaining `$0` net at household level.
- Forecast starting balances exclude future-dated transactions, preventing scheduled transfers from being reflected before their forecast date and then counted again.
- Unresolved overdue bills remain visible in the forecast until resolved, skipped, paid or rescheduled.
- Household closing balance is calculated independently from Account attribution, so forecast events without an Account still affect household cash flow correctly.
- Forecast values remain explicitly identified as projections rather than confirmed transactions.

### Mobile and accessibility
- Added responsive Cash Flow, Calendar and Upcoming layouts for phone, tablet and desktop widths.
- Retained semantic labels and non-colour text descriptions for important forecast warnings.

### Versioning and documentation
- Updated backend, frontend and Home Assistant add-on release metadata to 1.3.0.
- Added v1.3.0 release notes and updated the README to describe the current release.

### Known follow-up work
- Direct bank-feed confirmation, richer historical balance snapshots and full record-level Household permissions/audit history remain separate follow-up work and are not represented as completed by this release.

## v1.2.0 - Household Identity & Access

### Added
- Added a stable first-class Household model and explicit Household Membership model separate from User identity.
- Added Administrator, Household Member and Read Only roles as authoritative membership data.
- Added administrator-managed Household Members with create, edit, role change, deactivate, reactivate, password reset, MFA reset and session-revocation workflows.
- Added a safe temporary first-login credential workflow that requires the member to establish a new password.
- Added protection against deactivating or demoting the only active Administrator.
- Added deterministic username normalisation and duplicate prevention.
- Added Household Settings and responsive member-management UI for phone, tablet and desktop layouts.
- Added Household ownership and visibility metadata foundations for existing and new financial records.
- Added explicit Account owner management while keeping Owner, Creator and Last Updater as separate concepts.
- Added mobile architecture prerequisites for a future private SwiftUI client using the same Fynvo backend and authoritative database.

### Security and authentication
- Household context is established by the authenticated backend from User and active Household Membership, rather than trusting an arbitrary frontend Household ID.
- Member-management authority is enforced on the backend, not by hidden frontend controls.
- Password reset and deactivation revoke affected sessions while preserving the same User identity and historical attribution.
- Household members remain compatible with the v1.1.0 MFA foundation. Administrative MFA reset never returns the previous MFA secret.
- Member responses do not expose password hashes, MFA secrets, recovery secrets or session tokens.

### Migration and data preservation
- Existing installations migrate forward to an initial Household without database reset or duplicate financial records.
- Existing administrators are preserved and become Administrator members of the migrated Household.
- Existing records retain legacy-compatible Household Shared visibility foundations so the upgrade does not unexpectedly hide household financial data.
- Existing Account/Card relationships, transaction provenance, import provenance, Financial Data Coverage, transaction splits and reconciliation remain intact.

### Financial regression boundary
- Household identity does not redefine Fynvo's financial truth. Actual, Committed, Planned, Budget, Forecast and Scenario remain separate concepts.
- Existing Accounts, balances, Transactions, transfers, Categories, Income, Recurring Expenses, Bills, Planned Spending, Budgets, Goals, Scenarios, Insights, imports, Data Coverage and reconciliation remain the authoritative financial domains.

### Versioning and documentation
- Updated Home Assistant add-on, backend and frontend release metadata to 1.2.0.
- Added v1.2.0 release notes.
- Added private iPhone/mobile API prerequisite architecture documentation.

### Explicitly deferred
- Comprehensive record-level financial permissions and complete Private versus Household Shared enforcement remain v1.3.0 work.
- Immutable Audit Events, comprehensive Change History and full User Activity remain v1.3.0 work.
- No native iPhone application, public mobile API, APNs, widgets, Siri/App Intents, production CDR/Open Banking connection, automatic bank sync, Home Assistant financial entities or standalone/cloud migration is delivered in v1.2.0.

## v1.0.0 - Stable Production Release

### Production readiness
- Established v1.0.0 as Fynvo's first stable-production baseline, focused on acceptance, data preservation, security, upgrade safety and supportability rather than major feature expansion.
- Added a formal v1.0 acceptance checklist separating repository-verifiable gates from installed Home Assistant/manual release gates.
- Added documented Home Assistant backup and restore procedures for Fynvo's persistent `/data` state.
- Added explicit v1.0 known limitations so deferred capabilities are not represented as delivered.
- Added v1.0 release notes describing required automated and manual acceptance evidence.

### Versioning
- Updated Home Assistant add-on, backend and frontend release metadata to 1.0.0.
- Retained historical v0.x documentation and version references where they describe earlier releases.

### Stable baseline
- Retained v0.18.0 Category normalisation, merge, integrity diagnostics, recurring duplicate review, Card integrity diagnostics and Upcoming Commitments duplicate-suppression foundations.
- Retained the corrective removal of the redundant Overview `Upcoming / Next 7 days` card and the Income Date Range control.
- Retained existing authentication/bootstrap/recovery, Accounts, Transactions, Transfers, Income, Recurring Expenses, Bills, Planned Spending, Budgets, Goals, Forecasting, CSV import, reconciliation foundations, Spending Intelligence, Insights and responsive/mobile functionality as the v1.0 acceptance surface.

### Release gates
- Installed Home Assistant ingress, representative upgrade, iPhone/mobile acceptance and Home Assistant backup/restore remain manual release gates when they cannot be executed in the development environment.
- v1.0.0 must not be tagged as fully accepted based solely on source-level tests if those manual gates remain unverified.

### Deferred
- Direct ING connectivity and new production Open Banking/CDR provider integration.
- Automatic production bank synchronisation and production-grade automatic reconciliation.
- Advanced multi-user household roles and permissions, immutable audit logs and complete user activity/change history.
- Home Assistant financial sensors/entities and standalone Cloudways deployment.

## v0.18.0 - Financial Data Integrity, Category Management & Workflow Polish

### Added
- Added a supported Category merge workflow with a preview of affected Transactions, Income, Recurring Expenses, Bills, Planned Spending, Budgets and child Categories before any changes are made.
- Added Category health diagnostics for duplicate parent/child Categories, orphan children, children of inactive parents, circular relationships, orphan/inactive references, stale denormalised paths and Category-type conflicts.
- Added recurring-expense duplicate review using normalised name, amount, frequency, payment source and due-date proximity. Possible duplicates are surfaced for review and are never merged automatically.
- Added Account/Card integrity diagnostics for orphan Cards and active Cards linked to archived Accounts.
- Added a filtered Upcoming Commitments service foundation with overdue inclusion and duplicate-suppression support.
- Added a single-command CI-equivalent validation script covering Python compilation, Ruff, backend tests, application import, frontend tests/build, Home Assistant metadata and Docker build.

### Changed
- Category duplicate prevention now normalises case, leading/trailing whitespace and repeated whitespace for create and rename/move operations.
- Category merges preserve financial history by reassigning references and deactivating the source Category rather than deleting it.
- Merging parent Categories also consolidates same-name child Categories under the destination while retaining their linked records.
- Categories mobile presentation is more compact and no longer gives zero-entry links unnecessary visual emphasis.
- Categories now expose `Check Category Data` and `Merge Category` actions directly from the management page.
- Recurring Expenses now surface possible duplicate groups without automatically changing household data.
- Mobile financial table/card spacing has been tightened while preserving touch targets and desktop behaviour.
- Version metadata is aligned to v0.18.0 across the backend, frontend and Home Assistant add-on.

### Preserved behaviour
- The redundant Overview `Upcoming / Next 7 days` card remains removed. `Upcoming Commitments` remains the authoritative future-obligation view.
- The Income page remains independent of the global Date Range selector.
- Existing linked Bill/Recurring Expense schedule suppression remains in place so a linked Bill and its generated recurring occurrence are not both scheduled for the same date.
- Effective-dated recurring amount changes remain the mechanism for changes such as `$140/month` becoming `$80/month` from a future date without rewriting history.
- No direct ING connectivity, new production Open Banking/CDR provider, bank credentials or Cloudways migration is introduced by this release.
