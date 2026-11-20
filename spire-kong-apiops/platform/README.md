# Shared platform resources

This folder is owned by the platform team. API deployment never synchronizes it. Global plugins, Consumers, Vault definitions, certificates and Control Plane provisioning need a separate reviewed lifecycle and dedicated ownership scope/credentials. Keep secrets in the enterprise secret manager; never put actual certificates with private keys or Consumer credentials into API packages.

Spire's PDF includes these resources and Konnect catalog/teams in a broader monorepo. This deliverable implements the requested Gateway API delivery boundary. decK Gateway configuration does not create Konnect control planes, organization teams or catalog entries. If that scope is added, evaluate Kong's Konnect APIs/Terraform/kongctl separately; do not translate kongctl plan/sync to decK commands blindly.

Supply actual Control Plane names (per environment and tier), Konnect regional API URL, front-door/DP topology, CA trust, egress permissions, licensed plugin schema, IAM claims, Redis/Vault references and recovery storage to the CI team. Nothing in the samples proves these resources exist.
