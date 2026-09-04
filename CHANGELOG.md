# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.17.6 - Accounts & Cards Installed Interactivity Correction

- Fixes the installed Home Assistant/iPhone condition where Accounts & Cards rendered successfully but the page and surrounding Home Assistant controls became unresponsive to taps/clicks.
- Identifies the cause in the v1.16.3 Accounts/Cards compatibility wrapper: its document-wide `MutationObserver` rewrote the same page description on every callback, and that write retriggered the same observer indefinitely.
- Makes the observer idempotent by changing the heading/description only when the DOM actually differs from the expected Accounts & Cards state.
- Avoids repeatedly setting the same portal mount node, reducing unnecessary React state work while the compatibility observer is active.
- Keeps the v1.17.5 single-owner authentication/startup lifecycle and installed startup diagnostics unchanged.
- Aligns the production release version to v1.17.6. The outer production shell remains authoritative for the visible footer so an installed build can be verified directly in the UI.
- Adds regression protection that rejects unconditional self-triggering Accounts/Cards DOM writes and repeated identical portal mount state.
- No database migration is required and no financial calculations, records, payment lifecycle, forecasting, Accounts or Cards data are changed.

## v1.17.5 - Frontend Startup Lifecycle Correction & Diagnostics

- Uses evidence from the installed Home Assistant and Fynvo add-on logs: authentication, household security, Accounts and Cards requests were returning successfully while the iPhone webview still remained on the Fynvo loading screen.
- Removes the global `fetch` authentication bridge and the keyed automatic startup remount/watchdog from the production shell. A successful outer authentication now mounts one workspace instance and keeps it mounted.
- Keeps the v1.17.4 direct `authState` prop handoff through the Accounts/Cards compatibility wrapper into the base workspace, while removing the shared-global auth mutation from that wrapper.
- Restricts the compatibility wrapper's Accounts/Cards bootstrap calls to authenticated sessions.
- Removes the production `React.StrictMode` wrapper so the installed startup lifecycle and diagnostic sequence have one root mount.
- Adds explicit installed-runtime startup stages (`authenticated`, `workspace-mounted`, `workspace-rendered`) and records them in the Fynvo add-on log through a lightweight diagnostic endpoint.
- Marks the HTML app shell as non-cacheable at document level so Home Assistant's embedded webview is less likely to retain a stale shell across add-on upgrades. Hashed built assets remain managed by Vite.
- Adds regression coverage that rejects the removed auth bridge, keyed remount path and StrictMode wrapper, verifies direct auth propagation, startup diagnostics and no-cache document metadata.
- Preserves all financial calculations, records and payment lifecycle behaviour. No database migration is required.

## v1.17.4 - Direct Home Assistant Auth State Handoff

- Fixes the remaining installed iPhone/Home Assistant ingress freeze where the outer shell was authenticated but the inner workspace could still remain indefinitely on its `Loading...` splash.
- Identifies the underlying wrapper-chain defect: `AppCorrectiveV1163` received the authoritative `authState` from `AppV13` but rendered `AppCorrectiveV0174` without passing that state through.
- Passes the authenticated state directly through the complete production component chain and initialises the base workspace from it synchronously.
- Removes the second startup `/auth/state` dependency from the normal Home Assistant path. The base workspace only performs its own auth request when it is genuinely running without an outer/shared state, preserving standalone login/setup behaviour.
- Keeps the v1.17.3 non-blocking household-security request, temporary-password enforcement and recovery controls.
- Adds regression coverage for the complete auth-state prop chain and specifically rejects the previous unconditional base-workspace startup auth effect.
- Preserves all financial workflows and data. No database migration is required.

## v1.17.3 - Non-blocking Household Identity Startup

- Fixes the installed iPhone/Home Assistant ingress freeze where Fynvo could remain indefinitely on `Loading Household identity...` after authentication had already succeeded.
- Removes the secondary `/household/me/security` request as a mandatory render gate for the main Fynvo workspace.
- Gives the household-security refresh a 3.5-second abort timeout so a pending Home Assistant webview request cannot remain open forever.
- Keeps temporary-password enforcement active whenever household security state is returned, while allowing the finance workspace to continue rendering if the secondary security-status refresh is unavailable.
- Adds an explicit non-blocking Retry security check action instead of replacing the entire application with an endless loading card.
- Preserves the v1.17.2 authentication bridge, startup watchdog and Retry Fynvo recovery path.
- Preserves all v1.17 pay-cycle planning, Payment Centre, Cash Flow, Calendar, Accounts/Cards and reconciliation behaviour. No database migration is required.

## v1.17.2 - Home Assistant Ingress Startup Recovery

- Corrects the installed iPhone/Home Assistant ingress startup path after v1.17.1 still reproduced an authenticated outer shell with the nested Fynvo workspace frozen on `Loading...`.
- Publishes the authenticated outer-shell state synchronously before the nested workspace mounts and accepts both relative and ingress-expanded `/api/auth/state` request URLs.
- Replaces the synthetic browser `Response` dependency in the startup bridge with a minimal response-compatible result used only for the nested startup auth read.
- Removes the outer MutationObserver behaviour that repeatedly refreshed authentication whenever the nested login/loading DOM was present.
- Adds a 3.5-second startup watchdog. If the nested loading gate remains, Fynvo automatically remounts the workspace once and then exposes an explicit Retry Fynvo recovery action rather than remaining indefinitely frozen.
- Keeps normal login, logout, session expiry and authoritative backend authentication behaviour unchanged.
- Preserves all v1.17 pay-cycle planning, Payment Centre, Cash Flow, Calendar, Account/Card and reconciliation behaviour. No database migration is required.

## v1.17.1 - Home Assistant Startup Loading Fix

- Fixes an installed Home Assistant ingress startup failure where the production shell authenticated successfully but the nested main app could remain indefinitely on its second `Loading...` authentication gate.
- Adds a shared authentication-state bridge so the already-authenticated outer shell can satisfy the nested app's startup auth read immediately instead of depending on a second network request.
- Keeps the outer production shell's authentication refresh authoritative, including logout, session expiry and login refresh behaviour.
- Preserves all v1.17.0 pay-cycle planning, Payment Centre, Cash Flow, Calendar, Account/Card and reconciliation behaviour.
- Adds regression coverage for the duplicated auth-state startup path and aligns the add-on, backend, frontend package and production-shell release version to v1.17.1.
- No database migration is required.

## v1.17.0 - Pay-Cycle Cash Planning

### Before next pay
- Adds an authoritative pay-cycle planning service that answers when the next expected Income occurs, how much committed spending is due before then, how much active liquid cash is available, and the projected household position immediately before and after that Income event.
- Reuses the existing Income recurrence/effective-change logic, Scheduled Payment lifecycle, Bill suppression rules, Planned Spending forecast inclusion and Account/Card relationships. No parallel payment, recurrence, transaction, reconciliation or cash-flow model is introduced.
- Defines the before-pay planning window as Australia/Melbourne today up to, but not including, the chronologically next Income occurrence. The next Income is therefore not counted as cash available before it arrives.
- Uses the existing forecast ordering rule for same-date events: Income is applied before commitments on that date, so same-date commitments are after-pay items.
- Supports multiple Income sources and exposes a compact sequence of upcoming Income events and pay cycles.
- Shows an explicit Next income not known state instead of treating missing Income configuration as a $0 payment or an infinite planning window.

### Funding and Account pressure
- Calculates household and Account-level cash required before the next pay, including unresolved Scheduled Payments, Bills, overdue obligations, automatic payments that still require funding and forecast-included Planned Spending.
- Paid, reconciled, skipped and cancelled occurrences are excluded, and a linked Bill suppresses the matching Scheduled Payment occurrence to avoid double counting.
- Cards remain payment context only. Card-funded commitments derive their funding requirement through the linked Account and Card balances are never counted separately.
- Active transaction, savings, offset and cash Accounts provide available cash. Archived Accounts, liability Accounts and unassigned commitments are reported as unknown funding rather than silently becoming $0 balances.
- Adds clear Funded, Shortfall and Unknown states. No preferred minimum-balance values are invented because the current Account model has no authoritative buffer field; configurable Low buffer behaviour is therefore intentionally deferred.

### Overview and Payment Centre
- Adds a compact Before next pay Overview summary showing next pay date, required cash, available cash, projected pre-pay cash, projected post-pay cash and the most important Account funding warning.
- Adds the detailed pay-cycle summary and Accounts needing attention section to Payment Centre while retaining the existing authoritative payment list and lifecycle actions.
- Reuses the existing `/payment-planning` response on both screens instead of adding a second pay-cycle request during normal rendering. A dedicated `/payment-planning/pay-cycle` endpoint is also available for focused consumers.
- Adds explicit loading, no commitments, unknown Income, incomplete Account funding, funded and shortfall presentation states across responsive desktop, tablet, iPhone and Home Assistant ingress layouts.

### Cash Flow and Calendar reconciliation
- Aligns baseline Cash Flow starting cash with the same active liquid Account balance calculation used by payment planning.
- Baseline recurring outflows now consume authoritative Scheduled Payment lifecycle occurrences, including skip, reconciliation and one-off rescheduling state, instead of independently regenerating recurring dates.
- Keeps scenario forecasting isolated so temporary scenario adjustments continue using the scenario recurrence path without mutating authoritative Scheduled Payments.
- Calendar now consumes reconciled baseline forecast events so representative Income and commitment dates agree across Calendar, Cash Flow, Payment Centre and Pay-Cycle Planning.
- Expected Cash Flow may still include historical run-rate estimates by design; those estimates are not treated as committed before-next-pay obligations.

### Regression protection, data safety and versioning
- Adds backend coverage for weekly, fortnightly and monthly Income, multiple Income sources, no future Income, Income/payment date boundaries, overdue and automatic payments, Paid/Skipped/reconciled exclusions, Bill suppression, Planned Spending, Account/Card funding, unknown and archived Accounts, household and Account shortfalls, month-end recurrence, true fortnightly recurrence, effective-dated Income changes, multiple same-day commitments and cross-screen reconciliation.
- Adds frontend coverage for Overview and Payment Centre pay-cycle summaries, loading and unknown states, funded/shortfall/unknown Account pressure, drill-through, responsive stacking, overflow protection, shared request usage and version alignment.
- No database migration is required for v1.17.0. Existing financial records and Scheduled Payment/Transaction relationships are preserved.
- Aligns Home Assistant add-on, backend, frontend package and production-shell version reporting to v1.17.0.
- Installed desktop, tablet, iPhone and Home Assistant ingress acceptance remains a manual verification gate before merge.

## v1.16.3 - Accounts & Cards Consolidation, Account Archiving & Record Reassignment

### Accounts & Cards workspace
- Consolidates Accounts and Cards into one responsive Accounts & Cards workspace with a prominent Accounts / Cards segmented control.
- Removes Cards as a separate peer-level navigation destination while preserving direct Cards state by opening the combined workspace with Cards selected.
- Replaces the previous account-grouped Cards presentation with a card-first list. Accounts with zero Cards no longer create empty Card sections, and every Card identifies its linked Account as secondary context.
- Adds compact Account/Card rows, responsive summary metrics, search/filter controls and context-aware Add Account / Add Card actions across desktop, tablet, mobile and Home Assistant ingress-sized layouts.

### Account lifecycle
- Reuses the established `is_active` / `archived_at` Account lifecycle rather than introducing a parallel financial model.
- Adds Account dependency inspection, Archive Only, Restore Account and safe permanent deletion for dependency-free Accounts.
- Archived Accounts are hidden from normal active Account lists and existing new-record Account selectors, while historical displays continue resolving the archived Account.
- New Cards can only target active Accounts. Existing Cards can remain historically linked until explicitly reassigned.

### Reassignment and financial integrity
- Adds an authoritative transactional Move records & archive backend operation with server-side destination validation and rollback on failure.
- Classifies Cards as safe to move, active/future Account configuration as conditionally safe, and Scheduled Payments, Transfers plus protected reconciliation/transfer Transactions as historical records that must be preserved.
- Bulk Transaction movement is allowed only when balance semantics are safe. Accounts with non-zero opening balances or protected historical Transactions preserve their Transactions instead of rewriting history.
- Transaction reassignment between asset and liability Accounts is rejected because Fynvo stores their balance directions differently.
- Cards, Recurring Expense future configuration, Income destinations, Bills and Planned Spending can be reassigned to an explicitly selected active destination Account where valid.
- Permanent deletion is blocked with an explanatory dependency summary whenever preservation-required or movable relationships still exist.

### Regression protection and versioning
- Adds backend regression coverage for archive/restore visibility, dependency preview, safe bulk Transaction movement, opening-balance preservation, destination validation and dependency-free permanent deletion.
- Adds frontend regression coverage for the combined workspace, Card-first presentation, archived Account selector exclusion, lifecycle controls, responsive breakpoints and balance-safety protections.
- Selected v1.16.3 as a focused feature release on the merged v1.16.2 baseline, leaving the planned v1.17.0 Pay-Cycle Cash Planning roadmap scope unchanged.
- Aligns Home Assistant add-on, backend, frontend package, production shell and active frontend release metadata to v1.16.3.
- Installed desktop/tablet/mobile/Home Assistant visual comparison against the supplied designs remains a manual acceptance gate before merge.

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