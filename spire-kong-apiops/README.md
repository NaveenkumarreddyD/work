# Spire Kong APIOps

This repository stores API gateway configuration in GitLab. Jenkins checks changes and uses **decK** to deploy them to existing Kong Konnect Control Planes.

A merge to protected `main` automatically deploys enabled APIs to **DEV**. Higher environments use an approved release tag and the retained package built from that tag. You review the diff before deployment. Rollback uses a previously successful package.

The examples are disabled. Real URLs, Control Plane names, credentials and approval groups still need to be supplied by your team. This is a production-oriented starting repository; live production readiness has not been established.

## Where to look

```text
spire-kong-apiops/
├── konnect/
│   ├── nonprod/{dev,uat,training}/target.yaml
│   └── prod/{preprod,prod}/target.yaml
├── apis/
│   ├── documents/
│   ├── billing/
│   └── customers/
│       ├── metadata.yaml       # API owner and gateway tier
│       ├── kong.yaml           # Service, Routes and API policies
│       ├── openapi.yaml        # Client-facing contract
│       ├── tests.yaml          # Expected smoke-test results
│       └── overlays/           # dev, uat, training, preprod, prod values
├── platform/                   # Shared-resource ownership boundary
├── governance/                 # Proposed rules and review responsibilities
├── pipelines/                  # Trusted Jenkins jobs and setup inputs
├── scripts/                    # Build, validation, deployment and evidence
├── tests/                      # Tests of this delivery process
├── docs/                       # Setup, comparison and operations guides
└── Jenkinsfile                 # Credential-free MR validation
```

## Change a Route for DEV

1. Create a branch from `main`.
2. Edit `apis/<api>/kong.yaml`. A **Service** is the backend; a **Route** is the public path and HTTP method.
3. Update `openapi.yaml` and `tests.yaml` to match. Keep the API's ownership tag unchanged.
4. For DEV-only backend or IAM values, edit only `overlays/dev.yaml`.
5. Run the checks below, open a GitLab merge request and get the required reviews.
6. After merge, Jenkins builds protected main and deploys enabled DEV APIs. It runs a diff, blocks automatic deletions, synchronizes the API scope and checks authenticated and rejected requests.

Adding a Route in shared `kong.yaml` changes the next release candidate for all environments. Only DEV deploys on merge. Existing higher environments stay on their previous package until you explicitly promote a release. You do not maintain separate environment branches.

## Run the checks

Install Python 3.11+, Bash, Git, curl, **decK 1.70.0** and **Gitleaks 8.30.1** on the validation agent or your machine. Use official releases and verify their published checksums.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --require-hashes -r requirements.lock
bash scripts/check.sh
bash scripts/security.sh
```

These commands do not contact a gateway or deploy. They check source, all five overlays, OpenAPI schema, ownership, example policy rules, tests and offline decK rendering. No real secrets are needed.

## Add an API

```bash
python3 scripts/new_api.py --name your-api --path /domain/your-api/v1 \
  --owner your-team@example.com --body-contains expected-response-text
```

Replace the illustrative arguments with your API details. The starter creates four API files and five disabled overlays. It never enables or deploys anything. See [Add an API](docs/ADD_AN_API.md).

## Promote or roll back

A release manager creates a signed annotated `kong-vX.Y.Z` tag on a reviewed commit from protected main. Build that tag once in `Kong/Build`, then use its retained build number in the environment jobs:

```text
DEV success → UAT approval → PREPROD two-person approval → PROD two-person approval
          └→ TRAINING approval
```

Each job checks the preceding environment's successful receipt for the same API and commit. Higher environments also require the exact same package checksum. Each environment has different reviewed values, frozen together in that package. Releasing changed environment values requires a new tag.

For rollback, choose `ROLLBACK`, the old release/package build and a successful receipt from that same destination environment. Jenkins reviews and applies the reverse diff, then runs the same smoke tests. It does not assume a Git tag is a backup. See [Operations](docs/OPERATIONS.md).

## Start here as the CI owner

Follow [Setup](docs/SETUP.md) before enabling DEV. It covers GitLab protections, Jenkins jobs and permissions, credentials, approvals, durable release storage, drift scheduling and live acceptance checks.

[Reference comparison](docs/REFERENCE_COMPARISON.md) explains what came from Spire's PDF, KongAir and the earlier repository. [Verification report](docs/VERIFICATION.md) states exactly what was checked and what remains unverified.
