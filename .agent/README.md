# .agent Runtime

This directory is the repo-local runtime workspace for `build_master_crawler`.

It exists so owners and agents can inspect practical runtime state without digging through source internals.

## Standard Folders
- `state/`: lightweight current-state snapshots and resumable metadata
- `logs/`: execution logs and trace summaries
- `approvals/`: approval policy plus any saved approval artifacts
- `runs/`: run-scoped metadata and resumable records
- `bundles/`: issue bundles and handoff packages
- `queue/`: queued work items and deferred follow-ups
- `answers/`: archived durable handoff answers copied from repo-root `LAST_ANSWER.md`
- `registry/manifests/`: repo-local copies of mutation manifests
- `recovery/`: snapshot metadata and recovery archives

## Owner Commands
- `./repo agent-status`
- `./repo agent-log`
- `./repo agent-approvals`
- `./repo agent-bundle`
- `./repo agent-resume`
- `./repo agent-queue`
- `./repo last-answer`
- `./repo preflight`
- `./repo compliance`
- `./repo node-status`
- `./repo claim-node --node-id <id>`
- `./repo claim-auth-family <family_id>`
- `./repo claim-write-session --path <path>`
- `./repo create-manifest ...`
- `./repo snapshot-repo --reason "..."`

## Universal Autonomy And Handoff
- the default mode is autonomous repo-local execution with minimal interruption
- intermediate progress should primarily be written to durable files instead of repeated terminal updates
- the standard durable handoff path is:
  - repo-root `LAST_ANSWER.md`
  - `answers/`
  - `state/project_state.json`
  - `logs/`
  - `bundles/`
- approvals should interrupt execution only when the work crosses a real trust, scope, authentication, or destructive boundary

## Usage Notes
- keep durable guidance in tracked docs under `.agent/`
- keep generated runtime artifacts inside the matching subdirectory
- prefer launcher-level inspection commands before asking owners to inspect raw files manually
