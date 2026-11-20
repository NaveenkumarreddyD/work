# Add an API or Route

Start with the README commands. The three checked-in domains are illustrative disabled examples, not definitions of Spire's real APIs.

## New API

1. Run `scripts/new_api.py` with a unique API name, public path and real owning-team email. Choose `--tier external` only if platform confirms the target and policy model.
2. Review `metadata.yaml`, the Service and nested Routes/plugins in `kong.yaml`, the contract in `openapi.yaml` and checks in `tests.yaml`.
3. Complete only the DEV overlay initially. Ask platform/IAM for actual backend hostname, front-door URL, issuer/audience/role, Vault reference, Redis settings and quota. No credentials belong in these files. The sample numbers are proposed examples, not approved capacity values.
4. Platform supplies the existing DEV target and separately configures the trusted job target. Both the target and API overlay must be enabled. Leave higher-environment overlays disabled until their values are reviewed.
5. Run all checks and the secret scan. Submit an MR. Enablement with unresolved placeholders must fail.
6. Merge after API owner and platform/security review. The protected-main Build job validates and packages all APIs, then requests DEV deployment for each. Disabled APIs are recorded as NOT_BUILT and never synchronized. All enabled APIs are reconciled, so drift on an otherwise unchanged API also appears in the DEV plan.
7. Inspect the DEV receipt and smoke results. A failed sync or smoke test does not create a success receipt. Recover before promotion.

## Add a Route

Add another Route under the existing Service; copy its HTTPS/method/tag/strip-path/preserve-host fields. Choose a unique name prefixed with the API name. Add corresponding OpenAPI operations and tests. Do not create another ownership scope or change the backend Service when only a new public Route is needed.

The initial validator supports literal prefix paths. For example, `/crm/customers/v1` is a prefix that can also match `/crm/customers/v1/123`. For parameterized or regex routing, extend the reviewed validator and runtime contract tests first. The sample bearer-authentication setup uses application roles; delegated user access needs a separately approved design.

## DEV only and later promotion

Changing `kong.yaml` changes shared source, but merging deploys only to DEV. Higher environments continue to run the package already promoted there. A new tag freezes all environment variants, and higher jobs require explicit selection and approval. A DEV-only overlay affects only DEV's rendered bytes.

A tag created before higher overlays were enabled cannot later deploy there. Review/enable those values on main and create a new release tag. Never edit a retained package or move a tag to compensate.

## Remove or disable

Automatic DEV blocks deletions. For intentional Route removal, merge the reviewed change, create a release tag, and run the DEV job manually with that tag, a ticket and ALLOW_DELETIONS. Review the diff and provide approved encrypted backup storage. Automatic DEV failure on a deletion is expected until this controlled deployment is done.

Disabling an API or removing its folder does not delete live entities. It also does not remove an old scope from drift monitoring. Keep the old scope/package in monitoring until platform completes an approved retirement. Whole-API retirement and ownership-tag/CP moves require a separate maintenance plan with snapshot, consumer-impact review and a narrowly scoped removal operation; they are deliberately blocked by the one-Service baseline. Do not run unscoped decK reset or sync.
