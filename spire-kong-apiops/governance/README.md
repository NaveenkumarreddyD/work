# Governance boundary

Validation enforces a proposed baseline inherited from the earlier design: HTTPS downstream/upstream, verified upstream TLS, explicit methods/timeouts/retries, Service-level bearer OIDC with audience and role checks, rate limits, payload limits and correlation IDs. The external example adds IP restrictions and OAS validation. PREPROD/PROD require distributed Redis counters. These are implementation choices for review, not claimed Spire requirements.

`allowed plugins` and naming checks live in `scripts/validate.py`; change them through platform/security-owned reviews with regression tests. Do not disable checks to onboard an API. OIDC plugins and OAS validation may require enterprise licenses. Validate the actual plugin schema and entitlement on the supplied Gateway version. The local decK validator cannot establish these.

Each API has exactly one stable `owner-<api>` selection tag in `_info.select_tags`. Services, Routes and plugins carry the same ownership tag. Do not rename or transfer this tag as an ordinary API edit. Git `kong-v1.2.3` tags identify release source; ownership tags delimit mutable resources.

The supported initial routing profile is explicit literal prefix paths `/domain/api/v1/...`, one Service per API, and GET-based read-only smoke tests. Regex paths, parameterized paths, write smoke requests, delegated user authorization and per-client quotas need a reviewed extension of contract checks/tests. A prefix Route matches subpaths: contract checks do not imply exact-path or runtime schema enforcement. Platform/security must approve exposure before enablement.

Mandatory GitLab settings and Jenkins permissions are in `docs/SETUP.md`. CODEOWNERS placeholders have no enforcement until replaced and configured in GitLab.
