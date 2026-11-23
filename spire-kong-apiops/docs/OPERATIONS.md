# Release, rollback and drift

## Choose the release version

The release manager sets the repository version by creating a signed Git tag. Starting from `kong-v1.4.2`, choose `kong-v1.4.3` for a compatible fix, `kong-v1.5.0` for a compatible new endpoint, or `kong-v2.0.0` for a breaking change. Each API has its own contract version in `openapi.yaml` under `info.version`. Update that field in the merge request when the published contract changes.

## Normal release

1. Merge the reviewed change to main and wait for DEV success. Save the successful Deploy-dev build number for each API you will promote.
2. Finish reviewing values for all intended environments before tagging. A disabled variant cannot be enabled inside an already built release.
3. Copy the full commit SHA from the successful DEV run. In your GitLab clone, use your approved signing key and replace `DEV_COMMIT_SHA` and the example tag below with the tested commit and the next unused version.

   ```bash
   git fetch origin main --tags
   git tag --list 'kong-v*' --sort=-version:refname
   git tag -s kong-v1.4.3 DEV_COMMIT_SHA -m "Fix Invoices API routing"
   git verify-tag kong-v1.4.3
   git push origin refs/tags/kong-v1.4.3
   ```

4. Run Kong/Build with RELEASE_TAG. Keep this successful package build and its artifacts. The manifest records commit, annotated tag-object ID, decK version, targets and every environment-state checksum. The same immutable package is reused; no rendering happens during promotion.
5. Manually start Deploy-uat with API, REF, PACKAGE_BUILD, PREVIOUS_BUILD=the successful DEV receipt build, and CHANGE_TICKET. It verifies the same API/commit, fetches the current protected tag, validates the package/target and runs online plugin-schema validation/diff.
6. Review the redacted plan artifact. Approve using an authorized identity. Recomputed raw plan must match the approved plan before synchronization. Any change fails and needs a new plan/approval.
7. A release manager manually starts each higher-environment job when ready. Publishing a tag or successfully completing a preceding environment only makes the release eligible for promotion. PREPROD requires the successful UAT receipt and two distinct authorized approvers. PROD requires PREPROD and two distinct approvers. TRAINING requires DEV and one approval. Configure groups/permissions to satisfy your organization's separation-of-duty policy; group membership and Jenkins admin powers are external trust controls.
8. Success means sync completed, a post-sync diff is empty and positive/negative gateway smoke checks passed. Only then is receipt.json emitted. Archive that receipt and pin the related Build and Deploy builds in storage.

DEV and tag-package manifests differ in reference identity, so DEV→UAT compares API+commit. UAT→PREPROD→PROD also checks the exact manifest digest. Per-environment rendered files naturally differ because backends and IAM values differ, but their bytes are all frozen in the same retained release package.

## Approval and deletion

Automatic DEV may create/update API-owned resources and runs smoke tests. It cannot delete. Any intentional deletion requires a signed release, manual deployment, explicit ALLOW_DELETIONS, approved plan, ticket, and a nonempty scoped pre-change snapshot on approved encrypted storage. PREPROD/PROD also require the second approver.

The environment and CP locks are held through plan, approvals, apply and smoke. A 90-minute total timeout limits approval waits. If it expires, rerun and review a new plan. Other writers must honor the same lock/change freeze. No distributed transaction is implied.

Published plans redact secret-like fields. Raw plan/state and stderr stay only in the restricted private workspace and are removed at job end; snapshots remain outside artifacts. Enforce access restrictions on all release metadata and artifacts even after redaction.

## Rollback after failure

A failed sync may leave a partial configuration. A failed smoke check may mean the control plane changed successfully but routing, auth, upstream or DP propagation is broken. No success receipt is emitted, and the previous known-good receipt remains the drift baseline. Treat either failure as an incident; stop promotions.

Choose the last successful release that ran in the **destination** environment, not merely any old tag. Run that environment's Deploy job with ACTION=ROLLBACK, the old REF and PACKAGE_BUILD, PREVIOUS_BUILD=its known-good destination receipt, and an incident ticket. The job verifies the exact old package and CP, shows the reverse diff, requires approval, rechecks, syncs and retests. Use ALLOW_DELETIONS and approved snapshot storage if rollback removes resources introduced by the failed/new release.

For DEV, a previous retained `dev-<commit>` package can also be rolled back; the job verifies its commit is on main and its destination receipt/package. It does not require that old commit to still be main HEAD. Normal automatic DEV rejects a stale queued main package.

No automatic blind rollback is attempted. A newly introduced API with no previous successful package needs an approved retirement/remediation plan. Git does not preserve live database state, certificates, external resources or runtime secret values. A valid old configuration may still fail if a backend or secret was removed. Check backward compatibility and Vault-reference availability before recovery. A Control Plane/ownership migration needs a separate runbook.

## Drift and backups

Configure the separate Drift job's explicit target list after deployment. It takes the environment lock, selects the latest successful deployment **for that API**, downloads its exact original package using the recorded package build, checks target/checksums and runs read-only `deck gateway diff`. Rollback success becomes the new baseline. Nonzero differences, missing artifacts/history, authentication/schema/connectivity errors all fail the drift run; none trigger sync.

A disabled/removed API is not automatically deleted. Keep its old scope on the drift target list until API owners complete approved retirement. Entirely unmanaged entities without this repository's ownership tag are intentionally invisible to these drift checks. Platform needs separate CP inventory, backup and governance checks for shared/unmanaged resources.

An ad hoc scoped backup is available to authorized operators through `scripts/deploy.sh backup PACKAGE API ENV EVIDENCE_DIRECTORY`, with the same trusted expected-target variables and approved encrypted BACKUP_DIR. It calls `deck gateway dump --select-tag owner-<api>`. Handle outputs as sensitive and test restore separately; do not feed a raw dump into automated release promotion. Ordinary nondeleting changes do not require a dump every time. Agree an encrypted periodic backup/retention policy with platform in addition to Git/artifact retention.

## Reading failures

| Failure | Action |
|---|---|
| Placeholder or disabled target | Supply reviewed values; never bypass validation |
| Source/tag identity mismatch | Investigate moved ref or wrong package; create a new approved tag |
| Immutable registry mismatch | Never delete the registry entry to force a release; investigate and issue a new tag |
| Wrong predecessor/package | Use the receipt from the required environment and same source/package |
| Plan changed after approval | Replan/reapprove; investigate the external writer |
| Automatic deletion blocked | Follow the manual deletion path with snapshot and ticket |
| Smoke 401/403 unexpectedly | Check test-token freshness, audience, role, issuer and approved auth policy |
| Smoke 5xx/timeout | Check backend/CA/network/DP propagation; do not mark delivery successful |
| Drift job missing history | Restore retained package/receipt or onboard scope through an approved deployment |

Current smoke checks use a GET/HEAD endpoint and valid, missing and invalid bearer credentials. They do not prove all nodes/sites converged, performance under load, tenant isolation, authorization denial for an otherwise-valid wrong-role token, certificate rotation, Redis failover or full business behavior. Add those acceptance tests with API/security/platform owners before production enablement.

## APIOps scope and API rules

The platform team owns its separate repository. This repository consumes references to its existing Control Planes, Vault definitions, networking and other shared services. It never deploys Control Planes, global plugins, Consumers, Vault definitions or infrastructure. Keep those out of API packages.

The current example API baseline requires HTTPS upstream/downstream, verified upstream TLS, explicit methods/timeouts/retries, Service-scoped bearer OIDC with audience/role checks, rate/payload limits and correlation IDs. External API starter templates also include IP restrictions and OAS validation; PREPROD/PROD require reviewed Redis counters. These are proposed API rules inherited from the earlier design, not claimed company standards. API/security owners must review them and confirm licensed plugin support. Implementation checks live in scripts/validate.py.

Use one stable owner-<api> selection tag for each API's Service, Routes and plugins. Never mix shared resources or another API's owner tag into that scope. The initial profile is one Service per API, explicit literal prefix paths /domain/api/v1/... and read-only GET/HEAD smoke checks. Prefix matching can expose subpaths; regex/parameterized routing, delegated user auth and per-client quotas need reviewed validator/test extensions.
