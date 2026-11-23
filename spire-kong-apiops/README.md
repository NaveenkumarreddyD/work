# Kong APIOps

This repository delivers API changes to existing Kong Konnect control planes. Developers edit one folder per API, GitLab handles review, and Jenkins uses **decK** to deploy enabled APIs after approval or automatic DEV checks.

## Who owns what?

| Owner | Responsibilities |
|---|---|
| API developers | Maintain the Service, Routes, API-specific plugins, OpenAPI contract, backend settings and smoke tests in `apis/<business-domain>/<api-name>/`. |
| APIOps maintainers | Register APIs against existing control planes in `konnect/`. Maintain the Jenkins workflows for scoped deployments, approvals, rollback and drift checks. |
| Platform team | Provision and operate control planes, gateways and shared infrastructure using Terraform in a separate repository. Own shared gateway policies and supply the approved connection details for each environment. |

## Find the file to edit

| What do you want to change? | File (inside your API folder unless a full path is shown) |
|---|---|
| Public path, HTTP method, Service or API policy | `kong.yaml` |
| What clients can request and expect back | `openapi.yaml` |
| How Jenkins tests a request through the gateway | `tests.yaml` |
| Backend or other settings for one environment | `konnect/nonprod/dev/apis/<domain>/<api>.yaml` for DEV |
| Owner, team or gateway tier | `metadata.yaml` |

**Example: Billing → Invoices.** Billing is the business domain. Invoices is one API owned within that domain. A client calls `GET /billing/invoices/v1` to list invoices. To change the route, edit `apis/billing/invoices/kong.yaml`. To change only its DEV backend, edit `konnect/nonprod/dev/apis/billing/invoices.yaml`. The sample is disabled in every environment. [Explore the Invoices API](apis/billing/invoices)

## Add an API

From the project directory containing this README, prepare Python once:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --require-hashes -r requirements.lock
```

1. Create a branch and run `python3 scripts/new_api.py` in your terminal. Answer the questions about the API name, public path and team. The starter creates the files with deployment disabled.
2. Open the new API folder. Review the generated Route, contract and smoke checks. Fill in the DEV overlay with the values supplied by your backend and IAM teams. Store only secret references in Git.
3. Ask the APIOps maintainer to list the API in the matching DEV control-plane file and confirm the target, register the approved smoke-test gateway URL and configure the API's Jenkins smoke credential. Enable the DEV overlay when ready.
4. Open a GitLab merge request. Jenkins checks all environments. After merge, look for the successful DEV deployment and its receipt.

## Update a Route

Edit the existing API folder. For a new path, add the Route to `kong.yaml`, describe the same path and method in `openapi.yaml`, and update `tests.yaml`. Preserve the API's ownership tag. Submit the three files together for review. [Developer walkthrough](docs/ADD_AN_API.md)

## Promote a release

Before tagging, review the API’s settings in each intended destination. For Invoices, open the folder below and edit `apis/billing/invoices.yaml` inside it. The same folder holds the internal and external control-plane registrations.

| Destination folder | Jenkins deploys after |
|---|---|
| [DEV](konnect/nonprod/dev) | A reviewed merge to main, when enabled |
| [UAT](konnect/nonprod/uat) | Successful DEV run and one approval |
| [TRAINING](konnect/nonprod/training) | Successful DEV run and one approval |
| [PREPROD](konnect/prod/preprod) | Successful UAT run and two distinct approvers |
| [PROD](konnect/prod/prod) | Successful PREPROD run and two distinct approvers |

Tag the commit that passed DEV and build the signed tag once. For each higher environment, run its Jenkins Deploy job with the API name, the same tag and package build number, the preceding successful deployment build number, and the change ticket. Jenkins shows the proposed changes and pauses for approval before applying them. [Promotion and rollback instructions](docs/OPERATIONS.md)

## Maintainer folders

| Folder | What it contains |
|---|---|
| `konnect/` | Environment folders with per-API settings and control-plane registrations |
| `governance/` | Approved API plugin names enforced during validation |
| `pipelines/` | Jenkins jobs, trusted destinations, credential IDs and approval groups |
| `scripts/` | API starter, validators and deployment commands |
| `tests/` | Tests for the delivery process |
| `docs/` | Developer and operator guides |

Use Python 3.11+, decK 1.70.0 and Gitleaks 8.30.1. Run `bash scripts/check.sh` and `bash scripts/security.sh` to reproduce the offline checks. Start with isolated DEV to verify actual Jenkins permissions, plugin compatibility, routing and recovery. [Setup](docs/SETUP.md) · [Verification](docs/VERIFICATION.md)


## How the folders map to Kong’s proposal

`konnect/nonprod/` contains dev, uat and training. `konnect/prod/` contains preprod and prod. Each environment contains `internal.yaml` and `external.yaml`. The API’s tier in `metadata.yaml` selects the file. A maintainer lists the API under `apis` before its environment overlay can be enabled. Registration alone does not deploy it.

As in [KongAir](https://github.com/Kong/KongAir/tree/main), each team keeps its API contract next to the configuration it owns. This repository uses GitLab for review, Jenkins for delivery and decK for Gateway Services, Routes and plugins. The separate platform repository owns control-plane provisioning and shared policies.
