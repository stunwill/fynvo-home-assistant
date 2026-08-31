# Fynvo

**Fynvo** is a Home Assistant add-on for household budgeting, accounts, transactions, recurring expenses, planned spending and explainable cash-flow forecasting.

> Know what's coming.

## Current release

Current development release: **v1.16.3 Accounts & Cards Consolidation, Archiving & Reassignment**.

v1.16.3 builds on the merged v1.16.2 corrective release and keeps the planned **v1.17.0 Pay-Cycle Cash Planning** roadmap scope separate. It:

- combines Accounts and Cards into one responsive Accounts & Cards workspace with Accounts / Cards views;
- redesigns Cards as a Card-first list, so Accounts with no Cards no longer create empty Card sections;
- follows the supplied desktop, tablet and iPhone/Home Assistant design direction with compact rows, summary metrics, search/filter controls and clear linked-Account context;
- adds Account archiving and restoration while preserving historical financial records;
- adds Account dependency analysis and an optional Move records & archive workflow for eligible Transactions, Cards and future Account configuration;
- preserves protected historical Transactions, Scheduled Payments and Transfers rather than blindly rewriting Account history;
- allows permanent deletion only when no Account dependencies remain and explains blockers otherwise;
- keeps archived Accounts out of normal new-record Account selectors while retaining historical display information;
- aligns active frontend, backend, Home Assistant add-on and production-shell version reporting to v1.16.3.

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

## Accounts & Cards

Open **Accounts** to use the combined **Accounts & Cards** workspace.

The Accounts view provides compact Account rows, balances, status and linked-Card counts. The Cards view shows actual Card records first, including last four digits, type/status and the linked Account. Accounts without Cards do not appear in the Card list.

Account retirement uses **Archive Account** rather than destructive deletion by default. Archived Accounts remain available for historical records but are excluded from normal new-record selectors. Archived Accounts can be restored.

For duplicate or incorrectly configured Accounts, Fynvo can preview dependencies and optionally **Move records & archive** to an explicitly selected active destination Account. Eligible non-transfer/non-matched Transactions, Cards and future Account configuration may move; historical Scheduled Payments, Transfers and protected Transactions remain associated with the source Account. The operation is transactional so a failure does not leave a partially consolidated Account.

Permanent deletion is available only when no dependencies remain.

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
- Cash Flow Forecast / Forecast Summary → Cash Flow;
- Financial Health / Money Needed Soon → Payment Centre.
