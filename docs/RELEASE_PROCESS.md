# Fynvo Release Process

Starting with **v0.3.0**, every production Fynvo release must include:

- version bump;
- database migrations where required;
- automated tests;
- CI validation;
- `CHANGELOG.md` entry;
- Home Assistant-visible release notes;
- Git tag;
- GitHub Release;
- user-readable release notes;
- upgrade/migration notes where relevant.

The changelog must describe changes from the user's perspective rather than listing raw commits.

The Home Assistant add-on must expose useful release information through the repository's changelog/release notes so updates can be understood from the add-on/update experience.

## Container image publication

The add-on uses the immutable image reference `ghcr.io/stunwill/fynvo` from
`fynvo/config.yaml`. Production images are published only by the release-tag
workflow, using a tag such as `v1.22.0`; pull requests do not publish release
packages. The workflow builds the configured architectures, creates the generic
multi-architecture manifest, and verifies that every required platform is
present before the release is considered ready.

The GHCR package must be public so Home Assistant Supervisor can pull it without
unsupported credentials. Architecture images use the builder-compatible names
`ghcr.io/stunwill/<arch>-fynvo:vX.Y.Z`, while Supervisor consumes the generic
manifest. The release tag, add-on version, frontend version and backend version
must all match the image's semantic version.

The image contains the built frontend and installed backend dependencies. The
legacy `build.yaml` remains available for local and compatibility builds, but a
normal add-on install or update pulls the published image instead of building
application assets on the Home Assistant host. `/data` remains the persistent
add-on mount and must be backed up before upgrades or downgrades.

Home Assistant Supervisor owns the installation percentage. Fynvo does not
invent intermediate progress values; Supervisor may continue to show 0% while
an image is downloading or being extracted.

GitHub Releases should use the corresponding version tag, for example `v0.3.0`, with Added / Changed / Fixed / Security sections where applicable.

A release is not ready if the Home Assistant add-on cannot be opened through Home Assistant ingress, if `/` returns 404, if authentication only works through direct port access, or if the add-on enters an unexplained restart loop.
