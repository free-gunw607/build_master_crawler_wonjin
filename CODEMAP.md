# CODEMAP

## Core Entry Points
- `repo`: bash / WSL owner launcher and standard runtime command front door
- `repo.ps1`: PowerShell owner launcher and standard runtime command front door
- `ENTRY.md`: owner-facing front door
- `README.md`: high-level repository purpose and orientation
- `STATUS.md`: live situation board
- `src/.../cli.py`: CLI entrypoint
- `src/.../workflows.py`: operator workflow orchestration

## Agent Runtime
- `.agent/README.md`: runtime overview and conventions
- `.agent/state/`: resumable runtime state and snapshots
- `.agent/logs/`: execution logs and trace summaries
- `.agent/approvals/`: approval policy and approval artifacts
- `.agent/runs/`: run-scoped metadata and resumable records
- `.agent/bundles/`: issue bundles and handoff packages
- `.agent/queue/`: queued work items and deferred follow-ups

## Source / Integration
- fill in the source adapters or integration modules here

## Validation / Export
- fill in the validation, parsing, export, and artifact-writing modules here

## Notes
- start small
- keep one-line responsibilities only
- update this file whenever the repo gains a new major module or entrypoint
