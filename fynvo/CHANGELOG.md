# Fynvo Add-on Changelog

## v1.8.0 - Recurring Expenses Responsive UI/UX Completion

### Recurring Expenses
- Completed the production responsive Recurring Expenses redesign for desktop, tablet, mobile and Home Assistant ingress-sized viewports.
- List, Calendar and Summary now consume real Scheduled Payment occurrences from the v1.7 payment model.
- Added Search plus Date Range, Frequency, Category, Payment Method and Payment Status filtering, with Overdue Only and Payments Requiring Attention options.
- Added an active mobile filter count and draft/apply bottom-sheet filtering with iOS safe-area handling.
- Added a compact mobile Summary with expandable period breakdown, Largest Upcoming Expense, real payment-status totals and quick actions.
- Added grouped desktop rows and compact mobile rows with actual/relative due dates, payment method, Scheduled Payment status and source information.

### Calendar
- Added a functional Recurring Expenses Calendar with previous/next month navigation.
- Calendar month selection is its temporal scope while the List retains its relative Date Range.
- Search and non-temporal filters continue across List and Calendar.
- Added Monday-first Calendar grid, adjacent-month dates, multiple payments per date, priority ordering, `+N more`, selected-date details, status legend and Upcoming view.

### Payment handling and reconciliation
- Preserved v1.7 Scheduled Payment lifecycle semantics rather than introducing frontend-only status.
- Added Direct Debit Account presentation and Automatic Card Payment Card presentation with the Card-derived linked Account.
- Added state-aware Mark as Paid, Skip Payment, Review Payment and Review Match access from Recurring Expenses.
- Matched payments expose confirmation evidence from the existing Scheduled Payment/Transaction relationship.
- Payment-status summary buckets are mutually exclusive so their amounts reconcile with Scheduled Total.

### Data safety
- No v1.8 database migration is required.
- Existing Recurring Expenses, Scheduled Payments, Cards, Accounts, transaction matches and payment history are preserved.
- The Recurring Expense → Scheduled Payment → Transaction architecture remains unchanged.

### Versioning
- Updated Home Assistant add-on, frontend and backend API release metadata to 1.8.0.
- The production shell reports Fynvo v1.8.0.

### Manual release gates
- Real desktop Home Assistant ingress screenshots, iPhone 15 Pro-class ingress screenshots, Add/Edit, Direct Debit, Automatic Card, manual payment, Mark as Paid, Payments Requiring Attention, CSV-matched state and Calendar usability remain manual acceptance gates before merge.

## v1.7.0 - Payment Handling, Card Management & Reconciliation

### Payment handling
- Completed automatic/manual Payment Handling in the production Recurring Expense form.
- Direct Debit now conditionally uses a Bank Account, while Automatic Card Payment uses a Card and derives its linked Account automatically.
- Manual payment methods no longer require an unnecessary Account or Card.
- Added a configurable automatic-payment confirmation grace period, defaulting to 3 days.

### Account → Card management
- Added production UI Card creation, editing, activation/deactivation and linked-Account display.
- Existing Card IDs and Account relationships are preserved, and multiple Cards may belong to the same Account.
- Only Card last-four identification is stored/displayed by this workflow.

### Scheduled Payments
- Added additive Scheduled Payment records separate from Recurring Expense rules.
- Added Upcoming, Due, Overdue, Expected Automatically, Automatic Payment Not Confirmed, Paid, Skipped and Cancelled states.
- Added recurrence-aware generation across weekly, fortnightly, every-four-weeks, monthly, quarterly, yearly and custom-day schedules.
- Automatic payments are not blindly marked Paid on the due date.

### Reconciliation
- Added Payments requiring attention, Mark as Paid, Skip Payment and expected-vs-actual values.
- Added transaction matching foundations with confidence, merchant evidence, Card-derived Account evidence and one-to-one duplicate protection.
- Confirmed transaction matches record actual date/amount and may establish learned merchant mappings.

### Data safety
- v1.7 migration is additive and idempotent.
- Existing Accounts, Cards, Recurring Expenses and historical financial records are preserved.
- Legacy Account relationships are not falsely converted to Direct Debit without reliable existing evidence.

### Versioning
- Updated the Home Assistant add-on and frontend release metadata to 1.7.0.

### Manual release gates
- Installed Home Assistant ingress, representative upgrade/backup validation, real iPhone/mobile acceptance and production screenshots remain manual gates where repository CI cannot execute them.

## v1.2.0 - Household Identity & Access

### Household identity
- Added a first-class Household identity and explicit Household Membership records separate from User identity.
- Existing installations migrate automatically to an initial Household without resetting the database or recreating financial records.
- Existing administrators are preserved and become Administrator members of the migrated Household.

### Members and roles
- Added Administrator, Household Member and Read Only role vocabulary as authoritative membership data.
- Added Household member management for create, edit, role change, deactivate, reactivate, password reset, MFA reset and session revocation.
- Added protection against demoting or deactivating the only active Administrator.
- Added deterministic username normalisation and duplicate prevention.

### Authentication and security
- Added temporary first-login credentials with a required password-change workflow instead of permanent shared/default passwords.
- Password reset preserves the same User identity and historical attribution while revoking affected sessions.
- Household members remain compatible with the v1.1.0 MFA foundation, and administrative MFA reset never reveals another user's MFA secret.
- Household context is resolved by the authenticated backend and is not trusted from arbitrary frontend household identifiers.

### Ownership and attribution foundations
- Added Household ownership/visibility metadata foundations for existing financial records using legacy-compatible Household Shared behaviour.
- Added Account ownership management that keeps Household, Owner, Creator and Last Updater as separate concepts.
- Preserved Account → Card integrity, transaction provenance, import provenance, Financial Data Coverage, transaction splits and reconciliation semantics.
- Comprehensive Private versus Household Shared permission enforcement remains intentionally deferred to v1.3.0.

### User experience
- Added a responsive Household Settings/member-management experience for phone, tablet and desktop layouts.
- Added safe member/security status presentation without exposing password hashes, MFA secrets or session tokens.

### Mobile preparation
- Added architecture prerequisites for a future private native SwiftUI client using the same Fynvo backend, User identities, Household Memberships and authoritative financial database.
- Documented future API versioning, mobile sessions, Keychain, Face ID, device revocation, local/Tailscale access, offline read caching, idempotent writes and notification considerations.

### Versioning
- Updated the Home Assistant add-on, backend and frontend release metadata to 1.2.0.

### Deferred
- Comprehensive record-level permissions, Private/Household Shared enforcement, selected-member sharing, immutable Audit Events and comprehensive Change History remain v1.3.0 work.
- No native iPhone application, public mobile API, CDR/Open Banking connection, automatic bank sync, Home Assistant financial entities or standalone/cloud migration is introduced by v1.2.0.

## v1.0.0 - Stable Production Release

### Production readiness
- First stable Fynvo release, focused on acceptance, upgrade safety, data preservation, security and supportability rather than major feature expansion.
- Added formal v1.0 acceptance documentation separating repository-verifiable checks from installed Home Assistant/manual release gates.
- Added documented backup/restore procedure for Fynvo persistent data under `/data`.
- Added explicit known limitations so deferred capabilities are not represented as delivered.

### Stable baseline
- Retains the v0.18.0 Category normalisation, merge, integrity, recurring duplicate-review, Card-integrity and commitment duplicate-suppression improvements.
- Retains authentication/bootstrap/recovery, Accounts, Cards, Transactions, Transfers, Income, Recurring Expenses, Bills, Planned Spending, Categories, Budgets, Forecasting, Financial Calendar, Scenarios, Goals, CSV import, reconciliation foundations, Spending Intelligence, Insights and responsive/mobile functionality.
- Retains the removal of the redundant Overview seven-day Upcoming card and the Income Date Range control.

### Versioning
- Version updated to 1.0.0 across the Home Assistant add-on, backend and frontend.

### Release gates
- Installed Home Assistant ingress, representative upgrade, iPhone/mobile acceptance and Home Assistant backup/restore must be recorded as manual release gates when they cannot be executed by automated repository tests.
- Fynvo v1.0.0 must not be represented as fully accepted until required manual gates are actually completed.

### Deferred
- Direct ING connectivity and a new production CDR/Open Banking provider.
- Automatic production bank sync and production-grade automatic reconciliation.
- Advanced household roles/permissions, immutable audit logs and complete user activity/change history.
- Home Assistant financial entities and standalone Cloudways deployment.

## v0.18.0 - Financial Data Integrity, Category Management & Workflow Polish

### Added
- Category merge preview and confirmation workflow that reassigns linked financial records and deactivates the source Category without deleting history.
- Category health checking for duplicate parents/children, orphan relationships, circular hierarchy, invalid/inactive references, stale Category paths and Category-type conflicts.
- Non-destructive recurring-expense duplicate review using normalised names, amount, cadence, payment source and due-date proximity.
- Card integrity diagnostics for orphan Cards and active Cards attached to archived Accounts.
- Upcoming Commitments service foundation with overdue inclusion and duplicate suppression.
- CI-equivalent local validation script for compile, Ruff, backend tests, frontend tests/build, metadata and Docker checks.

### Changed
- Category create and edit now treat case differences and repeated/leading/trailing whitespace as the same Category name within a parent.
- Parent merges safely consolidate duplicate child Categories while preserving linked values and history.
- Category management is more compact on mobile and no longer over-emphasises repeated `0 entries` links.
- Recurring Expenses surface possible duplicate groups for review without automatically merging them.
- Mobile financial record spacing is tightened while preserving touch targets.
- Version updated to 0.18.0 across the Home Assistant add-on, backend and frontend.

### Preserved
- Upcoming Commitments remains the authoritative outgoing-obligation list. The redundant seven-day Upcoming Overview card remains removed.
- Income remains independent of the global Date Range selector.
- Linked Bill/Recurring Expense schedule suppression and effective-dated recurring amount changes continue to preserve existing forecast behaviour.
- No direct ING integration, new production CDR provider, bank credentials or standalone Cloudways deployment is introduced in this release.

### Regression protection
- Category duplicate create/update coverage including case and whitespace normalisation.
- Category merge and linked-record preservation coverage.
- Category health duplicate-detection coverage.
- Non-destructive recurring duplicate review coverage.
- Commitment duplicate-suppression unit coverage.

## v0.17.0 - Core Reliability & Pre-v1.0 Hardening

### Fixed
- Fixed Account creation from Accounts > Add. The generic modal previously sent new Accounts to `PUT /api/accounts/null`, causing the literal `null` path segment to be parsed as integer `account_id`.
- Fixed the shared RecordTable create path so new records use `POST` create endpoints and existing records use ID-based `PUT` updates.
- Fixed transfers into liability accounts so a credit-card/loan payment reduces the amount owing.
- Reinforced the mobile navigation drawer so it remains off-canvas and closed by default at phone widths.
- Fixed Australian date-only display handling to avoid UTC-driven one-day shifts.

### Changed
- Added user-friendly Account Type labels and expanded stable account identifiers for Offset, Car Loan, Line of Credit, Investment and Superannuation while preserving legacy `vehicle_loan` compatibility.
- Added explicit asset/liability classification to Account responses.
- Available Cash now includes active Transaction, Savings, Offset and Cash accounts only.
- Liability opening balances are entered as positive amounts owing.
- Archived Accounts remain available historically but are excluded from active selectors and blocked from new manual transactions/transfers.
- Improved user-facing validation messages and compact mobile Account/page actions.
- Version updated to 0.17.0 across Home Assistant add-on, backend and frontend metadata.

### Regression protection
- Exact `Kristy - Main AC` create/edit regression coverage.
- Account balance and cent-precision regression coverage.
- Available Cash and liability transfer coverage.
- Archived-account write protection coverage.
- Frontend create-versus-update contract and mobile navigation regression coverage.
- v0.15 authentication/recovery/session tests retained.

### Pre-v1.0
- Added a v1.0 readiness report. Installed Home Assistant ingress acceptance, representative v0.16.0 upgrade testing and backup/restore validation remain release gates before stable v1.0.0.
- The actual merged repository does not contain the previously proposed Home Assistant financial sensors/entities, so this release does not claim them as delivered.
