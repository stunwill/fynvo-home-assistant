# Fynvo Add-on Changelog

## v1.24.2 - Release Pipeline Hardening & Home Assistant Update Reliability

- Prevents Fynvo releases from being marked ready before the exact Home Assistant image reference is publicly available.
- Builds and verifies the multi-architecture GHCR image before GitHub Release publication.
- Verifies `ghcr.io/stunwill/fynvo:X.Y.Z` anonymously, including an actual amd64 pull, before release publication proceeds.
- Preserves `/data`, ingress and application behaviour. No database migration is required.

## v1.24.1 - Core UX Redesign Production Corrections

- Corrects Accounts and Activity loading and terminal states, with scoped errors, retry and deliberate empty states.
- Removes the obsolete mobile Payment Centre presentation around the redesigned Payments workspace.
- Improves Safe to Spend unavailable explanations and configuration follow-up while preserving financial semantics and data.
- Preserves Home Assistant ingress, existing routes, reconciliation and `/data` persistence. No database migration is required.

## v1.24.0 - Core UX Redesign

- Recommends a focused Overview around Safe to Spend, Needs attention, Coming up and Your plan.
- Consolidates payment work into Upcoming, Attention, Timeline and Manage, including Bills and recurring schedules.
- Recombines Plan into Overview, Forecast and Calendar views with projected balance, pressure points and financial events.
- Recombines Accounts into Accounts, Activity and Cards, with Account Detail, transaction reconciliation, search/filtering and supported insights.
- Establishes shared mobile cards, event rows, statuses, segmented navigation, action sheets and safe-area treatment across the redesigned destinations.
- Preserves existing financial calculations, payment lifecycle, reconciliation, historical data, API contracts, Home Assistant ingress and `/data` persistence. No database migration is required.

## v1.23.0 - Mobile Decision UX, Cash Plan Reliability & Information Hierarchy

- Makes Cash Plan resilient when optional pay-cycle or planning inputs are unavailable, preserving known planning data and returning structured availability diagnostics.
- Refocuses the mobile Overview around Safe to Spend, a concise Money requiring action list and a compact cash outlook while keeping deeper financial workspaces available.
- Organises mobile More navigation into Planning, Payments and Money & accounts groups and improves narrow-screen safe-area spacing without changing financial semantics.
- Preserves the v1.22.2 Home Assistant distribution contract, including prebuilt GHCR images, anonymous image resolution, ingress, port 8097 and `/data` persistence.
- Requires no database migration.
