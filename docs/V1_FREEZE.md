# V1 FREEZE (2026-05-16)

## Scope
- Sources: `LH`, `i-SH`, `GH`
- Schedule: every hour at `:00` (`cron: 0 * * * *`)
- Output channels:
  - Google Sheet vault (archive + index + run log)
  - Telegram dual-message alert

## Google Sheet (Production Vault)
- Spreadsheet URL: `https://docs.google.com/spreadsheets/d/1sZ9vSfGk9-FIjPTS_Khv7ESBIczlfWjhKpHOFqeQ8n8/edit`
- Required tabs:
  - `scheduler_run_logs`
  - `overall`
  - `LH`
  - `iSH`
  - `GH`
  - `GUIDE`

## Identity And New-Set Evaluation (Frozen Rule)
- Raw-coupled identity:
  - key: `(source, raw_id_value)`
  - no prefix stripping (ex. `BN-` kept)
  - no integer cast for identity
- Source raw id mapping:
  - `LH`: `panId`
  - `i-SH`: `seq`
  - `GH`: `annSeq`
- Normalized helper:
  - `id_sort_num` is for ordering only
  - never used for new-set judgment

## NEWSET EVAL LOGIC (Frozen)
1. Crawl current run records from all sources.
2. Append full current run rows to source archive tabs (`LH`, `iSH`, `GH`).
3. Load existing keys from `overall` and each source tab.
4. Compare current run keys against existing key set.
5. Append only unseen rows to `overall`.
6. Append run metrics to `scheduler_run_logs`.
7. Send Telegram:
   - 1st message: run briefing (always sent, even when 0 new)
   - 2nd message: per-source new summary + board links + latest 5 each

## Credential Contract (No Secret In Git)
- Never commit raw secrets or token values.
- Required GitHub Actions secrets:
  - `GDRIVE_CREDS` (service account JSON string)
  - `GOOGLE_SHEET_ID`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- Optional GitHub Actions variables:
  - `GOOGLE_SHEET_INDEX_TAB` (default: `overall`)
  - `GOOGLE_SHEET_RUNLOG_TAB` (default: `scheduler_run_logs`)
  - `GOOGLE_SHEET_TAB_LH` (default: `LH`)
  - `GOOGLE_SHEET_TAB_ISH` (default: `iSH`)
  - `GOOGLE_SHEET_TAB_GH` (default: `GH`)

## Notes
- Backward compatibility guard is implemented for old shifted rows during key load.
- GUIDE tab in sheet contains onboarding explanation for normalization and new-set logic.
