# Fynvo

**Fynvo** is a Home Assistant add-on for household budgeting, accounts, transactions, recurring expenses, planned spending and explainable cash-flow forecasting.

> Know what's coming.

## Current release

Current development release: **v1.16.2 Cash Flow, Calendar & Overview UX Corrections**.

v1.16.2 is a focused corrective patch over the merged v1.16.1 UX release. It:

- reuses already-loaded Overview forecast data so Cash Flow can render immediately when the selected range is already available;
- prevents loading from being shown as a genuine zero-event/empty state;
- makes Cash Flow primarily a financial-impact workspace with a prominent graph, concise balance summary and largest forecast-impact events;
- makes Calendar the date-oriented "what and when" workspace with selected-date event details;
- strengthens the recurring-expense month calendar's current-day highlight for iPhone and Home Assistant ingress;
- turns Overview KPI cards and relevant summary panels into accessible drill-down navigation;
- aligns active frontend, backend, Home Assistant add-on and production-shell version reporting.

The planned **v1.17.0 Pay-Cycle Cash Planning** roadmap scope remains separate from this corrective release.

Fynvo preserves the financial architecture established in earlier releases:

```text
Recurring Expense
→ Scheduled Payment
→ Transaction
→ Reconciliation
```

Recurring Expenses remain authoritative recurrence rules, Scheduled Payments remain expected occurrences, Transactions remain actual movements, and Reconciliation links expected and actual financial activity.

Forecast values and available-funds comparisons are based on the financial information recorded in Fynvo. They are not confirmed external bank balances or guarantees of future outcomes.

## Architecture

- FastAPI backend
- React/Vite frontend
- SQLite database stored under `/data`
- Docker-based Home Assistant add-on
- Home Assistant Ingress UI

The financial domain is intentionally kept separate from Home Assistant deployment concerns so Fynvo can later support standalone Docker, PWA/mobile clients, external integrations, CSV import, Australian Open Banking/CDR and hosted deployment.

## Authentication

Fynvo requires authentication before access to financial information.

On first run, create the initial administrator account through the Fynvo setup screen. Fynvo stores salted password hashes and server-side sessions in SQLite. v1.2.0 added the Household identity and membership foundation used by later releases.

## Payment Planning

Open **Payment Centre** to review:

- Money Needed Soon for the next 7, 14 and 30 days;
- manual and automatic payment funding requirements;
- overdue and unresolved automatic payments;
- grouped upcoming commitments by default;
- the detailed chronological payment lifecycle when needed;
- funding requirements by Account through expandable Funding Details;
- available funds and likely shortfalls when the relevant Account data is reliable;
- payment lifecycle details, including rescheduling, skip/restore history and matched Transactions.

The **Overview** consumes the same authoritative Payment Planning service for its household commitments summary, so it does not maintain a separate money-needed calculation.

## Cash Flow and Calendar

**Cash Flow** answers "what will happen to my money?" It presents the projected household balance graph, starting/projected/lowest balance information, inflows/outflows and the financial events with the largest effect on the selected forecast period. When the matching Overview forecast is already loaded, Cash Flow reuses it rather than waiting for the same complete forecast to be requested again.

**Calendar** answers "what is happening, and when?" It groups household financial events by date and provides selected-date details. The Recurring Expenses Calendar retains its dedicated month grid and clearly identifies the user's local current day.

Both experiences continue to consume Fynvo's canonical financial-event and forecast data so occurrence-specific date changes, skips, restorations and reconciliation remain consistent across screens.

## Overview drill-downs

Overview summary information is intended to lead to the authoritative detail workspace. Primary mappings include:

- Total Balance → Accounts;
- Next Income → Income;
- Upcoming Commitments → Payment Centre;
- Discretionary → Planned Spending;
- Goals → Goals;
- Cash Flow Forecast / Forecast Summary → Cash Flow.

The global date range is preserved during these in-app navigation changes where the destination uses the same relative scope.

## Home Assistant installation

Add this repository to Home Assistant:

```text
https://github.com/stunwill/fynvo-home-assistant
```

Then install and open the **Fynvo** add-on.

## Changelog and releases

Every release must include:

- `CHANGELOG.md` entry;
- Home Assistant-visible release notes;
- Git tag;
- GitHub Release;
- user-readable release notes.

See `docs/RELEASE_PROCESS.md`.

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the authoritative planned Fynvo development roadmap. The older `docs/FYNVO_PRODUCT_ROADMAP.md` remains historical planning context and should not be treated as the current release queue.

## Development metadata

DevHub and release tooling should use the Home Assistant manifest version in `fynvo/config.yaml` as Fynvo's primary repository release version. The matching version is also represented in `fynvo/frontend/package.json` and backend `APP_VERSION` in `fynvo/backend/app/config.py`; `/api/health` and `/api/version` report that backend version.

Release and planning metadata is exposed through:

- `ROADMAP.md` for the authoritative ordered future release plan;
- root `CHANGELOG.md` for detailed project release history;
- `fynvo/CHANGELOG.md` for concise Home Assistant-facing release notes;
- semantic Git tags using `vX.Y.Z`;
- intentional GitHub Releases for completed releases, with release notes derived from the final changelog.

CI runs `scripts/validate_release_metadata.py` to keep the manifest, frontend, backend, changelogs and roadmap contract consistent.