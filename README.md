# Fynvo

**Fynvo** is a Home Assistant add-on for household budgeting, accounts, transactions, recurring expenses, planned spending and explainable cash-flow forecasting.

> Know what's coming.

## Current release

Current development release: **v1.18.2 Payment Centre Mobile UX Completion**.

v1.18.2 builds on the merged v1.18.1 Overview Decision Dashboard baseline. It:

- redesigns Payment Centre on iPhone/Home Assistant ingress as a compact financial-management queue rather than a vertically heavy desktop-style card stack;
- keeps payment name and full amount prominent while consolidating due/overdue state, payment handling, payment method and funding metadata;
- makes incomplete payment information compact and actionable and keeps **Mark paid** visible while lower-frequency lifecycle actions remain available through an overflow path and the existing detailed Payment Centre workspace;
- replaces separate Grouped/Chronological controls with a segmented selector and improves date-group counts and within-group priority ordering;
- consolidates Quick Add, Add Bill and quick filters into a compact sticky mobile toolbar with active-filter counts and reset behaviour;
- simplifies the authoritative **Before next pay** funding summary around Available now, Required before pay and Next income, with explicit unavailable states and progressive disclosure of the full calculation;
- uses skeleton loading plus independent payment-list and funding-summary error states, deliberate empty states, and iOS/Home Assistant safe-area clearance;
- removes the redundant Payment Centre mobile footer and exposes the installed release version through **More → About**;
- preserves the existing Payment Planning, Pay-Cycle Cash Planning, Scheduled Payments, Bills, Recurring Expenses and reconciliation calculations and lifecycle semantics;
- aligns active frontend, backend, Home Assistant add-on and production-shell version reporting to v1.18.2.

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

- the **Before next pay** plan for the chronologically next expected Income event;
- cash required before that Income event;
- current available liquid cash;
- projected household cash immediately before and immediately after pay;
- Account-level funding pressure and known shortfalls;
- explicit unknown/unassigned funding states;
- Money Needed Soon for the next 7, 14 and 30 days;
- manual and automatic payment funding requirements;
- overdue and unresolved automatic payments;
- grouped upcoming commitments by default;
- the detailed chronological payment lifecycle when needed;
- payment lifecycle details, including rescheduling, skip/restore history and matched Transactions.

The active pay-cycle window starts on the current Australia/Melbourne date and runs up to, but does not include, the next expected Income occurrence. The next Income is therefore not counted as cash available before it arrives. If commitments share the Income date, Fynvo follows the forecast ordering rule of applying Income first and then same-date commitments.

Multiple active Income sources are supported. The immediate summary uses the chronologically next event, while the planning response can expose subsequent Income events for near-term household planning.

If no future Income can be determined, Fynvo reports **Next income not known** instead of inventing a $0 Income or an unlimited planning window.

Cards remain payment context only. A Card-linked commitment is funded through its linked Account and Card balances are never counted independently.

The Account model does not currently contain an authoritative preferred minimum-balance/buffer field, so Fynvo does not invent buffer values. Required funding and known shortfalls are calculated independently of any future optional preferred-buffer feature.

The **Overview** consumes the same authoritative Payment Planning service for its Before next pay, Needs attention and Money needed soon summaries, so it does not maintain a separate cash-requirement calculation.

## Cash Flow and Calendar

**Cash Flow** answers "what will happen to my money?" It presents the projected household balance graph, starting/projected/lowest balance information, inflows/outflows and the financial events with the largest effect on the selected forecast period. When the matching Overview forecast is already loaded, Cash Flow reuses it rather than waiting for the same complete forecast to be requested again.

Baseline Cash Flow now consumes Scheduled Payment lifecycle occurrences for recurring outflows so skip, reconciliation and one-off rescheduling state agree with Payment Centre and Pay-Cycle Planning. Scenario forecasts remain isolated and continue to use temporary scenario recurrence logic rather than mutating authoritative Scheduled Payments.

**Calendar** answers "what is happening, and when?" It groups household financial events by date and provides selected-date details. Calendar consumes the reconciled baseline financial-event sequence so representative Income and commitment dates agree with Cash Flow, Payment Centre and Pay-Cycle Planning. The Recurring Expenses Calendar retains its dedicated month grid and clearly identifies the user's local current day.

Expected Cash Flow may include historical run-rate estimates where supported. Those estimates are intentionally not treated as authoritative committed spending in the Before next pay calculation.

## Overview drill-downs

Overview summary information is intended to lead to the authoritative detail workspace. Primary mappings include:

- Available now / Accounts → Accounts;
- Next Income → Income;
- Before next pay / Committed before pay → Payment Centre;
- Needs attention → Payment Centre;
- Money needed soon → Payment Centre;
- What changed? → Transactions for detailed activity;
- Financial outlook → Cash Flow.

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