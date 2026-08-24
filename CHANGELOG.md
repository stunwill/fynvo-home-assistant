# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.9.2 - Recurring Expense Persistence & Reference Data Fixes

### Fixed
- Corrected the Recurring Expense edit form so related controlled-field updates use current React state instead of stale render state, preventing valid values from being overwritten during editing and save preparation.
- Loaded authoritative Expense Type reference data into the active Recurring Expense editor and replaced the free-text Expense Type field with a dropdown that preserves existing/archived selections.
- Changed the Account form's user-facing `Institution` label to `Bank` without renaming or rewriting existing stored data.
- Limited new Account Type choices to `Transaction Account` and `Cash`, while retaining existing legacy Account Types when editing historical records.
- Updated Card creation so the saved Card is inserted into the visible Card state immediately, followed by the normal canonical data refresh. Navigation away and back is no longer required.
- Renamed `Confirmation grace period` to `Payment confirmation period` and added an explanation that it controls how long Fynvo waits after the due date for automatic-payment confirmation, not the payment due date itself.
- Restored nullable Account/Card defaults for new Recurring Expenses and improved validation messaging for invalid Expense Type references.

### Preserved behaviour
- Preserved v1.9.1 mobile modal positioning, horizontal containment, sticky actions and Payment Method selection behaviour.
- Preserved v1.7 Account → Card relationships, Scheduled Payments and reconciliation.
- Existing legacy Account Types and existing financial records are not destructively migrated.

### Testing and versioning
- Added focused v1.9.2 frontend regression coverage for Account choices, Bank terminology, Expense Type reference data, Card refresh, confirmation-period help and nullable recurring references.
- Updated Home Assistant add-on, backend, frontend package and production-shell metadata to v1.9.2.
- Installed iPhone/Home Assistant Edit → Save → reload → reopen acceptance remains a manual release gate before merge.

## v1.9.1 - Recurring Expense Mobile Modal & Payment Fixes

### Fixed
- Kept the Recurring Expense editor below Fynvo's fixed mobile application bar so the modal heading and close action remain visible.
- Removed the mobile horizontal/sideways movement by constraining the recurring editor, Payment fieldset, form controls and explanatory copy to the available viewport width.
- Kept the recurring modal header and Save/Cancel footer accessible while the form content scrolls vertically inside the viewport-contained dialog.
- Fixed Payment Method selections reverting to `Not Set`. Payment Method is now applied as a single controlled state transition rather than being overwritten by stale Account/Card-clearing updates.

### Preserved behaviour
- Preserved v1.7 Payment Handling, Account → Card relationships, Scheduled Payments and reconciliation.
- Preserved v1.8 Recurring Expenses List, Calendar, filters, summary and responsive page experience.
- Preserved v1.9.0 edit/save and nullable-reference corrections.
- No database migration is required.

### Testing and versioning
- Added focused v1.9.1 frontend regression coverage for Payment Method state, conditional payment-source fields, mobile modal containment, sticky controls and stylesheet ordering.
- Updated Home Assistant add-on, backend, frontend package and production shell metadata to v1.9.1.
- Installed iPhone/Home Assistant ingress acceptance remains a manual release gate before merge.

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
