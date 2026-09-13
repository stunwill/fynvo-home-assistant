# Fynvo Home Assistant distribution

Fynvo production releases use a prebuilt multi-architecture image.

Home Assistant consumes:

`ghcr.io/stunwill/fynvo:X.Y.Z`

The release pipeline also publishes:

`ghcr.io/stunwill/fynvo:vX.Y.Z`

for Git/GitHub release consistency.

## Supported platforms

| Home Assistant architecture | OCI platform | Builder image |
| --- | --- | --- |
| `aarch64` | `linux/arm64` | `ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20` |
| `amd64` | `linux/amd64` | `ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20` |
| `armhf` | `linux/arm/v6` | `ghcr.io/home-assistant/armhf-base-python:3.12-alpine3.20` |
| `armv7` | `linux/arm/v7` | `ghcr.io/home-assistant/armv7-base-python:3.12-alpine3.20` |

The Raspberry Pi 5 target is `aarch64`.

## Release and update behaviour

Pull requests run application and metadata validation but do not publish production images.

For a production release, the repository metadata must already contain the target semantic version. The **Release Fynvo** workflow is then started for that exact version.

The workflow:

1. validates metadata consistency;
2. creates or reuses `vX.Y.Z`;
3. calls the reusable release-image workflow for that exact tag;
4. builds all supported architecture images;
5. publishes the generic multi-architecture manifest;
6. verifies all required platforms;
7. logs out of GHCR;
8. anonymously resolves `ghcr.io/stunwill/fynvo:X.Y.Z`;
9. anonymously pulls the amd64 variant of that reference;
10. only then publishes/updates the GitHub Release.

This ordering prevents release completion from being declared before the exact image Home Assistant needs is publicly consumable.

## Failure behaviour

If image publication or anonymous verification fails, the GitHub Release step is blocked.

The release process does not use arbitrary sleeps as a correctness mechanism.

Existing immutable images and tags are preserved so safe reruns remain possible.

## Persistence and rollback

Replacing the container does not replace `/data`.

Accounts, transactions, payments, settings and other application state remain in that mount. Take a Home Assistant backup before upgrading or downgrading.

## Supervisor progress

Home Assistant Supervisor controls install/update progress. Fynvo does not simulate percentage progress.
