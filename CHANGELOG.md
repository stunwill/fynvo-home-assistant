# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.24.2 - Release Pipeline Hardening & Home Assistant Update Reliability

- Hardens the production release lifecycle so GitHub Release publication is blocked until the exact Home Assistant image reference is built, published, anonymously resolved and anonymously pulled successfully.
- Converts release-image publication into an explicit reusable workflow invoked for the exact release tag, removing the earlier asynchronous dispatch/watch path that allowed temporary update visibility before GHCR readiness.
- Keeps the Home Assistant-consumed image tag `ghcr.io/stunwill/fynvo:X.Y.Z` authoritative while retaining the `vX.Y.Z` alias for release consistency.
- Documents deterministic failure and rerun behaviour, preserves immutable release images and `/data`, and does not change Fynvo financial logic or UX.

## v1.24.1 - Core UX Redesign Production Corrections

- Corrects Accounts and Activity loading so primary data reaches explicit loading, populated, empty or error states without waiting on slow supporting requests.
- Improves scoped retry and empty-state handling while preserving cards, transactions, reconciliation, historical data and API contracts.
- Removes the obsolete mobile Payment Centre outer shell, clarifies Safe to Spend configuration-unavailable states and keeps legitimate recurring occurrences distinct.
- Tightens mobile shell cleanup and safe-area presentation. No database migration is required.
