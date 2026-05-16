# Build Master Crawler

This repository is for Bootstrap a new crawling project scaffold in the A4 worker layer.

## Owner Front Door
- preferred owner goto command on bash / WSL: `./repo entry`
- preferred owner goto command on PowerShell: `\.\repo.ps1 entry`
- launcher-first usage is the default owner path

## Discoverability
- preferred owner launcher: `./repo ...` on bash/WSL and `\.\repo.ps1 ...` on PowerShell
- owner-facing front door: `ENTRY.md`
- file/module map: `CODEMAP.md`
- command examples: `COMMANDS.md`
- lightweight CLI discoverability commands should include: `entry`, `modes`, `examples`, `doctor`, `last-answer`

## Agent Runtime
- repo-local runtime workspace: `.agent/`
- approval policy: `.agent/approvals/POLICY.md`
- runtime overview: `.agent/README.md`
- durable handoff summary: `LAST_ANSWER.md`
- standard runtime commands should include: `agent-status`, `agent-log`, `agent-approvals`, `agent-bundle`, `agent-resume`, `agent-queue`

## Operating default
- proceed autonomously in normal repo-local work
- minimize interruptions
- prefer durable file-based handoff over frequent terminal progress summaries
- reserve approval requests for major scope, trust, authentication, remote-side-effect, privacy-sensitive, or destructive boundaries

## Current direction
- clarify the stable execution path
- prefer the simplest reliable implementation route
- keep repository-local execution reproducible and understandable
- keep durable handoff files current as work advances

## Policy references
- global policy: `~/.codex/AGENTS.md`
- A2 guide: `~/agent-coding/agent-system/A2-workspace-memory/Guide.md`
- A2 structure: `~/agent-coding/agent-system/A2-workspace-memory/Structure.md`
- target OS baseline: `~/agent-coding/agent-system/A1-system-governance/docs/TARGET_OS/00_ENTRY.md`

## Workspace placement
- worker repo root: `~/agent-coding/agent-projects/A4-worker-repos/build_master_crawler_wonjin`
- the repo may keep its own local operating rules, but new repos should anchor to the target-OS governance package
