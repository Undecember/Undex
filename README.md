# Undex

My reproducible Codex setup: tools, pstack workflows, preferences, and the account setup
steps that still need me.

Clone this repository, keep the checkout, and run:

```bash
bash install.sh
```

Run as your normal user. The installer uses sudo only when Linux packages or
browser dependencies need it. Internet access is required. Interactive setup can
show device codes or browser authorization links; these are completed personally.

Ubuntu is the primary target. The installer accepts Ubuntu/Debian-based Linux
distributions using apt; other distributions and macOS are not supported by this
version. Development checks ran on Ubuntu 24.04.5 LTS. Full fresh-machine
installation has not yet been verified in a disposable Ubuntu system.

## What installs

| Component | Method |
| --- | --- |
| Node.js | nvm's official release installer, then latest LTS on a fresh setup |
| Codex | `npm i -g @openai/codex` |
| RTK | Official installer below, then `rtk init -g --codex` |
| uv | Official standalone installer if missing |
| Graphify | `uv tool install 'graphifyy[mcp]'` |
| Playwright CLI | `npm install -g @playwright/cli@latest` |
| Playwright skill | `playwright-cli install --skills=agents --global` |
| Browser | Chrome, including missing Linux dependencies |
| Context7 | `npx ctx7 setup --codex --mcp`, with the selected CLI version recorded for retries |
| Default plugins | pstack from `michael-denyer/pstack-claude` and GitHub through Codex's plugin CLI |

RTK uses this installation command:

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
```

uv uses:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

nvm's current stable release is resolved from its official GitHub release API
before running that release's `install.sh`. Compatible active Node installations
are reused; otherwise an existing nvm default is tried before installing LTS.
This avoids losing access to global npm tools by switching Node versions on reruns.
The bootstrap requires curl, git, Python 3, certificates, and flock; missing system
packages are installed with apt. uv supplies a compatible Python for the locked
configuration utility when the system Python is too old.

Official references: [nvm](https://github.com/nvm-sh/nvm#installing-and-updating),
[uv](https://docs.astral.sh/uv/getting-started/installation/),
[RTK](https://github.com/rtk-ai/rtk),
[Graphify](https://github.com/Graphify-Labs/graphify),
[Playwright CLI](https://github.com/microsoft/playwright-cli), and
[Context7 for Codex](https://github.com/upstash/context7/blob/master/docs/clients/codex.mdx).

## Personal defaults

- Choose the main model and reasoning effort in Codex.
- Subagents are enabled. Run `$pstack:setup-pstack` to set the models and reasoning
  effort pstack uses for delegated roles. These settings apply when the Codex
  host supports the corresponding subagent overrides.
- Approval policy `never` and sandbox `danger-full-access` allow Codex commands to
  run without approval prompts or Codex filesystem sandbox restrictions.
- Undex includes Context7, Graphify, and RTK tool preferences.

On upgrade, Undex replaces its managed routing instructions, removes matching
legacy subagent defaults, and backs up stock agent profiles before removing them.
Existing main-model settings and customized profiles are preserved.

Personal instructions are placed in a marked block in `AGENTS.md`; existing text
outside that block remains. Context7 and RTK maintain their own generated content.
Context7 uses its MCP setup command. After pstack is installed and enabled,
Undex removes the curated Superpowers plugin if present.

## Optional plugins

The interactive installer asks for comma-separated names. Press Enter for none:

- `gmail`
- `google-calendar`
- `google-contacts`
- `google-drive`
- `openai-templates`
- `pages`
- `sites`
- `plugin-management`

You can also choose explicitly:

```bash
bash install.sh --plugins gmail,google-drive,sites
```

Omitting a previously installed plugin does not uninstall it. These choices are
separate from granting a plugin access to an external account.
An existing disabled plugin keeps its version and is reported as pending; enable
it through `/plugins` when you want to use it.

## Login and personal completion steps

1. **Codex:** the installer checks login and launches `codex login --device-auth`
   when needed. Open the verification link on any device and authorize it. Without
   a terminal, the installer reports login as pending and continues local setup.
2. **Context7:** its setup command handles personal authorization and writes the
   MCP configuration and instructions. Existing enabled MCP configuration is
   reused. Verify documentation lookup in a new Codex session; existing config is
   not evidence that a credential is still valid. To retry authorization:

   ```bash
   bash install.sh --configure-context7
   ```

3. **GitHub and other services:** open `/plugins` in Codex and complete any account
   connection/permissions prompts. Installed does not mean connected. The installer
   reports connections as pending because it cannot verify them from installation
   state alone.
4. **RTK:** start a fresh Codex session and trust its generated hook if Codex asks.
   The installer does not copy this server's remembered hook trust.

5. **pstack:** use `$pstack:setup-pstack` in a fresh Codex session to choose
   models and reasoning effort for your Codex profile. For automatic routing in
   every project, review and trust the pstack hook through `/hooks`. For routing
   only in projects you opt into, leave the hook untrusted or select
   `session hook: off` during setup, then use the project helper below.
   See [pstack's Codex setup reference](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/setup-pstack/references/runtimes.md#codex).

Undex uses these commands to install the default plugins.

```bash
codex plugin marketplace add michael-denyer/pstack-claude
codex plugin add pstack@pstack-claude
codex plugin add github@openai-curated-remote
```

If the account/catalog does not expose a plugin through the CLI, open `/plugins`,
search its name, and install it there. Then rerun Undex. Marketplace availability,
organization policy, and service authorization remain account-dependent.

Start a **new Codex session** after installation to load the new skills,
plugins, and MCP configuration.

## Project setup

The installer adds `undex-project-setup` to `~/.local/bin` and retires the
previous Undex-generated `undex-graphify` launcher. Keep the Undex checkout in
place so the launcher can find the helper. Run it from a Git repository or
pass the repository path.

```bash
undex-project-setup
undex-project-setup /path/to/my-repository
```

The helper runs `graphify extract . --code-only` from the repository root with
model calls disabled. It backs up an existing graph before extraction and merges
the Graphify MCP entry into the project's `.codex/config.toml`. Open the project
as trusted in Codex to load that MCP configuration.

The helper adds a short instruction in the repository's `AGENTS.md` to use
`pstack:poteto-mode`. Codex loads it in a fresh session for that repository.
The pstack plugin, model sheet, and SessionStart hook setting belong to the
Codex user profile. Project setup uses the installed plugin and does not write
model choices or change hook settings.

If an existing Graphify installation lacks MCP support, preserve its version and
add the extra explicitly:

```bash
# Replace VERSION with the current installed Graphify version.
uv tool install --force 'graphifyy[mcp]==VERSION'
```

An old global Graphify target is preserved as unrelated existing configuration.
Undex does not distribute it. Review/remove such an entry yourself if you want
Graphify available only inside configured projects.

## Reruns and updates

Ordinary reruns apply the current personal configuration while keeping existing
tool versions. Missing tools are installed at their latest stable release.
Context7's first selected CLI version is recorded for retries. System packages and
browser dependencies remain managed by their upstream installers/package manager.

```bash
bash install.sh                         # Apply preferences; keep installed versions
bash install.sh --reuse-options         # Reuse the last optional plugin selection
bash install.sh --update                # Explicitly update managed tools/plugins
bash install.sh --update --plugins sites # Override the saved optional selection
bash install.sh --non-interactive       # Skip new personal authorization and selection
bash install.sh --help
```

`--update` reuses the saved optional plugin selection unless `--plugins` is given.
It updates nvm, Node LTS, uv, Codex, RTK, Playwright, Graphify, and the managed
plugins. Previously selected optional plugins are the ones updated; unrelated
plugins and uv tools are untouched. Node migration reinstalls existing global npm
packages at their recorded versions before updating the tools owned by Undex.
Tools installed through another package manager may require updating through that
manager; a failure is reported rather than silently replacing the installation.

Noninteractive mode still performs tool/system installation, may need a configured
sudo session, and can install selected/default plugins when Codex is already logged
in. It skips new Codex and Context7 authorization. Optional installation failures
and personal completion steps are reported as pending. A core tool/configuration
or integration command failure returns a nonzero status. The script does not claim
a skipped component is configured.

## Backups and configuration ownership

Undex merges its own preferences into existing TOML. Unrelated MCP servers,
plugins, hooks, and trusted projects remain. New installs do not copy credentials,
trusted-project paths, history, databases, caches, or other server state.

State and private backups live in:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/undex/
  state.json
  backups/<unique-id>/<original-filename>
  backups/<unique-id>/source.json
```

Each backup's `source.json` records its original destination. Backups can include
credentials from existing config, so their directories are private and files use
mode `600`. Never commit them. Changed files are backed up before replacement;
upstream integration setup also gets a pre-operation snapshot. Undex does not
automatically roll back unrelated successful steps when another component fails.

To restore, stop the installer, inspect the backup's `source.json`, and copy its
original file to the recorded destination. For example, when the backup belongs
to the global Codex config:

```bash
cp -- /path/to/backup/config.toml "$HOME/.codex/config.toml"
chmod 600 "$HOME/.codex/config.toml"
```

`CODEX_HOME` is honored for personal configuration, Codex commands, and RTK.
The Context7 setup command is documented against `~/.codex`; Undex refuses to run
that integration against a custom Codex home until upstream support is verified.
Configure Context7 manually in your custom home instead. Playwright's global skill
uses `~/.agents/skills`, independently of Codex home. Managed writes through
symlinks are rejected rather than following an unexpected destination.

## Development and verification

```bash
uv run --locked python -m unittest discover -s tests -v
for file in install.sh bin/undex-project-setup lib/*.sh; do bash -n "$file" || exit; done
git diff --check
```

The tests use temporary homes and external-command doubles to exercise the actual
installer, configuration merger, plugin logic, and repository helper without
changing live accounts or system packages. A separate real Graphify smoke test
indexed a disposable Python repository with model credentials removed and verified
that only its project MCP config was created. A real RTK initialization check ran
twice in a temporary home and preserved an unrelated hook without duplicating RTK.
Complete fresh-machine installation,
browser provisioning, and new-account authorization still need a disposable host
for live validation; these are not claimed by the simulations.

The approved [design](docs/superpowers/specs/2026-10-29-codex-setup-design.md) and
[implementation plan](docs/superpowers/plans/2026-10-29-codex-setup.md) record the
chosen scope and defaults.

## Release and license

Version `0.1.1` is a preview release, updating model routing after the
initial `0.1.0` release. See the
[changelog](CHANGELOG.md), [release notes](docs/releases/v0.1.1.md), and
[release procedure](docs/RELEASING.md).

Undex is licensed under the [MIT License](LICENSE). Installed upstream tools and
services retain their own licenses and terms.
