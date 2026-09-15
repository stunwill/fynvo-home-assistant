# Fynvo Release Process

Every production Fynvo release must include:

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

## Deterministic production release sequence

A Fynvo release is not ready merely because `fynvo/config.yaml` advertises a new version.

The required release lifecycle is:

1. merge the completed release changes to `main`;
2. manually start the **Release Fynvo** workflow for the exact semantic version already present in repository metadata;
3. validate version consistency across Home Assistant, frontend, backend and changelogs;
4. create or reuse the corresponding `vX.Y.Z` Git tag;
5. invoke the reusable release-image workflow for that exact tag;
6. build each supported architecture image;
7. publish the generic multi-architecture manifest;
8. verify the expected platforms are present;
9. log out of GHCR and anonymously resolve the exact Home Assistant image reference `ghcr.io/stunwill/fynvo:X.Y.Z`;
10. anonymously pull the amd64 variant of that exact final reference;
11. only after those checks succeed, create or update the GitHub Release.

This ordering is intentional. It prevents the release pipeline itself from announcing completion before the container image is actually available to Home Assistant.

The release workflow is manual rather than automatically triggered by a `fynvo/config.yaml` push. This avoids starting container publication while the release PR merge is still becoming externally visible.

## Container image publication

The add-on uses the generic image reference `ghcr.io/stunwill/fynvo` from `fynvo/config.yaml`.

The Home Assistant-consumed immutable tag is:

`ghcr.io/stunwill/fynvo:X.Y.Z`

The corresponding alias is also published:

`ghcr.io/stunwill/fynvo:vX.Y.Z`

Architecture-specific build images use:

`ghcr.io/stunwill/<arch>-fynvo:X.Y.Z`

Pull requests do not publish production packages.

The GHCR package must remain public so Home Assistant Supervisor can pull it without registry credentials.

## Failure behaviour

If any architecture build, manifest publication, platform verification, anonymous resolution or anonymous pull fails:

- the release workflow fails;
- GitHub Release publication does not proceed;
- the exact failure remains visible in GitHub Actions;
- an existing valid immutable image is not deleted.

Re-running the workflow may reuse an existing Git tag and image tags. Release publication is idempotent: an existing GitHub Release is updated rather than duplicated.

## Home Assistant compatibility

Normal add-on updates replace the container but preserve `/data`.

Home Assistant Supervisor owns installation progress. Fynvo does not fabricate progress percentages.

Legacy saved add-on options may remain in existing Supervisor configuration after the application has moved settings into the Fynvo UI/database. These compatibility concerns must be handled without exposing passwords or deleting user data.

## Acceptance

A release is not ready if:

- the exact Home Assistant image reference cannot be pulled anonymously;
- the required architecture is missing;
- version metadata disagrees;
- Home Assistant ingress fails;
- `/data` persistence is broken;
- the add-on enters an unexplained restart loop.
