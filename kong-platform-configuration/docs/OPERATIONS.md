# Operations runbook

## First deployment
1. Verify the destination is the correct dedicated Control Plane and existing entities are inventoried.
2. Import/adopt existing APIs **before** the first sync. Never claim another team's ownership tag.
3. Replace every `REPLACE_...` value in environment files, and set `enabled: true` after platform approval.
4. Set `approved_for_deployment: true` on the API only after a reviewed merge request.
5. Inspect the rendered `build/<env>-<api>.yaml` and the entire decK diff. Require zero unexpected deletions.
6. Validate a bearer token against the real Entra audience, and test the F5 URL.

## Route changes
- Edit `apis/<api>/api.yaml` routes. Add any path to its `openapi.yaml`.
- For a new backend, create a separate API directory and `environments/*/values/<api>.yaml` files.
- Merge to protected `main` to deploy to DEV; edit only DEV values for DEV-only backend changes.
- Higher environments use the *same protected Git tag*, but their approved environment values.

## Promotion / rollback
- Use an annotated Git tag named `kong-vMAJOR.MINOR.PATCH` on a reviewed commit; protect the `kong-v*` pattern in GitLab.
- Jenkins `DEPLOY` to UAT/TRAINING/PREPROD/PROD requires a tag, approval and a ticket. It checks out the tag, not main.
- Roll back with `ROLLBACK` and the previously successful tag, **not** by altering a moving branch. This restores only that API's owner-tagged desired state.
- After rollback, record the affected environment and do not automatically promote the failed tag.
- Record the current successful release tag **per environment and per API** in your enterprise release tracker, not just in console logs.

## Backup policy
- An immutable Git tag is version control for approved *desired state*, not a backup of live Gateway state or secrets.
- A routine route addition need not trigger a new full dump when the approved prior tag is recoverable.
- For destructive or high-risk deployments enable the gated pre-change export into an encrypted restricted location.
- Run a scheduled tagged `BACKUP` job; upload encrypted snapshots outside the ephemeral workspace and apply retention.
- Separate backup/restore processes are needed for vault secrets, certificates and infrastructure.
- Test both tag rollback and dump restoration in a non-production Control Plane.

## Common problems
- `deck diff` proposes deleting unrelated entities: STOP; ownership tag is incorrect or prior entities weren't adopted.
- Route works in Konnect but not F5: check CP/DP config sync, DNS, F5, upstream firewall, TLS, OAuth and app health.
- `401`: check Entra token issuer, signature, audience, and scopes before changing gateway auth.
- `502/503`: verify backend reachability and upstream host/port/TLS.
- Drift: report and reconcile the manual change into Git; do not blindly overwrite a change during an incident.

## Company-specific prerequisites
- Dedicated hardened Jenkins agents, approved pinned decK/Python, secure outbound connectivity.
- Jenkins: credentials `kong-konnect-<env>` and `kong-smoke-<env>` (secret text), with separate prod access.
- Jenkins plugins: Pipeline, Git, Credentials Binding, Lockable Resources; GitLab webhook or multibranch integration.
- GitLab: protected `main`, CODEOWNERS, 2 approvals for prod, protected release tags and restricted creation, disable tag force updates.
- Assign an externally secured backup directory or artifact store if using backup jobs.
- Confirm target Control Plane names and Kong OIDC license before enabling environment deployment.
