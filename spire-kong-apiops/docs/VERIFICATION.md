# Verification

The audit covered developer onboarding, Route edits, environment selection, deployment credentials, approval, promotion, rollback and drift. The interactive starter and external API template are exercised by the onboarding tests. Three disabled Billing APIs are included.

We found that the package controlled the destination of bearer-token smoke requests. The trusted deployment job now requires an exact per-API gateway URL match in its pinned settings. Curl enforces HTTPS and ignores local curl configuration. Test a matching and a deliberately mismatched destination on the isolated DEV Jenkins job before rollout.

Offline verification passed on 23 November 2026. All 85 automated tests passed, decK 1.70.0 rendered and validated all three Billing APIs for all five environments, and Gitleaks reported no findings. Live operations in the tests use test doubles. The updated Jenkinsfile still needs a run on the actual controller.

Production acceptance requires a successful isolated DEV deployment, confirmation of GitLab protections and Jenkins permissions, live plugin and smoke checks, and a rollback rehearsal using retained artifacts. See [Setup](SETUP.md) and [Operations](OPERATIONS.md).
