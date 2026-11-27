# Changelog

## 0.2.0 — 2026-11-27 (preview)

- Replace `undex-graphify` with `undex-project-setup` for code-only Graphify
  extraction, project MCP registration, and a project pstack workflow instruction.

- Adopt pstack from `michael-denyer/pstack-claude` as the default workflow plugin.
- Use pstack for delegated model routing and leave the main model to Codex.
- Migrate older Undex installs by backing up and retiring stock routing profiles
  and replacing the curated Superpowers plugin after pstack is enabled.

## 0.1.1 — 2026-11-18 (preview)

- Upgrade the main agent and subagent fallback to GPT-6.2 Sol at medium reasoning.
- Upgrade debugger, reviewer, and UI engineer to GPT-6.2 Sol, preserving reasoning levels.
- Use GPT-6.2 Astra at high reasoning for consequential security reviews.
- Retain Luna and Terra assignments for focused work and keep concurrency at three.
- Define escalation to Astra for unresolved cross-module failures and competing
  architectural constraints, and to Sol for complex integration-test work.
- Document evaluation by total usage, retries, review corrections, elapsed time,
  and verification success per accepted result.

Full fresh-host provisioning and personal account authorization remain unverified;
this release is a preview until those checks are complete. See the release notes.

## 0.1.0 — 2026-10-29

Initial personal Codex setup bundle for Ubuntu/Linux.

- Modular one-command installer using nvm, npm, uv, and official tool installers.
- Sol/medium defaults, ten preserved agent roles, routing policy, and RTK integration.
- Context7 MCP setup, Playwright CLI/skill, and Chrome dependency provisioning.
- Default Superpowers/GitHub plugins and optional Google/productivity plugins.
- Private configuration backups, structural merges, and version-preserving reruns.
- Explicit updates, device login, and pending account-connection reporting.
- Separate Graphify helper with code-only indexing and repository-local MCP settings.
- MIT license and release preparation documentation.

Validation includes 44 automated tests, ShellCheck, Bash syntax checks, and real
temporary-directory RTK/Graphify smoke checks. Complete fresh-machine provisioning,
browser installation, and new-account authorization have not been live-validated.
