# Fynvo Add-on Changelog

## v1.17.1 - Home Assistant Startup Loading Fix

- Fixes the installed ingress startup condition where the outer Fynvo shell was authenticated but the nested main app could remain on `Loading...` while waiting for a second auth-state request.
- Reuses the outer shell's already-known authentication state for the nested startup auth read, while keeping normal login, logout and session refresh requests authoritative.
- Preserves all v1.17.0 pay-cycle, payment-planning, Cash Flow, Calendar, Accounts/Cards and reconciliation behaviour.
- Adds regression protection for the duplicated startup auth path.
- Requires no database migration.

## v1.17.0 - Pay-Cycle Cash Planning

- Adds a Before next pay plan based on the chronologically next active Income occurrence and the existing Australia/Melbourne financial calendar.
- Shows cash required before that Income, current active liquid cash, projected cash immediately before pay and projected cash immediately after pay.
- Includes unresolved Scheduled Payments, Bills, overdue obligations, automatic payments requiring funding and forecast-included Planned Spending while preserving existing duplicate suppression and payment lifecycle exclusions.
- Adds Account-level funding pressure and derives Card-funded commitments through the Card's linked Account without double-counting Card balances.
- Handles unknown Income, unassigned commitments, archived/liability Accounts and incomplete funding information explicitly instead of treating missing values as zero.
- Adds the compact Before next pay summary to Overview and the detailed operational summary to Payment Centre with responsive iPhone/Home Assistant ingress layouts.
- Reconciles baseline Cash Flow and Calendar recurring outflows with authoritative Scheduled Payment lifecycle state, including skipped, reconciled and rescheduled occurrences.
- Keeps preferred minimum-balance buffers neutral because the current Account model has no authoritative configured buffer field.
- Requires no database migration and preserves existing household financial records.
- Aligns add-on, backend, frontend package and production-shell version reporting to v1.17.0.

## v1.16.3 - Accounts & Cards Consolidation, Account Archiving & Record Reassignment

- Combines Accounts and Cards into one responsive Accounts & Cards workspace with Accounts / Cards segmented views.
- Removes the separate top-level Cards destination and replaces account-grouped Card sections with a compact card-first Cards list that shows each linked Account.
- Adds Account archiving, archived filtering, restoration and dependency-aware permanent-delete protection.
- Adds optional Move records & archive with explicit active destination selection, transactional rollback and preservation of historical Scheduled Payments, Transfers and protected Transactions.
- Prevents unsafe Transaction reassignment when opening-balance, reconciliation or asset/liability balance semantics would be changed.
- Keeps archived Accounts out of normal new-record selectors while preserving historical Account references.
- Adds desktop, tablet, mobile and Home Assistant ingress-responsive layouts, compact rows, search/filtering and context-aware Add Account / Add Card actions.
- Aligns add-on, backend, frontend package and production-shell version reporting to v1.16.3.

## v1.16.2 - Cash Flow, Calendar & Overview UX Corrections

- Makes Cash Flow a financial-impact workspace with a prominent forecast graph, balance summary and largest forecast-impact events rather than duplicating Calendar's chronological purpose.
- Reuses the Overview forecast for the selected range and only requests missing forecast series, reducing repeated work when navigating Overview → Cash Flow.
- Prevents loading from appearing as "0 forecast events" or a genuine empty state and keeps usable forecast data visible if a refresh fails.
- Clarifies Calendar as the date-oriented "what and when" workspace with selected-date event details.
- Strengthens the Recurring Expense Calendar's local-current-day blue highlight so it remains obvious on iPhone and Home Assistant ingress while preserving payment-status colours.
- Makes Overview KPI cards and relevant summary panels drill down to Accounts, Income, Payment Centre, Planned Spending, Goals and Cash Flow as appropriate.
- Aligns production-shell, frontend, backend and Home Assistant add-on version reporting to v1.16.2.

## v1.16.1 - Calendar, Payment Centre & Cash Flow UX Corrections

- Highlights today's date in the recurring-expense month calendar with a clear blue treatment while preserving payment-status colours.
- Simplifies Payment Centre around the authoritative Payment Planning service with a clearer summary, compact filters, expandable funding details and grouped payment sections.
- Keeps the detailed chronological Payment Centre available for full lifecycle actions while making the grouped view the default.
- Restores the Cash Flow forecast graph above the event list and adds explicit loading, no-data and error/retry states.
- Aligns production-shell, frontend, backend and Home Assistant add-on version reporting to v1.16.1.

## v1.16.0 - Payment Planning, Upcoming Commitments & Cash Requirements

- Added Money Needed Soon planning for the next 7, 14 and 30 days.
- Added chronological upcoming-payment views and account funding requirements.
- Added conservative available-funds and likely-shortfall visibility without treating unknown balances as zero.
- Improved Payment Centre and Overview consistency by using the same authoritative payment-planning calculations.
- Improved payment lifecycle details, filters and mobile/Home Assistant ingress layouts.

## v1.15.0 - Recurring Payment Scheduling & Lifecycle

- Added occurrence-safe Skip Payment and Restore Payment handling for unresolved Scheduled Payments.
- Improved automatic-payment attention states and payment lifecycle history.
- Kept skipped and cancelled occurrences out of active forecasts, calendars and normal reconciliation candidates.
- Improved mobile Payment Centre lifecycle workflows and modal behaviour.

## v1.14.0 - Recurring Payment Occurrence Overrides

- Added one-off Scheduled Payment date changes without modifying the parent Recurring Expense.
- Added Restore Original Date for unresolved occurrences.
- Preserved original occurrence identity while using the effective expected date across status, forecasts and reconciliation.
- Improved mobile payment-date editing and lifecycle history.

## v1.13.0 - Payment Centre Completion & Dashboard Integration

- Completed Payment Centre integration with dashboard and payment-attention workflows.
- Improved payment status, filtering and household obligation visibility.
- Strengthened consistency between bills, scheduled payments and recurring expenses.
- Improved responsive behaviour for Home Assistant and mobile layouts.

## v1.12.0 - Bills, Payment Centre & Household Obligations

- Expanded Bills and Payment Centre into a unified household obligations workflow.
- Improved payment status, automatic/manual handling and scheduled-payment visibility.
- Added clearer actions for payments requiring attention.
- Preserved existing recurring-payment and reconciliation data.

## v1.11.1 - Financial Event Consistency, Forecast & Calendar Fixes

- Corrected the v1.11 command-centre/frontend contract so Overview consumes `available_cash`, `scheduled_commitments`, forecast events and upcoming commitments from their authoritative response fields.
- Restored Calendar population by using the canonical upcoming/forecast event data instead of the removed `command.calendar` field.
- Fixed Forecast Summary Lowest Balance handling so the nested forecast balance value is rendered instead of the object itself.
- Hardened currency rendering so invalid/non-finite numeric values cannot appear as `$NaN`, `Infinity` or `-Infinity`.
- Restored the Overview Cash Flow Forecast by consuming the backend's canonical `chart_points` series.
- Corrected the mobile Cash Flow event presentation so forecast events render as contained, readable rows rather than oversized grey blocks.
- Preserved existing Recurring Expenses, Scheduled Payments, Transactions, reconciliation relationships and household financial data without a destructive migration.
- Updated frontend, backend, add-on and production-shell metadata to v1.11.1.
- Installed Home Assistant/iPhone cross-screen acceptance remains a manual verification gate.

## v1.10.1 - Installed Reliability, API & Workflow Hardening

- Hardened the Recurring Expense update contract so payment-aware fields are validated and persisted through the active v1.7 endpoint.
- Added fresh-fetch persistence coverage for representative Recurring Expense edits, including payment configuration, Card linkage, Expense Type, Payee/Merchant and Notes.
- Reduced the Recurring Expenses critical load path by deriving payment-attention rows from Scheduled Payments instead of making a second schedule-generation request.
- Removed a fast-state synchronisation loop risk and allows already-loaded Recurring Expense data to remain visible while a focused refresh runs.
- Preserved existing Accounts, Cards, Categories, Scheduled Payments, mobile navigation and mobile modal behaviour without a destructive data migration.
- Updated add-on, backend, frontend package, production shell and corrective-module version metadata to v1.10.1.
- Real installed Home Assistant/iPhone acceptance remains a required manual verification before merge.

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