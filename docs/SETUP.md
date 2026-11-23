# Set up GitLab and Jenkins

The repository ships disabled. Complete this checklist using real platform-supplied values. No server URL, region, CP name, account, group or credential is assumed to exist.

## 1. GitLab controls

- Protect `main`: no direct developer pushes, no force pushes; merge only through reviewed MRs.
- Replace CODEOWNERS groups with actual GitLab groups. Require API ownership and APIOps/security approval; reset approvals when commits change, disallow author/self approval and require a successful check for the latest MR commit. Code Owner approval enforcement depends on your GitLab tier. If unavailable, configure equivalent mandatory review controls before rollout.
- Connect a Jenkins multibranch job to MR heads/merged results using your approved GitLab Branch Source integration. Set the credential-free Jenkinsfile build status as a required merge gate. Verify that failed, missing or stale statuses prevent merging. Test fork MR behavior.
- Protect `kong-v*` tags. Restrict creation/deletion to release managers. Use signed annotated tags and an approved signing-key trust store. Do not allow force replacement or delete/recreate in release operations. Git tags are technically movable; protection, audit and the durable first-seen tag-object registry together enforce the release policy. Administrators remain a privileged trust boundary.
- Protect changes to pipeline/scripts, tool pins, target references and CODEOWNERS. A webhook from an MR must never be allowed to trigger a credentialed deployment job with arbitrary source or commands.

GitLab is SCM here. `.gitlab-ci.yml` is intentionally absent because Jenkins performs CI. Configure the Jenkins integration/status check in GitLab; no GitLab runner is required.

## 2. Agents and trusted code

Provision immutable, patched agent images with pinned decK 1.70.0, Gitleaks 8.30.1, Bash, Git, curl and Python 3.11+. Verify official binary checksums, install the hash-locked Python dependencies, then run checks. Pin your own approved container/image digest; none has been invented here.

Use separate labels/security boundaries:

| Label | Role | Access |
|---|---|---|
| kong-validate | MR validation | no deployment/production credentials or network |
| kong-release | reviewed source tests/build | no deployment credentials; isolated from trusted agents/storage |
| kong-nonprod | trusted nonprod delivery | nonprod scopes only |
| kong-prod | trusted PREPROD/PROD delivery | production scopes only |

Do not co-locate executors sharing Unix identity when one can read another's process environment or workspace. Do not expose Docker sockets, cloud machine credentials or the release registry to untrusted builds. Use restricted CA trust; never disable TLS verification. Network/DP/F5/IAM/Redis/Vault provisioning is outside this repo.

Standalone Build/Deploy/Drift job definitions and their `checkout scm` must use an **administrator-pinned reviewed tooling commit**, not a user-selected release tag or an MR branch. Update that pin only after review and testing. The Build job executes reviewed candidate code on the credential-free release agent. Deploy jobs consume its YAML/JSON packages as data and execute only trusted tooling. No candidate code runs with Konnect tokens.

Required Jenkins plugins: Pipeline, Git, approved GitLab Branch Source/integration, Credentials Binding, Pipeline Utility Steps, Copy Artifact, Lockable Resources, Input Step. Use supported versions approved for your controller. Groovy compilation alone cannot validate their runtime DSL behavior. Run the controller's Pipeline linter and an isolated DEV exercise after installation.

## 3. Supply trusted inputs

Edit `pipelines/settings.json` in the reviewed tooling revision:

- `repository_url`: actual GitLab SCM URL; `scm_credentials_id`: read-only checkout identity.
- `require_signed_tags`: true by default. Configure trusted public signing keys/allowed signers on release and identity-check agents; never accept arbitrary uploaded keys. GitLab protected-tag permission and trusted main are separate controls from signature validity.
- `release_registry`: an existing absolute directory on durable encrypted trusted storage, available to all deployment/drift agents. Keep outside Jenkins workspaces. Restrict writes to trusted pipeline identities; retain/back up entries. Scripts use exclusive first-write binding and reject changed tag object or manifest digest. All jobs take `kong-release-registry` lock; it does not coordinate multiple Jenkins controllers. Restrict to one controller or provide an equivalent global lock.
- `jobs`: exact job full names in your Jenkins. Included `Kong/...` names are a suggested local convention, not discovered jobs.
- `targets`: actual regional Konnect API URL, one `control_plane` name per environment, credential ID and approver groups. Approval groups are required for nonautomatic mutations; PREPROD/PROD use two distinct approved identities. Jenkins administrators can bypass input submitter restrictions: control/admin-audit that capability.
- `targets.<environment>.smoke_gateways` maps each API name to its approved HTTPS gateway URL. Enter the exact gateway_url from its approved overlay in the pinned tooling settings. Jenkins checks the destination before binding the API smoke token.
- `drift_targets`: explicit list such as `[{"environment":"dev","api":"invoices"}]`, only after that API has a successful deployment. This list is illustrative. Monitor every live managed scope, even disabled APIs pending retirement.

When upgrading pinned Jenkins tooling, replace the previous tier-specific settings with the verified control-plane name for each environment. Update Deploy and Drift together.

Populate source `environments/.../target.yaml` and per-API overlays with matching owner-approved values. Trusted settings are an independent target allowlist. A released package cannot redirect the deployment token to another CP. Renaming/moving a CP or ownership tag is a maintenance migration, not ordinary promotion.

Store environment-specific least-privilege Konnect machine-account tokens in Jenkins Secret Text, scoped by folders/roles; do not reuse a prod token in DEV. The token ID is configurable. Smoke tokens follow `kong-smoke-<environment>-<api>` and must be valid, short-lived, correctly scoped bearer tokens. Use your existing automated credential refresh/secret provider for expired test tokens. Tokens are injected into the environment; HTTP authorization is put in a private temporary header file, not process arguments. Runtime backend/plugin secrets stay as supported `{vault://...}` references. Provision Vault definitions separately and rotate underlying secrets without modifying source packages.

For deletion/optional snapshots, set trusted agent `BACKUP_DIR` to a pre-provisioned encrypted, access-restricted location and `BACKUP_STORAGE_APPROVED=true` only after storage review. Snapshots may contain live secrets: never archive them in ordinary Jenkins artifacts. Define retention, restore access and periodic backup policy with platform owners. The flag does not itself encrypt anything.

## 4. Create the jobs

1. MR multibranch validation: root Jenkinsfile, untrusted validation boundary only.
2. `Kong/Build`: pipelines/Build.Jenkinsfile from pinned tooling. Configure a protected-main push webhook. The job also polls its SCMs every few minutes as a fallback. Run once manually to install Pipeline properties/polling. Blank RELEASE_TAG builds current main and automatically calls DEV after packaging all APIs. An explicit tag builds that release and never deploys it automatically. Candidate checkout must include all main history and tags.
3. One Deploy job for each environment, all using pipelines/Deploy.Jenkinsfile from pinned tooling. Set fixed **job-level** TARGET_ENV (dev/uat/training/preprod/prod), not a build parameter. Ensure Build/Configure/Replay permissions cannot change job target or trusted scripts. Map the names in settings.json. Only the protected Build job/service and authorized release operators may start Deploy-dev; MR jobs cannot. Disable unauthenticated remote build triggers.
4. Optional scheduled `Kong/Drift`: pipelines/Drift.Jenkinsfile from pinned tooling. The included nightly hash-spread cron uses the Jenkins controller timezone. Set the intended controller timezone/schedule explicitly during rollout. It selects each API's latest successful deployment receipt and exact package, checks drift without applying changes, and reports drift, connectivity errors or missing history as failures. Route failed builds to your existing monitored Jenkins notification channel.

Copy Artifact permissions must allow only these trusted Build/Deploy/Drift jobs to read one another's release/receipt artifacts; MR jobs cannot publish into them. Validate package paths in the controller artifact browser. Configure restricted artifact access and encryption. Fingerprints/checksums detect changes but do not authenticate a malicious artifact store; Jenkins job identity, storage ACLs and signed source remain the trust boundary.

Retain successful active and rollback Build packages and deployment receipts indefinitely according to approved retention rules. The example build-discard counts are only operational defaults: mark active/rollback builds Keep Forever or use immutable external artifact retention before go-live. Losing a package/receipt blocks promotion, drift or rollback. New artifacts never replace the old tag/API binding in the durable registry.

The CP lock spans plan, approvals, synchronization and smoke checks across all writer jobs. Manual console edits and other controllers must obey the same change freeze/global lock. decK sync is not transactional; approval and plan comparison cannot prevent an uncoordinated external write after the last diff.

## 5. Live acceptance before PROD

Use isolated DEV first. Verify successful and failing MR statuses, job trust boundaries, disabled-target rejection, tag-signature validation, tag movement rejection, wrong-target rejection, approval identities, deletion/snapshot behavior, valid/missing/invalid bearer smoke checks and drift alarms. Cause a partial sync/smoke failure and rehearse recovery to a known-good package. Confirm Gateway/plugin schema and licenses using online validation on the real version.

Smoke requests prove behavior through the selected front door, not every data-plane node/site. Platform must separately prove all intended DPs have applied the config and that F5/network failover works. Freeze production enablement until that evidence, backup restore, secret rotation and the required security/policy decisions are approved. No environment values or acceptance evidence have been fabricated by this repository.
