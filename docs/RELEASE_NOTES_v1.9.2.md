# Fynvo v1.9.2

## Recurring Expense Persistence & Reference Data Fixes

Baseline: merged v1.9.1 from `main`.

### Corrective scope

- Fix Recurring Expense update persistence across Payment Handling, Payment Method, Account/Card references, Payee/Merchant, Notes and Expense Type.
- Replace Recurring Expense free-text Expense Type editing with the authoritative Expense Type reference-data selector.
- Change the user-facing Account field label from `Institution` to `Bank` while preserving the existing persisted field and historical data.
- Limit new Account creation to `Transaction Account` and `Cash`, while safely retaining legacy Account Types on existing records.
- Make newly created Cards visible immediately in the current Card view while the canonical parent data refresh completes.
- Rename the automatic-payment `Confirmation grace period` label to `Payment confirmation period` and explain that it is the number of days Fynvo waits after the due date for confirmation. It does not change the due date.

### Data safety

No destructive migration is introduced. Existing Account Types, Account/Card relationships, recurring records, Categories, Expense Types, Scheduled Payments and transaction reconciliation data remain preserved.

### Manual release gate

Before merge, verify the installed Home Assistant/iPhone workflow with Edit → Save → reload → reopen, including Automatic Card Payment, Direct Debit and BPAY cases. Repository automation cannot substitute for this installed-runtime acceptance step.
