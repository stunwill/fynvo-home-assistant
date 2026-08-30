# Fynvo Roadmap

Fynvo is a household finance and cash-planning application for understanding upcoming commitments, available cash, pay-cycle pressure, spending decisions and near-term financial risk. The roadmap prioritises practical household planning over business accounting, tax, payroll or investment-trading functionality.

The current development baseline is v1.16.2. Payment Centre, recurring-payment lifecycle, 7/14/30-day commitment planning, account funding requirements, available-cash comparisons, transactions, reconciliation, budgets, goals, scenarios, date-oriented financial Calendar, Cash Flow forecasting/impact analysis, CSV import, insights, Overview drill-down navigation and responsive Home Assistant ingress are already delivered and are not repeated below as new scope.

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

- [ ] Add a compact commitments intelligence view with filters for changed, missed, annual/long-cycle and incomplete commitments.
- [ ] Keep suggestions explicitly reviewable and never auto-update recurrence rules without user action.
- [ ] Link each suggestion back to the authoritative Recurring Expense, Bill, Scheduled Payment or supporting Transactions.

### Testing / Validation

- [ ] Add regression coverage for amount-change detection, absent-occurrence detection, annual/quarterly warnings, duplicate suppression and variable-payment history.
- [ ] Verify suggestions do not mutate financial records until explicitly accepted.
- [ ] Verify intelligence remains consistent with payment lifecycle and reconciliation state.

## v1.20.0 - Account Position & Cash Allocation

Status: Planned

Objective: Improve household understanding of where cash sits, what each Account must fund and how much remains safely available after near-term obligations.

### Features

- [ ] Add Account-level upcoming commitment summaries using the existing Payment Planning Account attribution and Card-to-Account relationships.
- [ ] Show projected Account balance after known upcoming commitments where the Account balance and funding path are reliable.
- [ ] Add optional Account purpose/role metadata such as everyday spending, bills, savings or offset without changing financial transaction semantics.
- [ ] Surface unfunded or underfunded Accounts before due dates using conservative unknown-balance handling.
- [ ] Support simple planned cash-allocation guidance between known liquid Accounts without creating automatic banking transfers.
- [ ] Reconcile Account-level totals back to household-level Payment Centre and Cash Flow totals.

### UX / Quality

- [ ] Add Account cards that distinguish current known balance, committed amount, projected balance and unknown information clearly.
- [ ] Provide drill-through from Account pressure warnings to the relevant commitments.
- [ ] Keep liability Accounts visually distinct from spendable cash and never include them as available funds unless explicitly valid.

### Testing / Validation

- [ ] Add regression coverage for transaction, cash and linked Card Accounts, unknown balances, liabilities and Account attribution.
- [ ] Verify Account projections reconcile with household forecast/payment-planning calculations.
- [ ] Verify no automated transfer or external banking action is implied by allocation guidance.

## v1.21.0 - Household Planning Scenarios

Status: Planned

Objective: Let households test realistic near-term financial decisions without changing authoritative financial records.

### Features

- [ ] Extend the existing scenario/forecast foundations into explicit temporary household planning scenarios.
- [ ] Allow users to model one-off income, one-off expenses, delayed purchases and adjusted discretionary spending assumptions.
- [ ] Show how a scenario changes lowest balance, projected ending balance, pay-cycle pressure and shortfall risk.
- [ ] Keep scenario events clearly separated from authoritative Bills, Recurring Expenses, Planned Spending and Transactions until a user explicitly converts a scenario item into a real record.
- [ ] Support compare-to-baseline and compare-to-expected views using the existing forecast engine.
- [ ] Allow scenarios to be discarded without leaving financial records behind.

### UX / Quality

- [ ] Provide clear "Scenario only" labelling throughout the workflow.
- [ ] Make before/after impacts understandable without requiring accounting terminology.
- [ ] Keep scenario creation and comparison usable on mobile and Home Assistant ingress.

### Testing / Validation

- [ ] Add regression coverage proving scenarios do not mutate authoritative records.
- [ ] Verify baseline/expected/scenario calculations use shared financial-event semantics.
- [ ] Verify discard and optional explicit conversion behaviours.

## v1.22.0 - Data Quality & Household Finance Maintenance

Status: Planned

Objective: Make Fynvo easier to keep accurate over time by surfacing stale, incomplete and contradictory financial records before they undermine planning.

### Features

- [ ] Add a dedicated household finance data-quality summary covering Accounts, Income, Bills, Recurring Expenses, Categories and payment setup.
- [ ] Detect stale expected dates, inactive references, missing funding Accounts/Cards, missing categories, implausible recurrence configurations and unreconciled long-overdue items.
- [ ] Surface duplicate-looking Income, Bills and Recurring Expenses as review candidates without automatic deletion or merging.
- [ ] Add clear remediation links to the affected record/workflow.
- [ ] Distinguish blocking planning issues from lower-priority tidy-up suggestions.
- [ ] Track resolution/dismissal state for non-critical data-quality suggestions where appropriate.

### UX / Quality

- [ ] Replace unexplained aggregate warnings with actionable issue descriptions and affected-record counts.
- [ ] Keep review workflows non-destructive by default.
- [ ] Provide a concise maintenance summary on Overview or Settings only when attention is genuinely required.

### Testing / Validation

- [ ] Add regression coverage for missing/invalid references, stale records, duplicate candidates and warning resolution.
- [ ] Verify data-quality analysis cannot alter authoritative financial records without explicit user action.
- [ ] Verify warnings explain why a record is considered problematic.

## Longer-term direction

Future work may include richer bank/open-banking integrations, notifications, household collaboration, hosted/mobile distribution and more advanced financial intelligence. Those areas should continue to preserve Fynvo's core principles: authoritative household records, explainable calculations, conservative handling of unknown information and explicit user control over financial changes.
