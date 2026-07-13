const OWNER = "free-gunw607";
const REPO = "build_master_crawler_wonjin";
const WORKFLOW_FILE = "hourly_notices.yml";
const WORKFLOW_DISPATCH_URL =
  `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`;
const RUNS_URL =
  `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=6`;

const TIMEZONE = "Asia/Seoul";
const EXPECTED_MINUTE_UTC = 7;
const GRACE_MINUTES = 18;
const RECOVERY_COOLDOWN_MINUTES = 45;
const SHEET_PREVIEW_TABS = ["overall", "LH", "iSH", "GH", "scheduler_run_logs"];

function checkHourlyCrawler() {
  const props = PropertiesService.getScriptProperties();
  const token = mustGet_(props, "GITHUB_PAT");
  const branch = props.getProperty("GITHUB_DEFAULT_BRANCH") || "main";
  const telegramToken = props.getProperty("TELEGRAM_BOT_TOKEN") || "";
  const telegramChatId = props.getProperty("TELEGRAM_CHAT_ID") || "";

  const runs = listRuns_(token);
  const latest = runs[0];
  if (!latest) {
    notify_(
      telegramToken,
      telegramChatId,
      "[watchdog] 최근 workflow run 이력이 없어 recovery dispatch를 시도합니다."
    );
    dispatchRecovery_(token, branch, "missing_run_history");
    return;
  }

  const now = new Date();
  const currentHourUtc = Utilities.formatDate(now, "Etc/UTC", "yyyy-MM-dd'T'HH");
  const currentMinuteUtc = Number(Utilities.formatDate(now, "Etc/UTC", "m"));
  const latestCreated = new Date(latest.created_at);
  const latestHourUtc = Utilities.formatDate(latestCreated, "Etc/UTC", "yyyy-MM-dd'T'HH");
  const ageMinutes = Math.floor((now.getTime() - latestCreated.getTime()) / 60000);

  const missingThisHour =
    latestHourUtc !== currentHourUtc && currentMinuteUtc >= EXPECTED_MINUTE_UTC + GRACE_MINUTES;
  const stale = ageMinutes > 90;
  if (!missingThisHour && !stale) {
    return;
  }

  const lastRecoveryEpoch = Number(props.getProperty("LAST_RECOVERY_EPOCH_MS") || "0");
  const coolingDown = now.getTime() - lastRecoveryEpoch < RECOVERY_COOLDOWN_MINUTES * 60000;
  const reason = missingThisHour ? "missing_current_hour" : "stale";
  const latestSummary =
    `last_created=${latest.created_at}, conclusion=${latest.conclusion || "unknown"}, age=${ageMinutes}m`;

  if (coolingDown) {
    notify_(
      telegramToken,
      telegramChatId,
      `[watchdog] recovery cooldown 중입니다. ${latestSummary}`
    );
    return;
  }

  dispatchRecovery_(token, branch, reason);
  props.setProperty("LAST_RECOVERY_EPOCH_MS", String(now.getTime()));
  notify_(
    telegramToken,
    telegramChatId,
    `[watchdog] hourly_notices recovery dispatch 실행. reason=${reason}, ${latestSummary}`
  );
}

function manualRecoveryNow() {
  const props = PropertiesService.getScriptProperties();
  const token = mustGet_(props, "GITHUB_PAT");
  const branch = props.getProperty("GITHUB_DEFAULT_BRANCH") || "main";
  const telegramToken = props.getProperty("TELEGRAM_BOT_TOKEN") || "";
  const telegramChatId = props.getProperty("TELEGRAM_CHAT_ID") || "";

  dispatchRecovery_(token, branch, "manual");
  props.setProperty("LAST_RECOVERY_EPOCH_MS", String(Date.now()));
  notify_(
    telegramToken,
    telegramChatId,
    "[watchdog] manualRecoveryNow()로 hourly_notices recovery dispatch 실행"
  );
}

function testConfiguration() {
  const props = PropertiesService.getScriptProperties();
  const token = mustGet_(props, "GITHUB_PAT");
  const runs = listRuns_(token);
  Logger.log({
    ok: true,
    latest_run_created_at: runs[0] ? runs[0].created_at : null,
    latest_run_conclusion: runs[0] ? runs[0].conclusion : null,
    run_count_sample: runs.length,
  });
}

function previewSheetsHeadTail() {
  const props = PropertiesService.getScriptProperties();
  const sheetId = mustGet_(props, "GOOGLE_SHEET_ID");
  const ss = SpreadsheetApp.openById(sheetId);
  const summary = {};

  SHEET_PREVIEW_TABS.forEach((tab) => {
    const ws = ss.getSheetByName(tab);
    if (!ws) {
      summary[tab] = { exists: false };
      return;
    }
    const lastRow = ws.getLastRow();
    const lastCol = ws.getLastColumn();
    if (lastRow === 0 || lastCol === 0) {
      summary[tab] = { exists: true, rows: 0, cols: 0, head: [], tail: [] };
      return;
    }

    const values = ws.getRange(1, 1, lastRow, lastCol).getDisplayValues();
    const header = values[0];
    const body = values.slice(1);
    const head = body.slice(0, 5);
    const tail = body.slice(Math.max(0, body.length - 5));

    summary[tab] = {
      exists: true,
      rows_including_header: lastRow,
      body_rows: body.length,
      cols: lastCol,
      header: header,
      head: head,
      tail: tail,
    };
  });

  Logger.log(JSON.stringify(summary, null, 2));
  return summary;
}

function listRuns_(token) {
  const resp = githubFetch_(RUNS_URL, token, { method: "get" });
  const data = JSON.parse(resp.getContentText());
  return data.workflow_runs || [];
}

function dispatchRecovery_(token, branch, reason) {
  const payload = {
    ref: branch,
    inputs: {
      dry_run: "false",
      from_date: "",
    },
  };
  githubFetch_(WORKFLOW_DISPATCH_URL, token, {
    method: "post",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
  Logger.log({
    dispatched: true,
    reason: reason,
    ref: branch,
    workflow: WORKFLOW_FILE,
  });
}

function githubFetch_(url, token, options) {
  const resp = UrlFetchApp.fetch(
    url,
    Object.assign(
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
        },
      },
      options || {}
    )
  );
  const code = resp.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error(`GitHub API failed: ${code} ${resp.getContentText()}`);
  }
  return resp;
}

function notify_(telegramToken, telegramChatId, text) {
  if (!telegramToken || !telegramChatId) {
    return;
  }
  UrlFetchApp.fetch(`https://api.telegram.org/bot${telegramToken}/sendMessage`, {
    method: "post",
    payload: {
      chat_id: telegramChatId,
      text: `[${timestampKst_()}]\n${text}`,
    },
    muteHttpExceptions: true,
  });
}

function timestampKst_() {
  return Utilities.formatDate(new Date(), TIMEZONE, "yyyy-MM-dd HH:mm:ss");
}

function mustGet_(props, key) {
  const value = props.getProperty(key);
  if (!value) {
    throw new Error(`Missing Script Property: ${key}`);
  }
  return value;
}
