"""Portable preferences and private backups. Never print configuration values."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import sys
import tempfile
import uuid

import tomlkit

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- undex:personal:start -->'
END = '<!-- undex:personal:end -->'


def check_destination(path: Path) -> None:
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError(f'Refusing managed write through symlink: {p}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Expected a regular file: {path}')


def private_dir(path: Path) -> None:
    check_destination(path / '.directory-check')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def backup(path: Path, backup_root: Path) -> None:
    if not path.exists():
        return
    private_dir(backup_root)
    folder = backup_root / uuid.uuid4().hex
    private_dir(folder)
    target = folder / path.name
    shutil.copyfile(path, target)
    target.chmod(0o600)
    manifest = folder/'source.json'
    manifest.write_text(json.dumps({'source': str(path.absolute()), 'file': path.name}, indent=2)+'\n')
    manifest.chmod(0o600)


def write_managed_text(path: Path, text: str, backup_root: Path) -> bool:
    check_destination(path)
    if path.exists() and path.read_text() == text:
        return False
    backup(path, backup_root)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.undex-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def recursive_merge(document, patch: dict) -> None:
    for key, value in patch.items():
        if isinstance(value, dict):
            if key not in document or not hasattr(document[key], 'items'):
                document[key] = tomlkit.table()
            recursive_merge(document[key], value)
        else:
            document[key] = value


def legacy_agent_profiles(bundle_root: Path, agent_dir: Path):
    if agent_dir.is_symlink():
        return
    for line in (bundle_root/'config/legacy-agent-profiles.sha256').read_text().splitlines():
        digest, name = line.split()
        path = agent_dir/name
        if not path.is_symlink() and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            yield path


def apply_personal_config(bundle_root: Path, codex_home: Path, backup_root: Path) -> None:
    patch = tomlkit.parse((bundle_root/'config/codex.toml').read_text()).unwrap()
    path = codex_home/'config.toml'
    check_destination(path)
    document = tomlkit.parse(path.read_text()) if path.exists() else tomlkit.document()
    agents = codex_home/'AGENTS.md'
    check_destination(agents)
    existing = agents.read_text() if agents.exists() else ''
    policy = (bundle_root/'config/AGENTS.md').read_text().replace('{{RTK_PATH}}', str(codex_home/'RTK.md'))
    block = f'{START}\n{policy.rstrip()}\n{END}'
    retired_profiles = []
    if START in existing or END in existing:
        if existing.count(START) != 1 or existing.count(END) != 1 or existing.index(START) > existing.index(END):
            raise ValueError('Malformed Undex instruction markers; restore or repair AGENTS.md')
        before, rest = existing.split(START, 1)
        old_policy, after = rest.split(END, 1)
        instructions = before + block + after
        if old_policy.lstrip().startswith('## Agent Routing and Cost Policy'):
            retired_profiles = list(legacy_agent_profiles(bundle_root, codex_home/'agents'))
            settings = document.get('agents', {})
            if hasattr(settings, 'items'):
                legacy_defaults = {
                    'default_subagent_model': ('gpt-6.1-sol', 'gpt-6.2-sol'),
                    'default_subagent_reasoning_effort': ('medium',),
                    'max_concurrent_threads_per_session': (3,),
                }
                for key, defaults in legacy_defaults.items():
                    if settings.get(key) in defaults:
                        del settings[key]
    else:
        instructions = (existing.rstrip() + '\n\n' if existing.strip() else '') + block + '\n'
    recursive_merge(document, patch)
    hooks = codex_home/'hooks.json'
    check_destination(hooks)
    if hooks.exists():
        json.loads(hooks.read_text())
    write_managed_text(path, tomlkit.dumps(document), backup_root)
    for profile in retired_profiles:
        backup(profile, backup_root)
        profile.unlink()
    write_managed_text(agents, instructions, backup_root)


def snapshot(codex_home: Path, backup_root: Path) -> None:
    paths = [codex_home/n for n in ['config.toml', 'AGENTS.md', 'hooks.json', 'RTK.md']]
    paths += list((codex_home/'agents').glob('*.toml'))
    for path in paths:
        check_destination(path)
    for path in paths:
        backup(path, backup_root)


def configure_graphify(repo: Path, command: Path, graph: Path, backup_root: Path) -> None:
    path = repo/'.codex/config.toml'
    check_destination(path)
    document = tomlkit.parse(path.read_text()) if path.exists() else tomlkit.document()
    if 'mcp_servers' not in document:
        document['mcp_servers'] = tomlkit.table()
    # This helper owns its server definition; retaining HTTP fields would make
    # Codex reject the resulting stdio transport. Other servers remain intact.
    document['mcp_servers']['graphify'] = {
        'command': str(command), 'args': [str(graph)], 'enabled': True,
    }
    write_managed_text(path, tomlkit.dumps(document), backup_root)


def configure_project(repo: Path, command: Path, graph: Path, backup_root: Path) -> None:
    agents = repo/'AGENTS.md'
    check_destination(agents)
    existing = agents.read_text() if agents.exists() else ''
    start = '<!-- undex:project-pstack:start -->'
    end = '<!-- undex:project-pstack:end -->'
    block = (
        f'{start}\n'
        'Use the `pstack:poteto-mode` skill for development work in this repository.\n'
        f'{end}'
    )
    if start in existing or end in existing:
        if existing.count(start) != 1 or existing.count(end) != 1 or existing.index(start) > existing.index(end):
            raise ValueError('Malformed Undex pstack markers in project AGENTS.md')
        before, rest = existing.split(start, 1)
        _, after = rest.split(end, 1)
        instructions = before + block + after
    else:
        separator = '' if not existing or existing.endswith('\n\n') else ('\n' if existing.endswith('\n') else '\n\n')
        instructions = existing + separator + block + '\n'
    configure_graphify(repo, command, graph, backup_root)
    write_managed_text(agents, instructions, backup_root)


def launcher_text(target: Path) -> str:
    return '#!/usr/bin/env bash\nexec ' + shlex.quote(str(target)) + ' "$@"\n'


def install_project_launcher(path: Path, backup_root: Path) -> None:
    write_managed_text(path, launcher_text(ROOT/'bin/undex-project-setup'), backup_root)
    path.chmod(0o700)
    legacy = path.with_name('undex-graphify')
    if legacy.is_symlink() or not legacy.is_file():
        return
    contents = legacy.read_text(errors='replace')
    try:
        lines = contents.splitlines()
        tokens = shlex.split(lines[1]) if len(lines) == 2 else []
    except ValueError:
        return
    if len(tokens) == 3:
        target = Path(tokens[1])
        if target.is_absolute() and target.parts[-2:] == ('bin', 'undex-graphify') and contents == launcher_text(target):
            backup(legacy, backup_root)
            legacy.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply', 'snapshot', 'project', 'state-get', 'state-set', 'plugins', 'pstack-marketplace', 'context7-check', 'backup-file', 'check-graph', 'launcher'])
    parser.add_argument('values', nargs='*')
    parser.add_argument('--codex-home', type=Path)
    parser.add_argument('--backup-root', type=Path)
    parser.add_argument('--state-file', type=Path)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--command', type=Path)
    parser.add_argument('--graph', type=Path)
    args = parser.parse_args()
    if args.action == 'launcher':
        if not args.command or not args.backup_root:
            parser.error('--command and --backup-root are required')
        install_project_launcher(args.command, args.backup_root)
    elif args.action == 'backup-file':
        if not args.graph or not args.backup_root:
            parser.error('--graph and --backup-root are required')
        check_destination(args.graph)
        backup(args.graph, args.backup_root)
    elif args.action == 'check-graph':
        if not args.graph:
            parser.error('--graph is required')
        check_destination(args.graph)
        graph = json.loads(args.graph.read_text())
        if not isinstance(graph, dict) or not isinstance(graph.get('nodes'), list) or not isinstance(graph.get('links', graph.get('edges')), list):
            raise ValueError('Unsupported graph JSON')
    elif args.action in ['apply', 'snapshot']:
        if not args.codex_home or not args.backup_root:
            parser.error('--codex-home and --backup-root are required')
        if args.action == 'apply':
            apply_personal_config(ROOT, args.codex_home, args.backup_root)
        else:
            snapshot(args.codex_home, args.backup_root)
    elif args.action == 'project':
        if not all([args.repo, args.command, args.graph, args.backup_root]):
            parser.error('project requires --repo, --command, --graph, --backup-root')
        configure_project(args.repo, args.command, args.graph, args.backup_root)
    elif args.action == 'context7-check':
        if not args.codex_home:
            parser.error('--codex-home is required')
        path = args.codex_home/'config.toml'
        document = tomlkit.parse(path.read_text()) if path.exists() else {}
        server = document.get('mcp_servers', {}).get('context7', {})
        enabled = server.get('enabled', True)
        supported = server.get('url', '').startswith('https://mcp.context7.com/') or any('@upstash/context7-mcp' in str(a) for a in server.get('args', []))
        sys.exit(0 if enabled and supported else 1)
    elif args.action == 'pstack-marketplace':
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or not isinstance(data.get('marketplaces'), list):
            raise ValueError('Unsupported Codex marketplace JSON schema; update Codex explicitly')
        for marketplace in data['marketplaces']:
            if marketplace.get('name') != 'pstack-claude':
                continue
            source = marketplace.get('marketplaceSource') or {}
            url = 'https://github.com/michael-denyer/pstack-claude'
            if source.get('sourceType') != 'git' or source.get('source') not in (url, url + '.git'):
                sys.exit('The pstack-claude marketplace points to a different source.')
            print('registered')
    elif args.action == 'plugins':
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or not isinstance(data.get('installed'), list):
            raise ValueError('Unsupported Codex plugin JSON schema; update Codex explicitly')
        for row in data['installed']:
            if row.get('installed') and row.get('pluginId'):
                print(row['pluginId'])
                if not row.get('enabled', False):
                    print('disabled:' + row['pluginId'])
    else:
        if not args.state_file or len(args.values) != (1 if args.action == 'state-get' else 2):
            parser.error('state commands require --state-file and KEY [VALUE]')
        check_destination(args.state_file)
        state = json.loads(args.state_file.read_text()) if args.state_file.exists() else {}
        if args.action == 'state-get':
            print(state.get(args.values[0], ''))
        else:
            state[args.values[0]] = args.values[1]
            # No backups of non-secret installer state; preserve atomic replacement.
            write_managed_text(args.state_file, json.dumps(state, indent=2)+'\n', args.state_file.parent/'state-backups')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, tomlkit.exceptions.TOMLKitError) as exc:
        # Parse exceptions may contain inline secrets: report type, never content.
        print(f'Undex configuration failed ({type(exc).__name__}); originals/backups preserved.', file=sys.stderr)
        sys.exit(1)
