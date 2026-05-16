# Repo AGENTS

> Scope: repository-local rules  
> Global policy: `~/.codex/AGENTS.md`  
> Human master guide: `~/agent-coding/agent-system/A2-workspace-memory/Guide.md`  
> Structure reference: `~/agent-coding/agent-system/A2-workspace-memory/Structure.md`

## Repository
- current repo: `build_master_crawler_wonjin`
- workspace path: `~/agent-coding/agent-projects/A4-worker-repos/build_master_crawler_wonjin`
- standardized project name: `build_master_crawler_wonjin`

## Objective
Bootstrap a new crawling project scaffold in the A4 worker layer

## Usage rules
1. Follow the global rules in `~/.codex/AGENTS.md`.
2. Read A2 workspace-memory docs when project-wide context, naming, workflow, status, or decision history is needed.
3. Keep this file focused on repository-specific rules only.
4. Update this file only when repository-local behavior changes.
5. If required capability is missing, identify the likely MCP or tool, explain why it is needed, and ask before installation or activation.
6. For new repos, treat `~/agent-coding/agent-system/A1-system-governance/docs/TARGET_OS/` as the target-OS governance baseline.
7. In owner-approved proactive mode, propose needed MCPs/tools/packages immediately and install right after explicit approval, then continue execution without delay.

## Repository-specific rules
- preferred approach:
  - define after project scoping
- constraints:
  - define after project scoping
- local expectations:
  - keep repository-local execution reproducible
  - keep repository-local docs aligned with reality
  - keep `.agent/` readable for owners and useful for runtime handoff
  - keep `.agent/approvals/POLICY.md` aligned with actual approval behavior

## Key files
- `README.md`
- `ENTRY.md`
- `AGENTS.md`
- `STATUS.md`
- `.agent/README.md`
- `.agent/approvals/POLICY.md`

## Vault update triggers
Update the relevant A2 document when:
- project status changes
- a reusable workflow emerges
- a major architecture decision is made
- a new MCP or tool meaningfully changes the workflow

## MCP tracking
- Do not assume MCP installation is desired just because a capability is missing.
- If this repo adopts or depends on an MCP, update `~/agent-coding/agent-system/A2-workspace-memory/MCPs.md`.
- Update `STATUS.md` when MCP dependency or capability status changes.
- Update this file when MCP adoption changes repository-local behavior.
