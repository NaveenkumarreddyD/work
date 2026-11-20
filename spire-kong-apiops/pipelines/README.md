# Jenkins jobs

Use root Jenkinsfile for credential-free MR validation. Use the three files in this directory for trusted standalone jobs loaded from an administrator-pinned reviewed commit:

- Build.Jenkinsfile: protected main → automatic DEV; explicit release tag → retained package only.
- Deploy.Jenkinsfile: fixed job environment; DEPLOY or ROLLBACK; no caller-selected drift baseline.
- Drift.Jenkinsfile: scheduled, read-only, latest successful per-API destination package.

`settings.json` contains nulls where actual environment/account values are unknown. Job names and node labels are suggested local conventions. Replace/configure them during setup. Do not enter secrets into this file.

See docs/SETUP.md before installing jobs. A Git repository cannot configure GitLab protections, Jenkins credential scopes, approver group membership or artifact-store retention by itself.
