# Fynvo v1.8.0

## Recurring Expenses Responsive UI/UX Completion

Fynvo v1.8.0 completes the production Recurring Expenses responsive experience on top of the real Payment Handling and Scheduled Payment lifecycle introduced in v1.7.0.

### Highlights

- Completed the Recurring Expenses responsive redesign for desktop, tablet, mobile and Home Assistant ingress-sized viewports.
- Replaced the active rule-centric presentation with a Scheduled Payment occurrence-based data pipeline for List, Calendar and Summary.
- Added a fully functional Recurring Expenses Calendar with month navigation, adjacent-month dates, multiple payments per date, selected-date details, status legend and Upcoming view.
- Added real Payment Method and Scheduled Payment Status filtering.
- Added Overdue Only and Payments Requiring Attention filters.
- Added a mobile Filters bottom sheet with draft changes, explicit Apply/Clear actions, focus handling and iOS safe-area padding.
- Added a compact mobile financial Summary with expandable breakdown, largest upcoming expense, payment-status totals and quick actions.
- Added real Direct Debit Account and Automatic Card Payment Card/linked-Account presentation.
- Added state-aware payment actions using v1.7 Mark as Paid, Skip Payment and reconciliation workflows.
- Added matched-transaction evidence for confirmed Scheduled Payments.
- Improved mobile rows, sorting, touch targets and Calendar density without normal horizontal page scrolling.
- Preserved v1.5.1 search, date-range, frequency, category, summary, sorting, action-menu and empty-state behaviour.
- Preserved v1.7 Account, Card, Scheduled Payment, attention and transaction-reconciliation behaviour.

### Production route cleanup

The active production route still enters through the established application shell, but the historical `RecurringExpensesPageV151` component is now only a compatibility wrapper. Production rendering resolves to the durable `RecurringExpensesPage` component rather than adding another release-numbered page component.

### Calendar temporal model

List and Calendar deliberately use different temporal scopes while sharing the same Scheduled Payment source and all non-temporal filters:

- List uses the selected relative Date Range, defaulting to Next 30 days.
- Calendar uses the explicitly selected calendar month.
- Search, Frequency, Category, Payment Method and Payment Status continue to apply in Calendar.
- Navigating Calendar months does not mutate the List Date Range.
- Returning to List restores the previously selected relative Date Range.

This avoids an apparently empty Calendar when the user deliberately navigates outside a relative range.

### Payment-status summary logic

The Summary status groups are mutually exclusive so their amounts reconcile to Scheduled Total:

1. Paid Scheduled Payments are counted as Paid.
2. Due, Overdue and Automatic Payment Not Confirmed are counted in Overdue / Needs attention.
3. Remaining automatic payments are counted in Expected automatically.
4. Remaining manual payments are counted in Requires payment.

Payments Requiring Attention remains backed by the v1.7 `/payments/attention` API for the authoritative attention workflow.

### Data safety

No v1.8.0 database migration is required. The release uses the Scheduled Payment, Payment Handling, Card relationship and transaction-matching schema already introduced by v1.7.0.

The architecture remains:

**Recurring Expense** defines the rule

↓

**Scheduled Payment** represents an expected occurrence

↓

**Transaction** represents actual financial movement

Payment completion and reconciliation state remain on Scheduled Payments, not on the recurring rule. Existing payment, Card, Account and transaction data are not reset or recreated.

### Validation

Automated frontend regression coverage includes:

- durable production Recurring Expenses routing;
- Scheduled Payment-based shared data pipeline;
- Search and all filters;
- active mobile filter counting;
- mobile draft/apply filters;
- totals, count, average, Next Payment, breakdown and largest expense;
- mutually exclusive payment-status totals;
- grouped list presentation and sorting;
- Direct Debit and Card-linked payment sources;
- payment action wiring;
- matched payment presentation;
- List/Calendar switching;
- month-scoped Calendar behaviour;
- multiple-payment Calendar cells and `+N more`;
- selected-date and Upcoming behaviour;
- responsive/mobile presentation safeguards.

Existing v1.7 backend lifecycle tests remain the authoritative unit coverage for Scheduled Payment status transitions, automatic-payment grace periods, Mark as Paid, Skip Payment and transaction matching.

### Manual acceptance and screenshots

Real installed Home Assistant ingress and iPhone runtime screenshots cannot be truthfully produced from repository-only automation. Before merge, manually verify and capture:

#### Desktop

1. List view
2. Filtered view
3. Payment-status presentation
4. Actions menu
5. Calendar

#### Mobile

1. Collapsed Summary/List
2. Expanded Summary
3. Filters bottom sheet
4. Calendar
5. Selected date
6. Manual payment requiring attention
7. Automatic payment
8. Automatic Payment Not Confirmed

Manual acceptance must also cover Add/Edit Recurring Expense, Direct Debit Account display, Automatic Card display and linked Account, Mark as Paid, Payments Requiring Attention, CSV matched payment state and Calendar usability inside Home Assistant ingress.
