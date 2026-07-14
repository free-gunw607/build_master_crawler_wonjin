# LAST ANSWER

## Current state
- repo scaffold created
- durable handoff convention is active
- source research for LH/i-SH/GH completed
- hourly-ops design documented for GitHub scheduler + Google Sheets vault + Telegram alerts
- first crawler implementation completed (`main.py`)
- first 1-year crawl workbook generated with source table-oriented sheets
- v1 freeze completed: normalization/new-set rules + sheet schema + dual Telegram format fixed
- production vault sheet structure finalized and GUIDE tab documented
- duplicated accumulation issue fixed in sheet sync path (`new-only append`)
- sheet insertion order changed to newest-first top insert (`row=2`) for `overall`/source tabs
- scheduler reliability hardening applied (workflow concurrency + watchdog recovery dispatch)
- external watchdog path prepared to escape GitHub schedule single-point failure
- import source list registered in `config/source_registry.json`; new sources remain disabled
- first parser pilots selected: `BMC`, `UMCA`
- `ISH_SEOUL_CANDIDATE` merged into existing `i-SH` after 59/59 raw-ID overlap review
- dry-run-only adapters and parser smoke tests added for BMC and UMCA
- overnight onboarding plan recorded in `docs/OVERNIGHT_PLAN.md`; queue now tracks source-family batches
- first source family dry-run passed for BMC, UMCA, DUDC, DCCO, SCTC, and JNDC; all remain production-disabled
- Telegram notifier hardened against HTML, size, rate-limit, API-response, and missing-secret failures
- BMC and UMCA promoted to `active_v2` and production-verified in workflow run `29280240103`; the run executed LH, i-SH, GH, BMC, UMCA and completed Sheets/Telegram sync successfully
- batch-01 current-page post-production dry-run reconfirmed DUDC 38, DCCO 6, SCTC 4, JNDC 6; these remain disabled pending detail/schema/alert gates
- all remaining registry source IDs now have adapter dispatch coverage or an explicit merged/disabled decision; non-approved sources remain blocked from production and Sheets creation
- latest production regression run `29302647947` passed on commit `7d82e8d`; enabled sources remained LH, i-SH, GH, BMC, UMCA
- DUDC/DCCO/SCTC/JNDC passed controlled activation run `29302911754` and now use the same production Sheets/Telegram contract
- CBDC/CNDC passed controlled activation run `29303970882`; IH/JBDC were held back after CI remote TLS/availability failures to protect the hourly job

## Default operating behavior
- proceed autonomously in normal repo-local work
- minimize interruptions
- reserve approval requests for important trust, scope, authentication, privacy-sensitive, remote-side-effect, or destructive boundaries

## Phase status
- current phase: `PHASE-3-V1-FROZEN`
- next phase: `PHASE-4-EXTEND-SOURCES`
- resume pointer: `config/source_registry.json`, then `src/build_master_crawler_wonjin/main.py`

## Deliverable proof
- artifact path(s):
  - `src/build_master_crawler_wonjin/main.py`
  - `.github/workflows/hourly_notices.yml`
  - `ops/google_apps_script_watchdog.js`
  - `docs/V1_FREEZE.md`
  - `docs/SOURCE_FREEZE.md`
  - `STATUS.md`
- proof timestamp: `2026-07-14`
- completion rule: credentials remain outside git and are injected via GitHub secrets/vars

## Durable handoff path
- repo root `LAST_ANSWER.md` is the current summary
- `.agent/answers/` stores archived timestamped copies
- `.agent/state/project_state.json` stores machine-readable current state
- `.agent/logs/` and `.agent/bundles/` hold deeper runtime evidence
