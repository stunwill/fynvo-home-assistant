# Fynvo Financial Integrity & Account-Level Cash Flow Forecasting

Final implementation specification for approval, 9 October 2026 (Australia/Sydney).

## Decision requested

Approve one focused **v1.31.0** feature release that consolidates the existing financial-event, balance, forecasting and funding calculations. Implement after approval on one dedicated feature branch, with focused commits and one PR. Do not create an Issue or merge automatically. Recheck main and version availability immediately before implementation.

Fynvo remains cash-flow-first: actual accessible bank balances, expected income, recurring obligations, dated one-off spending, expected bills, chronological account balances, lowest balances, funding needs and Safe-to-Spend. Wealth, net worth, superannuation, new banking providers and a general UX rebuild are outside this release.

## Verified baseline and limits

| Item | Verified result |
| --- | --- |
| Latest merged main | `074a62d46ef5b06c075b5e1602a896c32461286e`, merged PR #102 on 5 October 2026 |
| Latest published release | v1.30.0 |
| Release tag | Annotated tag object `d618a5efe35b5395e927cbbac9f81c0accfe9e45` resolves to the exact main commit above |
| Application metadata | Backend `APP_VERSION`, frontend package and Home Assistant config all report 1.30.0 |
| Open PRs | None at verification |
| Version availability | No v1.31.0 tag or branch reservation in the retrieved tag and branch collections |
| Effective startup schema | Version 18, confirmed through a fresh production-style TestClient lifespan without the test fixture's supplemental migration call |
| Main CI | Success, backend, frontend and add-on jobs all passed |
| Published image pipeline | All four architecture builds, manifest publication and anonymous verification succeeded before GitHub Release publication |
| Existing GitHub test results | 256 backend tests and 293 frontend tests passed |
| Local untouched backend rerun | 256 passed in 111.37 seconds, with 55,926 warnings |

Verification combined commit-pinned source inspection, GitHub job and step results, CI logs, a local rerun of the complete unchanged backend suite, and isolated runtime probes against temporary databases. No repository code was changed. No branch, commit, Issue or PR was created. Downloaded source was used solely as a read-only audit snapshot.

The installed Home Assistant instance, live household database, actual Redbark responses and physical-device upgrade behaviour were not accessed. Their validation is a release gate, not a completed result. Frontend CI and source were inspected; the complete frontend suite was not rerun locally. Existing passing tests do not demonstrate correctness of the newly identified edge cases.

## Runtime architecture and findings

1. `database.py` establishes schema 8, package initialization layers v1 and payment migrations, household imports extend the runner, and `main.lifespan` adds funding, banking and bank-activity schemas. Banking targets 18; bank activity targets 17 and does not lower it. New migration work must enter this effective startup path and advance monotonically to 19.
2. `v1251_mount.py` installs resilience wrappers into the shared `payment_planning` module at import time. The live Safe-to-Spend callable is `payment_planning_runtime_v1251.install.<locals>.build_safe_to_spend`, which delegates to `payment_planning_v1251.py`. Editing only the earlier implementation in `payment_planning.py` would miss the live path.
3. `payments_v114.py` replaces recurring-event and calendar generation with occurrence-aware wrappers. Scheduled payment identity already includes the original `occurrence_date`, independently of its rescheduled `expected_date`. Reuse that identity and its existing unique index.
4. `/api/forecast` uses `forecast.generate_forecast`. `/api/v1.3/cash-flow` adds per-account balances, transfers, overdue bills, overrides, buffer warnings and purchase simulation. This is reusable forecasting functionality, not a missing feature to recreate. It is inconsistent with the main forecast's opening-balance calculation and account eligibility: the v1.3 helper includes unarchived account types without the main liquid-account filter, and uses transactions strictly before the selected start date.
5. The active frontend chain is `main.jsx` to `AppV13.jsx`, `AppCorrectiveV1163.jsx` and the current workspace components. Plan requests `/api/forecast` plus v1.25.1 planning and Safe-to-Spend. Accounts requests the v1.25.1 account-funding endpoint. The older `App.jsx` is not the application entry point.
6. Funding already supports account assignment, Card-to-Account derivation, preferred buffers, current/next cycles, monthly requirements and payday allocation. Its core requirement calculation sums commitments and compares them with starting balances; it does not calculate the minimum balance along the full chronological account path.
7. Redbark already isolates connections and transaction identities using stable identifiers, imports posted transactions, reconciles successful bank balances by rebasing `opening_balance_cents`, and retains external snapshot evidence. Preserve these integrations and safeguards. The current provider adapter requests `includePending=false`; this release must not promise live pending-transaction ingestion.
8. Ledger and planning balance queries sum all transaction amounts without a date/status cutoff. A future-dated expense can therefore reduce today's displayed balance immediately. Missing-bank-balance sync marks an account stale but imported ledger rows still affect that calculated balance. The existing household banking test explicitly expects a manual $50 fallback to become $45 after importing a $5 transaction without a bank balance; this is an estimate, not a freshly verified bank balance.
9. Explicitly re-entering an unchanged manual balance skips the write and leaves the freshness timestamp unchanged. A separate balance-confirmation operation is needed without manufacturing a financial transaction.
10. Runtime inspection found duplicate route registrations for authentication state/login and command-centre. This release must verify the first registered handler actually serving each affected financial API. Broad authentication/router cleanup is outside scope.

### Reproduced calculation inconsistencies

| Probe | Current result | Required release behaviour |
| --- | --- | --- |
| Bills account $100, Savings $1,000, Bills expense $200 before pay, Bills buffer $50 | Safe-to-Spend reports $900, protected buffer $0 and `covered`; v1.3 projection reports Bills at minus $100 and buffer shortfall $150 | Reserve the account buffer, expose $150 needed in Bills before the expense, and never report all payments covered until funding is feasible and accounted for |
| Unresolved $75 bill due yesterday | Absent from `/api/forecast`, present in `/api/v1.3/cash-flow` | Both adapters include one unresolved obligation at the forecast anchor, retaining its original due date |
| $100 recurring payment moved two days later, linked actual bill $120 dated to the original occurrence | Main forecast includes both $120 and $100 | One obligation, $120 remaining, linked by original occurrence identity irrespective of rescheduling |
| $100 current account, manually entered $20 expense four days in the future | Current displayed balance becomes $80 immediately | Today's actual balance stays $100; projected balance falls by $20 on its date |

These are verified runtime outcomes, not hypotheses about production household data.

## 1. Canonical financial events and duplicate prevention

Create a shared event normalizer around the existing scheduled-payment lifecycle, income occurrence generator, bills, planned spending, effective amount changes, occurrence overrides, transactions and Transfers. Do not create a second persistent financial ledger. Canonical forecast events should normally be derived from existing records.

Each event carries a stable key, authenticated data scope, source type and ID, original occurrence identity, effective cash date, signed integer cents, debit/credit Account or transfer legs, lifecycle state, certainty, remaining amount, reconciliation evidence and traceable inclusion/exclusion reasons. Serialize monetary API values with the existing decimal-string conventions.

Use scheduled-payment ID and original recurring occurrence as the durable identity. A bill-to-occurrence link takes precedence over inferred date matching. Add an optional explicit scheduled-payment/occurrence reference to Bills. Backfill only unambiguous matches; preserve uncertain legacy records and expose them for review. Names and amounts alone cannot justify deleting or merging records.

Apply one precedence policy: accepted actual settlement evidence supersedes the outstanding amount it settles; a linked bill supplies the actual remaining obligation in place of its recurring estimate; occurrence overrides adjust that same event; unresolved scheduled payments remain reserved until resolved. Paid, reconciled, skipped and cancelled occurrences contribute no remaining future debit. Restoring or unmatching restores the remaining obligation without changing original identity.

Reuse existing reconciliation links and scheduled-payment transaction matching. Partial settlement reserves only the remaining amount. Suggested matches remain suggestions. Guard confirmed settlement allocation against double use, including concurrent requests; ambiguous historical cross-links require review rather than destructive cleanup. Preserve histories and optimistic version checks.

Dated one-off `planned_spending` in planned/committed state appears once. Expected Bills and variable recurring estimates must retain their estimated label until replaced by actual bill evidence. Undated obligations remain visible as incomplete commitments; do not invent a date or assign them to an arbitrary Account. Materialized occurrences must remain idempotent when forecast, calendar and planning calls run concurrently.

## 2. Current balances, reconciliation and freshness

Introduce one balance resolver used by Accounts, forecast, Overview and planning. Return actual book/current balance, conservative accessible balance, source, observed-at and fetched-at timestamps, verification/freshness state, connection health and the calculation basis. A known zero is valid; missing evidence is not zero.

Add immutable balance-observation records for successful provider balances and explicit manual confirmations. Preserve existing account and transaction records and banking identities. Maintain the existing opening-balance compatibility representation, but stop treating imported history as an independent debit against a provider snapshot that already incorporates it.

For connected Accounts, a successfully obtained provider snapshot is authoritative for actual balance. Historical imports, edits and new sync rows cannot drift that actual balance without a new observation. When the balance endpoint fails, retain the previous observation and its original timestamp, mark it stale and expose ledger-derived estimates separately. Do not infer which bank movements are outside a snapshot solely from transaction date or insertion ID. Unsupported reflection evidence produces an incomplete result, not a fabricated current balance.

For manually maintained Accounts, use the ledger with explicit settled/effective-date rules, excluding future transactions from today's actual figure. Manual confirmation records the observed amount and the covered ledger basis so importing older transactions cannot silently double-count them. Identify covered records and their revisions, not just an insertion watermark. Same-value confirmation refreshes observation evidence without creating a fake income/expense transaction.

The proposed starting freshness policy is bank observations older than 24 hours and manual confirmations older than 7 days flagged stale, configurable and explained in the UI. Sync failure marks bank verification degraded immediately, regardless of age. These are proposed release defaults, not existing repository behaviour. Stale balances remain visible with their timestamp, while an unqualified positive Safe-to-Spend result requires sufficiently verified inputs or explicit manual reconfirmation.

Where a provider supplies both current and available balance, use a conservative accessible amount capped by actual current cash, excluding overdraft/credit facilities. Preserve book-balance charts separately from accessible-cash decisions. Do not deduct a pending hold twice when already reflected in available balance. Redbark stays posted-only in this release; unsupported pending evidence is reported honestly.

Legacy manual balances without reliable timestamps remain legacy ledger balances requiring confirmation. Migration must not manufacture observation times. Legacy future transactions stay in history but move from current-balance effect to dated projection effect; expose the explanation and test the intentional numerical correction.

## 3. Chronological account and household projections

Consolidate `forecast.py`, v1.3 projection helpers and pay-cycle calculations behind one shared projection service. Reuse recurrence/effective amount logic, Transfers, overrides, overdue retention and warning logic. Avoid another layer of import-time replacements.

Inputs are one coherent balance/input snapshot, canonical events, eligible Account scope, mode, anchor and horizon. Expand once, project once and derive API outputs from the same result. Obtain the final calculation inputs in a consistent read transaction after any required occurrence materialization. Include `as_of`, input fingerprint and rules version so clients can detect a mixed or obsolete result.

Calculate account and household trajectories in integer cents, including the opening point in minimum and breach detection. Return current balance, end balance, lowest balance/date, first negative point, first buffer breach, incoming/outgoing totals, transfers and contributing event keys for each Account. Household totals must reconcile with eligible account totals plus explicitly identified unassigned effects.

Preserve the established date-only convention that income on a date precedes that date's obligations. Order dated transfer receipts before expenses they are intended to fund, check the donor's balance before applying a transfer, and use stable IDs for tie-breaking. Explain that date-only forecasts do not guarantee intraday bank settlement order. Do not invent arrival times.

Overdue unresolved obligations are retained once at the anchor, with original due date shown. Rescheduled occurrences use their effective cash date. Apply existing start/end dates, effective changes, skips, restores and monthly/fortnightly rules consistently. An unknown or missing Account affects household commitments but cannot receive a fictional Account forecast.

A transfer has two linked legs. Transfers between eligible cash Accounts have zero household effect. A transfer to a liability or excluded external Account is cash leaving the eligible household cash perimeter, not a neutral movement. Existing future Transfers already have ledger legs; exclude them from actual opening cash and replay their forecast effect exactly once.

Active transaction, savings, offset and cash Accounts fund cash-flow decisions. Archived/inactive Accounts, Cards, credit limits and liability balances cannot create available funding. Preserve their records and historical views. Use existing authenticated ownership/access rules, and test separate household/member contexts without broadening visibility.

Baseline contains explicit known obligations and explicitly entered expected Bills. Expected mode adds clearly labelled historical estimates only for uncovered category/period amounts. Category overlap must be period-aware; a single known bill must not suppress an unrelated year's estimates. Unassigned historical estimates stay unassigned unless there is defensible account evidence. Scenario and purchase-simulator adapters operate on copies of the same events and never modify source financial records.

A forecast anchored in the future rolls forward from verified current cash; it cannot reuse today's amount as if no intervening events occur. Historical anchor requests require historical evidence or a clearly incomplete reconstruction. Do not present today's rebased bank opening balance as a historical bank snapshot.

## 4. Account funding and protected buffers

Derive funding from the chronological trajectory, not total expenses alone. For Account a, buffer shortfall is `max(0, preferred_buffer[a] - minimum_projected_balance[a])` over the decision window. Return the first deadline and contributing obligations as well as the maximum requirement. Show negative-cash shortfall separately from buffer shortfall.

An incoming payment after a bill's due date does not fund that earlier bill. Account-specific income enters only its destination Account. A surplus elsewhere can support a proposed transfer, but the destination stays at risk until that funding action is recorded or confirmed in the plan.

Protect preferred Account buffers and the existing household cash buffer. Recommended policy: the household buffer is an additional household reserve; protect it once, with an explicit breakdown showing Account-buffer total and household extra reserve. Defaults remain zero. Do not silently reserve the same buffer in several calculation stages.

Generate explainable transfer recommendations from donors' transferable headroom after their own dated obligations and buffers. Allocate donor capacity once across all destinations, with deterministic deadlines and no circular transfers. If donors cannot cover all deficits, show the remaining household shortage. Recommendations do not execute bank transfers or silently change projections. Distinguish `needs_transfer`, `cash_shortfall`, `needs_information`, `unavailable` and `covered`.

Keep current-cycle, next-cycle and monthly figures as separate scopes. Unknown assignment, inaccessible balances and archived funding Accounts must retain existing setup/error guidance.

## 5. Safe-to-Spend and payday allocation

Use the same canonical events, balance observations, buffers and chronological projection for Safe-to-Spend, account funding and payday allocation. Preserve existing API keys and signed shortfall information; add fields for account headroom, funding actions, verified/provisional capacity, freshness and completeness.

Safe-to-Spend's default decision window remains now until immediately before the next eligible income boundary. Future income at that boundary cannot inflate spending capacity today. Without a valid next-income boundary, retain the current incomplete/null behaviour and useful known commitments rather than inventing a payday.

Calculate capacity from the lowest projected accessible cash after all explicit commitments and protected reserves in that window, capped by accessible cash now. Reserve dated one-off spending and explicit expected Bills, not only scheduled payments. Separately show the effect of additional discretionary historical estimates; do not silently represent an expected-mode estimate as a confirmed obligation.

Household capacity and payment readiness are distinct. Money in Savings cannot label an underfunded Bills Account `covered`. Where a transfer plan is feasible, disclose transferable capacity and required transfers; keep payment readiness `needs_transfer`. A positive unqualified Safe-to-Spend headline requires verified balances, complete essential obligations and funding assignments, and protected destination funding. Until those conditions hold, present provisional capacity with the reason, not a green covered state. Negative shortfalls remain visible even when the positive spendable amount is unavailable.

Payday allocation starts from projected balances immediately before the income date, applies only destination-specific income that is eligible at that boundary, and funds the next decision window using the same donor rules. It never treats today's balance as the payday opening position or spends the same salary across multiple destinations. Preserve the existing no-income, partial-planning and structured-stage-error responses.

## 6. API and screen integration

| Surface | Integration contract |
| --- | --- |
| `/api/forecast` and drilldown/scenario consumers | Existing fields preserved, household and account projections supplied by shared service, explicit completeness/freshness added |
| `/api/v1.3/cash-flow`, upcoming, calendar and purchase simulator | Compatibility adapters over the same canonical event/projection result |
| `/api/payment-planning` and pay-cycle endpoints | Existing periods, current/next cycle and payday allocation derived from shared projections |
| Safe-to-Spend, original and v1251 endpoints | Same value, boundary, buffers, event keys and readiness for identical inputs |
| Account-funding, original and v1251 endpoints | Same dated shortfalls, donor constraints and structured unavailable/setup states |
| Accounts balance responses | Shared current/accessible balance resolver with source and timestamp, no separate frontend sums |
| Overview | Current household cash, qualified Safe-to-Spend, next income, first account funding deadline and lowest projected cash; link to account-specific causes |
| Accounts | Current/source/freshness, buffer, lowest/date, first breach and required funding; retain balances, Cards, activity and banking navigation |
| Plan | Household/Account selector, chronological chart and events, baseline/expected distinction, traceable shortfalls and payday transfers; preserve existing horizon and calendar controls |

Update the active workspace components and endpoint constants, not obsolete app files. Use a shared frontend load result or snapshot fingerprint across each screen. Invalidate projections on balance confirmation, sync, payment lifecycle, transfer, income, bill, planned spending and buffer changes. Reject stale responses after rapid navigation or changes; preserve useful partial results and retry controls.

The charts must show starting, lowest and end points, zero and buffer reference where relevant, readable mobile amounts and date labels. Actual, expected and estimated information must be visibly distinguishable. Do not add client-side financial arithmetic.

## 7. Migration, tests and Home Assistant gates

Schema 19 is proposed for additive balance observations, covered-ledger evidence and explicit bill-to-occurrence linkage. Derived projections do not need persistent duplicated events. Add indexes and uniqueness guards only after validating existing rows. Keep existing financial IDs, transaction histories, reconciliation decisions, ownership, provider identities, credentials and scheduled-payment history intact.

Migration must run from the real lifespan and be idempotent across repeated restarts, fresh install and representative older schemas. Check schema and row preservation, indexes, integrity and orphan references. Back up SQLite before upgrade using a consistent backup operation. Do not promise a database downgrade; test restoring the pre-upgrade backup with the matching previous image. Keep version advancement after successful structural work and prevent partial backfills from being reported complete.

Tests must assert financial outcomes, not just implementation strings. Retain the 256-test backend baseline and existing frontend suite, updating an existing assertion only where this specification deliberately changes incorrect behaviour.

Required new regression coverage:

- Rescheduled recurring occurrence plus linked Bill reserves exactly one actual remaining amount; ambiguous links are flagged.
- Paid/matched/skipped/cancelled, partial settlement, restore/unmatch and concurrent confirmations preserve identity and remaining obligation.
- Successful balance plus overlapping transaction history has no second cash effect; missing balance plus imported history leaves provider actual observation unchanged and labels estimates stale.
- Future transaction/transfer does not change current actual cash; historical import after manual observation does not double-count it; same-value confirmation refreshes evidence.
- Genuine zero, unknown, stale, negative and current-versus-available bank balances behave distinctly; no credit limit becomes cash.
- Two Accounts, multiple income sources, income after expense, same-day ordering, pre-existing negative opening point and protected buffers yield correct minima/deadlines.
- Internal transfers conserve household cash; liability/external legs obey the eligible cash perimeter; one donor cannot fund two deficits beyond its headroom.
- Unassigned events reconcile household and account totals without zero-filling missing balances.
- Baseline, expected, scenario, calendar, payment planning, Safe-to-Spend and payday allocation agree for the same input snapshot; scenarios preserve records.
- Weekly, true fortnightly, month-end, leap-year, start/end boundaries, rescheduling beyond a horizon and configured Australian timezone/DST are deterministic.
- API compatibility, authentication and household isolation remain intact. Financial route handlers are checked through actual dispatch, not names alone.
- Behavioural frontend tests render freshness, provisional capacity, funding actions and Account selection, handle refresh failures and reject obsolete responses. Keep existing source checks but do not rely on them as financial proof.

Validation gates: Python compilation, lint, full backend tests and application import; full frontend regressions and production build; YAML and release metadata validator; add-on Docker build; migration rehearsal with retained historical records; performance checks for 365-day forecasts and repeated page loads without excessive writes or database locks.

Home Assistant rehearsal must cover amd64 and the user's Raspberry Pi aarch64 path, persistent `/data`, ingress and direct authentication, restart/resume, stale frontend cache, disconnected banking, partial sync failure, reconnect and real iPhone/desktop Overview, Accounts and Plan. Verify all four advertised image architectures and exact anonymous version image reference through the existing release pipeline. Actual installed-device verification remains pending until an accessible test instance is available.

## Delivery dependency order

1. Recheck latest main/version, establish isolated feature branch and baseline contracts after approval.
2. Add schema 19 observations/linkage and migration safety checks.
3. Introduce shared balance resolver and snapshot/reflection rules.
4. Consolidate canonical events and lifecycle/duplicate precedence.
5. Consolidate chronological projection and compatibility adapters.
6. Derive funding, buffers, Safe-to-Spend and payday allocation from that result.
7. Integrate active Overview, Accounts and Plan workspaces with shared freshness and invalidation.
8. Complete regression, migration, container and Home Assistant gates; synchronize all version metadata and release notes; open one complete PR with evidence and remaining installed-device limitations. Do not merge.

These are focused implementation commits within one release branch, not separate feature PRs. The critical path is balance evidence and event identity before projection, then funding/Safe-to-Spend, then UI and release validation.

## Technical risks and controls

| Risk | Control |
| --- | --- |
| Import-time wrappers or duplicate dispatch bypass a fix | Verify real handlers and adapt all live financial entry points; bounded refactor with contract tests |
| Provider snapshot and imported history represent overlapping money | Authoritative immutable observations, explicit reflection basis and separate stale estimates |
| Legacy bill identity is ambiguous | Unambiguous backfill only, explicit occurrence links, retained evidence and visible review state |
| Migration changes known display values | No record deletion/rewrite, explain corrected date cutoffs, compare before/after fixtures and retain backup |
| Positive household cash hides a destination deficit | Separate transferable capacity from funded payment readiness; dated donor validation |
| Combined requests see different sync states | Consistent read snapshot, shared input fingerprint and UI response invalidation |
| Credit/liability/archived Accounts inflate cash | One eligibility policy and explicit perimeter tests |
| Provider available balance lacks pending-item detail | Conservative accessible cap, posted-only integration preserved, no invented pending coverage |
| Large warning volume obscures failures | New tests must not add unexplained warnings; inspect financial/migration warnings, defer unrelated framework cleanup |
| CI image checks are mistaken for installed-device proof | Separate pipeline evidence from mandatory upgrade/ingress/device rehearsal |

## Acceptance criteria for approval

The release is acceptable only when:

1. Every obligation has stable identity and contributes its remaining cash effect once across all financial surfaces.
2. Original histories, banking connections/mappings and current API contracts survive upgrade and repeated restart.
3. Account balances show their actual evidence, source and timestamp, and missing/stale information cannot be promoted to verified zero or fresh cash.
4. Future transactions affect their future date; imports cannot double-apply movements already represented in a balance observation.
5. Account and household forecasts expose correct starting/lowest/end balances, dates, funding deadlines and buffer breaches from one event stream.
6. Same-day/date ordering and cash-perimeter rules are deterministic and disclosed, with unknown Account effects explicitly reconciled.
7. The reproduced $100 Bills/$1,000 Savings/$200 expense/$50 buffer case reports Bills at minus $100, a $150 funding requirement and $850 household transferable capacity before any additional household reserve. It cannot report all payments `covered` before the Bills funding action is addressed; the positive headline remains qualified as specified.
8. The linked rescheduled $120 Bill case reserves $120 once, and the overdue $75 Bill appears once in both forecast adapters.
9. Safe-to-Spend, funding and payday allocation share events, balances, protected reserves and boundaries, with useful partial/error states instead of false certainty.
10. Overview, Accounts and Plan agree for identical snapshot/rules/horizon, with legible mobile views and current refresh behaviour.
11. All required automated checks pass, migration/restart rehearsals preserve financial records, and Home Assistant validation is documented with any remaining live-device gate stated explicitly.
12. One PR contains the full release, updated metadata and reviewer evidence. It remains unmerged.

## Primary evidence

- [Pinned main](https://github.com/stunwill/fynvo-home-assistant/tree/074a62d46ef5b06c075b5e1602a896c32461286e)
- [v1.30.0 Release](https://github.com/stunwill/fynvo-home-assistant/releases/tag/v1.30.0)
- [Main CI and tests](https://github.com/stunwill/fynvo-home-assistant/actions/runs/37263490099)
- [Release build, manifest and publication](https://github.com/stunwill/fynvo-home-assistant/actions/runs/37263728554)
- [Startup and route wiring](https://github.com/stunwill/fynvo-home-assistant/blob/074a62d46ef5b06c075b5e1602a896c32461286e/fynvo/backend/app/main.py)
- [Active planning wrappers](https://github.com/stunwill/fynvo-home-assistant/blob/074a62d46ef5b06c075b5e1602a896c32461286e/fynvo/backend/app/payment_planning_runtime_v1251.py)
- [Account funding and pay cycles](https://github.com/stunwill/fynvo-home-assistant/blob/074a62d46ef5b06c075b5e1602a896c32461286e/fynvo/backend/app/payment_planning.py)
- [Existing account projection, transfers and warnings](https://github.com/stunwill/fynvo-home-assistant/blob/074a62d46ef5b06c075b5e1602a896c32461286e/fynvo/backend/app/v13_cashflow.py)
- [Bank observation reconciliation and identity](https://github.com/stunwill/fynvo-home-assistant/blob/074a62d46ef5b06c075b5e1602a896c32461286e/fynvo/backend/app/banking_v126.py)
- [Occurrence identity and wrappers](https://github.com/stunwill/fynvo-home-assistant/blob/074a62d46ef5b06c075b5e1602a896c32461286e/fynvo/backend/app/payments_v114.py)
- [Current Plan consumers](https://github.com/stunwill/fynvo-home-assistant/blob/074a62d46ef5b06c075b5e1602a896c32461286e/fynvo/frontend/src/PlanWorkspaceV1240.jsx)

Approval authorizes implementation of this concrete specification and its stated policies. Repository modifications remain paused until that approval.
