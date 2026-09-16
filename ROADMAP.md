# Fynvo Roadmap

Fynvo is a household finance and cash-planning application for understanding upcoming commitments, available cash, pay-cycle pressure, spending decisions and near-term financial risk. The roadmap prioritises practical household planning over business accounting, tax, payroll or investment-trading functionality.

The current development baseline is v1.25.1. Payment Centre, recurring-payment lifecycle, 7/14/30-day commitment planning, pay-cycle cash planning, account funding requirements, Payday Allocation, bulk balance updates, available-cash comparisons, transactions, reconciliation, budgets, goals, scenarios, date-oriented financial Calendar, Cash Flow forecasting/impact analysis, CSV import, insights, Overview drill-down navigation, responsive Home Assistant ingress and prebuilt add-on image distribution are already delivered and are not repeated below as new scope.

## v1.25.1 - Post-v1.25.0 Production Corrections

Status: Implemented on release branch, pending Pull Request review and installed acceptance

- [x] Add precise Safe-to-Spend and Payday Allocation failure diagnostics while preserving partial known financial data.
- [x] Label fallback commitment totals with their actual generated planning horizon.
- [x] Keep account funding state visible during incomplete/unavailable pay-cycle planning.
- [x] Correct Plan Calendar Date-object handling so valid dates do not render as unavailable.
- [x] Refine bulk balance entry and propagate successful balance changes to dependent planning views.
- [x] Harden release-image source-ref handling so candidate images can be verified before Home Assistant version metadata is exposed.

## v1.25.0 - Account Funding, Payday Allocation & Balance Management

Status: Released and installed; post-release corrections tracked in v1.25.1

- [x] Reuse canonical Payment Planning, pay-cycle, account balance and Safe-to-Spend calculations.
- [x] Distinguish current-cycle funding from next-cycle Payday Allocation with explicit boundaries.
- [x] Add atomic bulk balance updates, freshness metadata and immediate planning refresh.
- [x] Complete preferred account buffers and Account Detail funding breakdowns.
- [x] Integrate concise funding decisions into Accounts, Overview and Plan.
- [x] Add deterministic backend and mobile frontend regression coverage.

## Future

Status: Planned

- [ ] Validate post-v1.25.1 installed iPhone/Home Assistant ingress behaviour and use production evidence for the next focused release.
