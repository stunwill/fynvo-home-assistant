# Fynvo Add-on Changelog

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
