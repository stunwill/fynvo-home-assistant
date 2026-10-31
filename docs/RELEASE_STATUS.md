# Fynvo release status and remaining acceptance

Evidence checked: 31 October 2026. Repository evidence does not establish the installed version or live household balances.

## Published baseline

- [PR #103](https://github.com/stunwill/fynvo-home-assistant/pull/103) merged on 10 October 2026 at commit `f671b4db56e39f98ec2e756ab4060f1be7ef0949` (source tree `01a7a3b56c432f0a5741efbec99a967fcee64f1d`).
- [v1.31.0](https://github.com/stunwill/fynvo-home-assistant/releases/tag/v1.31.0) was published at 2026-10-10 14:17 UTC, 11 October Australian time. Its annotated tag resolves to that merged commit.
- [Final PR CI](https://github.com/stunwill/fynvo-home-assistant/actions/runs/37796079695) passed. The PR records 298 backend tests, 301 frontend regressions and a successful add-on Docker build.
- [Merged-main CI](https://github.com/stunwill/fynvo-home-assistant/actions/runs/38007886948) failed at Ruff 0.17.0 with seven FURB162/UP017 timezone findings. Backend tests and application import were skipped; frontend and Home Assistant checks passed. This is not evidence of failed backend financial tests.
- The automatic release was skipped after that CI failure. A later [manual release run](https://github.com/stunwill/fynvo-home-assistant/actions/runs/38058815435) built aarch64, amd64, armhf and armv7 images, verified anonymous image resolution and published the release. Manual publication did not make merged-main CI green.
- No formal review submission or PR discussion was returned for PR #103. Independent technical review described in its body is distinct from a GitHub approval and installed owner acceptance.

## v1.31.1 corrective candidate

Status: Prepared, pending PR checks and review. Not yet established as merged, released or installed.

Corrects the reported timezone lint failures using Python 3.12 ISO timestamp parsing and the UTC alias. Naive UTC storage in `security.utcnow()` is preserved. Pins Ruff 0.17.0 in shared development requirements to prevent an unannounced tool upgrade from changing the lint gate. Updates current version metadata and release documentation. No schema, bank credential, funding policy or financial calculation changes are introduced.

After PR checks, explicit review/merge is needed. Merged-main CI and the existing release workflow must then be verified. Do not move or reuse the published v1.31.0 tag. The manual recovery path remains privileged release functionality and a successful build/publication is not a substitute for green CI or live acceptance.

## Outstanding installed and financial acceptance

Use the detailed [v1.31.0 acceptance checklist](RELEASE_VALIDATION_v1.31.0.md), retaining schema v19 and substituting the actual accepted candidate version when testing v1.31.1.

| Evidence required | Status | Owner / date |
| --- | --- | --- |
| Home Assistant upgrade, schema 19 and repeat restart without record loss | Not recorded | Not assigned / not scheduled |
| Authenticated ingress and iPhone navigation, refresh and failure states | Not recorded | Not assigned / not scheduled |
| Restore pre-v19 backup with the matching previous application image | Not recorded | Not assigned / not scheduled |
| Live Redbark current/available balances, stale/error sync and recovery | Not recorded | Not assigned / not scheduled |
| Partial/rescheduled Bills, salary timing, dated one-offs and transfers | Not recorded | Not assigned / not scheduled |
| Overview, Accounts and Plan agree for identical inputs and horizons | Not recorded | Not assigned / not scheduled |
| Reviewer acceptance and installed version confirmation | Not recorded | Not assigned / not scheduled |

These checks require the installation and consenting household test operator. Synthetic tests cannot certify live bank balances or device behavior. Record version, date, scenario, expected result, observed result and pass/fail, using masked account identities and redacted evidence. Do not commit credentials, full account numbers or household banking exports.

## Next decisions

Assign an acceptance operator and test window, record the installed version, and decide whether observed results satisfy each gate. No milestone deadline, deployment completion or financial approval is inferred. Future feature prioritisation follows the canonical product roadmap after this evidence is recorded.
