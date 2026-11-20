# Reference review — 20 November 2026

## Inputs actually reviewed

- The uploaded two-page **folder-structure.pdf**, recovered from the earlier chat attachment. The referenced `/mnt/data` path was not mounted here; the attachment was available through the chat's local preview. Both rendered pages were inspected. Much of the prose is graphical and absent from plain text extraction.
- Earlier chat “Kong CI CD Guide” and local `kong-api-cicd` source/scripts/tests. That later local version explicitly had no automatic merge-to-DEV deployment, unlike the requested continuation.
- [KongAir main](https://github.com/Kong/KongAir/tree/main), its README and `.github/workflows` examples. Local checkout reviewed at commit `f1a952e2284227e7470d6bda803026c55ab047ec`; official raw README and PRD workflow were also fetched to check current upstream content. Web fetch of GitHub's tree page itself failed, so the local tree plus official raw files were used. Main is mutable; this is a bounded comparison, not a claim every file at remote HEAD was audited.
- Current official CLI and product docs linked below. The uploaded PDF is the only Spire-specific document supplied; no private Spire standards, environment data or other internal documentation have been assumed.

## Comparison and decisions

| Area | Spire PDF | KongAir / earlier design | This repository |
|---|---|---|---|
| Shape | konnect/nonprod and prod, apis, platform, governance, pipelines | KongAir teams own domains; older repo used environments/ | Keeps Spire hierarchy; API-local overlays; shared ownership boundary |
| Tools | Jenkins with kongctl plan/sync | KongAir GitHub Actions/decK; earlier repo GitLab/Jenkins/decK | GitLab SCM and Jenkins, decK Gateway commands |
| API model | Spec, gateway config, backend addresses per environment | KongAir generates from OAS then patches; earlier native Kong YAML | Reviewed native Service/Routes/plugins plus checked OpenAPI and values overlays |
| DEV | Automatic on merge | KongAir stages generated PRs; later local repo required manual deploy | Protected-main build → enabled DEV sync and smoke, deletion gate |
| Promotion | Same commit, UAT→preprod→prod, approval | KongAir copies generated PRD config; earlier protected tag/package design | Signed annotated protected Git tag, retained package, predecessor receipt and diff-bound approval |
| Scope | Platform vs integrations | KongAir broad platform managed tag; earlier per-API owner tags | One stable API owner scope; shared/global resources excluded |
| Recovery | Not detailed | Earlier package/snapshot controls | Known-good destination receipt, retained package, reverse diff, approval, smoke, read-only drift |

The PDF includes Konnect control planes, API catalog and teams under platform responsibility. Those platform lifecycle resources are not created by decK API synchronization. [kongctl](https://developer.konghq.com/kongctl/) is suitable for a separately scoped Konnect lifecycle workflow if requested. Adding it here would expand the agreed Gateway delivery boundary.

[KongAir's PRD example](https://raw.githubusercontent.com/Kong/KongAir/main/.github/workflows/deploy-kong-PRD.yaml) uses decK 1.26.0, legacy `deck sync`, `-s` and runtime-group naming. It is reference material, not the production command contract for this repository. The broad generated aggregate and GitHub Actions flow were not copied.

Native configuration is kept deliberately: owners can see and review Route/policy edits directly, without automatically regenerating entity identities whenever the contract changes. [openapi2kong](https://developer.konghq.com/deck/file/openapi2kong/) remains an option for a reviewed future workflow; introducing it would require a stable UUID/naming and migration strategy. Contract checks here are not an automatic conversion step.

## Verified command contract

Pinned CLI: [decK v1.70.0 official release](https://github.com/Kong/deck/releases/tag/v1.70.0). Official macOS archive checksum was checked, then actual version/help/offline rendering were executed locally. This pin is explicit; no claim of indefinite “latest” compatibility is made.

| Purpose | Command used |
|---|---|
| Render native YAML with nonsecret values | `deck file render --populate-env-vars input.yaml -o state.yaml` |
| Offline structural validation | `deck file validate state.yaml` |
| Live reachability/schema | `deck gateway ping` / `deck gateway validate state.yaml` |
| Review and drift | `deck gateway diff state.yaml --json-output` |
| Scoped reconciliation | `deck gateway sync state.yaml --yes` |
| Scoped sensitive snapshot | `deck gateway dump --select-tag owner-API -o snapshot.yaml` |

The trusted job passes an explicit config file and `--konnect-control-plane-name` / `--konnect-addr`; the token uses DECK_KONNECT_TOKEN, never a literal command argument. `_info.select_tags` is validated in every API state. The CLI render can omit that management metadata, so the build restores it from the checked source and revalidates ownership. Entity tags are checked independently.

[Sync docs](https://developer.konghq.com/deck/gateway/sync/) describe deletion reconciliation. [Tag docs](https://developer.konghq.com/deck/gateway/tags/) explain partial ownership and AND semantics for multiple selection tags. [Configuration docs](https://developer.konghq.com/deck/configuration/) document flag/environment precedence. [Diff docs](https://developer.konghq.com/deck/gateway/diff/) define JSON summary/changes and optional exit status 2 for differences. This implementation deliberately parses the JSON and treats any CLI failure as an error; it does not rely on grepping a human summary or treating exit code 2 as an ordinary success.

[Offline validation](https://developer.konghq.com/deck/file/validate/) cannot prove live plugin-schema validity. That is why delivery runs online Gateway validation and runtime smoke checks. [decK Gateway support](https://developer.konghq.com/deck/gateway/) covers Konnect/hybrid/traditional Admin API configurations, not DB-less Gateway management.

For server controls see [GitLab protected tags](https://docs.gitlab.com/user/project/protected_tags/), [Code Owners](https://docs.gitlab.com/user/project/codeowners/), [Jenkins approvals](https://www.jenkins.io/doc/pipeline/steps/pipeline-input-step/) and [Copy Artifact parameter selection](https://www.jenkins.io/doc/pipeline/steps/copyartifact/). Settings outside the repository must be configured and proven on your servers.
