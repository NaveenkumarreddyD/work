# Implementation plan

1. Preserve the earlier repository; create a separate deliverable and adapt paths to Spire hierarchy.
2. Test and implement strict enabled-target validation, tag/commit identity, same-commit promotion and known-good rollback receipts, automatic DEV authorization and deletion gates.
3. Add trusted Jenkins build, automatic DEV, promotion and drift jobs. Keep merge-request agents credential-free and deployment scripts independent of release-owned executable code.
4. Write beginner README, onboarding, GitLab/Jenkins setup, reference comparison, secrets and recovery guidance.
5. Run all tests, actual pinned decK offline rendering for all overlays, scanner, pipeline syntax checks and clean ZIP extraction checks. Record live-system limitations.

Review focus: moved tags; tampered packages; enabled examples with unresolved values; changed live plan after approval; disabled/deleted APIs leaving orphaned resources; rollback after partial sync; leaking secrets in reports.
