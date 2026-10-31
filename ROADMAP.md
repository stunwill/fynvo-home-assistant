# Fynvo Roadmap

Fynvo is a household finance and cash-planning application for understanding upcoming commitments, available cash, pay-cycle pressure, spending decisions and near-term financial risk. The roadmap prioritises practical household planning over business accounting, tax, payroll or investment-trading functionality.

The latest verified published baseline is v1.31.0. The v1.31.1 corrective candidate is pending CI and review. This file is a release summary; [docs/FYNVO_PRODUCT_ROADMAP.md](docs/FYNVO_PRODUCT_ROADMAP.md) remains the canonical development queue. Payment Centre, recurring-payment lifecycle, 7/14/30-day commitment planning, pay-cycle cash planning, account funding requirements, Payday Allocation, bulk balance updates, available-cash comparisons, transactions, reconciliation, budgets, goals, scenarios, date-oriented financial Calendar, Cash Flow forecasting/impact analysis, CSV import, insights, Overview drill-down navigation, responsive Home Assistant ingress and prebuilt add-on image distribution are already delivered and are not repeated below as new scope.

## v1.31.1 - CI Reliability and Release Status Correction

Status: Planned

- [x] Correct seven Ruff timezone findings without changing financial semantics.
- [x] Pin shared local/CI development dependencies.
- [x] Reconcile published release status and retain unverified installed acceptance.
- [ ] Pass PR CI, record review, merge and verify merged-main CI before publication.

## v1.31.0 - Financial Integrity & Account Cash Flow

Status: Merged via PR #103 on 10 October 2026 and published on 11 October Australian time; installed Home Assistant and live financial acceptance remain unverified.

- [x] Canonical occurrence identity, remaining Bill amounts and explicit duplicate prevention.
- [x] Observed cash, accessible balance caps, freshness and unchanged-value manual confirmation.
- [x] Chronological Account and household projections with funding deadlines and protected buffers.
- [x] Consistent cash decisions and provisional capacity when transfers or verified inputs are needed.
- [x] Overview, Accounts and Plan integration, regression tests and additive migration backup.
- [ ] Installed Home Assistant ingress, restart, Redbark sync and restored-data acceptance.

## v1.27.0 - Bank Account Lifecycle

Status: Merged via PR #98 on 28 September 2026; retained in the published v1.31.0 baseline. Separate v1.27.0 publication is not established here.

- [x] Connect discovered Redbark accounts to the Fynvo household model through explicit account setup.
- [x] Persist ignored and missing-account states, and preserve balances and history across connection failures.
- [x] Surface deterministic bank account actions within Accounts.

## v1.25.1 - Post-v1.25.0 Production Corrections

Status: Historical release-branch status superseded by the merged v1.31.0 baseline; installed acceptance remains unverified.

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

- [ ] Complete and record current installed iPhone/Home Assistant, restore, live banking and financial acceptance. See [release status](docs/RELEASE_STATUS.md). Owners and dates are not yet recorded.
