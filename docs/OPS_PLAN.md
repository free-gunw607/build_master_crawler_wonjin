# OPS PLAN

## Goal
- Run crawler every hour on the hour in GitHub Actions.
- Collect only new notices since last collected state.
- Save canonical records to Google Sheets (vault).
- Send only new records to Telegram.
- Keep source onboarding extensible for future additions.

## Current Sources
- LH: `https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1062`
- i-SH: `https://www.i-sh.co.kr/app/lay2/program/S48T561C564/www/brd/m_255/list.do`
- GH: `https://buy.gh.or.kr/land/svc/announce/land_announce_list.jsp?MenuId=SVC_ANN`

## Scheduler
- GitHub Actions cron: `0 * * * *` (UTC 기준, 매시 정각).
- Note: GitHub cron can be delayed by a few minutes under load.

## Incremental Collection Strategy
- Primary key: `(source, notice_id)`.
- Fallback key: `(source, title, posted_at)`.
- Per run flow:
1. Crawl list pages per source.
2. Normalize records.
3. Load existing keys from Google Sheets.
4. Filter to new keys only.
5. Append new rows to Sheets.
6. Send Telegram summary + item links for new rows only.

## Time Range Policy
- Operational default: rolling 90 days window for list collection.
- Initial backfill: 2 years (one-time job, separate workflow/manual trigger).
- Safety rule: if source does not support strict date filter, crawl first N pages and rely on key-based dedup.

## Google Sheets Vault Design
- Sheet `notices_raw`:
  - `source`
  - `notice_id`
  - `title`
  - `posted_at`
  - `deadline_at`
  - `status`
  - `detail_url`
  - `attachments_json`
  - `collected_at_utc`
  - `record_hash`
- Optional sheet `run_logs`:
  - `run_at_utc`, `source`, `fetched_count`, `new_count`, `error_count`, `duration_ms`

## Telegram Delivery
- Send message only if `new_count > 0`.
- Message format:
  - header: run timestamp + source summary
  - body: new notices list (title + posted date + link)
- If no new items:
  - either skip send (default) or send heartbeat once daily.

## Feasibility Evaluation
- Feasible: Yes.
- Why feasible:
  - all three sources expose server-rendered list rows and deterministic detail identifiers (`panId`, `seq`, `annSeq`).
  - dedup via Sheets keyset is straightforward.
  - hourly GitHub scheduler + Telegram + Sheets is standard architecture.
- Main risks:
  - source HTML structure changes.
  - transient blocking/rate-limits.
  - GitHub cron jitter.
- Mitigations:
  - parser fallback selectors
  - retry with backoff
  - idempotent dedup before append/send

## Required Secrets
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SHEET_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Next Implementation Unit
1. create source adapters (`lh`, `ish`, `gh`)
2. create normalizer + deduper
3. create Sheets client
4. create Telegram notifier
5. wire GitHub Actions hourly workflow
