## What changes for clients?

API and environment:
Owner and change ticket:

- [ ] OpenAPI, Kong Routes and smoke checks agree.
- [ ] Full offline checks and secret scan passed on the latest MR revision.
- [ ] Owner tag remains stable; no shared/global resources were added.
- [ ] DEV is the only environment being enabled, unless higher-environment values have owner approval.
- [ ] Authentication, authorization, TLS, payload and rate policies were reviewed.
- [ ] Deletions, breaking changes and recovery steps are described below.
- [ ] API owner and platform/security review requirements are satisfied.

Rollback / compatibility notes:
