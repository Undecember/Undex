# Codex Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Reproduce the user's Codex tools and preferences through a modular Linux installer and a separate Graphify repository helper.

**Architecture:** Bash entry scripts coordinate focused installation modules. A small Python utility uses TOMLKit for comment-preserving structural merges, atomic file replacement, backups, and non-secret installer state. Tool installers and account setup remain upstream commands, with explicit status reporting rather than assumed success.

**Tech Stack:** Bash, uv-managed Python 3.11+, TOMLKit, Python unittest, official npm/uv tool installers, and Codex CLI.

**Spec:** [Approved design](../specs/2026-10-29-codex-setup-design.md).

## Global Constraints

- Ubuntu/Linux only; explicitly document tested Ubuntu releases and reject unsupported platforms before mutation.
- Fresh installs use latest stable tools; Node uses latest LTS through nvm.
- Reruns preserve installed versions unless `--update` is requested.
- Install GitHub and Superpowers by default; Context7 uses `npx ctx7 setup --codex --mcp`, without the separate plugin.
- Optional plugins: Gmail, Google Calendar, Google Contacts, Google Drive, OpenAI Templates, Pages, Sites, Plugin Management; none preselected.
- Exclude Work Pets from installer and end-user README.
- Preserve all ten role files exactly, including existing instructions and model assignments.
- Default model and fallback: `gpt-6.1-sol`, `medium`; agents enabled; concurrency `3`.
- Preserve `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`.
- Back up changed files; preserve unrelated configuration; never copy credentials or machine/session state.
- Install Graphify through uv; project MCP configuration must never be written globally.
- Do not run installation commands against this user's actual global environment during development.
- Execute inline; no independent implementer handoffs. Make commits at coherent task boundaries only when the execution workflow calls for them; do not push or publish.

## Review Focus

1. Custom homes, spaces, and symlinks: commands and backups resolve the intended destination without shell interpolation bugs (Tasks 1, 2, 5).
2. Invalid existing config or interrupted writes: preserve originals and avoid partial configuration (Task 1).
3. Missing TTY or failed authentication: report pending personal steps without hanging or claiming success (Task 4).
4. Existing Node/npm tools and cached setup packages: reruns preserve versions and avoid switching away from installed global tools (Tasks 2, 4).
5. Plugin/API failures and existing Graphify targets: preserve unrelated settings and report scoped failures accurately (Tasks 4, 5).

## File Map

- `install.sh`: installer entry, argument parsing, module ordering, final status.
- `bin/undex-graphify`: repository helper entry.
- `lib/common.sh`: paths, preflight, status collection, command execution helpers.
- `lib/tools.sh`: nvm/Node, uv, npm tools, RTK, Graphify installation/update logic.
- `lib/integrations.sh`: RTK, Context7, and Playwright browser/skill configuration.
- `lib/plugins.sh`: authentication and default/optional plugin management.
- `lib/configure.py`: structured merges, backups, instructions, role installation, state.
- `config/codex.toml`: owned portable preferences only.
- `config/AGENTS.md`: personal policy only, with an RTK path placeholder.
- `config/agents/*.toml`: exact copies of the ten approved role files.
- `pyproject.toml`, `uv.lock`: Python utility dependency metadata and lockfile.
- `tests/`: unittest fixtures, command doubles, shell integration tests.
- `README.md`, `.gitignore`: usage, personal steps, exclusions, verification instructions.

## Task 1: Portable Configuration and Safe Merging

**Files:** `lib/configure.py`, `config/*`, `pyproject.toml`, `uv.lock`, `tests/test_configure.py`, `.gitignore`.

**Interfaces:**

- `merge_config(path: Path, patch: dict, backup_root: Path) -> bool`: recursive TOML merge; return whether the destination changed.
- `write_managed_text(path: Path, text: str, backup_root: Path) -> bool`: back up before changed writes, then atomically replace.
- `apply_personal_config(bundle_root: Path, codex_home: Path, backup_root: Path) -> None`.
- CLI: `uv run --project "$UNDEX_ROOT" python lib/configure.py apply --codex-home PATH --backup-root PATH`.
- Shared state commands: `state-get KEY` and `state-set KEY VALUE`, stored under `${XDG_STATE_HOME:-$HOME/.local/state}/undex/state.json`; no credentials.

- [x] Write tests for recursive merges preserving unrelated MCP/plugin/project/hook values and TOML comments, exact defaults, malformed input leaving originals untouched, file permissions, same-content reruns, unique backups, and destination paths with spaces.
- [x] Run `uv run python -m unittest discover -s tests -p test_configure.py -v`; confirm failure because the utility does not yet exist.
- [x] Implement the utility, managed instruction block, and version/state helpers. Parse all affected input before starting writes; back up existing instruction, hook, and config files before upstream setup calls too.
- [x] Copy only approved roles from `~/.codex/agents`; create portable config from explicit values. Extract personal policy without copying the generated Context7 block or server credentials. Adapt the RTK reference at render time.
- [x] Add fixtures verifying role file byte equality against captured approved copies; personal instruction blocks must not duplicate or erase existing user text.
- [x] Run the Task 1 tests and verify repository files contain no secrets or server-specific repository targets in executable configuration.

## Task 2: Linux Bootstrap and Tool Installation

**Files:** `install.sh`, `lib/common.sh`, `lib/tools.sh`, `tests/test_tools.py`, shell command doubles under `tests/fixtures/`.

**Interfaces:**

- `undex_preflight`: Linux/distro/root/privilege checks before writes; install only missing required Ubuntu packages.
- `ensure_node`, `ensure_uv`, `ensure_codex`, `ensure_rtk`, `ensure_playwright`, `ensure_graphify`: Bash functions; nonzero means installation failed.
- `undex_record COMPONENT STATUS DETAIL`: status in `ok`, `pending`, or `failed`.
- Flags: `--update`, `--non-interactive`, `--help`; unknown flags fail before mutation. Noninteractive mode skips new personal auth and optional selection, and reports what remains.

- [x] Write command-double tests for fresh bootstrap, reused uv/nvm, an existing nvm default Node without an inherited PATH, a compatible system Node, unsupported OS, missing sudo, network failures, and paths containing spaces.
- [x] Run `uv run python -m unittest discover -s tests -p test_tools.py -v`; confirm failures.
- [x] Implement nvm using its official release installer, select latest LTS for fresh Node setup, and preserve an existing compatible active/default environment on ordinary reruns. Record the selected Node version so a new shell reuses the same environment.
- [x] Install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh` only when missing; load its executable path into the current script environment.
- [x] Install Codex with `npm i -g @openai/codex`, Playwright with `npm install -g @playwright/cli@latest`, RTK with the user's exact preferred upstream URL, and Graphify with `uv tool install 'graphifyy[mcp]'`. Verify minimum CLI capabilities before relying on them; an old incompatible installation requires an explicit update rather than a silent upgrade.
- [x] Implement explicit updates scoped to these tools, not all packages on the machine. For a deliberate Node update, preserve unrelated global package versions during migration.
- [x] Test that a second run invokes no tool upgrade/install operation for already usable tools. Run Task 2 tests and `bash -n` on the new shell files.

## Task 3: Integration Setup and Browser Provisioning

**Files:** `lib/integrations.sh`, `lib/configure.py`, `tests/test_integrations.py`.

**Interfaces:** `configure_rtk`, `configure_context7`, `configure_playwright`; use Task 1 backup/state helpers and Task 2 status functions.

- [x] Write tests for repeated setup, failed setup, pre-existing integrations, custom Codex home handling, Context7 credentials absent from output/state, and browser provisioning without forced reinstall.
- [x] Run the integration tests and confirm failures.
- [x] Run `rtk init -g --codex` with required backups. Check supported unattended flags before use; report required hook trust as pending rather than bypassing it.
- [x] On first Context7 setup, resolve and record the stable `ctx7` version, then invoke its setup in MCP mode. Use that recorded version on retries/reruns and refresh it only under `--update`; skip setup when the integration is already healthy. Offer an explicit `--configure-context7` retry flag.
- [x] Install/update the Playwright global agents skill with `playwright-cli install --skills=agents --global`. Provision Chrome with `playwright-cli install-browser chrome --with-deps`, using upstream checks to reuse installed browsers; choose Chrome because CLI launches can use that channel directly. Validate current browser behavior before finalizing this choice.
- [x] Preserve unrelated hooks and integration blocks. If an upstream installer cannot honor a custom home, fail that component with an actionable message rather than silently modifying a different home.
- [x] Run the integration tests; verify first run, rerun, and failed/retried setup paths.

## Task 4: Codex Authentication and Plugins

**Files:** `lib/plugins.sh`, `install.sh`, `lib/configure.py`, `tests/test_plugins.py`.

**Interfaces:** `ensure_codex_login`, `select_optional_plugins`, `install_plugins`; plugin catalog is an explicit allowlist. Persist the last selected optional set as non-secret state, without preselecting it in a new interactive selection.

- [x] Write tests for authenticated/unauthenticated states, device-login failure, no TTY, invalid selections, no optional selections, unavailable plugins, and installed plugins staying untouched on reruns.
- [x] Run plugin tests and confirm failures.
- [x] Check `codex login status`; invoke `codex login --device-auth` when authentication is missing and a TTY is available. Report login as pending in unattended mode.
- [x] Read installed plugin state using `codex plugin list --json`; parse the actual supported JSON schema. Install missing defaults with `codex plugin add superpowers@openai-curated-remote` and `codex plugin add github@openai-curated-remote`.
- [x] Offer the eight optional plugins as individually selectable numbered choices, default empty. Reuse previous choices only when explicitly requested through a documented flag or update mode; never uninstall previously installed plugins when they are omitted.
- [x] Install selected available plugins through the same CLI. Separate package installation from external account connection and show the latter as pending unless confirmed by supported status APIs. Do not infer authentication from cache presence.
- [x] Preserve unrelated plugins and avoid duplicate Context7 installation. Explicit update uses supported plugin update/reinstall behavior only for managed plugins.
- [x] Run plugin tests and test the installer summary/exit status: core failure is nonzero; pending account steps and optional failures are clearly reported with component-specific recovery commands.

## Task 5: Per-Repository Graphify Helper

**Files:** `bin/undex-graphify`, `lib/configure.py`, `tests/test_graphify.py`.

**Interfaces:** `bin/undex-graphify [PATH] [--refresh]`; default PATH is current working directory; detect repository root with `git rev-parse --show-toplevel`. Add `configure.py graphify --repo PATH --command PATH --graph PATH` for structural project TOML updates.

- [x] Write tests for invocation from a nested directory, no Git repository, spaces in paths, existing graphs, failed indexing, existing local MCP settings, and a conflicting global Graphify entry.
- [x] Run Graphify tests and confirm failures.
- [x] Resolve `graphify` and `graphify-mcp`; do not install/upgrade dependencies from this helper. Fail with the main installer command if tools are missing.
- [x] Verify `graphify update PATH --no-cluster` can create a first AST graph and that `graphify cluster-only PATH --no-label --no-viz` performs no model calls. Use this path by default; semantic indexing stays an explicitly documented advanced workflow.
- [x] Generate only when no graph exists or `--refresh` was requested. Back up an existing graph before requested refresh; never use destructive force flags automatically. Verify a valid `graphify-out/graph.json` before writing MCP configuration.
- [x] Merge `mcp_servers.graphify` into the repository's `.codex/config.toml`, pointing to the resolved executable and that repository's graph. Never edit global config or auto-trust a repository. Install a helper launcher into the user's local bin that references the retained checkout; explain this dependency in the README.
- [x] Run Graphify tests and a real AST indexing smoke test in a disposable sample repository, with model credentials removed from the subprocess environment.

## Task 6: Documentation and Whole-Installer Verification

**Files:** `README.md`, `tests/test_installer.py`, finalized plan checkboxes and spec status.

**Interfaces:** `bash install.sh` after cloning is the one-command entry; `undex-graphify` is the installed repository helper. `uv run python -m unittest discover -s tests -v` is the complete automated test command.

- [x] Add whole-installer command-double tests: fresh installation, no-op rerun, explicit update, configuration merge, partially failed install, and noninteractive pending-login behavior. Record commands so tests assert no unintended network/system/account actions.
- [x] Run these tests before integrating modules and confirm failures; wire the installer sequence and summary to pass them.
- [x] Write the README covering actual flags, default/optional components, credentials and login, Chrome dependencies/sudo, graph creation and refresh, backups/restoration, update behavior, and supported/tested distributions. Link official installation documentation and preserve manual browser plugin installation as fallback.
- [x] Explain that the ten role definitions are intentionally preserved, including the optional Impeccable reference; explain model-account availability without silently substituting models.
- [x] Run all tests, `bash -n` on all shell scripts, ShellCheck when available, and `git diff --check`. Inspect tracked/untracked content for credentials and generated artifacts.
- [x] If a disposable Ubuntu container/runtime is available, run a real tool/bootstrap smoke test there. Otherwise report that fresh-machine installation has only been simulated; do not mutate this server to obtain a stronger claim.
- [x] Request one independent final review under the applicable review skill, address evidenced issues, and rerun affected checks. Do not add per-task independent reviews.
- [x] Report implemented commands, test evidence, and any remaining live account/install validation limitations. Do not push or publish.

## Execution Notes

Implemented inline on `feat/codex-setup`. Automated verification covers configuration
merging and complete installer flows with temporary homes/command doubles. Real
Graphify AST indexing and RTK two-run initialization were checked in disposable
directories. ShellCheck and Bash syntax checks passed. Full fresh-host installation
was not attempted because this account cannot access the Docker socket.

One independent review identified Graphify transport/lock handling and inactive
nvm migration issues; each received a failing regression test and was corrected.
A separate real RTK smoke caught an unsupported generic flag combination; the
installer now uses the exact approved `rtk init -g --codex` command.

Rulings: kept work in a feature branch of the fresh checkout because there was no
initial commit for a linked worktree; selected Chrome from the approved
Chrome/Chromium alternatives; used isolated live checks plus simulations when
Docker was unavailable. RTK supports custom `CODEX_HOME`; Context7 custom-home
setup is explicitly declined rather than modifying a different home. Existing
disabled plugins are reported pending without forcing a version change. No
commits, merges, pushes, or publications were performed during implementation.
The user subsequently requested a commit and integration into `dev`. There are no deferred
review findings.

## Plan Self-Review

All confirmed preferences map to tasks above. The five Review Focus conditions
have explicit tests. Module function names and Python command interfaces are
defined before use; credentials remain upstream-owned. Live browser/indexing
commands still require capability verification against the installed versions,
and tests must not substitute for a real installation claim.
