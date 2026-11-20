# Design and decisions

GitLab stores source and enforces reviews. Jenkins validates untrusted merge requests without deployment credentials. Standalone jobs loaded from an administrator-pinned tooling commit build reviewed source on isolated agents and deploy only data packages on trusted agents. decK 1.70.0 manages API-owned Gateway entities; no kongctl commands are used.

Spire hierarchy is retained: konnect/nonprod/{dev,uat,training}, konnect/prod/{preprod,prod}, apis, platform, governance, pipelines. Native Services and nested Routes/plugins remain together in each API kong.yaml; OpenAPI is the contract, overlays hold environment values. Platform resources and Konnect control-plane/catalog/team provisioning require separate lifecycle tooling and are explicitly outside API sync.

The supplied scope fixes the architecture. Alternatives considered: whole-Control-Plane sync risks shared resources; kongctl expands lifecycle scope; per-API decK states give the requested ownership boundary. Choose per-API states. Stable owner tags are checked; Git release tags identify versions. They serve different purposes.

Automatic DEV follows successful protected-main validation. Higher environments use an annotated protected release tag and one retained checksum-bound package. Approval binds package, target, state and plan. Replanning must match before apply. Deletions need explicit authorization plus a scoped snapshot. A shared CP lock covers plan/approval/apply/test. Promotion checks a successful predecessor receipt for the same API/commit. Rollback checks an earlier successful receipt in the destination environment. Drift is read-only against the actual last successful package.

No organization targets, region, approvals, secrets, entitlements or policy decisions are inferred. Examples are disabled and marked placeholders. Baseline policies are proposed examples carried forward from the prior repo, not evidence of Spire standards. Enablement requires live schema validation and a recovery exercise.
