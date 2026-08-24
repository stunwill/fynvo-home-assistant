# Fynvo v1.10.0

## Workflow Reliability, Performance & Data Integrity

Baseline: merged v1.9.3 (`main` at `f4ddf6a`).

### What changed

- Added a canonical relative API client suitable for Home Assistant ingress paths.
- Recurring Expenses now distinguishes loading, loaded and request-error states and provides Retry instead of treating a failed or pending request as an empty dataset.
- Recurring Expense save/update mutations normalize nullable references and optional dates before submission.
- Successful Recurring Expense changes refresh the recurring/scheduled/attention slice directly rather than waiting for the complete dashboard, Insights, Forecast, import and budgeting data set.
- Feature errors clear on navigation instead of leaking into unrelated pages.
- Preserved the v1.9.3 mobile navigation fix and v1.9.1 mobile modal containment.

### Root causes addressed

The recent slow Recurring Expenses screen was caused by two overlapping data paths: the application boot path waited for a large `Promise.all()` of approximately twenty unrelated datasets, while the page also requested recurring/scheduled data independently. The page could therefore render before authoritative recurring data had completed. v1.10.0 keeps recurring data on its own focused path with explicit request state.

Recurring save failures were made harder to diagnose because the frontend sent optional reference/date fields in UI form shapes and then collapsed any unsuccessful response into a generic message. The v1.10.0 mutation path normalizes empty optional IDs/dates to `null` at the save boundary and preserves structured backend errors.

### Installed acceptance still required

Repository automation cannot run the actual Home Assistant installation on the user's iPhone. Before merge, validate in the installed add-on:

- Existing Recurring Expenses do not flash the empty state while loading.
- Existing Recurring Expenses become visible promptly.
- Edit a representative recurring expense, Save, reload Fynvo and reopen the expense to verify persistence.
- Verify Direct Debit, Automatic Card Payment, Expense Type, Category, Payee/Merchant and Notes persistence.
- Verify mobile navigation and the recurring editor remain correctly positioned.
