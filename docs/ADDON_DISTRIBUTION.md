# Fynvo Home Assistant distribution

Fynvo production add-on releases use a prebuilt multi-architecture image:

`ghcr.io/stunwill/fynvo:vX.Y.Z`

The add-on manifest points to that generic image. Release-tag CI first builds
architecture images, then publishes the generic manifest only after all required
platforms are present.

## Supported platforms

| Home Assistant architecture | OCI platform | Builder image |
| --- | --- | --- |
| `aarch64` | `linux/arm64` | `ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20` |
| `amd64` | `linux/amd64` | `ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20` |
| `armhf` | `linux/arm/v6` | `ghcr.io/home-assistant/armhf-base-python:3.12-alpine3.20` |
| `armv7` | `linux/arm/v7` | `ghcr.io/home-assistant/armv7-base-python:3.12-alpine3.20` |
| `i386` | `linux/386` | `ghcr.io/home-assistant/i386-base-python:3.12-alpine3.20` |

The Raspberry Pi 5 target is `aarch64` and is explicitly included in the
release manifest verification.

## Release and update behaviour

Pull requests run application and metadata checks but do not publish a
production image. Pushing a semantic Git tag such as `v1.22.0` runs the release
workflow, publishes the five architecture images, creates
`ghcr.io/stunwill/fynvo:v1.22.0`, and inspects the resulting manifest. A release
is not ready if the manifest is incomplete or its version does not match the
application metadata.

The runtime image already contains the Vite frontend bundle and Python
dependencies. Home Assistant therefore pulls and starts the prepared image;
the host does not run the frontend or backend build during the normal update
path. The add-on continues to use port 8097, ingress and `/data` unchanged.

Home Assistant Supervisor controls the install/update percentage. Fynvo does
not simulate 25%, 50% or 75% progress. Supervisor may show 0% during image
download or extraction even though the update is progressing.

The GHCR package must be public for an ordinary Home Assistant installation to
pull it without credentials. Release operators should verify package visibility
and the published manifest after each release.

## Local build

Local development remains independent of GHCR. From the repository root:

```sh
docker build \
  --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20 \
  --build-arg BUILD_VERSION=1.22.0 \
  --build-arg BUILD_ARCH=amd64 \
  -t fynvo-local ./fynvo
```

The multi-stage Dockerfile keeps build-only Node tooling out of the runtime
stage. OCI labels and runtime environment metadata expose the semantic version,
architecture, revision and build timestamp for diagnostics.

## Persistence and rollback

Replacing the container does not replace `/data`. Accounts, transactions,
payments, settings and other application state remain in that mount. Take a
Home Assistant backup before upgrading. To roll back, restore the prior add-on
version or backup after confirming database compatibility; this release adds no
database migration and the previous image tag remains immutable when available.

Update timing on a real Home Assistant host, including a Raspberry Pi 5, must
be recorded during release acceptance. This repository does not claim a host
timing improvement without that measurement.
