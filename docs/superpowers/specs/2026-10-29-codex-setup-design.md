# Undex Codex setup design

Status: approved by the user on 2026-10-29; implemented and reviewed. Live fresh-host provisioning and account authorization remain to be validated.

## Intent

Make the user's Codex preferences reproducible on Ubuntu/Linux through one
installer entry command. Keep the implementation modular, and provide a README
for authentication, optional features, and repository-specific setup.

This is a personal setup bundle, not a backup of this server's Codex state.

## Agreed approach

The user chose one entry command backed by separate modules for tool installation,
Codex configuration, plugins, and repository setup. A separate Graphify command
will configure whichever repository the user runs it in.

The alternative considered was one self-contained installer script. It is easier
to copy, but harder to maintain and rerun selectively as the setup grows.

## Confirmed preferences

| Component | Installation and behavior |
| --- | --- |
| Platform | Ubuntu/Linux only; no macOS support in the first version. |
| Node.js | Use nvm; install the latest LTS release on a fresh setup. |
| Codex | Install globally with `npm i -g @openai/codex`. |
| Codex login | Check authentication; launch device authorization when needed. |
| RTK | Install with `curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh \| sh`, then run `rtk init -g --codex`. The backslash in this table escapes the Markdown separator; the shell command uses an ordinary pipe. |
| Superpowers | Install automatically as the Codex marketplace plugin, equivalent to the user's previous browser installation. |
| Context7 | Run `npx ctx7 setup --codex --mcp`; complete authentication as needed. Do not also install the Context7 plugin or duplicate its skill. |
| Playwright CLI | Install with `npm install -g @playwright/cli@latest`. |
| Playwright skill | Run `playwright-cli install --skills=agents --global`. There is no Codex-specific installation flag. |
| Playwright browser | Include Chrome/Chromium and missing Linux dependencies; system dependencies may require sudo. |
| uv | Reuse if present; otherwise use its official installer. |
| Graphify | Install through uv. Provide a separate command for per-repository graph generation and local MCP setup. |
| Agent roles | Preserve all ten current role files, model assignments, reasoning settings, and instructions exactly. |
| Global instructions | Preserve personal routing/workflow rules, adapt the RTK reference to the destination machine, and let Context7 setup own its instruction block. |
| Default model | `gpt-6.1-sol`, reasoning `medium`. |
| Subagents | Enabled; fallback `gpt-6.1-sol` / `medium`; concurrency setting `3`. |
| Approval policy | `never`. |
| Sandbox | `danger-full-access`. |
| GitHub plugin | Install by default. Account connection remains personal. |
| Other plugins | Offer interactive selection, with none selected by default. |
| Work Pets | Excluded from the installer and end-user README. |
| Versions | Latest stable tool/plugin releases on fresh installation. |
| Reruns | Keep installed tool versions unless an update is explicitly requested; still apply this repository's configuration changes. |
| Existing configuration | Back up before changes, merge owned preferences, and preserve unrelated settings. |

Optional plugin choices are Gmail, Google Calendar, Google Contacts, Google Drive,
OpenAI Templates, Pages, Sites, and Plugin Management. Authentication and service
permissions cannot be supplied by this repository.

## Installer responsibilities

1. Detect the supported environment and available dependencies.
2. Install missing prerequisites and tools using the methods above.
3. Apply the versioned personal configuration and agent role files with backups.
4. Configure RTK and Context7 using their supported setup commands, preserving
   the personal instructions alongside the integration-owned sections.
5. Check Codex authentication and offer its device authorization flow when needed.
6. Install default plugins and selected optional plugins through supported Codex
   commands, after any required account setup.
7. Install the browser components needed for Playwright on this platform.
8. Verify the resulting installation and print completed, failed, and pending
   personal setup steps, including a reminder to start a fresh Codex session.

The actual order may change to respect prerequisites, login requirements, and
upstream behavior. Installation must not report success for a skipped or failed
component. A failed optional connection should be reported separately from core
installation results.

The installer must work from a fresh machine and on reruns. It must not silently
upgrade an existing tool merely because an upstream setup command downloads a
newer release. Existing nvm-managed installations and the active Node environment
need explicit detection so reruns do not appear to lose global npm tools.

## Configuration ownership

Store reviewed, portable preferences in the repository instead of copying the
whole live `config.toml`. Merge TOML and JSON structurally. Preserve unrelated
configuration, including existing MCP servers, plugins, hooks, and project entries.

Do not copy this server's trusted-project entries, username, absolute repository
paths, hook trust hashes, authentication files, tokens, API keys, plugin caches,
session history, memories, logs, databases, or worktrees. Honor the destination's
Codex home where supported by the tools; document upstream fixed-path limitations.

RTK and Context7 maintain their own integration content. Avoid duplicate instruction
blocks, hooks, skills, or servers on repeated installation. Credentials obtained
through their setup flows stay on the destination machine.

The ten role files are browser_tester, code_explorer, debugger, docs_researcher,
reviewer, scoped_fix, security_reviewer, test_engineer, triage, and ui_engineer.
The current ui_engineer instructions reference Impeccable, which was not found
installed. Preserve that reference as requested; do not silently add Impeccable.

## Graphify repository helper

Install the tools globally, but do not write a global MCP server targeting a
particular repository. The helper must determine the selected repository, generate
its graph through the supported Graphify workflow, and merge its MCP configuration
into that repository's `.codex/config.toml` with backup protection.

Resolve paths on the destination machine. Do not carry over the accidental
repository target from this server. Do not remove or change the existing server's global
configuration as a side effect of developing this repository.

The helper should detect an existing graph/configuration and avoid destroying
unrelated project settings. Any upstream credential, model, or indexing-cost
requirements must be established from current documentation and explained before
the helper invokes work that needs them.

## README responsibilities

Explain the entry command, supported Linux environments, installed components,
defaults, optional plugin selection, rerun/update behavior, backup locations,
and how to recover configuration from backups.

Document Codex device login, Context7 authorization, GitHub and Google service
connections, any plugin availability limitations, RTK hook trust if prompted,
browser dependency privileges, and Graphify repository setup. Explain the selected
approval/sandbox defaults without adding a new confirmation flow.

Separate an installed plugin from a connected account. Retain browser installation
instructions as a fallback if a marketplace item cannot be installed through the
CLI on the supported Codex version.

## Verification and acceptance

- Exercise configuration merging and reruns in temporary homes with fixtures;
  check that unrelated values survive, owned values apply, and backups are usable.
- Verify repeated runs do not duplicate integration blocks or upgrade existing
  tools without an explicit update request.
- Check CLI syntax and use command doubles for installation/authentication paths
  so routine tests do not mutate the user's global setup or contact accounts.
- Verify the Graphify helper writes only the selected repository's configuration
  and uses that repository's graph path.
- Test failures and pending personal steps so the completion report is truthful.
- Run appropriate shell/script checks and report their actual results.
- Validate any real installation in an isolated disposable environment when
  available; distinguish it from simulated command execution in the report.

## Builder decisions

Choose file layout, implementation language(s), configuration merge tooling,
flags, backup naming, terminal selection UI, and how modules are invoked. Prefer
supported upstream installers and avoid unnecessary dependencies.

Verify current official installation commands for nvm, uv, Graphify, browser
provisioning, and plugins before implementation. Select Chrome or Chromium based
on supported Playwright CLI behavior; the user approved either. The exact tested
Ubuntu releases and behavior on other Linux distributions must be stated honestly
in the README rather than promising unverified compatibility.

The user approved this design and its implementation plan. Inline implementation
and review are complete; see the plan execution notes and README for verification
evidence and limits.
