# Kong APIOps

Developers add and update APIs in **`apis/<api-name>/`**. GitLab holds the configuration. After review and merge, Jenkins deploys enabled APIs to DEV. The platform team manages gateways and shared infrastructure in its own repository.

## Find the file to edit

| What do you want to change? | File inside your API folder |
|---|---|
| Public path, HTTP method, Service or API policy | `kong.yaml` |
| What clients can request and expect back | `openapi.yaml` |
| How Jenkins tests a request through the gateway | `tests.yaml` |
| Backend or other settings for one environment | `overlays/dev.yaml` or the corresponding environment file |
| Owner, team or gateway tier | `metadata.yaml` |

[Open the documents API](apis/documents) for a complete disabled example.

## Add an API

From the project directory containing this README, prepare Python once:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --require-hashes -r requirements.lock
```

1. Create a branch and run `python3 scripts/new_api.py` in your terminal. Answer the questions about the API name, public path and team. The starter creates the files with deployment disabled.
2. Open the new API folder. Review the generated Route, contract and smoke checks. Fill in the DEV overlay with the values supplied by your backend and IAM teams. Store only secret references in Git.
3. Ask the APIOps maintainer to confirm the DEV target, register the approved smoke-test gateway URL and configure the API's Jenkins smoke credential. Enable the DEV overlay when ready.
4. Open a GitLab merge request. Jenkins checks all environments. After merge, look for the successful DEV deployment and its receipt.

## Update a Route

Edit the existing API folder. For a new path, add the Route to `kong.yaml`, describe the same path and method in `openapi.yaml`, and update `tests.yaml`. Preserve the API's ownership tag. Submit the three files together for review. [Developer walkthrough](docs/ADD_AN_API.md)

## Promote a release

A release manager tags the commit that passed DEV. Jenkins builds that tag once. UAT and TRAINING each require a DEV receipt and one approval. PREPROD requires the UAT receipt and PROD requires the PREPROD receipt. Both require two distinct approvers. [Promotion and rollback instructions](docs/OPERATIONS.md)

## Maintainer folders

| Folder | What it contains |
|---|---|
| `environments/` | References to existing DEV, UAT, TRAINING, PREPROD and PROD targets |
| `pipelines/` | Jenkins jobs, trusted destinations, credential IDs and approval groups |
| `scripts/` | API starter, validators and deployment commands |
| `tests/` | Tests for the delivery process |
| `docs/` | Developer and operator guides |

Use Python 3.11+, decK 1.70.0 and Gitleaks 8.30.1. Run `bash scripts/check.sh` and `bash scripts/security.sh` to reproduce the offline checks. Start with isolated DEV to verify actual Jenkins permissions, plugin compatibility, routing and recovery. [Setup](docs/SETUP.md) · [Verification](docs/VERIFICATION.md)
