# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

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
