# GitHub Actions CD

These workflows are self-contained and runnable directly from this repo — `workflow_dispatch` from the Actions tab, no dependency on any other repo.

- `dpn-gha-file-scan-cd.yaml` — installs/deploys the file-scan-service chart.
- `dpn-gha-file-scan-prerequisites-cd.yaml` — provisions the cloud infrastructure (S3/SNS/SQS on AWS, Storage/Event Grid on Azure) that must exist before the install workflow runs.
- `dpn-gha-file-scan-rollback.yaml` — `helm rollback` to a specific or auto-resolved previous revision. Requires typing the release name (`dpn-file-scan-service`) again to confirm.
- `dpn-gha-file-scan-uninstall.yaml` — `helm uninstall`. Requires the same confirmation. Does not remove the cloud infrastructure provisioned by the prerequisites workflow.

## One-time setup required (not a workflow change)

- **GitHub Environments** named `<environment>-<cluster>` for each target (e.g. `dev-dpn01`, `test-dpn02`).
- **Repository or Environment secrets**: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` (Azure OIDC federated identity).
- **AWS path**: relies on OIDC role-chaining into the shared hub role, then your account's `oidc_github_runner_admin` role — no AWS secret needed, but that role/trust must exist.
- **Self-hosted runner**: targets `runs-on: [self-hosted, vmss]` — register a runner with that label, or change `runs-on` to a pool you control.
- **Per-environment config**: `.github/config/{aws,azure}/<environment>-<cluster>.json` already has real target values — update if pointing at different infrastructure. Note this component's own keys (e.g. `FILESCAN_SOURCE_BUCKET`) are interleaved with other components' keys in the same shared JSON files.

Nothing in the workflow logic itself needs editing to run these.
