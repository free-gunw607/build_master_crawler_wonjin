# ENTRY

## Launch Modes
Preferred owner launcher:

```bash
./repo <command> [args...]
```

PowerShell:

```powershell
.\repo.ps1 <command> [args...]
```

`entry`
Print this front door.

`modes`
Print the main launch/use-case modes.

`examples`
Print the copy-paste command catalog.

`doctor`
Run lightweight discoverability checks.

`last-answer`
Print the current durable handoff summary.

## Runtime Commands
`agent-status`
Show the standard `.agent` runtime summary.

`agent-log`
Inspect runtime logs.

`agent-approvals`
Show approval policy and approval artifacts.

`agent-bundle`
Inspect issue bundles and handoff packages.

`agent-resume`
Show resumable run guidance.

`agent-queue`
Inspect queued work items.

## Agent Runtime
Runtime overview: `.agent/README.md`

Required runtime folders:
- `.agent/state/`
- `.agent/logs/`
- `.agent/approvals/`
- `.agent/runs/`
- `.agent/bundles/`
- `.agent/queue/`
- `.agent/answers/`

Approval policy:
- `.agent/approvals/POLICY.md`

Answer / handoff trail:
- repo root `LAST_ANSWER.md` holds the latest durable handoff summary
- `.agent/answers/YYYYMMDD_HHMMSS_last_answer.md` stores timestamped archived copies

## Operating Default
- proceed autonomously in normal repo-local work
- minimize interruptions
- use the durable handoff files before relying on repeated terminal updates
- interrupt only for important approvals or hard blockers

## Code Map
See `CODEMAP.md` for one-line file/module responsibilities.

## Command Catalog
See `COMMANDS.md` for copy-paste examples.

## Status / Current Objective
- current objective: `Bootstrap a new crawling project scaffold in the A4 worker layer`
- start with `STATUS.md` for live progress

## Links
- `README.md`
- `STATUS.md`
- `CODEMAP.md`
- `COMMANDS.md`
- `LAST_ANSWER.md`
- `.agent/README.md`
