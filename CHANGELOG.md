# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.16.2 - Cash Flow, Calendar & Overview UX Corrections

### Cash Flow
- Reworks Cash Flow as the financial-impact workspace, with the forecast graph near the top, a compact Starting Balance / Income / Outgoing / Net Movement / Projected Balance / Lowest Balance summary, and an "Events affecting this forecast" section focused on the largest balance movements rather than another full chronological calendar list.
- Reuses the authoritative forecast already returned to Overview for the selected range so navigating Overview → Cash Flow can render immediately without waiting for the same complete baseline/expected forecast to be requested again.
- Requests only a missing baseline or expected series when the shared forecast is incomplete, rather than automatically requesting both again.
- Keeps explicit loading, loaded, genuine-empty, refresh and error states. Loading is never represented as zero events, and usable forecast information remains on screen if a later refresh fails.
- Preserves the existing forecast engine and financial-event model. Summary fallbacks are derived only from the authoritative forecast response/events when a dedicated aggregate field is unavailable.

### Calendar
- Clarifies Calendar as the date-oriented workspace: "what is happening and when". Financial events are grouped by date and selecting a date shows the events for that day, rather than mirroring Cash Flow's financial-impact presentation.
- Strengthens the existing local-current-day treatment in the Recurring Expenses month calendar for installed mobile/Home Assistant use. Today's cell receives a light Fynvo-blue background and strong blue inset outline, while the date number is rendered in a solid blue marker with white text.
- Loads the v1.16.2 calendar override after prior mobile/corrective styles and targets both the semantic `aria-current="date"` state and the existing `today` class so older CSS cannot silently hide the treatment.
- Preserves payment-status colours within the highlighted current-day cell.

### Overview drill-down navigation
- Makes the primary Overview KPI cards actionable and keyboard-accessible.
- Total Balance opens Accounts, Next Income opens Income, Upcoming Commitments opens Payment Centre, Discretionary opens Planned Spending and Goals opens Goals.
- Renames the previous "Next Bills" card to "Upcoming Commitments" because its amount is sourced from Payment Planning unresolved commitments rather than only Bill records.
- Adds sensible drill-through to Cash Flow Forecast / Forecast Summary, Financial Health, Money Needed Soon, Upcoming Commitments and planned-spending summaries.
- Preserves the global date range and uses in-app navigation rather than a full browser reload.

### Mobile, performance and data safety
- Adds responsive Cash Flow summary and Calendar selected-date layouts for tablet, iPhone-sized and Home Assistant ingress viewports.
- Keeps cached forecast information scoped by selected horizon and invalidates it after forecast-affecting financial mutations so speed improvements do not introduce stale financial truth.
- Preserves the Recurring Expense → Scheduled Payment → Transaction → Reconciliation lifecycle and introduces no database migration or parallel finance model.

### Versioning and validation
- Selected v1.16.2 as a corrective patch on the merged v1.16.1 baseline. The planned v1.17.0 Pay-Cycle Cash Planning scope remains unchanged.
- Aligned Home Assistant add-on, backend, frontend package, production shell and active frontend version markers to v1.16.2.
- Added regression coverage for installed current-day styling, forecast reuse/loading behaviour, Calendar/Cash Flow responsibility separation and Overview drill-down mappings.
- Installed Home Assistant, tablet, iPhone and ingress visual acceptance remains a manual verification requirement and is not represented as completed by repository CI.

## v1.16.1 - Calendar, Payment Centre & Cash Flow UX Corrections

### Calendar
- Highlights the actual local current day in the Recurring Expenses month calendar with a subtle Fynvo-blue cell treatment and a stronger blue date marker.
- Preserves the existing payment-status colours inside today's cell and adds `aria-current="date"` so the current day is not communicated by colour alone.
- Keeps adjacent-month dates muted and avoids highlighting an arbitrary date when the current month is not being viewed.

### Payment Centre
- Introduces a simplified grouped Payment Centre as the default presentation while continuing to use the authoritative `/payment-centre` and `/payment-planning` services.
- Reorganises the top of the page around Money Required Soon, Upcoming at a Glance and one compact summary strip for total scheduled, overdue, due soon, upcoming and paid obligations.
- Moves Account funding requirements and available-funds comparisons behind expandable Funding Details without changing unknown-balance safeguards.
- Reduces the default filter surface to Search, Date Range, Status and Category, with Account, Card, payment method, payment handling and action-only filtering under More Filters.
- Groups payment rows into Overdue, Due in Next 7 Days, Due Later, No Date Set and Payment History sections, shows a compact preview for large groups and provides explicit View All controls.
- Keeps the existing detailed chronological Payment Centre available as a persisted secondary view so advanced lifecycle details, rescheduling, skip/restore, reconciliation and other existing actions remain available.
- Keeps a direct Mark as Paid workflow in the simplified grouped view for eligible manual payments.

### Cash Flow
- Restores the existing Cash Flow Forecast graph to the main Cash Flow page above the forecast-event list.
- Corrects the routing regression where the Cash Flow navigation rendered only the event list even though the reusable forecast graph component still existed and remained in use on Overview.
- Loads baseline and expected forecast series from the authoritative forecast API for the selected global date range.
- Adds explicit loading, refresh, no-data and error/retry states rather than presenting loading or failure as zero financial activity.

### Responsive UX and data safety
- Adds responsive layouts for the simplified Payment Centre and restored Cash Flow graph across desktop, tablet, mobile and Home Assistant ingress-sized viewports.
- Preserves the existing Recurring Expense → Scheduled Payment → Transaction → Reconciliation architecture and introduces no database migration or duplicate financial model.
- Preserves previously loaded Payment Centre and Cash Flow information during refresh where possible.

### Versioning
- Selected v1.16.1 as a corrective patch on the merged v1.16.0 baseline, leaving the planned v1.17.0 Pay-Cycle Cash Planning scope intact.
- Aligned Home Assistant add-on, backend, frontend package, production shell and active frontend version markers to v1.16.1.
- Installed Home Assistant, tablet, iPhone and ingress visual acceptance remains a manual verification requirement and is not represented as completed by repository CI.

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

### Scheduled Payment occurrence overrides
- Added occurrence-safe Skip Payment and Restore Payment handling for unresolved Scheduled Payments without modifying the parent Recurring Expense rule.
- Preserves original occurrence identity and history while allowing effective expected date/status changes.

### Automatic-payment lifecycle
- Improved automatic-payment attention states and review handling.
- Skipped and cancelled occurrences remain excluded from active forecasts, calendars and normal reconciliation candidates.

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
- Updated add-on, backend, frontend package and production-shell release metadata to v1.10.1.
- Real installed Home Assistant/iPhone acceptance remains a required manual verification before merge.
