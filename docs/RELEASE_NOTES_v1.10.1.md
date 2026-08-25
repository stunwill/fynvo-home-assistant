# Fynvo v1.10.1

## Installed Reliability, API & Workflow Hardening

Baseline: merged v1.10.0 on `main` at `504b6d4104100f3235250c83df45daa6d5fb1007`.

### Why this corrective release exists

v1.10.0 established a canonical ingress-safe API client and explicit Recurring Expense loading/error states, but repository-level success does not prove the installed Home Assistant workflow. v1.10.1 tightens the contracts and removes two concrete reliability risks discovered during review of the merged code.

### Recurring Expense update contract

The active v1.7 payment-aware Recurring Expense PUT endpoint now accepts the canonical `RecurringExpenseCreateV17` schema rather than a loose dictionary. Payment Handling and Payment Confirmation Period are validated explicitly, while the remaining fields are delegated to the existing v1 Recurring Expense persistence layer.

A new integration test uses a representative iCloud Storage record with Automatic Card Payment and verifies the full mutation lifecycle by fetching the record again after the PUT. The test verifies Payee/Merchant, Notes, Payment Method, Payment Handling, Card, derived Account, Expense Type and confirmation-period persistence.

### Recurring Expense loading

The focused page previously requested both Scheduled Payments and Payment Attention even though Payment Attention is a filtered view of Scheduled Payments and both backend endpoints invoke schedule generation. v1.10.1 removes that duplicate critical-path request and derives attention locally from the authoritative Scheduled Payments response.

The page also no longer mirrors the entire parent application data object back into its fast local state. Existing authoritative recurring data can render immediately while a focused refresh proceeds in the background. A user with an existing dataset should therefore never see a false empty state simply because secondary application data is still loading.

### API and ingress review

The canonical `apiRequest()` client continues to use ingress-safe relative `api/...` paths with same-origin credentials. Several older modules still use the established relative `fetch('api...')` helper. Those requests are also ingress-relative, so they are documented as legacy implementation rather than being rewritten wholesale in this corrective release.

### Data safety

No destructive migration is introduced. Existing Accounts, Cards, Recurring Expenses, Scheduled Payments, Categories, Expense Types and financial history are preserved.

### Automated verification

Added or updated coverage for:

- full Recurring Expense PUT persistence through a fresh GET;
- actionable invalid Automatic Card Payment validation;
- focused Recurring Expense loading without a duplicate Payment Attention request;
- immediate rendering of already-loaded recurring data;
- nullable mutation normalization;
- preservation of Payment Handling, Payment Method and Card-to-Account UI fields.

### Installed Home Assistant verification required

Repository tooling cannot perform the real installed iPhone/Home Assistant ingress acceptance test. Before merge, verify in the installed add-on:

1. Recurring Expenses loads without a false empty state.
2. Record approximate load time to existing expenses.
3. Edit an existing recurring expense, including Payee/Merchant, Notes, Expense Type and payment configuration.
4. Save, reload Fynvo, reopen the expense and confirm the values remain.
5. Create a Card and confirm immediate display and availability in the recurring Card selector.
6. Verify mobile navigation, modal containment and overlay behaviour remain correct.
7. Review browser/network diagnostics for unexpected 4xx/5xx or failed requests where available.

These installed checks must not be reported as passed until they are actually performed.
