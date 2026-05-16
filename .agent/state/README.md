# Runtime State

Use this folder for lightweight state snapshots and resumable metadata for `build_master_crawler`.

Examples:
- latest successful checkpoint
- normalized progress marker
- cached runtime metadata needed to resume safely
- `project_state.json`
- `execution_lease.json`
- `auth_family_lease.json`
- `compliance_state.json`
- `write_session.json`

Keep this folder small, explicit, and easy for an owner to inspect.
