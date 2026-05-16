# STATUS

## Repository
- repo: `build_master_crawler`
- workspace path: `~/agent-coding/agent-projects/A4-worker-repos/build_master_crawler`
- standardized project name: `build_master_crawler`

## Current objective
Bootstrap a new crawling project scaffold in the A4 worker layer

## Current phase
bootstrap

## Current focus
- initialize repository structure
- clarify first approved scope
- align repo with the universal autonomy policy

## Recent completed work
- project created via bootstrap script
- launcher, .agent runtime, and durable handoff scaffolding generated
- repo policy and status board created

## Current blockers
- none yet
- define after first implementation review

## Capability and MCP status
- required external capabilities: none confirmed yet
- approved but not active: none
- active MCP dependencies: none

## Progress snapshot
- overall progress: 5%
- current confidence: early but structured
- current stability: initial scaffold only

## Next actions
1. register the project in the vault
2. define the first approved implementation scope
3. start the first implementation cycle while keeping durable handoff files current

## Phase marker
- current: keep explicit phase id (example: `PHASE-0`, `PHASE-1`)
- next: keep one immediate next phase id
- resume pointer: one file/section pointer for zero-warmup resume

## Deliverable proof
- latest artifact path(s): record concrete file paths for the latest deliverable
- proof timestamp: record when the artifact was written or verified
- note: do not mark completed from chat-only promises without file proof

## Relevant anchors
- global policy: `~/.codex/AGENTS.md`
- A2 guide: `~/agent-coding/agent-system/A2-workspace-memory/Guide.md`
- A2 structure: `~/agent-coding/agent-system/A2-workspace-memory/Structure.md`
- target OS baseline: `~/agent-coding/agent-system/A1-system-governance/docs/TARGET_OS/00_ENTRY.md`

## Notes for operators
This file is the repository situation board.
`ENTRY.md` should act as the owner-facing front door for the repo.
A repo-local runtime workspace should exist under `.agent/`.
A repo-root `LAST_ANSWER.md` should summarize the latest durable handoff, with archived copies under `.agent/answers/`.
A human should be able to read this file and immediately understand:
- what is happening now,
- what happened recently,
- what the blockers are,
- whether any important capability gap exists,
- whether MCP adoption changed repository behavior,
- how much progress has been made,
- what should happen next.
