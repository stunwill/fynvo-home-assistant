# Fynvo Add-on Changelog

## v1.18.2 - Payment Centre Mobile UX Completion

- Redesigns Payment Centre for iPhone and Home Assistant ingress as a compact working queue with materially denser payment cards and clearer name/amount hierarchy.
- Consolidates overdue, payment handling, payment method and funding metadata into concise rows, while keeping incomplete-data warnings visible and actionable.
- Keeps **Mark paid** as the primary visible action and moves lower-frequency lifecycle actions behind a compact overflow path backed by the existing detailed Payment Centre workspace.
- Replaces separate Grouped/Chronological buttons with a persisted segmented selector, improves readable date-group counts and keeps priority ordering within groups explicit.
- Makes Quick Add and Add Bill proportionate mobile controls, adds compact quick filters with active-filter counts, and suppresses redundant global Payment Centre header controls.
- Simplifies **Before next pay** around the authoritative funding conclusion, Available now, Required before pay and Next income, with explicit unavailable states and progressive calculation disclosure.
- Adds structure-preserving skeleton loading, independent payment/funding error recovery and deliberate empty states without blocking usable sections unnecessarily.
- Hides the redundant mobile footer on Payment Centre, moves version visibility to **More → About**, and adds bottom-navigation/iOS safe-area clearance for the final payment and modal actions.
- Preserves desktop Payment Centre, authoritative payment-planning/pay-cycle calculations, Scheduled Payment lifecycle, Bills, Recurring Expenses and reconciliation semantics.
- Adds v1.18.2 regression coverage for Payment Centre density, actions, grouped/chronological controls, filters, pay-cycle summary, loading/error/empty states, responsive breakpoints and release metadata.
- Requires no database migration.

## v1.18.1 - Overview Decision Dashboard

- Refines the mobile Overview into a denser decision-first dashboard using the supplied iPhone 15 Pro references.
- Replaces repeated unknown/funding labels with one clear before-next-pay state and actionable missing-data explanation.
- Uses compact stacked rows for Available now, Committed before pay, Next income and Projected after pay.
- Moves Needs attention directly below the pay-cycle decision, shows only the top three priority exceptions and links the full workflow to Payment Centre.
- Adds Money needed soon for Next 7 days, Before next pay and Next 30 days.
- Compacts Cash position and Accounts, adds a lightweight What changed? comparison and moves lower-priority forecast information behind More financial insights.
- Preserves Home Assistant ingress shell ownership, five-item mobile navigation, iOS safe-area handling and existing financial calculation semantics.
- Requires no database migration.

## v1.18.0 - Mobile Financial Decision UX

- Puts the before-next-pay financial decision first on mobile, showing available cash, next income, commitments, projected after-pay balance and either a safe-to-spend surplus, funding shortfall or incomplete-funding state.
- Promotes overdue payments, payments requiring attention and incomplete funding information into actionable Overview exceptions.
- Prevents final mobile financial values from being ellipsised, replaces the textual cash-plan loader with a stable skeleton and respects reduced-motion preferences.
- Makes Cash Flow explicitly explain its lowest projected balance and any predicted shortfall, with Next events as the default mobile ordering and Largest movements retained as an alternate view.
- Adds interpreted Payment Centre funding states, compact filter chips, a mobile filter sheet and visible incomplete-payment warnings for missing dates, payment methods and funding accounts.
- Improves Recurring Expenses with overdue aggregates and incomplete-payment warnings while keeping Mark as paid, Skip and Edit available through explicit accessible controls.
- Groups More navigation into Plan, Payments, Money, Data & System and Tools sections.
- Reuses the existing pay-cycle, payment-planning and forecast calculations. No database migration is required and financial semantics are unchanged.
- Installed iPhone/Home Assistant ingress acceptance remains a manual gate before merge.

## v1.17.9 - Mobile Overview & Workspace UX Refinement

- Refines the mobile Overview to follow the supplied iPhone design direction with a four-card Snapshot, compact Cash Flow summary and Top Accounts hierarchy while retaining authoritative Fynvo financial data.
- Prevents mobile currency values from wrapping into isolated digits and uses human-readable period labels such as `Next 6 months`.
- Repairs the Cash Flow forecast graph and Baseline/Expected legend styling for the active SVG path implementation, and limits the default event preview to five high-impact movements with full-list access.
- Reworks Transactions mobile filtering around Search, period and a Filters sheet that retains Account, Category, direction, reconciliation and source filters with active-filter indication.
- Keeps Accounts & Cards compact and current-state focused and removes redundant global mobile toolbar actions from specialised Transactions and Recurring Expenses workspaces.
- Preserves the five-item mobile bottom navigation, More → Tools, Home Assistant ingress header ownership, iOS safe-area handling and horizontal-overflow protections introduced in v1.17.8.
- Preserves v1.17.5 startup lifecycle, v1.17.6 Accounts/Cards interactivity and v1.17.7 request deduplication/read caching.
- Requires no database migration and does not change household financial records, payment lifecycle semantics, reconciliation rules or forecast calculations.

## v1.17.8 - Mobile Overview Redesign & Optimisation

- Removes the duplicate internal Fynvo app bar from the effective Home Assistant mobile ingress presentation so Home Assistant owns the outer header and Fynvo content begins cleanly beneath it.
- Removes the floating mobile Tools trigger and keeps Tools available through the More navigation flow and a dedicated mobile tools sheet.
- Adds persistent mobile primary navigation for Overview, Accounts, Cash Flow, Transactions and More with iOS safe-area handling.
- Reorganises the mobile Overview around four Snapshot metrics followed by Cash Flow and Top Accounts while preserving existing financial calculations and data sources.
- Compacts Accounts & Cards on iPhone and ingress-sized viewports with full-width tabs, a 2×2 summary, responsive search/status filters and denser account/card rows.
- Removes irrelevant Date Range/Quick Add header controls from the Accounts & Cards mobile workspace and reduces excess space above account content.
- Aligns add-on, backend, frontend package and production-shell reporting to v1.17.8 while preserving v1.17.5 startup, v1.17.6 Accounts interactivity and v1.17.7 request-deduplication protections.
- Requires no database migration and does not change household financial records or financial calculation semantics.
- Installed iPhone/Home Assistant ingress acceptance remains a manual gate before merge.

## v1.17.7 - Mobile Performance & Ingress UX Optimisation

- Deduplicates identical in-flight frontend GET requests so the Home Assistant webview does not issue the same Account/Card reads multiple times during startup.
- Reuses the Dashboard Command Centre's expected Forecast and Financial Health data for matching startup reads instead of recalculating those same datasets through separate API requests.
- Moves the Accounts & Cards compatibility workspace onto the shared API client and adds a short mutation-safe read cache for repeated in-app navigation.
- Adds a final iPhone/Home Assistant ingress responsive layer with tighter spacing, smaller headings, denser two-column KPI cards, compact header controls, contained Account/Card rows, touch-friendly actions, safer modals and iOS safe-area handling.
- Preserves the v1.17.6 interactivity fix, authentication/startup lifecycle and all financial calculation semantics.
- Requires no database migration and does not change household financial records.

## v1.17.6 - Accounts & Cards Installed Interactivity Correction

- Fixes the installed Home Assistant/iPhone condition where Accounts & Cards rendered but the page and surrounding Home Assistant controls became unresponsive to taps/clicks.
- Corrects a self-triggering document-wide `MutationObserver` in the v1.16.3 compatibility workspace. The wrapper now updates its heading/description only when the DOM actually differs from the expected Accounts & Cards state.
- Avoids repeatedly setting the same Accounts/Cards portal mount DOM node.
- Keeps the v1.17.5 single-owner authentication/startup lifecycle and installed startup diagnostics intact.
- Updates the production shell, frontend package, backend API and add-on manifest to v1.17.6 so the installed footer can be used as a build-version check.
- Requires no database migration and does not change financial records or calculations.

## v1.17.5 - Frontend Startup Lifecycle Correction & Diagnostics

- Uses the installed Fynvo add-on logs to correct the remaining iPhone/Home Assistant startup freeze after authentication, household security, Accounts and Cards requests were all returning successfully.
- Removes the global frontend auth `fetch` bridge and automatic keyed workspace remount/watchdog so a successful authenticated startup mounts one workspace instance and keeps it mounted.
- Preserves the v1.17.4 direct auth-state prop handoff while removing the wrapper's shared-global auth mutation and deferring Accounts/Cards bootstrap until authentication is confirmed.
- Removes the production StrictMode wrapper to keep installed startup effects and diagnostics single-pass.
- Adds installed-runtime startup diagnostics to the Fynvo add-on log for `authenticated`, `workspace-mounted` and `workspace-rendered` stages.
- Marks the HTML shell as non-cacheable at document level to reduce stale Home Assistant webview shells after add-on upgrades.
- Requires no database migration and does not change financial records or calculations.

## v1.17.4 - Direct Home Assistant Auth State Handoff

- Fixes the remaining installed iPhone/Home Assistant ingress freeze where the inner Fynvo workspace could still remain on `Loading...` after the outer shell had already authenticated.
- Corrects the production wrapper chain so `AppV13` passes authenticated state through `AppCorrectiveV1163` into `AppCorrectiveV0174` instead of dropping it before the base workspace mounts.
- Initialises the base workspace directly from the supplied authoritative authentication state, eliminating the second startup `/auth/state` request from the normal Home Assistant path.
- Retains the standalone login/setup fallback when the base workspace is run without an outer authentication state.
- Preserves the v1.17.3 non-blocking household-security check and existing recovery controls.
- Requires no database migration and does not change financial records or calculations.

## v1.17.3 - Non-blocking Household Identity Startup

- Fixes the Home Assistant ingress freeze where the authenticated app could remain indefinitely on `Loading Household identity...`.
- Stops `/household/me/security` from acting as a mandatory startup render gate.
- Adds a 3.5-second abort timeout to the household-security refresh so a pending embedded-webview request cannot freeze the whole app.
- Keeps temporary-password enforcement when household security state is available and shows a non-blocking Retry security check action if that secondary refresh cannot complete.
- Preserves the v1.17.2 auth bridge, startup watchdog, Retry Fynvo recovery and all existing financial behaviour.
- Requires no database migration.

## v1.17.2 - Home Assistant Ingress Startup Recovery

- Hardens the installed Home Assistant startup path after v1.17.1 still reproduced an inner `Loading...` freeze on iPhone ingress.
- Publishes the authenticated outer-shell state before the nested Fynvo workspace mounts and accepts both relative and ingress-expanded auth-state URLs.
- Removes the browser `Response` construction dependency from the startup auth bridge and stops the outer DOM observer from repeatedly refreshing authentication when the nested login/loading DOM is present.
- Adds a 3.5-second startup watchdog: Fynvo automatically remounts the workspace once if the nested loading gate remains, then exposes an explicit Retry Fynvo recovery action instead of freezing indefinitely.
- Preserves normal backend-authoritative login, logout and session refresh behaviour and all v1.17 financial functionality.
- Requires no database migration.

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
