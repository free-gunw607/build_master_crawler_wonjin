# Overnight Execution Plan

## Objective

Move every source through the same controlled path:

`registry -> adapter -> parser smoke -> detail smoke -> normalized Notice -> dedup -> Sheets schema -> Telegram render -> production approval -> enabled`

No source is enabled merely because its list page can be crawled.

## Operating rules

- Continue normal repo-local work without interactive questions.
- Keep existing LH/i-SH/GH production behavior stable.
- Add Sheets tabs only for sources with `enabled=true` and `production_approved=true`.
- Keep pilot sources dry-run-only until all gates pass.
- Use the existing 17-column source archive table shape for every source tab.
- Use the existing `overall` and `scheduler_run_logs` structures; extend runlog source counters only through the common source map.
- Keep raw-coupled identity `(source, raw_id_value)` for every source.
- Never send Telegram during parser or schema smoke tests.
- Telegram notifier must escape HTML, chunk under API limits, retry 429 responses, and fail visibly on rejected/missing credentials.

## Execution phases

### Phase 1 — Common onboarding foundation

- Load source selection from `config/source_registry.json`.
- Use one `Notice` contract and one Sheets sync path.
- Require an explicit boolean `production_approved` value for every registry entry; absence is invalid.
- Dynamically create source tabs only for active approved sources.
- Dynamically include source counters in `scheduler_run_logs`.
- Dynamically include source labels and board links in Telegram rendering.
- Enforce `production_approved=true` before an enabled source can run.

### Phase 2 — First new production candidates

- BMC: server-rendered href adapter, board-scope collection.
- UMCA: server-rendered onclick/dataId adapter, board-scope collection.
- Run parser fixtures, current-page dry-run, detail URL smoke, duplicate checks, and workbook schema checks.
- Prepare but do not enable until production gate evidence is complete.

### Phase 3 — Remaining source families

Process in small batches, never all at once:

1. DUDC, DCCO, SCTC, JNDC — server query/href boards
2. IH, GMCC, GDCO, CBDC — legacy or access-sensitive boards
3. CNDC, JBDC, GBDC, GNDC — onclick/unknown boards requiring dedicated inspection
4. GH sale/rental candidate — resolve overlap with existing GH before any adapter work

Each source gets its own registry status, fixture/smoke evidence, and activation decision.

### Phase 4 — Production activation

- Add source tab only when the source passes all gates.
- Keep the tab schema identical to existing source tabs.
- Run a controlled production dispatch with Telegram/Sheets writes.
- Verify row insertion, `overall` dedup, runlog counts, and Telegram links.
- Only then set `enabled=true` and `production_approved=true`.

## Current checkpoint

- Common registry-driven selection: implemented locally.
- BMC/UMCA adapters: implemented and dry-run validated.
- DUDC/DCCO/SCTC/JNDC adapters: implemented and current-page dry-run validated; production gates still pending.
- BMC/UMCA Sheets/Telegram common wiring: production-verified successfully in workflow runs `29280240103` and regression run `29302647947` (latest commit `7d82e8d`).
- Existing production sources: remain enabled and approved.
- DUDC/DCCO/SCTC/JNDC: dry-run, normalized/dedup/detail/schema/Telegram gates passed and controlled production activation succeeded in workflow `29302911754`.
- CBDC/CNDC: source-specific detail/scope gates passed and controlled production activation succeeded in workflow `29303970882`.
- GBDC/GNDC: supply-scope category/title filters passed and controlled production activation succeeded in workflow `29355931391`.
- Batch-02 progress: IH, GDCO, CBDC list adapters are implemented with legacy/div-board fallback parsing; GMCC adapter handles the live board with a certificate-tolerant session and remains disabled pending detail/security review.
- Batch-03 progress: CNDC/JBDC onclick adapters and GBDC/GNDC JSON-board adapters are implemented and live-smoked; GH sale/rental candidate adapter is implemented, with 4 exact title overlaps found against active GH in the sampled window. All remain disabled pending detail/schema/overlap gates.
- Common gate evidence: implemented sources passed normalized-field and source-local dedup checks; sample detail requests returned HTTP 200 for the live-smoked sources. CBDC has no records since 2026-01-01 but returned 30 records in a 2025 range. GMCC remains subject to transient DNS/remote-access checks.
- Next automatic task: stabilize IH/JBDC remote TLS/availability and finish GMCC/GDCO scope/access gates; overlap-ambiguous GH candidate remains disabled.

## Handoff evidence

- registry: `config/source_registry.json`
- onboarding policy: `docs/SOURCE_REGISTRY.md`
- runtime: `src/build_master_crawler_wonjin/main.py`
- parser smoke: `tests/test_pilot_parsers.py`
- queue: `.agent/queue/tasks.json`
