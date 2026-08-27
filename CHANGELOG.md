# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.14.0 - Recurring Payment Occurrence Overrides

### One-off scheduled payment dates
- Added first-class `Change payment date` support for an individual Scheduled Payment without modifying the parent Recurring Expense rule.
- Added an immutable generated occurrence date alongside the effective expected date so a moved payment remains the same logical occurrence and cannot be regenerated on its original date.
- Added `Restore original date` for unresolved overridden payments without creating replacement Scheduled Payments.
- Preserved future recurrence generation from the authoritative recurring rule. Moving one monthly, fortnightly, 28-day or custom occurrence does not re-anchor later dates.

### Failed and unconfirmed automatic payments
- Automatic Direct Debit and Automatic Card Payment occurrences can be moved to a later retry date while remaining unpaid.
- Status is recalculated from the effective expected date, so an unconfirmed past automatic payment moved into the future returns to an appropriate expected-automatic state rather than remaining overdue solely because its original date passed.
- Payments Requiring Attention and Payment Centre both expose the one-off date-change workflow.

### Expected versus actual history
- Scheduled Payments retain the original expected date, effective expected date and actual payment date as separate financial facts.
- Date changes write auditable history containing the previous date, new date, source, optional reason/note and timestamp.
- Paid, matched and other completed financial history cannot be silently rescheduled. Matched payments must be unmatched before an expected-date correction.
- Rescheduling never changes `actual_date` or a matched Transaction date and never marks a payment paid.

### Schedule, forecast and reconciliation consistency
- Schedule materialisation now keys logical occurrence identity from the immutable generated date while using the effective expected date for current status.
- Repeated generation remains idempotent after an override and cannot recreate the original-date occurrence.
- Calendar, Overview commitments, Cash Flow and Forecast recurring events now consume effective Scheduled Payment dates so a moved occurrence appears once on the new date.
- Transaction matching continues to use the effective expected date for date proximity while preserving existing amount, account, merchant, learned-mapping and one-to-one safeguards.

### Payment Centre and mobile UX
- Payment Centre shows a subtle `Date changed` indicator only for overridden Scheduled Payments and displays `Usual payment date` and `Expected this time` in payment detail.
- Added optional reasons including failed payment, provider date change, insufficient funds, deferred payment and user-requested date changes.
- The occurrence editor uses the existing top-layer modal protections, closes the originating payment detail before opening, prevents mobile horizontal overflow and keeps Save/Cancel controls accessible in Home Assistant and iPhone-sized viewports.

### Data migration and regression protection
- Added an additive, idempotent schema migration that backfills existing Scheduled Payments with their current expected date as the original occurrence identity. Existing payment status, reconciliation links and household records are preserved.
- Added backend regression coverage for future monthly overrides, repeated generation, failed automatic retries, restore behaviour, audit history, completed-payment protection, effective-date matching and cross-screen consistency.
- Added frontend regression coverage for Payment Centre and Payments Requiring Attention date-change actions plus mobile modal containment.

### Versioning
- Selected v1.14.0 from the merged v1.13.0 baseline after confirming PR #53 was merged and no overlapping Fynvo PR remained open.
- Corrected inherited metadata drift and aligned Home Assistant add-on, backend, frontend package and production-shell versioning to v1.14.0.
- Installed Home Assistant and iPhone verification remains required before merge and is not represented as completed by repository CI.

## v1.10.1 - Installed Reliability, API & Workflow Hardening

### Recurring Expense persistence
- Replaced the loose Recurring Expense update payload with the canonical v1.7 payment-aware request contract, so Payment Handling, Payment Method, Card/Account relationships, Expense Type, Payee/Merchant, Notes and confirmation-period fields are validated consistently before persistence.
- Added an end-to-end backend regression that creates a representative iCloud Storage recurring expense, updates it, performs a fresh GET and verifies the changed values remain persisted.
- Added a specific invalid-card regression so Automatic Card Payment returns an actionable validation error instead of a generic save failure.

### Loading and performance hardening
- Reduced the Recurring Expenses critical loading path from three requests to two by deriving payment-attention rows from the authoritative Scheduled Payments response rather than invoking the schedule-generation endpoint a second time.
- Removed the fast-data mirroring effect that could repeatedly copy parent application state back into the Recurring Expenses local state.
- Allows already-loaded recurring data to render immediately while a background refresh runs, while still preserving distinct Loading, Error and Loaded behaviour when no authoritative data is available.

### Regression protection
- Added v1.10.1 frontend regression coverage for the focused recurring-data path, existing-data rendering, canonical recurring mutation normalization and payment configuration fields.
- Preserved v1.9.3 mobile navigation, v1.9.1 mobile modal containment, Category integrity behaviour and existing financial data.

### Versioning
- Updated Home Assistant add-on, backend, frontend package, production shell and corrective-module version metadata to v1.10.1.
- Installed Home Assistant/iPhone acceptance remains an explicit user-verification requirement before merge and is not represented as completed by repository CI.

## v1.10.0 - Workflow Reliability, Performance & Data Integrity

### Reliability and API handling
- Added a canonical ingress-safe frontend API client with consistent relative request paths, JSON handling, structured errors and development-only slow-request diagnostics.
- Hardened Recurring Expense save/update handling so nullable reference/date fields are normalized before mutation, API errors are surfaced with useful validation detail, and successful mutations refresh only the Recurring Expense data slice instead of blocking on every Fynvo dataset.
- Cleared feature-specific errors when navigating between Fynvo screens so stale operation errors do not leak into unrelated workflows.

### Recurring Expense loading and performance
- Split Recurring Expenses into explicit Loading, Error, Empty/Loaded behaviour. Existing expenses are no longer represented as an empty dataset while their authoritative requests are still in flight.
- Added a retry state for failed recurring-data requests.
- Retained the focused Recurring Expenses fast-loading path so slow Insights, Forecast, Budgeting or reconciliation requests do not block primary recurring rules and scheduled payments from rendering.

### Data integrity and regression protection
- Preserved the v1.9.3 mobile navigation hotfix and the v1.9.1 mobile recurring-modal containment fixes.
- Added frontend regression coverage for ingress-safe requests, recurring loading/error states, nullable mutation normalization, focused refresh behaviour and error lifecycle.
- Added backend API-contract coverage for nullable Recurring Expense references and invalid empty-string ID payloads.

### Versioning
- Updated Home Assistant add-on, backend, frontend package and production shell metadata to v1.10.0.

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

See repository history for earlier releases.
