# Fynvo v1.9.0

## Recurring Expense Management, Workflow Completion & v1.8.0 Regression Fixes

Baseline: v1.8.0 from merged `main`.

### v1.8.0 regression fixes

- Recurring Expense Edit now uses the complete active payment model and can persist Payment Method, payment handling, Account/Card links, amount type and optional lifecycle fields.
- Expense overflow menus are closed before Edit or Mark as Paid activates, so stale popovers cannot cover modal actions.
- Recurring workflow errors clear on navigation and modal close instead of leaking into Cards, Accounts or Categories.
- Category health now displays all contributing issue classes and an expandable detail view. The UI also warns if the headline and detailed counts ever disagree.

### Recurring management completion

- Payment Method and payment handling are independent. A schedule may be marked automatic or manual regardless of method where the user needs that behaviour.
- Direct Debit requires an Account. Automatic Card Payment requires a Card and derives its linked Account.
- Fixed and Variable amount types, Payee/Merchant, End Date, reminder lead time and Notes are editable.
- Automatic occurrences become Paid when due and are protected by the existing unique `(user, recurring expense, expected date)` occurrence key. Re-evaluation is idempotent.
- Manual occurrences remain Due or Overdue until Mark as Paid or Skip Payment is used.
- Calendar month arithmetic remains calendar-based for Monthly, Quarterly and Annual schedules.

### Data and migrations

No destructive schema migration is required. Existing v1.7 scheduled-payment tables and v1.8 Category integrity structures are reused.

### Regression coverage

Added frontend source-level workflow checks and backend recurrence/payment-state tests for the release-critical defects.

### Manual acceptance

The implementation is structured for the supplied iPhone/Home Assistant ingress workflows. Final device-level validation should be completed against the release branch build before merge.
