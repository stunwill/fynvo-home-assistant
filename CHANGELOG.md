# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

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
