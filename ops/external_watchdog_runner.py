from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class Config:
    owner: str
    repo: str
    workflow_file: str
    github_pat: str
    branch: str
    expected_minute_utc: int
    grace_minutes: int
    stale_minutes: int
    cooldown_minutes: int
    state_file: str


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def load_config() -> Config:
    owner = os.environ["WATCHDOG_GITHUB_OWNER"].strip()
    repo = os.environ["WATCHDOG_GITHUB_REPO"].strip()
    workflow_file = os.environ.get("WATCHDOG_WORKFLOW_FILE", "hourly_notices.yml").strip()
    github_pat = os.environ["WATCHDOG_GITHUB_PAT"].strip()
    branch = os.environ.get("WATCHDOG_BRANCH", "main").strip()
    return Config(
        owner=owner,
        repo=repo,
        workflow_file=workflow_file,
        github_pat=github_pat,
        branch=branch,
        expected_minute_utc=_env_int("WATCHDOG_EXPECTED_MINUTE_UTC", 7),
        grace_minutes=_env_int("WATCHDOG_GRACE_MINUTES", 18),
        stale_minutes=_env_int("WATCHDOG_STALE_MINUTES", 90),
        cooldown_minutes=_env_int("WATCHDOG_COOLDOWN_MINUTES", 45),
        state_file=os.environ.get("WATCHDOG_STATE_FILE", ".watchdog_state.json").strip(),
    )


def gh_request(config: Config, method: str, path: str, payload: dict | None = None) -> dict:
    url = f"https://api.github.com{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {config.github_pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url=url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8") or "{}"
            return json.loads(body)
    except HTTPError as e:
        text = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API failed: {e.code} {text}") from e
    except URLError as e:
        raise RuntimeError(f"GitHub API network error: {e}") from e


def read_state(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_state(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def dispatch_recovery(config: Config, reason: str) -> None:
    gh_request(
        config,
        "POST",
        f"/repos/{config.owner}/{config.repo}/actions/workflows/{config.workflow_file}/dispatches",
        {"ref": config.branch, "inputs": {"dry_run": "false", "from_date": ""}},
    )
    print(f"dispatch=ok reason={reason}")


def main() -> None:
    config = load_config()
    now = datetime.now(UTC)
    runs = gh_request(
        config,
        "GET",
        f"/repos/{config.owner}/{config.repo}/actions/workflows/{config.workflow_file}/runs?event=schedule&per_page=1",
    ).get("workflow_runs", [])

    if not runs:
        dispatch_recovery(config, "missing_run_history")
        return

    latest = runs[0]
    latest_created = datetime.strptime(latest["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    age_minutes = int((now - latest_created).total_seconds() // 60)
    missing_this_hour = (
        latest_created.strftime("%Y-%m-%dT%H") != now.strftime("%Y-%m-%dT%H")
        and now.minute >= config.expected_minute_utc + config.grace_minutes
    )
    stale = age_minutes > config.stale_minutes
    if not missing_this_hour and not stale:
        print(f"status=ok latest_created={latest['created_at']} age_minutes={age_minutes}")
        return

    state = read_state(config.state_file)
    last_recovery = state.get("last_recovery_utc", "")
    if last_recovery:
        try:
            last_recovery_dt = datetime.strptime(last_recovery, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            if now - last_recovery_dt < timedelta(minutes=config.cooldown_minutes):
                print(
                    "status=cooldown "
                    f"latest_created={latest['created_at']} age_minutes={age_minutes} "
                    f"last_recovery_utc={last_recovery}"
                )
                return
        except ValueError:
            pass

    reason = "missing_current_hour" if missing_this_hour else "stale"
    dispatch_recovery(config, reason)
    write_state(config.state_file, {"last_recovery_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "reason": reason})


if __name__ == "__main__":
    main()
