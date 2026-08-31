# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.16.3 - Accounts & Cards Consolidation, Archiving & Reassignment

### Accounts & Cards workspace
- Consolidates Accounts and Cards into one responsive `Accounts & Cards` workspace with dedicated Accounts and Cards views instead of treating Cards as an unrelated top-level Money page.
- Implements the supplied desktop and mobile design direction with a prominent segmented view control, compact summary cards, search/filter controls, compact Account rows and Card-first Card rows.
- Removes the old Cards-page pattern that rendered every Account, including Accounts with no Cards. Cards now appear as first-class records and show their linked Account as secondary context.
- Preserves existing Account and Card CRUD behaviour, last-four-digits-only Card storage and active Account validation.

### Account lifecycle
- Uses the existing Account `is_active` / `archived_at` lifecycle for safe Account retirement.
- Adds dependency analysis before consolidation so Fynvo can explain linked Transactions, Cards, Recurring Expenses, Income, Bills, Planned Spending, Scheduled Payments and Transfers.
- Adds Restore Account for archived Accounts and excludes archived Accounts from new Card destinations and the existing active Account selectors.
- Adds safe permanent deletion only when no Account dependencies remain, with explanatory blockers instead of destructive cascades.

### Move records & archive
- Adds an explicit user-selected destination Account workflow for duplicate/misassigned Account consolidation.
- Moves eligible non-transfer, non-matched Transactions without recreating Transaction identity, reassigns Cards, and moves future Account configuration for Recurring Expenses, Income, Bills and Planned Spending.
- Preserves protected historical Transactions, Scheduled Payments and Transfers on the original Account instead of blindly rewriting historical financial truth.
- Executes reassignment and archive in one backend transaction with rollback on failure.

### Responsive and accessibility
- Adds desktop, tablet and iPhone/Home Assistant responsive layouts based on the supplied mock-ups, with compact rows, readable balances and linked Account context without horizontal overflow.
- Adds keyboard-accessible Accounts/Cards tabs, semantic statuses and clear mobile Add Account/Add Card actions.

### Versioning
- Selected v1.16.3 because v1.17.0 remains reserved in ROADMAP.md for Pay-Cycle Cash Planning. This release extends the existing Accounts/Card capability without consuming that planned feature version.
- Aligns Home Assistant add-on, backend, frontend package and production-shell version reporting to v1.16.3.

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
- Highlights today's date in the recurring-expense month calendar with a clear blue treatment while preserving payment-status colours.

### Payment Centre
- Simplifies Payment Centre around the authoritative Payment Planning service with a clearer summary, compact filters, expandable funding details and grouped payment sections.
- Keeps the detailed chronological Payment Centre available for full lifecycle actions while making the grouped view the default.

### Cash Flow
- Restores the Cash Flow forecast graph above the event list and adds explicit loading, no-data and error/retry states.

### Versioning
- Aligns production-shell, frontend, backend and Home Assistant add-on version reporting to v1.16.1.
