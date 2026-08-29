# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.16.0 - Payment Planning, Upcoming Commitments & Cash Requirements

### Payment planning and Money Needed Soon
- Added a shared backend Payment Planning service over authoritative Bills and Scheduled Payments, without introducing another payment, transaction or recurrence model.
- Added Today, Next 7 Days, Next 14 Days and Next 30 Days planning summaries with total commitments, payment counts, manual and automatic funding, overdue obligations, unresolved automatic payments, paid amounts and remaining funding requirements.
- Automatic Direct Debits and Automatic Card Payments continue to require funding until they are paid/reconciled, even when no manual payment action is required.
- Paid, reconciled, skipped and cancelled obligations are excluded from unresolved funding requirements.
- Linked Bills suppress the matching Scheduled Payment occurrence when both represent the same Recurring Expense and effective date, preventing double-counted household commitments.

### Account funding and shortfall visibility
- Added next-7-day account funding requirements using existing Account and Card relationships, including automatic Card to Account derivation.
- Obligations with no determinable funding Account are grouped as `Account not specified` rather than silently assigned.
- Available-funds comparisons reuse active liquid Account balances derived from opening balance plus actual Transactions. Liability and unknown balances are not treated as available cash.
- Household shortfall calculations are shown only when the complete relevant funding picture is known. Unknown balances are never represented as $0.

### Payment Centre and Overview
- Added a chronological Payment Centre timeline grouped by effective payment date, with Today/Tomorrow/date headings and concise status, payment method, Account/Card and source information.
- Added Payment Centre planning cards for Money Needed Soon, account funding requirements, available funds and likely shortfalls.
- Added Today and Next 14 Days to Payment Centre date filtering and retained combined filtering for status, source, category, payment method/handling, Account, Card and action-required state.
- Overview now consumes the same `/payment-planning` service as Payment Centre for Money Needed Soon, payment-attention counts, next payment and upcoming commitments. The previous independent Overview money calculation was removed.
- Payment details prioritise useful lifecycle information, including occurrence date, current expected date, actual date, payment handling, funding Account, Card, skip/reschedule notes, matched Transaction and lifecycle history, while hiding empty fields.

### Lifecycle and route integrity
- Preserved the authoritative Recurring Expense → Scheduled Payment → Transaction → Reconciliation architecture.
- Made v1.14 occurrence-safe Scheduled Payment materialisation authoritative wherever payment screens request occurrence generation.
- Removed the remaining legacy duplicate Skip Payment route and retained the v1.15 lifecycle implementation as the single authoritative skip mutation path.
- Overdue unresolved obligations are included in Next 7/14/30 Day planning views so visible Payment Centre rows can reconcile to Money Needed Soon totals.

### Mobile, Home Assistant ingress and accessibility
- Added responsive planning and funding layouts that collapse cleanly on tablet and iPhone-sized viewports.
- Added page-level horizontal containment, wrapping for long payment names, mobile-friendly timeline cards, safe-area-aware modals and sticky modal actions.
- Preserved semantic buttons, labels, status text, keyboard-accessible controls and status communication that does not rely on colour alone.

### Data safety and regression protection
- v1.16.0 introduces no database migration. Existing Recurring Expenses, Bills, Scheduled Payments, Transactions, reconciliation relationships, occurrence identities and lifecycle history remain in place.
- Added backend regression coverage for 7/14/30-day planning, automatic funding, paid/skipped/cancelled exclusion, restoration, rescheduling, occurrence identity, account aggregation, Card-to-Account derivation, unknown funding, shortfalls, overdue inclusion, Bill/Scheduled Payment deduplication, reconciliation and duplicate route/materialisation protection.
- Added frontend source-level regression coverage for shared Overview/Payment Centre planning, timeline grouping, status/attention clarity, funding/shortfall states, filters, lifecycle detail, mobile containment and modal layering.

### Versioning
- Selected v1.16.0 from the merged v1.15.0 baseline after confirming PR #55 was merged and no Fynvo PRs were open at implementation start.
- Aligned Home Assistant add-on, backend, frontend package and production-shell version metadata to v1.16.0.
- Installed Home Assistant, tablet, iPhone and ingress acceptance remains a manual verification requirement and is not represented as completed by repository CI.

## v1.15.0 - Recurring Payment Scheduling & Lifecycle

### Scheduled Payment lifecycle
- Formalised occurrence-level lifecycle behaviour around the existing Scheduled Payment model without introducing another recurrence engine.
- Completed occurrence-safe `Skip Payment` handling for unresolved Scheduled Payments. Skipping one payment does not edit the parent Recurring Expense, re-anchor future dates or create another occurrence on regeneration.
- Added optional household-friendly skip reasons and notes, including paused, waived and user-requested payments.
- Added `Restore payment` for safely reactivating the same skipped Scheduled Payment. Restoration retains the immutable recurrence occurrence identity and preserves any existing one-off expected-date override.
- Paid, matched and otherwise protected financial history cannot be silently skipped or restored.

### Automatic payments and attention states
- Preserved the existing distinction between `Expected automatically` and `Auto payment unconfirmed`; passing an expected automatic-payment date does not create a Transaction or mark a payment paid.
- Kept failed/delayed automatic payments compatible with the v1.14 `Change payment date` workflow so a retry date changes only that occurrence and continues to use the effective expected date for status and reconciliation.
- Payment Centre now presents concise attention reasons such as unconfirmed automatic payments, overdue payments and possible transaction matches.

### Payment Centre and audit history
- Added a dedicated Skip Payment confirmation workflow with optional reason/note and clear copy explaining that the recurring schedule is not changed.
- Added Restore payment for skipped Scheduled Payments and retained `Change payment date` / `Restore original date` for unresolved occurrences.
- Added a focused Scheduled Payment detail endpoint that exposes lifecycle history, skip metadata and matched-transaction evidence without overloading Recurring Expense mutation routes.
- Skip and restore actions write meaningful Scheduled Payment history with source, state transition, reason/note and timestamp. Restoring clears the current skip marker while preserving the historical audit event.

### Forecast, matching and occurrence integrity
- Preserved the v1.14 immutable `occurrence_date` as the logical occurrence identity and `expected_date` as the effective operational date.
- Skipped and cancelled occurrences remain excluded from canonical active schedule/forecast events and normal reconciliation candidates.
- Repeated materialisation recognises skipped, restored, overridden and completed logical occurrences and does not recreate the original occurrence or shift future recurrence dates.
- Existing linked-Bill suppression, effective-date amount/scenario behaviour and cross-screen financial-event consistency remain intact.

### Mobile and Home Assistant UX
- Extended Payment Centre mobile modal protections to the Skip Payment workflow.
- Lifecycle modals remain within the dynamic viewport, avoid horizontal overflow, close the originating detail layer before opening and keep confirmation controls accessible in Home Assistant ingress and iPhone-sized layouts.

### Data migration and regression protection
- Added a small additive and idempotent migration for current skip metadata (`skip_reason`, `skip_note`, `skipped_at`, `skipped_by_user_id`) without resetting Scheduled Payments, reconciliation links or household data.
- Added backend regression coverage for monthly skip identity, repeated materialisation, overridden-then-skipped restoration, audit history, forecast/match exclusion, completed-payment protection and migration idempotency.
- Added frontend regression coverage for Skip/Restore actions, focused detail routing, attention wording, mobile modal containment and v1.15.0 production version reporting.

### Versioning
- Selected v1.15.0 after confirming v1.14.0/PR #54 was merged into `main`, no Fynvo PRs were open, and no later GitHub Release was published when implementation began.
- Aligned Home Assistant add-on, backend, frontend package and production-shell version metadata to v1.15.0.
- Installed Home Assistant, iPhone, tablet and ingress acceptance remains a manual verification requirement and is not represented as completed by repository CI.

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