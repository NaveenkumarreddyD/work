# Verification — 20 November 2026

## Passed locally

- `bash scripts/check.sh`: **81 Python automated tests passed, no skips**, followed by source metadata/OpenAPI schema checks, real pinned decK rendering/structural validation for **3 APIs × 5 environments = 15 states**, baseline policy/contract checks and Bash syntax checks.
- Tests cover malformed OpenAPI, disallowed external references, source/tag ancestry, annotated-vs-lightweight tags, identity mismatch, package checksums, extra/unsafe/symlink package paths, disabled targets, wrong targets, per-API ownership, multiple owner tags, required policies, plaintext secret rejection, automatic DEV gates, forbidden automatic deletions, snapshot-before-deletion, changed plans, tampered approved state, sync/smoke failures, read-only drift, immutable registry binding, predecessor receipts, rollback destination/package checks, safe onboarding and report redaction.
- Real disposable Git/decK package integration built an annotated tag and a DEV reference from one commit. All five environment-state files and tests.json had identical digests between those two builds; tag-object identity was retained. The fixture was local and used disabled examples, not real environment values or remote pushes.
- `tests/pipeline_guards.groovy`: **8 guard scenarios passed** without allocating an agent or contacting external services. This includes rejection of DRIFT in the deployment job, invalid API/build/reference/target/ticket inputs, and acceptance of valid requests up to the agent boundary.
- All **four** Jenkins files compiled with Groovy 2.4.21: root validation, Build, Deploy, Drift. This is language syntax validation, not a Jenkins controller/DSL/CPS integration run.
- `bash scripts/security.sh`: pinned Gitleaks 8.30.1 reported **no leaks**. Published JSON evidence redacts secret-like keys; raw live reports are not archived by the pipeline.
- Documentation local-link and ZIP extraction/content integrity checks are part of final packaging. Hash-locked Python dependencies are included.

Official release binaries used for testing were downloaded and verified against their published SHA256 files:

| Binary archive | SHA256 |
|---|---|
| decK 1.70.0 macOS universal | b425046d9347a68d4f79196bac674077a303687ecc2f3ee8c8507386f1c090af |
| Gitleaks 8.30.1 macOS arm64 | b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5 |

Actual decK output: `decK v1.70.0 (e8909bc)`. Version/help for the command families and real offline render/validate were checked; live gateway commands were verified against CLI help and official documentation, not executed against a live Control Plane.

An independent code review identified a drift baseline selection defect in the initial implementation. It was removed from the promotion job; dedicated drift now chooses the latest successful per-API destination receipt under the environment lock. Deployment guard checks reject caller-selected DRIFT actions. The author also reviewed artifact path handling, disabled-API triggers, lock ordering, stale DEV requests and inherited decK environment variables.

## Not established locally

No real environment settings or credentials were provided. No live Konnect/DP mutation, Jenkins controller run, GitLab MR/protection integration, signing-key trust deployment, actual approval-group authorization, IAM token flow, licensed plugin schema, F5/network/DP convergence, backup encryption/restore, retention enforcement or production recovery exercise was performed.

The decK orchestration failure-path tests use explicit process test doubles for live diff/sync/HTTP behavior. They prove local guard/orchestration logic, not enterprise connectivity or Gateway compatibility. Offline example validation deliberately permits placeholders only while deployment is disabled. Enabled variants require complete reviewed values and online acceptance.

The repository is **production-oriented, not production-certified**. Follow SETUP.md's live acceptance checklist before enabling production. Existing local repositories were preserved. No remote push or publication was performed.

## Reproduce

Install official pinned CLI/scanner builds and hash-locked dependencies, then run the README commands. To additionally exercise the Groovy guard checks, install approved Groovy 2.4+ and run `groovy tests/pipeline_guards.groovy`. Run Jenkins' own linter/controller acceptance for the installed plugin versions; generic Groovy compilation cannot replace it.
