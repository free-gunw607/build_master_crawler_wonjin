# STATUS

## Repository
- repo: `build_master_crawler_wonjin`
- workspace path: `~/agent-coding/agent-projects/A4-worker-repos/build_master_crawler_wonjin`
- standardized project name: `build_master_crawler_wonjin`

## Current objective
Build a multi-source public notice crawler (LH, i-SH, GH) with hourly GitHub scheduler, Google Sheets vault persistence, and Telegram alert delivery

## Current phase
v1_frozen

## Current focus
- preserve v1 stability and monitor source selector drift
- keep Sheets schema and GUIDE tab synchronized with code
- operate hourly production workflow with idempotent delta alerts
- move recovery trigger outside GitHub schedule domain
- keep import sources registered but disabled until parser and operational smoke checks pass

## Recent completed work
- project created via bootstrap script
- launcher, .agent runtime, and durable handoff scaffolding generated
- repo policy and status board created
- source structure research completed for LH/i-SH/GH list/detail/paging patterns
- implemented initial crawler runtime and hourly workflow scaffold
- generated first 1-year crawl workbook with 3 source sheets
- applied raw-coupled normalization contract (`source + raw_id_value`)
- frozen tab structure (`scheduler_run_logs`, `overall`, `LH`, `iSH`, `GH`, `GUIDE`)
- cleaned legacy tabs and header-row contamination from production sheet
- updated workflow env contract for per-tab variables
- fixed sheet duplication bug: source tabs now write only `new_records` instead of full fetched set
- changed sheet write order: `overall`/source tabs now insert new rows at top (row 2, newest-first)
- added external cron watchdog runner script (`ops/external_watchdog_runner.py`) for GitHub schedule recovery outside GitHub scheduler domain
- added in-run dedup guard before sheet sync (`source + raw_id_value`)
- added workflow-level concurrency lock for hourly crawler
- upgraded schedule watchdog from alert-only to auto-recovery dispatch
- added external-watchdog design path using Google Apps Script trigger + GitHub dispatch
- registered the full import source list in `config/source_registry.json` with new sources disabled
- added a 45-minute cooldown to GitHub-native recovery dispatch to prevent repeated recovery attempts

## Current blockers
- none critical (schedule reliability mitigated by watchdog auto-recovery)

## Capability and MCP status
- required external capabilities: GitHub Actions secrets, Google Sheets API, Telegram Bot API
- optional external ops capability: Google Apps Script trigger with GitHub PAT
- approved but not active: none
- active MCP dependencies: none

## Progress snapshot
- overall progress: 100% (v1 scope)
- current confidence: production workflow and sheet vault validated
- current stability: frozen baseline

## Next actions
1. deploy Google Apps Script watchdog and script properties
2. monitor hourly logs and source HTML drift
3. add source-specific regression smoke checks
4. investigate the exact failed GitHub Actions run behind repeated watchdog notifications
5. classify registry sources and select the first 2-3 parser pilots

## Phase marker
- current: `PHASE-3-V1-FROZEN`
- next: `PHASE-4-EXTEND-SOURCES`
- resume pointer: `config/source_registry.json`, then `src/build_master_crawler_wonjin/main.py`

## Deliverable proof
- latest artifact path(s): `src/build_master_crawler_wonjin/main.py`, `.github/workflows/hourly_notices.yml`, `.github/workflows/schedule_watchdog.yml`, `docs/V1_FREEZE.md`, `docs/SOURCE_FREEZE.md`, `STATUS.md`
- proof timestamp: 2026-05-16
- note: credentials are configured via GitHub secrets/vars only (no raw secret in repo)

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
