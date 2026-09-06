# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

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
