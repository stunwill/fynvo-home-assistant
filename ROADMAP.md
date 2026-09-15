# Fynvo Roadmap

Fynvo is a household finance and cash-planning application for understanding upcoming commitments, available cash, pay-cycle pressure, spending decisions and near-term financial risk. The roadmap prioritises practical household planning over business accounting, tax, payroll or investment-trading functionality.

The current development baseline is v1.24.2.

## v1.24.2 - Release Pipeline Hardening & Home Assistant Update Reliability

Status: Complete on release branch, pending Pull Request review

Objective: Prevent Home Assistant from being offered a Fynvo update before the exact GHCR image it needs is publicly available.

### Features

- [x] Replace asynchronous dispatch/watch release-image orchestration with an explicit reusable release-image workflow.
- [x] Pass the exact release tag into the image workflow and build that immutable ref.
- [x] Verify the final multi-architecture manifest contains the configured Home Assistant platforms.
- [x] Verify `ghcr.io/stunwill/fynvo:X.Y.Z` anonymously after logout.
- [x] Perform an anonymous amd64 pull of the exact Home Assistant-consumed image before GitHub Release publication.
- [x] Preserve the `vX.Y.Z` alias, `/data`, ingress and application behaviour.
- [x] Document deterministic failure and rerun behaviour.

### Validation

- [ ] Complete CI on the Pull Request.
- [ ] Confirm release workflow syntax and reusable-workflow dependency graph on GitHub Actions.
- [ ] Confirm the next production release publishes the image before the GitHub Release is exposed.

## v1.24.1 - Core UX Redesign Production Corrections

Status: Released

Objective: Correct production reliability issues discovered after the v1.24.0 Core UX Redesign.

### Features

- [x] Correct Accounts and Activity loading/terminal states.
- [x] Remove the obsolete mobile Payment Centre outer presentation.
- [x] Improve Safe to Spend unavailable-state explanations.
- [x] Preserve Home Assistant ingress, routes, reconciliation and `/data` persistence.

## v1.24.0 - Core UX Redesign

Status: Released

Objective: Recompose Fynvo's core financial destinations into a consistent, focused mobile experience without changing financial semantics.

### Features

- [x] Establish shared navigation, cards, event rows, statuses, forms, action sheets, spacing and safe-area treatment.
- [x] Recompose Overview around Safe to Spend, Needs attention, Coming up and Your plan.
- [x] Recompose Payments around Upcoming, Attention, Timeline and Manage.
- [x] Recompose Plan around Overview, Forecast and Calendar.
- [x] Recompose Accounts around Accounts, Activity and Cards.
- [x] Preserve existing payment lifecycle, transaction, reconciliation, account and historical data behaviour.

## Future

Status: Planned

- [ ] Continue production validation and corrective releases based on installed Home Assistant usage.
