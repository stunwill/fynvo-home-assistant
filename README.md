# Fynvo

**Fynvo** is a Home Assistant add-on for household budgeting, accounts, transactions, recurring expenses, planned spending and explainable cash-flow forecasting.

> Know what's coming.

## Current release

Current development target: **v1.16.0 Payment Planning, Upcoming Commitments & Cash Requirements**.

v1.16.0 builds on the production payment lifecycle with:

- authoritative Today, Next 7 Days, Next 14 Days and Next 30 Days payment planning;
- Money Needed Soon totals that include unresolved automatic payments as funding requirements;
- chronological upcoming-payment timelines;
- account-level funding requirements with Card to Account derivation;
- conservative available-funds and shortfall comparisons that never treat unknown balances as zero;
- shared Payment Planning calculations across Overview and Payment Centre;
- explicit payment-attention reasons and consistent lifecycle statuses;
- Bill and Scheduled Payment deduplication where both represent the same obligation;
- occurrence-safe skipped, restored and rescheduled payment handling;
- responsive Payment Centre layouts for desktop, tablet, mobile and Home Assistant ingress.

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
- chronological upcoming commitments;
- funding requirements by Account;
- available funds and likely shortfalls when the relevant Account data is reliable;
- payment lifecycle details, including rescheduling, skip/restore history and matched Transactions.

The **Overview** consumes the same authoritative Payment Planning service for its household commitments summary, so it does not maintain a separate money-needed calculation.

## Cash Flow Intelligence

Open **Cash Flow** from the authenticated Fynvo shell to review projected household balances and authoritative financial events. Calendar, Cash Flow and Forecast continue to use the established canonical financial-event model so occurrence-specific date changes, skips, restorations and reconciliation remain consistent across screens.

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

See [`docs/FYNVO_PRODUCT_ROADMAP.md`](docs/FYNVO_PRODUCT_ROADMAP.md).
