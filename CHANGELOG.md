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

## v1.24.0 - Core UX Redesign

- Reorganises the mobile product around Overview, Payments, Plan, Accounts and More.
- Refocuses Overview on Safe to Spend, Needs attention, Coming up and Your plan.
- Consolidates Payments into Upcoming, Attention, Timeline and Manage, preserving Bills and recurring schedule workflows.
- Consolidates Plan into Overview, Forecast and Calendar, preserving authoritative planning and forecast calculations.
- Consolidates Accounts into Accounts, Activity and Cards, preserving transaction history, reconciliation, account details and card management.
- Extends shared mobile navigation, financial-event rows, summary surfaces, statuses, forms and action-sheet behavior across the redesign.
- Preserves Home Assistant ingress, direct routes, existing APIs, financial data and historical lifecycle semantics. No database migration is required.

## v1.23.0 - Mobile Decision UX, Cash Plan Reliability & Information Hierarchy

- Makes Cash Plan resilient when optional pay-cycle or planning inputs are unavailable, preserving known planning data and returning structured availability diagnostics.
- Refocuses the mobile Overview around Safe to Spend, a concise Money requiring action list and a compact cash outlook while keeping deeper financial workspaces available.
- Organises mobile More navigation into Planning, Payments and Money & accounts groups and improves narrow-screen safe-area spacing without changing financial semantics.
- Preserves the v1.22.2 Home Assistant distribution contract, including prebuilt GHCR images, anonymous image resolution, ingress, port 8097 and `/data` persistence.
- Requires no database migration.

## v1.22.2 - Home Assistant GHCR Tag Resolution Correction

- Corrects the release-tag/image-tag mismatch that caused Home Assistant Supervisor to request `ghcr.io/stunwill/fynvo:1.22.1` while the workflow had only published `ghcr.io/stunwill/fynvo:v1.22.1`.
- Publishes the Home Assistant-consumed semantic version tag without the Git `v` prefix while retaining the `vX.Y.Z` alias for GitHub release consistency.
- Adds an unauthenticated post-publication registry-resolution check for the exact image reference Supervisor will pull, so a release fails before Home Assistant users are told an unusable image is available.
- Preserves `aarch64`, `amd64`, `armhf`, `armv7`, `/data`, ingress and port 8097. No database migration is required.

## v1.22.1 - Release Image Compatibility Correction

- Removes the `uvicorn[standard]` production extra so 32-bit ARM release builds no longer pull the Rust-backed `watchfiles` dependency that cannot be built for the Home Assistant musl targets used by `armhf` and `armv7`.
- Removes the unsupported `i386` target from Fynvo release metadata and image publication after `pydantic-core` could not be built for `i686-unknown-linux-musl`.
- Keeps `aarch64`, `amd64`, `armhf` and `armv7` as supported Home Assistant release architectures and verifies the published manifest contains each supported platform.
- Preserves Fynvo application behaviour, `/data`, ingress and port 8097. No database migration is required.
- Corrects the v1.22.0 release-image failure that prevented Home Assistant from installing the advertised update.

## v1.22.0 - Home Assistant Add-on Distribution & Update Experience

- Publishes release-tagged, prebuilt multi-architecture Fynvo images through GHCR so normal Home Assistant updates pull prepared application assets instead of rebuilding them on the host.
- Keeps the generic Supervisor image reference aligned with the add-on, frontend and backend versions and verifies the published manifest before release readiness.
- Adds OCI provenance metadata for version, architecture, revision and build time, plus clearer release diagnostics and local-build documentation.
- Preserves ingress, port 8097, `/data` persistence and the existing financial application behaviour.
- Does not fabricate installation percentages; Home Assistant Supervisor remains responsible for update progress and may show 0% during image download or extraction.
