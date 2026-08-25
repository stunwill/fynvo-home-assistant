# Fynvo Add-on Changelog

## v1.10.1 - Installed Reliability, API & Workflow Hardening

- Hardened the Recurring Expense update contract so payment-aware fields are validated and persisted through the active v1.7 endpoint.
- Added fresh-fetch persistence coverage for representative Recurring Expense edits, including payment configuration, Card linkage, Expense Type, Payee/Merchant and Notes.
- Reduced the Recurring Expenses critical load path by deriving payment-attention rows from Scheduled Payments instead of making a second schedule-generation request.
- Removed a fast-state synchronisation loop risk and allows already-loaded Recurring Expense data to remain visible while a focused refresh runs.
- Preserved existing Accounts, Cards, Categories, Scheduled Payments, mobile navigation and mobile modal behaviour without a destructive data migration.
- Updated add-on, backend, frontend package and production-shell release metadata to v1.10.1.
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

See repository history for earlier add-on release entries.
