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
- keep unverified import sources registered but disabled until parser and operational smoke checks pass

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
- classified registered source pages and selected `BMC` and `UMCA` as the first parser pilots
- confirmed `ISH_SEOUL_CANDIDATE` is a 59/59 raw-ID duplicate of existing `i-SH` and merged it into that source
- implemented dry-run-only pilot adapters and parser unit smoke tests for BMC and UMCA
- added registry-driven onboarding guard and overnight execution plan
- first source family dry-run passed: BMC 22, UMCA 5, DUDC 38, DCCO 6, SCTC 4, JNDC 6
- hardened Telegram delivery for HTML escaping, message chunking, 429 retry, API response checks, and missing-secret visibility
- promoted BMC and UMCA to `active_v2` for controlled production verification; later-family sources remain disabled
- completed controlled BMC/UMCA production workflow `29280240103` successfully; enabled source set was LH, i-SH, GH, BMC, UMCA
- post-production batch-01 dry-run reconfirmed DUDC 38, DCCO 6, SCTC 4, JNDC 6 at 2026-07-14 04:56 KST
- registry-wide adapter coverage completed for IH, GDCO, CBDC, GMCC, CNDC, JBDC, GBDC, GNDC, and GH sale/rental candidate; all remain disabled until source-specific production gates pass
- explicit production activation guard now rejects registry entries without boolean `production_approved`
- latest production regression `29302647947` on commit `7d82e8d` passed with enabled set LH/i-SH/GH/BMC/UMCA
- DUDC/DCCO/SCTC/JNDC promoted to `active_v2`; controlled activation workflow `29302911754` passed with enabled set LH/i-SH/GH/BMC/DUDC/DCCO/UMCA/SCTC/JNDC
- CBDC/CNDC promoted to `active_v2`; controlled activation workflow `29303970882` passed after IH/JBDC were held for remote TLS/availability instability
- GBDC/GNDC promoted to `active_v2` after supply-scope filtering; controlled activation workflow `29355931391` passed

## Current blockers
- no production runtime blocker; remaining unverified sources remain intentionally disabled, with IH/JBDC subject to remote TLS/availability, GMCC subject to DNS, GDCO subject to scope/access filters, and GH candidate subject to overlap policy

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
1. complete batch-01 detail/schema/Telegram gates without enabling unverified sources
2. implement the legacy/access-sensitive batch (IH, GMCC, GDCO, CBDC)
3. continue the onclick/unknown batch (CNDC, JBDC, GBDC, GNDC)
4. resolve GH sale/rental candidate overlap before any separate identity
5. follow `docs/OVERNIGHT_PLAN.md` and `.agent/queue/tasks.json` for unattended source-family batches

## Phase marker
- current: `PHASE-3-V1-FROZEN`
- next: `PHASE-4-EXTEND-SOURCES`
- resume pointer: `config/source_registry.json`, then `src/build_master_crawler_wonjin/main.py`

## Deliverable proof
- latest artifact path(s): `src/build_master_crawler_wonjin/main.py`, `.github/workflows/hourly_notices.yml`, `.github/workflows/schedule_watchdog.yml`, `docs/V1_FREEZE.md`, `docs/SOURCE_FREEZE.md`, `STATUS.md`
- proof timestamp: 2026-07-14
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
