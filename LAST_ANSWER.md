# LAST ANSWER

## Current state
- repo scaffold created
- durable handoff convention is active
- repo-local objective should be summarized here as work advances

## Default operating behavior
- proceed autonomously in normal repo-local work
- minimize interruptions
- reserve approval requests for important trust, scope, authentication, privacy-sensitive, remote-side-effect, or destructive boundaries

## Phase status
- current phase: record exact phase id
- next phase: record immediate next phase id
- resume pointer: record first file/command to restart without warm-up

## Deliverable proof
- artifact path(s): record concrete path(s) produced in this cycle
- proof timestamp: record verification time
- completion rule: if no artifact path exists, treat as not completed

## Durable handoff path
- repo root `LAST_ANSWER.md` is the current summary
- `.agent/answers/` stores archived timestamped copies
- `.agent/state/project_state.json` stores machine-readable current state
- `.agent/logs/` and `.agent/bundles/` hold deeper runtime evidence
