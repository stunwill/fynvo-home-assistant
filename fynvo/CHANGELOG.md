# Fynvo Add-on Changelog

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
