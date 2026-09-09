# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.21.0 - Safe-to-Spend, Cash Buffer & Payment Readiness

- Adds one authoritative backend Safe-to-Spend calculation shared by Overview and Payment Centre.
- Reserves known unpaid commitments through the next pay-cycle boundary, preserves negative shortfalls, excludes paid/skipped/cancelled occurrences and never treats credit limits as cash.
- Adds a persisted per-household Cash Buffer setting endpoint, with the existing account minimum-balance model preserved separately.
- Exposes the calculation breakdown, planning horizon, payment-readiness state, coverage events, warnings and reserved payment occurrences for explainable UI work.
- Integrates the authoritative Safe-to-Spend result into the mobile Overview and Payment Centre summaries.
- Preserves existing payment, pay-cycle, reconciliation and Home Assistant ingress contracts. No database schema migration is required.
- Aligns release metadata to v1.21.0.

## v1.20.0 - Payment Centre UX Completion & Workflow Reliability

- Completes the mobile Payment Centre as a decision-first operational queue, with distinct overdue, due today, before-next-pay, upcoming and payment-history sections.
- Corrects automatic-payment grouping so an unconfirmed automatic payment is only treated as overdue when its expected date has actually passed.
- Makes relative timing explicit while retaining the actual due date, including due today, tomorrow, due in N days and overdue wording.
- Closes overflow menus on outside tap and Escape, closes menus before opening details or corrective dialogs, and exposes menu semantics for assistive technology.
- Adds contextual mutation-failure recovery for bulk Mark paid and Skip actions without presenting unsuccessful payments as complete.
- Preserves the authoritative Payment Centre, Scheduled Payment, Bill, reconciliation and pay-cycle contracts. No database migration or new financial calculation engine is introduced.
- Aligns the Home Assistant add-on, backend, frontend and production-shell versions to v1.20.0.

## v1.19.0 - Household Cash Plan & Weekly Money Guidance

- Redesigns the mobile Overview around a decision-first household cash plan led by Safe to spend, followed by before-next-pay commitments, the next pressure point and immediate payment actions.
- Separates current available cash, money reserved for known commitments and expected future income so projected income is never presented as money already available.
- Adds a compact three-week cash-plan view with explicit Comfortable, Tight, Shortfall and Incomplete states and progressive access to deeper planning detail.
- Adds deterministic What to pay next guidance using existing overdue, attention, due-before-pay and due-soon payment states without inventing a financial-advice score.
- Adds explainable Money reserved and Accounts at a glance summaries to clarify why account balances differ from safe-to-spend cash.
- Preserves Payment Centre as the operational payment-management workspace and reuses authoritative Payment Planning, pay-cycle, account, income and forecast data rather than creating a parallel budgeting engine.
- Adds iPhone/Home Assistant ingress responsive protections, safe-area handling, minimum touch-target support and reduced-motion behaviour for the new Overview hierarchy.
- Aligns Home Assistant, backend, frontend and production-shell release metadata to v1.19.0. Installed iPhone/Home Assistant visual acceptance remains a manual gate before merge.

## v1.18.3 - Payment Centre Actionability & Planning UX

- Adds quick Payment Centre counts and monetary summaries for Overdue, Before next pay and Next 30 days using the existing authoritative payment and pay-cycle data.
- Replaces the generic unavailable before-pay presentation with an actionable cash-position setup state, direct Fix setup or Review Income actions and progressively disclosed calculation detail.
- Makes missing due date, payment method, funding account and category information explicit and interactive.
- Refines mobile payment-card hierarchy, reduces repeated full-width action weight and clearly distinguishes expected automatic payments from confirmed paid or reconciled state.
- Adds collapsible planning groups for Overdue, Due before next pay, Next 7 days and Later this month with counts and reliable totals.
- Adds deliberate bulk selection with confirmed Mark paid and Skip operations that reuse the existing single-payment lifecycle endpoints, version checks and matched-transaction protections.
- Preserves the v1.18.2 mobile Payment Centre foundation, desktop Payment Centre, Scheduled Payments, Bills, Recurring Expenses, reconciliation and pay-cycle financial semantics.
- Adds responsive, safe-area, reduced-motion and sticky mobile modal-action protections. No database migration is required.

## v1.18.2 - Payment Centre Mobile UX Completion

- Redesigns the iPhone/Home Assistant Payment Centre as a compact financial-management queue instead of a vertically heavy card stack.
- Introduces denser payment rows that keep payment name and full amount prominent, consolidate due/overdue, handling, payment-method and funding metadata, and summarise missing details with a compact actionable warning.
- Keeps Mark paid as the visible primary action while moving lower-frequency lifecycle actions behind a compact overflow path and preserving access to the existing detailed Payment Centre workspace.
- Reworks Grouped and Chronological into a clear segmented selector, improves date-group counts and priority ordering within groups, and keeps chronology authoritative.
- Consolidates Quick Add, Add Bill and quick filters into a sticky mobile toolbar, removes duplicate global Payment Centre header actions and keeps active-filter counts and reset behaviour available.
- Simplifies the before-next-pay funding summary around Available now, Required before pay and Next income, replaces ambiguous bare Unknown text with explicit before-pay availability explanations, and keeps full calculation detail behind View calculation.
- Replaces large text-only loading states with structure-preserving skeletons, separates payment-list and funding-summary failures so one secondary failure does not unnecessarily block the other workspace, and adds deliberate empty states.
- Hides the redundant mobile Payment Centre footer, moves the release version into More → About, and adds explicit bottom-navigation and iOS safe-area clearance.
- Preserves authoritative Payment Planning, Pay-Cycle Cash Planning, Scheduled Payments, Bills, Recurring Expenses and reconciliation semantics. No database migration is required.

## v1.18.1 - Overview Decision Dashboard

- Refines the merged v1.18.0 mobile financial-decision work into a denser, decision-first iPhone/Home Assistant Overview based on the supplied 1179 × 2556 iPhone 15 Pro references.
- Replaces the repeated Funding incomplete / Not known / UNKNOWN presentation with one explicit before-next-pay state and actionable explanation of missing funding or income information.
- Replaces the large 2 × 2 nested pay-cycle cards with four compact stacked decision rows for Available now, Committed before pay, Next income and Projected after pay.
- Makes committed-before-pay values explainable through the existing Payment Centre drill-through and keeps authoritative payment-planning calculations unchanged.
- Promotes Needs attention directly below the pay-cycle decision, limits Overview to the three highest-priority exceptions and keeps the full operational workflow in Payment Centre.
- Adds a compact Money needed soon section for Next 7 days, Before next pay and Next 30 days using the existing Payment Planning service.
- Reworks Cash Flow into a compact Cash position summary and Accounts into a compact balance list, using available width responsively and stacking on narrower screens.
- Adds a lightweight What changed? comparison using a local previous-Overview snapshot, without creating a second financial ledger or altering canonical Transactions.
- Moves lower-priority forecast information behind More financial insights and keeps detailed forecasting in Cash Flow.
- Preserves the five-item mobile navigation, Home Assistant ingress shell ownership, iOS safe-area handling, shared API request caching/deduplication and existing financial calculation semantics.
- Adds v1.18.1 regression coverage for information hierarchy, responsive density, safe-area behaviour, version alignment and the new Overview sections.
- No database migration is required.

## v1.18.0 - Mobile Financial Decision UX

- Reorients the iPhone and Home Assistant ingress Overview around the authoritative before-next-pay position so available cash, next income, commitments, projected after-pay balance, safe-to-spend surplus or funding shortfall are visible before secondary dashboard detail.
- Promotes overdue payments, payments requiring attention and incomplete funding information into explicit mobile exceptions with direct routes into Payment Centre or Income.
- Removes financial-value ellipsis from the final mobile responsive layer and preserves complete currency values across narrow supported viewports.
- Replaces the textual pay-cycle loading card with a stable skeleton state that respects reduced-motion preferences.
- Makes Cash Flow explicitly state its lowest projected balance and whether a cash shortfall is predicted, while defaulting the event list to chronological next events and retaining Largest movements as an alternate analytical view.
- Adds a Payment Centre decision summary for funded, shortfall and incomplete states, compact mobile filter chips and a bottom-sheet filter experience, while retaining the detailed desktop filter workspace.
- Distinguishes incomplete payment records by calling out missing due dates, payment methods or funding accounts instead of presenting those omissions as ordinary metadata.
- Improves Recurring Expenses with actionable overdue aggregates, incomplete-payment notices and a clearer path to Payment Centre while preserving existing Mark as paid, Skip and Edit actions.
- Groups the mobile More navigation into Plan, Payments, Money, Data & System and Tools sections instead of a single flat list.
- Preserves the existing v1.17 pay-cycle planning service, Payment Centre calculations, forecast semantics, account balances, scheduled-payment lifecycle and reconciliation behaviour. No database migration is required.
- Adds v1.18.0 regression coverage for decision summaries, shortfall/unknown states, compact filters, incomplete records, Cash Flow interpretation, recurring-expense exceptions, responsive value handling and aligned release versions.
- Installed iPhone/Home Assistant ingress acceptance remains a manual release gate before merge.

## v1.17.9 - Mobile Overview & Workspace UX Refinement

- Refines the iPhone/Home Assistant Overview around the supplied visual direction with a compact greeting, contextual Date Range and Quick Add controls, exactly four Snapshot actions, a concise Cash Flow summary and Top Accounts using authoritative Account data.
- Keeps mobile financial values readable on one line, uses human-facing horizon labels such as `Next 6 months`, and preserves the existing command-centre, Accounts and payment-planning calculations rather than introducing duplicate finance logic.
- Repairs the Cash Flow forecast presentation by explicitly styling the active SVG baseline/expected path implementation with no fill, responsive sizing and separated legend items.
- Reduces the default Cash Flow event list to five high-impact movements with explicit access to the complete event set.
- Reworks Transactions mobile filtering so Search and the primary period remain visible while secondary Account, Category, direction, reconciliation and source filters are available through a touch-friendly filter sheet with active-filter indication.
- Keeps Accounts & Cards compact and current-state focused, and removes redundant global mobile header actions from Transactions and Recurring Expenses where page-specific controls are more useful.
- Adds a final responsive refinement layer while preserving the v1.17.5 startup lifecycle, v1.17.6 Accounts/Cards interactivity, v1.17.7 GET deduplication/read caching and v1.17.8 ingress header, bottom navigation, More → Tools and safe-area protections.
- No database migration is required and no household financial records, payment lifecycle rules, reconciliation semantics or forecast calculations are changed.
- Installed iPhone/Home Assistant ingress acceptance remains a manual release gate.

## v1.17.8 - Mobile Overview Redesign & Optimisation

- Corrects Home Assistant ingress mobile chrome so the Home Assistant header remains authoritative and the duplicate internal Fynvo app bar no longer competes with or clips page content.
- Removes the persistent floating Tools trigger on mobile while retaining Tools through the mobile More navigation sheet and preserving desktop access.
- Adds a persistent five-destination mobile navigation bar for Overview, Accounts, Cash Flow, Transactions and More with iOS bottom safe-area handling.
- Redesigns the mobile Overview hierarchy around four Snapshot KPIs followed by Cash Flow and Top Accounts while retaining existing command-centre, account and payment-planning data semantics.
- Compacts Accounts & Cards for iPhone and Home Assistant ingress use with full-width Accounts/Cards tabs, a 2×2 summary, responsive search/status controls and denser account/card rows with balances and status visible.
- Hides the global Date Range/Quick Add header controls on the current-state Accounts & Cards mobile workspace and removes the excess spacing they created above the primary account content.
- Aligns Home Assistant add-on, backend, frontend package and production-shell release reporting to v1.17.8 and preserves the v1.17.5 startup lifecycle, v1.17.6 Accounts interactivity and v1.17.7 request-deduplication protections.
- No database migration is required and no financial records, calculations, reconciliation semantics or payment lifecycle behaviour are changed.
- Installed iPhone/Home Assistant ingress acceptance remains a manual gate before merge.

## v1.17.7 - Mobile Performance & Ingress UX Optimisation

- Reduces duplicate frontend startup work by deduplicating identical in-flight GET requests through the shared API client.
- Reuses the already-authoritative Dashboard Command Centre response for the matching expected Forecast and Financial Health reads instead of asking the backend to calculate the same data again during the same startup cycle.
- Moves the Accounts & Cards compatibility wrapper onto the shared API client so its Account/Card bootstrap reads can be coalesced with identical workspace requests rather than creating duplicate backend traffic.
- Adds a short in-memory read cache for repeated navigation within the same Home Assistant webview and clears that cache immediately after any mutation so financial changes are never hidden behind stale cached state.
- Adds a final iPhone/Home Assistant ingress responsive layer with tighter page spacing, smaller headings, more efficient two-column KPI cards, compact header controls, contained Account/Card rows, touch-friendly controls, safer modal actions and bottom safe-area spacing.
- Keeps the v1.17.6 Accounts & Cards interactivity fix and the v1.17.5 single-owner startup lifecycle unchanged.
- No database migration is required and no financial calculations, records, payment lifecycle, forecasting rules or reconciliation semantics are changed.

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
