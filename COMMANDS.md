# COMMANDS

## Quick Start
```bash
cd ~/agent-coding/agent-projects/A4-worker-repos/build_master_crawler
./repo entry
./repo doctor
./repo agent-status
./repo last-answer
```

## Discoverability Commands
`entry`
Show the owner-facing front door.

`modes`
Show the main launch/use-case modes.

`examples`
Show the copy-paste command catalog.

`doctor`
Run lightweight discoverability checks.

`last-answer`
Show the current durable handoff summary.

## Runtime Commands
`agent-status`
Show the standard `.agent` runtime summary.

`agent-log`
Inspect the latest runtime log or show the log directory.

`agent-approvals`
Show the default approval policy and any saved approval artifacts.

`agent-bundle`
Inspect the issue-bundle directory and related bundle guidance.

`agent-resume`
Show resumable run guidance and the latest run artifacts if present.

`agent-queue`
Inspect queued work items and queue guidance.

`node-status`
Show execution lease, auth-family lease, and write-session state.

`preflight`
Check repo identity, required B3 files, and runtime readiness.

`compliance`
Refresh and display `.agent/state/compliance_state.json`.

`claim-node --node-id <id>`
Claim the active execution node lease for this repo.

`claim-write-session --path <path>`
Claim active write ownership for the intended repo paths.

`create-manifest --target-repo <repo> --path <path>`
Create a durable mutation manifest before approved inter-repo mutation.

`snapshot-repo --reason "..."`
Create a repo snapshot and register it in the workspace ledger.

`publish-repo-snapshot --drive-folder-id <id>`
Upload a repo snapshot to Google Drive via `gws`, update registry metadata, and emit a Slack receipt payload.

## Launcher
- preferred owner path on bash / WSL: `./repo ...`
- preferred owner path on PowerShell: `\.\repo.ps1 ...`
- raw Python module invocation is the lower-level contributor path

## Examples
- `./repo entry`
- `./repo doctor`
- `./repo agent-status`
- `./repo last-answer`
- `./repo agent-approvals`
- `./repo preflight`
- `./repo claim-node --node-id 1`
- `./repo claim-write-session --path src/build_master_crawler`
- `./repo create-manifest --target-repo some_other_repo --path STATUS.md --reason "approved shared change"`
- `./repo snapshot-repo --reason "manual checkpoint"`
- `./repo publish-repo-snapshot --drive-folder-id <google_drive_folder_id>`
- add project-specific workflow examples here as the repo matures

## Notes
- prefer use-case examples over raw subcommand lists
- use `LAST_ANSWER.md` and `.agent/` runtime files as the default progress trail
- make any company-tracking or target-tracking mode explicit if the repo supports it
