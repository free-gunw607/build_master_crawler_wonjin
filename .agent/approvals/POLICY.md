# Approval Policy

This repository starts with a universal autonomy policy: proceed autonomously in normal repo-local work and minimize interruptions.

## Auto-Allowed
- repo-local file edits
- docs, `STATUS.md`, and `LAST_ANSWER.md` updates
- `.agent` state, log, answer, run, queue, and bundle updates
- local non-destructive tests
- local artifact generation
- local analysis, refactoring, normalization, and documentation work
- continued work inside the already approved scope or family

## Approval-Required
- major scope changes
- branch or strategy deviations from the agreed objective
- initial login or re-login
- access to a new authenticated family outside current approved scope
- `git push`
- external uploads
- destructive actions
- trust-sensitive or privacy-sensitive actions
- individual-account or personal-information-sensitive actions
- privileged operations or commands that require escalation outside the normal sandbox
- installing or activating new MCPs, integrations, or external tools that materially change workflow or trust boundaries

## Operating Notes
- prefer durable file-based handoff over repeated terminal interruption
- use `LAST_ANSWER.md`, `.agent/answers/`, `.agent/state/project_state.json`, `.agent/logs/`, and `.agent/bundles/` as the default progress trail
- explain the blocked task and the reason clearly when approval is required
- record durable approval artifacts here when they become important to future operation
- if owner enables install-first mode, propose missing capabilities quickly, ask once, install immediately after approval, and continue
