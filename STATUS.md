# STATUS

## Repository
- repo: `build_master_crawler_wonjin`
- workspace path: `~/agent-coding/agent-projects/A4-worker-repos/build_master_crawler_wonjin`
- standardized project name: `build_master_crawler_wonjin`

## Current objective
Build a multi-source public notice crawler (LH, i-SH, GH) with hourly GitHub scheduler, Google Sheets vault persistence, and Telegram alert delivery

## Current phase
implementation_in_progress

## Current focus
- stabilize source parsers for LH/i-SH/GH
- finalize idempotent Sheets append and Telegram delta notifier
- validate hourly GitHub Actions workflow path and secrets contract

## Recent completed work
- project created via bootstrap script
- launcher, .agent runtime, and durable handoff scaffolding generated
- repo policy and status board created
- source structure research completed for LH/i-SH/GH list/detail/paging patterns
- implemented initial crawler runtime and hourly workflow scaffold
- generated first 1-year crawl workbook with 3 source sheets

## Current blockers
- none critical
- credentials setup required before production run (`GOOGLE_SERVICE_ACCOUNT_JSON`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)

## Capability and MCP status
- required external capabilities: GitHub Actions secrets, Google Sheets API, Telegram Bot API
- approved but not active: none
- active MCP dependencies: none

## Progress snapshot
- overall progress: 55%
- current confidence: first implementation validated locally
- current stability: workable baseline with source-specific parsing

## Next actions
1. run non-dry execution with real secrets to verify Sheets/Telegram delivery
2. harden parser edge cases and add retry/backoff logging
3. add regression checks for selector drift

## Phase marker
- current: `PHASE-2-IMPLEMENTATION`
- next: `PHASE-3-OPERATIONS-HARDENING`
- resume pointer: `src/build_master_crawler_wonjin/main.py`

## Deliverable proof
- latest artifact path(s): `src/build_master_crawler_wonjin/main.py`, `.github/workflows/hourly_notices.yml`, `output/notices_first_run_1y.xlsx`, `output/notices_first_run_1y_prod.xlsx`, `docs/SOURCE_FREEZE.md`
- proof timestamp: 2026-05-16
- note: production dry-run and non-dry-run both verified; Sheets append and Telegram send executed once

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
