# Fynvo Roadmap

Fynvo is a household finance and cash-planning application for understanding upcoming commitments, available cash, pay-cycle pressure, spending decisions and near-term financial risk. The roadmap prioritises practical household planning over business accounting, tax, payroll or investment-trading functionality.

The current development baseline is v1.18.0. Payment Centre, recurring-payment lifecycle, 7/14/30-day commitment planning, pay-cycle cash planning, account funding requirements, available-cash comparisons, transactions, reconciliation, budgets, goals, scenarios, date-oriented financial Calendar, Cash Flow forecasting/impact analysis, CSV import, insights, Overview drill-down navigation and responsive Home Assistant ingress are already delivered and are not repeated below as new scope.

## v1.18.0 - Mobile Financial Decision UX

Status: Implemented in release branch, pending PR review and manual installed acceptance

Objective: Make the existing authoritative pay-cycle, payment-planning and forecast results immediately understandable and actionable on iPhone and Home Assistant ingress without changing financial calculation semantics.

### Features

- [x] Put the before-next-pay position first on mobile Overview, including available cash, next income, commitments and projected after-pay balance.
- [x] Express an authoritative positive before-pay remainder as safe-to-spend context and a negative projected position as a funding shortfall.
- [x] Promote overdue payments, payments requiring attention and incomplete funding information into explicit exceptions.
- [x] Add interpreted funded, shortfall and incomplete states to Payment Centre without duplicating the pay-cycle service.
- [x] Add explicit Cash Flow lowest-balance and shortfall interpretation while retaining the forecast chart.
- [x] Default Cash Flow events to chronological next events while retaining Largest movements as an alternate view.
- [x] Add compact mobile Payment Centre filters and visible incomplete-payment states.
- [x] Improve Recurring Expenses overdue aggregation and incomplete-payment visibility while retaining explicit lifecycle actions.
- [x] Group mobile More navigation into task-oriented sections.

### UX / Quality

- [x] Prevent final mobile financial values from being ellipsised.
- [x] Replace the disruptive textual pay-cycle loader with a stable skeleton and reduced-motion fallback.
- [x] Preserve Home Assistant ingress safe-area handling, touch-friendly controls and desktop analytical layouts.
- [x] Keep status meaning explicit in text and labels rather than relying on colour alone.

### Testing / Validation

- [x] Add frontend regression coverage for decision summaries, funded/shortfall/unknown states, compact filters, incomplete records, Cash Flow interpretation and release metadata.
- [x] Preserve existing backend pay-cycle, payment-planning, forecast and payment lifecycle test suites unchanged because calculation semantics are unchanged.
- [ ] Complete installed desktop, tablet, iPhone and Home Assistant ingress manual acceptance before merge.

## v1.19.0 - Budget Decision Support

Status: Planned

Objective: Build on Fynvo's existing Budget model so households can see what remains safe to spend after committed obligations, rather than only comparing budget amounts with historical activity.

### Features

- [ ] Add clear committed-versus-discretionary classification for budget analysis, using existing recurring commitments, bills, planned spending and actual transactions where reliable.
- [ ] Show remaining budget for the active period after Actual, Committed and included Planned amounts are applied.
- [ ] Add projected end-of-period budget position using the existing forecast/event model instead of a separate budget forecast engine.
- [ ] Surface categories likely to exceed budget before period end and explain the contributing committed/planned items.
- [ ] Add previous-period comparison for major categories and household totals so month-to-month change is visible.
- [ ] Review and refine existing rollover behaviour so positive and negative rollover are understandable in household terms and do not obscure current-period spending limits.
- [ ] Add a household-level discretionary amount indicator only when sufficient budget, commitment and balance information exists.

### UX / Quality

- [ ] Redesign Budgeting summaries around "Budget", "Spent", "Committed", "Planned", "Remaining" and "Projected" with consistent definitions.
- [ ] Provide drill-through from overspend or risk warnings to the transactions and commitments causing them.
- [ ] Keep category hierarchy and parent/child budget relationships readable on mobile without dense accounting-style tables.

### Testing / Validation

- [ ] Add regression coverage for shared parent pools, parent-equals-children budgets, rollover, unbudgeted categories and discretionary calculations.
- [ ] Verify budget projections use the same actual/committed/planned records as Cash Flow and Forecast.
- [ ] Validate month-boundary and true-fortnightly budget periods against representative Australian household examples.

## v1.20.0 - Commitment Intelligence & Renewal Planning

Status: Planned

Objective: Make recurring household obligations easier to maintain by identifying meaningful changes, exceptions and longer-cycle commitments without automatically altering financial records.

### Features

- [ ] Detect meaningful recurring-payment amount changes from reconciled Transaction history and present them as reviewable suggestions rather than silently editing Recurring Expenses.
- [ ] Identify missed or unexpectedly absent recurring payments when an expected occurrence passes without a matching Transaction or valid lifecycle resolution.
- [ ] Highlight annual, quarterly and other infrequent commitments early enough to plan for registrations, insurance, rates, memberships and similar household costs.
- [ ] Add optional renewal/expiry metadata for relevant recurring commitments and Bills where it provides planning value.
- [ ] Show recent expected-versus-actual amount history for variable recurring expenses without overwriting the authoritative recurring rule.
- [ ] Improve duplicate/overlap diagnostics for Bills, Recurring Expenses and Scheduled Payments while preserving the existing v1.16 deduplication rules.
- [ ] Add actionable data-quality prompts for commitments missing amount, expected date, Account/Card or payment method.

### UX / Quality

- [ ] Add a focused Commitment Health view or section that separates upcoming obligations, exceptions, amount changes, renewals and missing information.
- [ ] Make suggested changes explicitly reviewable with Accept/Dismiss behaviour and supporting evidence.
- [ ] Keep renewal and exception indicators visible in List, Calendar and payment detail without adding status clutter.

### Testing / Validation

- [ ] Add regression coverage for variable amounts, infrequent recurrence, missed occurrences, duplicate suppression and renewal metadata.
- [ ] Verify accepted suggestions update only the intended recurring rule/effective date and preserve historical Scheduled Payments and Transactions.
- [ ] Verify no intelligence workflow automatically creates, pays, skips or reconciles a payment.

## v1.21.0 - Household Reporting & Cost Trends

Status: Planned

Objective: Turn Fynvo's existing transactions, commitments, budgets and forecast data into practical household trend reporting without becoming an enterprise BI product.

### Features

- [ ] Add monthly household income-versus-expense reporting with drill-through to the underlying Transactions.
- [ ] Add category spending trends across recent months with clear treatment of transfers, refunds and uncategorised activity.
- [ ] Show recurring-cost growth over time, including material changes to regular household commitments.
- [ ] Add committed-versus-discretionary spending trend reporting using the classification introduced in v1.19.0.
- [ ] Add year-to-date household totals for income, expenses, committed costs and selected major categories.
- [ ] Add account-level cash movement summaries while keeping internal transfers separate from household income/expense totals.
- [ ] Add simple export of report-ready CSV data where useful, reusing existing canonical records and privacy boundaries.

### UX / Quality

- [ ] Add a Reports area with a small set of purpose-built household views rather than a generic report builder.
- [ ] Support mobile-friendly trend summaries with detail available on demand instead of wide tables.
- [ ] Use plain-language comparison labels such as "up from last month" and always expose the comparison basis.

### Testing / Validation

- [ ] Add regression coverage for transfer exclusion, refunds/negative amounts, category hierarchy, year boundaries and incomplete months.
- [ ] Reconcile report totals against canonical Transaction and commitment data for representative periods.
- [ ] Verify exported values match on-screen totals and retain Australian date/currency conventions.

## v1.22.0 - Home Assistant Financial Entities & Alerts

Status: Planned

Objective: Deepen Fynvo's Home Assistant value by exposing a small, stable set of household financial entities and actionable alerts based on the same authoritative Fynvo calculations.

### Features

- [ ] Expose stable Home Assistant-facing values for available cash, next income date/amount, cash required before next pay, projected before-pay balance and near-term shortfall state.
- [ ] Add entities or equivalent HA integration surfaces for upcoming commitment totals and payment-attention counts where they remain semantically stable.
- [ ] Add opt-in alerts for predicted before-pay shortfall, overdue payment attention and materially incomplete funding information.
- [ ] Keep alerts state-based and idempotent so Home Assistant restarts do not create repeated notifications for the same unchanged condition.
- [ ] Provide clear entity availability/unknown behaviour when Fynvo lacks sufficient source data.

### UX / Quality

- [ ] Document entity meanings and update cadence in household language.
- [ ] Keep Home Assistant alerts opt-in and avoid noisy notifications for low-value state changes.
- [ ] Ensure the Fynvo ingress UI remains the detailed investigation surface while HA entities serve dashboards and automations.

### Testing / Validation

- [ ] Verify entities reconcile with the same pay-cycle and payment-planning service values shown in Fynvo.
- [ ] Add restart/idempotency coverage for alert state.
- [ ] Verify unknown values remain unavailable rather than silently becoming zero.

## Future

Status: Planned

- [ ] Continue evidence-led improvements that strengthen household financial decisions without turning Fynvo into business accounting software.
