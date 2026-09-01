# Fynvo Roadmap

Fynvo is a household finance and cash-planning application for understanding upcoming commitments, available cash, pay-cycle pressure, spending decisions and near-term financial risk. The roadmap prioritises practical household planning over business accounting, tax, payroll or investment-trading functionality.

The current development baseline is v1.17.0. Payment Centre, recurring-payment lifecycle, 7/14/30-day commitment planning, pay-cycle cash planning, account funding requirements, available-cash comparisons, transactions, reconciliation, budgets, goals, scenarios, date-oriented financial Calendar, Cash Flow forecasting/impact analysis, CSV import, insights, Overview drill-down navigation and responsive Home Assistant ingress are already delivered and are not repeated below as new scope.

## v1.17.0 - Pay-Cycle Cash Planning

Status: Implemented in release branch, pending PR review and manual installed acceptance

Objective: Extend v1.16 payment planning so Fynvo can answer how much cash is required before the household's next expected income event, what will be left afterwards, and which accounts are under pressure.

### Features

- [x] Add a shared pay-cycle planning service that identifies the next expected household income date from existing active Income records without creating a separate income model.
- [x] Calculate committed payments due before the next expected income event, including overdue unresolved obligations and automatic payments that still require funding.
- [x] Show cash required before next pay at household and Account level, while preserving Card-to-Account derivation and explicit unknown-account handling.
- [x] Calculate projected available cash immediately before and after the next expected income event using existing account balances, scheduled commitments and expected income.
- [x] Support multiple household income sources by showing the next income event and the commitments covered before following income events where practical.
- [x] Respect existing income recurrence, effective-dated changes, occurrence dates, payment status and reconciliation rules rather than introducing parallel forecast logic.
- [x] Inspect minimum-balance/buffer support. The current Account model has no authoritative preferred-buffer field, so v1.17.0 keeps buffer values neutral rather than inventing defaults. Configurable Low buffer behaviour remains available for a later additive enhancement.

### UX / Quality

- [x] Add a concise "Before next pay" summary to Overview and Payment Centre using the same backend calculation.
- [x] Clearly distinguish known shortfall and unknown balance/account states instead of treating missing information as zero. Low buffer is not emitted without a configured authoritative buffer.
- [x] Keep the planning summary compact and touch-friendly on Home Assistant ingress and iPhone-sized screens without horizontal scrolling.

### Testing / Validation

- [x] Add regression coverage for weekly, fortnightly, monthly and multiple-income pay cycles, overdue commitments, automatic payments and no-income-known states.
- [x] Add reconciliation regression coverage across Payment Centre, Overview data, Cash Flow, Calendar and pay-cycle planning using the same authoritative occurrences and amounts.
- [x] Add Australia/Melbourne planning semantics and month-end/fortnightly recurrence coverage.
- [ ] Complete installed desktop, tablet, iPhone and Home Assistant ingress manual acceptance before merge.

## v1.18.0 - Budget Decision Support

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

## v1.19.0 - Commitment Intelligence & Renewal Planning

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

## v1.20.0 - Household Reporting & Cost Trends

Status: Planned

Objective: Turn Fynvo's existing transactions, commitments, budgets and forecast data into practical household trend reporting without becoming an enterprise BI product.

### Features

- [ ] Add monthly household income-versus-expense reporting with drill-through to the underlying Transactions.
- [ ] Add category spending trends across recent months with clear treatment of transfers, refunds and uncategorised activity.
- [ ] Show recurring-cost growth over time, including material changes to regular household commitments.
- [ ] Add committed-versus-discretionary spending trend reporting using the classification introduced in v1.18.0.
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

## v1.21.0 - Home Assistant Financial Entities & Alerts

Status: Planned

Objective: Expose a carefully selected set of useful household-finance state to Home Assistant without turning every Fynvo database field into an entity.

### Features

- [ ] Add Home Assistant entities for selected high-value household state such as available cash, next expected income, cash required before next pay, projected before-pay balance and payments requiring attention.
- [ ] Add optional alerts for meaningful shortfalls, overdue obligations or upcoming payment pressure using the same authoritative calculations shown inside Fynvo.
- [ ] Keep entity naming, availability and unknown-state semantics stable and explicit.
- [ ] Avoid exposing sensitive transaction descriptions, merchant detail or unnecessary personal financial data through broad entity state.

### UX / Quality

- [ ] Add a Settings section explaining available Home Assistant entities and their privacy implications.
- [ ] Keep entity creation opt-in where appropriate and avoid noisy or redundant entities.

### Testing / Validation

- [ ] Verify entity values reconcile with Fynvo screens and APIs.
- [ ] Verify unknown/incomplete financial information maps to unavailable/unknown rather than zero.
- [ ] Validate add-on restart, upgrade and ingress behaviour on Home Assistant.
