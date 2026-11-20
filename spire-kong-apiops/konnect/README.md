# Existing deployment targets

`nonprod/dev`, `nonprod/uat`, `nonprod/training`, `prod/preprod` and `prod/prod` each contain target.yaml. These are references to existing Konnect Control Planes, not provisioning declarations. All are disabled. Region and names are placeholders.

Target enablement and each API overlay enablement are independent. Both must be true for deployment. The trusted deployment job separately pins the expected region/CP in pipelines/settings.json, outside the released data package. Copy actual owner-approved values into both through platform review.

The sample permits internal/external tiers, carried from the earlier repo. Confirm whether your organization actually has both. The implementation currently requires both target names when enabling a target; change this reviewed model before use if you have a different topology. Do not invent a second CP to satisfy the example.
