# Fynvo Roadmap

Fynvo is a household finance and cash-planning application for understanding upcoming commitments, available cash, pay-cycle pressure, spending decisions and near-term financial risk. The roadmap prioritises practical household planning over business accounting, tax, payroll or investment-trading functionality.

The current merged baseline is v1.16.0. Payment Centre, recurring-payment lifecycle, 7/14/30-day commitment planning, account funding requirements, available-cash comparisons, transactions, reconciliation, budgets, goals, scenarios, financial calendar, forecasting, CSV import, insights and responsive Home Assistant ingress are already delivered and are not repeated below as new scope.

## v1.17.0 - Pay-Cycle Cash Planning

Status: Planned

Objective: Extend v1.16 payment planning so Fynvo can answer how much cash is required before the household's next expected income event, what will be left afterwards, and which accounts are under pressure.

### Features

- [ ] Add a shared pay-cycle planning service that identifies the next expected household income date from existing active Income records without creating a separate income model.
- [ ] Calculate committed payments due before the next expected income event, including overdue unresolved obligations and automatic payments that still require funding.
- [ ] Show cash required before next pay at household and Account level, while preserving Card-to-Account derivation and explicit unknown-account handling.
- [ ] Calculate projected available cash immediately before and after the next expected income event using existing account balances, scheduled commitments and expected income.
- [ ] Support multiple household income sources by showing the next income event and the commitments covered before each following income event where practical.
- [ ] Respect existing income recurrence, effective-dated changes, occurrence dates, payment status and reconciliation rules rather than introducing parallel forecast logic.
- [ ] Add configurable minimum-balance/buffer visibility where the existing Account minimum-balance field is reliable, clearly separating required commitment funding from preferred buffer amounts.

### UX / Quality

- [ ] Add a concise "Before next pay" summary to Overview and Payment Centre using the same backend calculation.
- [ ] Clearly distinguish known shortfall, low buffer and unknown balance/account states instead of treating missing information as zero.
- [ ] Keep the planning summary compact and touch-friendly on Home Assistant ingress and iPhone-sized screens without horizontal scrolling.

### Testing / Validation

- [ ] Add regression coverage for weekly, fortnightly, monthly and multiple-income pay cycles, overdue commitments, automatic payments and no-income-known states.
- [ ] Verify Payment Centre, Overview, Cash Flow and pay-cycle planning reconcile to the same underlying occurrences and amounts.
- [ ] Verify pay-cycle calculations remain stable across Australia/Melbourne date boundaries and month-end recurrence cases.

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

Objective: Expose a small, privacy-conscious set of Fynvo planning states to Home Assistant so automations and dashboards can surface important household finance events without duplicating Fynvo calculations.

### Features

- [ ] Add Home Assistant entities for next-7-day amount required, overdue amount/count, next payment date/amount and next-pay cash requirement.
- [ ] Add projected available cash/shortfall entities only where the underlying Fynvo balance information is sufficiently reliable.
- [ ] Add optional entities for budget risk and selected savings-goal progress where the state can be represented safely and clearly.
- [ ] Add event/trigger support for material states such as payment overdue, automatic payment unconfirmed, projected shortfall and commitment due soon.
- [ ] Add notification actions that deep-link back into the relevant Fynvo screen or payment detail.
- [ ] Keep sensitive transaction descriptions, credentials and detailed household data out of entity attributes by default.
- [ ] Reuse Payment Planning, Budgeting, Goals and Forecast services as authoritative sources rather than recalculating finance rules inside the Home Assistant layer.

### UX / Quality

- [ ] Add a Settings area for enabling/disabling optional finance entities and selecting alert thresholds where appropriate.
- [ ] Document practical Home Assistant dashboard and automation examples without making Home Assistant the primary Fynvo interface.
- [ ] Ensure entity names and units are stable, understandable and migration-safe.

### Testing / Validation

- [ ] Add entity-state tests for known, unknown and shortfall cases plus update behaviour after payment lifecycle changes.
- [ ] Verify no sensitive values are exposed in unauthenticated endpoints or inappropriate Home Assistant attributes.
- [ ] Validate add-on restart, upgrade and entity availability without modifying existing household financial records.

## v1.22.0 - Debt & Liability Planning

Status: Planned

Objective: Extend Fynvo's existing liability Account types into useful household repayment planning while keeping the feature focused on visibility and cash requirements rather than lending advice.

### Features

- [ ] Add optional liability metadata for loans and credit facilities, including current balance/amount owing, minimum payment, repayment frequency, next repayment date and interest rate where the user chooses to record it.
- [ ] Link liability repayments to existing Scheduled Payments/Transactions where practical instead of creating a second payment workflow.
- [ ] Show upcoming minimum repayments alongside other household commitments and include them in cash planning when not already represented by a recurring payment.
- [ ] Add repayment-progress views for mortgage, car/personal loans and credit-card style liabilities.
- [ ] Add simple payoff projections based on recorded balance, rate and planned repayment amount, clearly labelled as estimates rather than financial advice.
- [ ] Prevent double counting when a liability repayment already exists as a Recurring Expense, Bill or reconciled Scheduled Payment.
- [ ] Investigate whether buy-now-pay-later schedules can be represented safely using the same liability/commitment architecture before adding dedicated support.

### UX / Quality

- [ ] Add liability detail that shows amount owing, next repayment, minimum requirement and projected progress in plain household language.
- [ ] Keep debt projections separate from cash-flow certainty and explain assumptions used in any estimate.
- [ ] Ensure mobile layouts prioritise amount owing, next payment and progress rather than dense amortisation tables.

### Testing / Validation

- [ ] Add regression coverage for liability balance direction, internal transfers/repayments, repayment deduplication and payoff estimates.
- [ ] Verify liability balances are never counted as available cash in Payment Planning or Forecast.
- [ ] Validate historical Transactions and existing Account types remain intact through any additive migration.

## v1.23.0 - Savings Goals & Surplus Allocation

Status: Planned

Objective: Build on Fynvo's existing Goals capability so households can understand what surplus is realistically available for goals after near-term commitments and preferred cash buffers.

### Features

- [ ] Calculate goal contribution capacity from projected surplus after committed payments and configured account buffers, without automatically moving money.
- [ ] Show whether planned goal contributions remain affordable before the next pay cycle and over a selected forecast horizon.
- [ ] Support emergency-fund goals with target coverage expressed in practical household terms such as selected months of committed expenses.
- [ ] Add goal progress history from actual linked contributions where reliable Account/Transaction evidence exists.
- [ ] Show the effect of changing a planned contribution using existing Scenario/What-If foundations rather than mutating the real Goal immediately.
- [ ] Allow multiple active savings goals to be prioritised for planning while keeping allocation suggestions optional and explainable.
- [ ] Preserve a clear distinction between available cash, committed money, planned goal contributions and completed actual transfers.

### UX / Quality

- [ ] Add an "Available for goals" summary only when the underlying cash and commitment picture is sufficiently complete.
- [ ] Present goal affordability and progress without implying guaranteed outcomes or financial advice.
- [ ] Provide drill-through from goal contribution evidence to the relevant Transactions/Accounts.

### Testing / Validation

- [ ] Add regression coverage for multiple goals, unknown balances, cash buffers, planned versus actual contributions and scenario isolation.
- [ ] Verify goal calculations never reduce Payment Planning funding requirements or silently create Transfers/Transactions.
- [ ] Verify goal progress remains consistent across Overview, Goals and reporting views.

## Future

The following are longer-term possibilities and are not committed release scope:

- [ ] Richer cross-account cash optimisation, including suggested internal transfers before commitments, subject to explicit user review and no automatic money movement.
- [ ] More advanced household forecast confidence and uncertainty ranges where they can remain explainable.
- [ ] Additional financial alerts and Home Assistant entities based on demonstrated household usefulness.
- [ ] Import automation and broader bank-file support after reviewing practical Australian institution export formats.
- [ ] Production Australian CDR/Open Banking connectivity only if a secure provider, consent model and sustainable implementation path are established.
- [ ] Optional local financial intelligence that highlights patterns or risks without providing regulated financial advice or silently changing financial records.
- [ ] Deeper audit/change-history coverage for important household finance mutations where existing lifecycle history is incomplete.
- [ ] Further backup/restore, migration resilience, data-retention and diagnostic controls as the household data model grows.

Fynvo will not pursue double-entry bookkeeping, BAS/GST reporting, payroll, business invoicing, corporate accounting, tax preparation, investment trading or personalised financial advice as part of its household-finance product direction.
