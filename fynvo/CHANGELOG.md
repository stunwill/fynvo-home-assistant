# Fynvo Add-on Changelog

## v1.16.3 - Accounts & Cards Consolidation, Archiving & Reassignment

- Combines Accounts and Cards into one responsive Accounts & Cards workspace with an Accounts/Cards segmented view control based on the supplied desktop and mobile designs.
- Replaces the old Account-grouped Cards page with a Card-first list so Accounts with no Cards no longer create empty sections.
- Adds Account archiving and restoration while preserving historical financial records.
- Adds Account dependency analysis and an explicit Move records & archive workflow for eligible Transactions, Cards and future Account configuration.
- Preserves protected historical Transactions, Scheduled Payments and Transfers during consolidation instead of blindly changing Account foreign keys.
- Allows permanent Account deletion only when no dependencies remain and explains blockers otherwise.
- Keeps archived Accounts out of normal new Card/financial-record destination selectors while retaining their historical names and relationships.
- Adds compact responsive layouts for desktop, tablet, iPhone and Home Assistant ingress.
- Aligns production-shell, frontend, backend and Home Assistant add-on version reporting to v1.16.3.

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

- Added authoritative Scheduled Payment lifecycle behaviour for recurring obligations.
- Added manual Mark as Paid, Skip Payment, automatic-payment confirmation and payment-attention workflows.
- Added expected-versus-actual payment history and reconciliation support while preserving recurring rules.

## Earlier releases

See the repository root CHANGELOG.md for the complete historical release record.