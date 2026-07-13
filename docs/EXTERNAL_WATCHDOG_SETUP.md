# External Watchdog Setup

## Goal
- keep recovery trigger alive even when GitHub `schedule` misses runs
- avoid VPS cost
- avoid requiring a 24/7 local PC

## What This Uses
- Google Apps Script time trigger
- GitHub API
- optional Telegram alert

## Alternative (No Apps Script UI)
- Use `ops/external_watchdog_runner.py` on any external cron host (Cloud Run job, VM cron, GitHub-hosted self scheduler, etc.)
- This avoids script.google.com manual operation once env vars are set

## Files
- script source: `ops/google_apps_script_watchdog.js`
- target workflow: `.github/workflows/hourly_notices.yml`

## One-Time Setup
1. Open `https://script.google.com/`
2. Create a new Apps Script project
3. Replace the default file contents with `ops/google_apps_script_watchdog.js`
4. Save the project
5. In Apps Script:
   - `Project Settings`
   - `Script Properties`
   - add:
     - `GITHUB_PAT`
     - `GITHUB_DEFAULT_BRANCH=main`
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHAT_ID`
     - `GOOGLE_SHEET_ID` (for `previewSheetsHeadTail()`)
6. Create a GitHub classic PAT with scopes:
   - `repo`
   - `workflow`
7. Put that PAT into `GITHUB_PAT`

## First Validation
1. In the Apps Script editor, run `testConfiguration()`
2. Approve permissions when prompted
3. Confirm the execution log shows the latest run metadata
4. Run `previewSheetsHeadTail()`
5. Confirm logs include each tab's `header`, `head` (first 5 body rows), `tail` (last 5 body rows)

## Manual Recovery Button
- In the Apps Script function dropdown, select `manualRecoveryNow`
- Click `Run`
- This sends an immediate `workflow_dispatch` to `hourly_notices.yml`
- Use this when the hourly job is clearly missing and you want to wake it manually

## Automatic Watchdog Trigger
1. Open `Triggers`
2. Add trigger
3. Choose function: `checkHourlyCrawler`
4. Event source: `Time-driven`
5. Type: `Minutes timer`
6. Interval: `Every 10 minutes`

## Expected Behavior
- normal case:
  - no message
  - no dispatch
- missing current hour run:
  - Telegram alert
  - `workflow_dispatch` recovery run
- repeated checks shortly after recovery:
  - cooldown suppresses duplicate dispatches

## Operational Notes
- GitHub workflow cron is currently `7 * * * *` UTC
- watchdog grace is `18` minutes after expected minute
- recovery cooldown is `45` minutes
- these values can be adjusted in `ops/google_apps_script_watchdog.js`

The GitHub-native schedule watchdog also skips duplicate recovery dispatches for 45 minutes after a recent `workflow_dispatch` run. This prevents a failed recovery run from causing a new dispatch every 15 minutes while the root failure is being investigated.

## Failure Cases
- `GitHub API failed: 401`
  - PAT is wrong or expired
- `Missing Script Property`
  - required property is absent
- no Telegram message
  - Telegram fields are empty or invalid

## Recommended Owner Routine
1. Run `testConfiguration()` once after any token change
2. Keep `manualRecoveryNow()` available for one-click recovery
3. If GitHub schedules drift again, use manual recovery first, then inspect recent run history

## External Cron Runner (Fully Scriptable)
Run every 10 minutes:

```bash
export WATCHDOG_GITHUB_OWNER=free-gunw607
export WATCHDOG_GITHUB_REPO=build_master_crawler_wonjin
export WATCHDOG_WORKFLOW_FILE=hourly_notices.yml
export WATCHDOG_BRANCH=main
export WATCHDOG_GITHUB_PAT=... # scope: repo, workflow
python3 ops/external_watchdog_runner.py
```

Behavior:
- checks latest `schedule` run age
- triggers `workflow_dispatch` when missing/stale
- applies local cooldown state (`.watchdog_state.json`)
