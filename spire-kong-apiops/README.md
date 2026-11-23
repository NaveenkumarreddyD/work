# Kong APIOps

This repository delivers API changes to existing Kong Konnect control planes. Developers edit one folder per API, GitLab handles review, and Jenkins uses **decK** to deploy enabled APIs after approval or automatic DEV checks.

## Who owns what?

| Owner | Responsibilities |
|---|---|
| API developers | Maintain the Service, Routes, API-specific plugins, OpenAPI contract and smoke tests in `apis/<business-domain>/<api-name>/`. Update backend settings under `environments/` when a destination changes. |
| APIOps maintainers | Register APIs against existing control planes in `environments/`. Maintain the Jenkins workflows for scoped deployments, approvals, rollback and drift checks. |
| Platform team | Provision and operate control planes, gateways and shared infrastructure using Terraform in a separate repository. Own shared gateway policies and supply the approved connection details for each environment. |

## What do I update?

| Task | Where to work |
|---|---|
| Add a Payments route | In `apis/billing/payments/`, update `kong.yaml` (route), `openapi.yaml` (contract) and `tests.yaml` (smoke checks) together. Every environment uses that route definition. |
| Change only the Payments UAT backend | Edit `environments/nonprod/uat/apis/billing/payments.yaml`. If a new route also needs that backend, include both changes in the same merge request. |
| Change the API owner or team | Edit `metadata.yaml` in the API folder. |
| Add a new API | Run the starter once. It creates the API folder and disabled settings for all five environments. Follow the onboarding steps below to prepare DEV first. |
| Promote an already configured API | Use Jenkins. Routine promotion requires **zero file edits**. |

## Billing examples

One business domain can own several APIs. Each row below is a separate folder, with its own Service, Routes, contract, smoke tests and ownership tag. All three samples are disabled in every environment.

| API folder | Example request | What it returns |
|---|---|---|
| [Invoices](apis/billing/invoices) | `GET /billing/invoices/v1` | Invoices with an `invoiceId` |
| [Payments](apis/billing/payments) | `GET /billing/payments/v1` | Payments with a `paymentId` |
| [Refunds](apis/billing/refunds) | `GET /billing/refunds/v1` | Refunds with a `refundId` |

## Add an API

From the project directory containing this README, prepare Python once:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --require-hashes -r requirements.lock
```

1. Create a branch and run `python3 scripts/new_api.py` in your terminal. Answer the questions about the API name, public path and team. The starter creates the files with deployment disabled.
2. Open the new API folder. Review the generated Route, contract and smoke checks. Fill in the DEV overlay with the values supplied by your backend and IAM teams. Store only secret references in Git.
3. Ask the APIOps maintainer to list the API in the DEV target file (`environments/nonprod/dev/target.yaml`) and confirm the target, register the approved smoke-test gateway URL and configure the API's Jenkins smoke credential. Enable the DEV overlay when ready.
4. Open a GitLab merge request. Jenkins checks all environments. After merge, look for the successful DEV deployment and its receipt.

## Update a Route

Edit the existing API folder. For a new path, add the Route to `kong.yaml`, describe the same path and method in `openapi.yaml`, and update `tests.yaml`. Preserve the API's ownership tag. Submit the three files together for review. [Developer walkthrough](docs/ADD_AN_API.md)

## Promote a release

Prepare and review the settings for each intended destination before tagging. If a destination needs new settings after the tag is created, merge the change, verify it in DEV and create a new release tag.

| Destination | Trigger and requirements |
|---|---|
| [DEV](environments/nonprod/dev) | A reviewed merge to main, when enabled |
| [UAT](environments/nonprod/uat) | Successful DEV run and one approval |
| [TRAINING](environments/nonprod/training) | Successful DEV run and one approval |
| [PREPROD](environments/prod/preprod) | Successful UAT run and two distinct approvers |
| [PROD](environments/prod/prod) | Successful PREPROD run and two distinct approvers |

1. After DEV succeeds, create a signed release tag on the exact commit recorded by that deployment. Run **Kong/Build** once with the tag as `RELEASE_TAG`. Save the package build number.
2. When ready, **manually start** the destination job, such as `Deploy-uat`. Enter the API name, release tag, package build number, change ticket and successful deployment build number from the preceding environment in the table.
3. Review the proposed changes in Jenkins. After the required approvals, Jenkins applies them and runs smoke tests. Save the successful build number for the next promotion. Each higher environment waits for a separate manual start, using the same tag and package build.

[Tagging commands, promotion and rollback instructions](docs/OPERATIONS.md)

## Maintainer folders

| Folder | What it contains |
|---|---|
| `environments/` | Environment folders with per-API settings and control-plane registrations |
| `pipelines/` | Jenkins jobs, trusted destinations, credential IDs and approval groups |
| `scripts/` | API starter, validators and deployment commands |
| `tests/` | Tests for the delivery process |
| `docs/` | Developer and operator guides |

Use Python 3.11+, decK 1.70.0 and Gitleaks 8.30.1. Run `bash scripts/check.sh` and `bash scripts/security.sh` to reproduce the offline checks. Start with isolated DEV to verify actual Jenkins permissions, plugin compatibility, routing and recovery. [Setup](docs/SETUP.md) · [Verification](docs/VERIFICATION.md)


## How the folders map to Kong’s proposal

`environments/nonprod/` contains dev, uat and training. `environments/prod/` contains preprod and prod. Each environment has one `target.yaml`. It identifies the existing Konnect control plane and lists the APIs registered for that environment. The `tier` in API metadata selects API-specific policy checks. Both profiles use the same environment target. A maintainer lists the API under `apis` before its environment overlay can be enabled. Registration alone does not deploy it.

As in [KongAir](https://github.com/Kong/KongAir/tree/main), each team keeps its API contract next to the configuration it owns. This repository uses GitLab for review, Jenkins for delivery and decK for Gateway Services, Routes and plugins. The separate platform repository owns control-plane provisioning and shared policies.
