# Fynvo

**Fynvo** is a Home Assistant add-on for household budgeting, accounts, transactions, recurring expenses, planned spending and explainable cash-flow forecasting.

> Know what's coming.

## Current release

Current development release: **v1.24.2 Release pipeline hardening and Home Assistant update reliability**.

Fynvo publishes versioned prebuilt multi-architecture images through GHCR for normal Home Assistant add-on installation and updates.

Production Home Assistant releases use the semantic-version image reference:

`ghcr.io/stunwill/fynvo:X.Y.Z`

The corresponding `vX.Y.Z` alias is also published for GitHub release consistency.

A production release is considered ready only after the exact Home Assistant image reference has been built, published and verified anonymously. The release workflow must not publish a GitHub Release before that image verification succeeds. See [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md) and [docs/ADDON_DISTRIBUTION.md](docs/ADDON_DISTRIBUTION.md).

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

## Authentication

Fynvo requires authentication before access to financial information.

On first run, create the initial administrator account through the Fynvo setup screen. Fynvo stores salted password hashes and server-side sessions in SQLite.

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

The release lifecycle is intentionally ordered so the Home Assistant-consumed image is verified before GitHub Release publication. See `docs/RELEASE_PROCESS.md`.

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the authoritative planned Fynvo development roadmap.

## Development metadata

DevHub and release tooling use the Home Assistant manifest version in `fynvo/config.yaml` as Fynvo's primary repository release version. The matching version is also represented in `fynvo/frontend/package.json` and backend `APP_VERSION` in `fynvo/backend/app/config.py`; `/api/health` and `/api/version` report that backend version.

CI runs `scripts/validate_release_metadata.py` to keep the manifest, frontend, backend, changelogs and roadmap contract consistent.
