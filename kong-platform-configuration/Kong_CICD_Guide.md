# Spire Kong API configuration

This repository is where our API teams request Kong routes and where Jenkins safely deploys them. You **do not** need to log in to Kong Konnect to add a route. Make a GitLab merge request instead.

**Stack:** on-prem GitLab → Jenkins → decK → Kong Konnect Control Plane → connected Kong Data Planes. F5 sends API traffic to the Data Planes. Terraform owns Konnect platform resources; Ansible/Nexus own the RHEL gateway hosts. This repository owns everyday API configuration only.

> **Not connected to production yet.** Everything starts disabled. Replace the sample values, confirm the real Control Plane names, onboard existing API entities, configure Jenkins credentials/permissions, and test in an isolated DEV scope before enabling deployments.

## Repository layout

```text
kong-platform-configuration/
├── Jenkinsfile                       # CI/CD stages and approvals
├── CODEOWNERS                        # GitLab code review ownership (replace placeholder)
├── apis/
│   └── example-orders/
│       ├── api.yaml                  # service, routes, and team ownership
│       └── openapi.yaml              # public API contract
├── environments/
│   ├── dev/
│   ├── uat/
│   ├── training/
│   ├── preprod/
│   └── prod/
│       ├── environment.yaml          # CP names per internal/external tier
│       └── values/<api>.yaml         # backend URL, audience, smoke URL
├── scripts/                           # render, deploy, diff, smoke, tag validation
├── tests/                             # offline checks
├── docs/OPERATIONS.md                 # rollbacks, backup policy, onboarding
└── .gitlab/merge_request_templates/   # developer MR checklist
```

## How developers add a new route in DEV

1. Create a branch from `main`: `git switch -c feature/orders-status-route`.
2. Open `apis/<your-api>/api.yaml` and add a Route under `routes:`. For a brand new API, copy the `example-orders` folder, change its name/service/team and create a `values/<your-api>.yaml` in **each environment**. The higher-environment values can remain disabled until approved.
3. Update `apis/<your-api>/openapi.yaml` with the same endpoint and method. The route format is `/domain/api/v1/...`.
4. For DEV-specific backend changes, edit only `environments/dev/values/<your-api>.yaml`. Do not change a production backend just to test DEV.
5. Run checks locally, then open a GitLab merge request using the **New API** template. Platform/security owners review it.
6. Once approved and merged into protected `main`, Jenkins `AUTO` checks which APIs changed and deploys those APIs **only to DEV**. It does not deploy to UAT or PROD.
7. Jenkins uses the configured test Entra bearer token to verify the new route through the F5 gateway URL.

Example route entry:

```yaml
  - name: example-orders-status-v1
    paths: [/orders/orders/v1/status]
    methods: [GET]
    strip_path: false
    preserve_host: false
```

## How we promote the same version to UAT / PREPROD / PROD

We use **protected annotated Git release tags**, not environment branches. A tag refers to one reviewed commit that includes API config and the approved values for each environment.

```bash
# From a reviewed commit already merged and proven in DEV:
git tag -a kong-v1.0.0 -m "Kong API release 1.0.0"
git push origin kong-v1.0.0
```

In Jenkins, run `ACTION=DEPLOY`, select `API_NAME`, set `TARGET_ENV=uat`, enter `RELEASE_TAG=kong-v1.0.0`, and provide the change ticket. Jenkins checks out that tag, renders UAT's environment configuration, previews the exact diff, asks for approval, syncs, and smoke-tests. Repeat with the **same release tag** for PREPROD and PROD after sign-offs. TRAINING should follow the agreed business promotion path; it is separate from PROD.

Each environment has its **own Control Plane** (and separate internal/external tier), URLs, and Entra audience. Only the intended environment is changed by a Jenkins run.

## Two different kinds of tags

- **Git release tag:** `kong-v1.0.0` identifies which approved source commit we deploy or roll back. GitLab must protect tag creation and reject deletion or modification; an ordinary Git tag is not inherently immutable.
- **decK owner tag:** `owner-example-orders` is written into every API-owned Kong entity and into `_info.select_tags`. This keeps our API's Service/Routes/Plugins in a bounded management scope. It is **not** a release version.

A tag is not a live backup. We keep known-good release tags and run scheduled encrypted configuration snapshots. A high-risk or destructive change needs a pre-change snapshot. We do **not** dump the entire Control Plane before every routine route addition.

## Rollback

Look up the last successful tag for this API and environment in the release tracker. In Jenkins, select `ACTION=ROLLBACK`, set `TARGET_ENV`, `API_NAME`, `ROLLBACK_TAG`, and the incident/change ticket. The pipeline checks out that known-good tag, reviews differences, seeks approval, syncs the older desired state and reruns smoke tests. This **does not** restore unrelated manually created entities, secrets, or infrastructure.

## Local validation

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 scripts/validate_all.py
python3 scripts/kong_config.py --api example-orders --env dev --out build/dev-example-orders.yaml
deck file validate --konnect-compatibility build/dev-example-orders.yaml
```

The sample contains fake URLs and has `enabled: false` in every environment. Local rendering is available; **live deployment intentionally fails** until approved settings are populated.

## CI/CD safety gates

- Protected `main`, CODEOWNERS, code review, signed/protected release tags (configured in GitLab).
- Jenkins dedicated hardened agents, one deployment per Control Plane at a time, separate prod credentials.
- Offline checks, remote validation and decK diff before sync; unexpected deletions are blocked.
- Approval for higher environments; high-risk changes need a snapshot.
- OIDC bearer plugin generated for every Service using environment-specific Entra issuer/audience (validate with IAM first).
- Post-deploy diff must be empty, then the authenticated smoke test must pass.
- Deploy and audit logs identify the Git commit, API, environment, release tag, and change ticket.

## What platform owners must configure before go-live

1. Replace `YOUR-GITLAB-GROUP` in CODEOWNERS; protect `main`, `kong-v*` tags, and restrict deploy job permissions. Restrict who can approve PROD; Jenkins's generic input step alone does not enforce role separation.
2. Install and pin approved decK/Python on trusted Jenkins agents. Check tool/flag compatibility in your Kong version.
3. Configure isolated Konnect Control Plane names, F5 gateway URLs, Entra issuer/audience, and backend URLs under each environment. Confirm prod/nonprod organization boundaries.
4. Create Jenkins secrets `kong-konnect-dev`, `kong-konnect-uat`, etc., and `kong-smoke-<env>` test Entra bearer tokens or replace static token binding with short-lived token acquisition. Do not store tokens in Git. Verify the token does not expire during the run.
5. Confirm OpenID Connect plugin entitlement and token validation policy. Add approved ACL, rate limits, request-size limits, and external IP restrictions before exposing APIs. The repository's minimal OIDC plugin is **not** the complete company security baseline.
6. Decide the protected GitLab release-tag signing and archival process, plus enterprise release tracker recording the last successful tag per API/environment.
7. Define encrypted backup storage/retention and set `BACKUP_DIR` securely on Jenkins agents for selected high-risk backups or scheduled backup jobs.
8. Review `docs/OPERATIONS.md`, test DEV first, practice rollback, and confirm that all existing API entities are correctly tagged before the first synchronization.

**See:** [docs/OPERATIONS.md](docs/OPERATIONS.md) for incident and first-deployment steps.

**Sources:** Spire's Kong implementation blueprint (sections 3, 5 and 6), CI/CD meeting notes, and current decK documentation: https://developer.konghq.com/deck/gateway/tags/ and https://developer.konghq.com/deck/gateway/konnect-configuration/.
