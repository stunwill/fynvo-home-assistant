# v1.31.0 release validation

This candidate implements the approved Financial Integrity and Account-Level Cash Flow specification on `release/v1.31.0-financial-integrity-account-forecasting`, based on merged main `074a62d46ef5b06c075b5e1602a896c32461286e`. No merge, release tag, published image or Issue is authorized by this work.

## Financial behavior

`balance_evidence.py` owns observed versus estimated cash. Bank snapshots remain authoritative when transaction history is imported. Manual observations retain the identities and financial revisions they cover; late imports and revised covered transactions require confirmation. New manual movements after an observation adjust its balance. Future transactions are projected on their effective date. Available cash is capped by actual cash. Credit limits and liability balances do not fund household decisions.

`financial_projection.py` materializes recurring occurrences before pinning a SQLite read snapshot. Canonical events reuse existing recurrence, effective amount changes, Bill lifecycle, transfers, overrides and scenario adapters. An explicit Bill occurrence link survives rescheduling. Remaining Bill amounts replace their scheduled occurrence. Accepted income receipts retire only the nearest unambiguous occurrence, considering occurrences outside the requested forecast window. Existing conflicting Bill links retain their records and produce an incomplete, conservative projection.

`cash_decisions.py` derives dated funding requirements and Safe-to-Spend from the same projection. It reserves preferred Account buffers plus the household buffer once, excludes the next payday from today's capacity, and allocates each donor's headroom once. Recommendations are advisory and do not create ledger or bank transfers. Positive spendable cash requires verified evidence and funded destinations. Signed negative shortages remain visible. Additional household capacity is explicitly provisional when transfers or confirmations remain outstanding.

Account forecasts use book cash; cash decisions use conservative accessible cash. Legacy API structures remain available, including string warnings, positive reserved payment amounts and payment coverage dates. Structured integrity issues and canonical cash events are additive. Input fingerprints are independent of forecast scope; projection fingerprints also cover scope and scenario. The UI suppresses positive cash when combined results have different inputs, ignores superseded Plan requests and clears failed planning reads.

## Automated checks

- Unchanged baseline: 256 backend tests passed locally, 293 frontend regressions passed in main CI.
- Implementation: **276 backend tests passed locally** in the full regression suite, including v19 upgrade preservation, observation immutability, identity/receipt regressions and a 365-day forecast with 10,000 historical transactions.
- Frontend: 298 regressions passed locally, including rendered notices, escaped Account names and mixed-input suppression.
- Python compilation, application import, Ruff, production Vite build and release metadata validation passed locally.
- GitHub PR CI must pass backend, frontend and Home Assistant add-on checks, including its Docker image build. Docker is unavailable in the implementation workspace.

The Vite bundle-size warning and Python SQLite/date adapter deprecation warnings predate this candidate's release checks. They do not indicate a failed test, but remain visible in CI logs.

## Migration and restore

Schema v19 is additive: balance observations, indexes, immutable-observation guard and nullable Bill occurrence references. The upgrade backfills only an unambiguous original occurrence and preserves all source records. Existing collisions remain available for review; database guards prevent new active occurrence collisions.

Before the upgrade, SQLite's backup API writes `<database>.pre-v19.sqlite3` atomically through a temporary file. A backup failure blocks the upgrade. The backup is not overwritten on repeated startup. Tests recreate the v18 schema around existing financial records, upgrade twice, inspect the preserved transaction rows and verify the backup's v18 version and integrity.

For rollback, stop the candidate before replacing its database with the pre-v19 backup and reinstalling the previously approved image. Preserve the candidate database separately because post-upgrade financial edits would otherwise be lost. The older application must not be allowed to write the upgraded database as a substitute for restoring a matching backup.

## Installed Home Assistant acceptance gate

The following checks require the real supported device and bank connection and have not been claimed as passed:

1. Take the normal Home Assistant backup and retain the application's pre-upgrade database copy. Install the reviewed candidate image on representative data.
2. Confirm app version 1.31.0, schema 19, successful startup and second restart without changed financial row counts or repeated migrations.
3. Reconcile actual current/available balances with Redbark evidence. Check fresh sync, stale/missing balances, failed sync and recovery without losing history or inventing freshness.
4. Confirm an unchanged manual balance and verify updated observation evidence without an income/expense transaction. Import older activity and confirm it cannot inflate current cash.
5. Rehearse Bills $100, Savings $1,000, a $200 Bill and a $50 Bills buffer. Expect Bills lowest balance -$100, $150 funding required by its due date, $850 provisional household capacity and transfer action required. A recommendation alone must not clear the shortfall.
6. Test salary arriving after a due date, partial Bills, rescheduled Bills, dated one-offs, future transactions and internal versus liability transfers. Confirm Overview, Accounts and Plan agree within identical scopes.
7. Check ingress authentication, relative API paths, mobile widths, Account selector, buffer/funding dates, stale-data notices, refresh failure and rapid horizon changes.
8. Verify a restored v18 backup opens with the prior approved image and preserves pre-upgrade records. Record installed acceptance and reviewer approval before merging or releasing.

Historical forecasts are explicitly incomplete reconstructions when no historical balance observation exists. Date-only projections apply income, transfers, then expenses, and cannot guarantee intraday bank settlement order. Donor recommendations are deliberately conservative: future donor receipts do not become transferable cash before their availability is established.
