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

## When to update target.yaml

Each environment has one `target.yaml` shared by its APIs. For example, the [UAT target](environments/nonprod/uat/target.yaml) identifies the existing Konnect control plane Jenkins will use and lists the APIs registered for UAT.

| What changed? | What to update |
|---|---|
| An API is being onboarded to UAT. | Ask an APIOps maintainer to add its name to the UAT target’s `apis` list before enabling its UAT settings. |
| The platform team changed the UAT destination. | The maintainer updates the UAT target and coordinates the matching change to Jenkins’ trusted settings. See the [setup guide](docs/SETUP.md). |
| Only the Payments UAT backend changed. | Update the [Payments UAT settings](environments/nonprod/uat/apis/billing/payments.yaml). |
| A Payments route changed. | Update the route, contract and smoke tests together in the [Payments API folder](apis/billing/payments). |

**Promoting an already configured API requires no file changes.** Start the destination job in Jenkins with the tested tag and package build, then review the proposed changes. See [Promote a release](#promote-a-release).

## Payments walkthrough

Add `GET /billing/payments/v1/summary`, test it through the DEV gateway, then promote Payments to UAT, PREPROD and PROD. This example assumes the backend already serves that path and returns a JSON field named `totalPayments`. The checked-in Payments sample is disabled. Before the first live run, an APIOps maintainer must configure and enable DEV with approved connection details and Jenkins credentials. [Environment setup](docs/SETUP.md)

### 1. Add the route on a feature branch

Create `feature/payments-summary` from the latest `main`. Make these three edits in one merge request:

| File | Edit |
|---|---|
| [kong.yaml](apis/billing/payments/kong.yaml) | Under `payments-service.routes`, copy the existing `payments-v1` route. Name the copy `payments-summary-v1` and set its path to `/billing/payments/v1/summary`. Keep the GET method, HTTPS, `strip_path: false` and the `owner-payments` tag. |
| [openapi.yaml](apis/billing/payments/openapi.yaml) | Add a GET operation for the same path. Describe the successful response with `totalPayments`, retain bearer authentication, and document 401 and 403. For this compatible addition, update the sample contract version from `1.0.0` to `1.1.0`. |
| [tests.yaml](apis/billing/payments/tests.yaml) | Keep the existing tests and copy the three checks for the new path. Give each copy a unique name. With valid credentials expect 200 and set `body_contains: totalPayments`. With missing or invalid credentials expect 401. |

### 2. Validate the change and test in DEV

From the directory containing this README, run the local checks with the project tools installed:

```bash
bash scripts/check.sh
bash scripts/security.sh
```

Push the feature branch and open a GitLab merge request into `main`. After validation, review and merge, Jenkins automatically deploys enabled APIs to DEV. Open the successful **Payments** run of **Deploy-dev**. Check that the new endpoint passed all three smoke checks and that the run archived `receipt.json`. Record the DEV deployment build number and the full commit SHA from that run.

### 3. Tag the tested commit and build the release

The release manager checks that Payments is configured and enabled in each intended destination **before tagging**. If settings need a change, merge it and use the commit from the next successful DEV run. In the commands below, replace `DEV_COMMIT_SHA` with that SHA and `kong-v1.5.0` with the next unused release tag. Use your approved signing key.

```bash
git fetch origin main --tags
git tag -s kong-v1.5.0 DEV_COMMIT_SHA -m "Add Payments summary route"
git verify-tag kong-v1.5.0
git push origin refs/tags/kong-v1.5.0
```

In Jenkins, open **Kong/Build → Build with Parameters**, enter the signed tag in `RELEASE_TAG`, and start the build. Record the successful build number as `PACKAGE_BUILD`. This package contains the reviewed settings for every destination.

### 4. Manually promote Payments in Jenkins

When the team is ready for a destination, open its job and select **Build with Parameters**. Choose `ACTION=DEPLOY`, change the default `API` from `invoices` to **`payments`**, enter the signed tag in `REF`, and supply your `CHANGE_TICKET`. Leave `ALLOW_DELETIONS` unchecked for this route addition.

Reuse the same `REF` and `PACKAGE_BUILD` in all three jobs. For `PREVIOUS_BUILD`, enter the successful Payments **deployment** build from the preceding environment:

| Start this job manually | Use this run for `PREVIOUS_BUILD` | Approval after Jenkins shows the proposed changes |
|---|---|---|
| `Deploy-uat` | `Deploy-dev` from step 2 | One authorized approver |
| `Deploy-preprod` | Successful `Deploy-uat` | Two distinct authorized approvers |
| `Deploy-prod` | Successful `Deploy-preprod` | Two distinct authorized approvers |

At each stage, review the plan for `payments-summary-v1`. After approval, Jenkins applies the change, checks the resulting configuration and runs the smoke tests. A successful run produces the receipt needed for the next stage. Each higher environment waits for a separate manual start. **Promotion requires zero file edits.**

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

`environments/nonprod/` contains dev, uat and training. `environments/prod/` contains preprod and prod. Both API policy profiles use the same environment target.

As in [KongAir](https://github.com/Kong/KongAir/tree/main), each team keeps its API contract next to the configuration it owns. This repository uses GitLab for review, Jenkins for delivery and decK for Gateway Services, Routes and plugins. The separate platform repository owns control-plane provisioning and shared policies.
