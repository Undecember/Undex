"""Portable preferences and private backups. Never print configuration values."""
import argparse
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


def merged_text(path: Path, patch: dict) -> str:
    check_destination(path)
    document = tomlkit.parse(path.read_text()) if path.exists() else tomlkit.document()
    recursive_merge(document, patch)
    return tomlkit.dumps(document)


def merge_config(path: Path, patch: dict, backup_root: Path) -> bool:
    return write_managed_text(path, merged_text(path, patch), backup_root)


def apply_personal_config(bundle_root: Path, codex_home: Path, backup_root: Path) -> None:
    patch = tomlkit.parse((bundle_root/'config/codex.toml').read_text()).unwrap()
    updates = {codex_home/'config.toml': merged_text(codex_home/'config.toml', patch)}
    agents = codex_home/'AGENTS.md'
    check_destination(agents)
    existing = agents.read_text() if agents.exists() else ''
    policy = (bundle_root/'config/AGENTS.md').read_text().replace('{{RTK_PATH}}', str(codex_home/'RTK.md'))
    block = f'{START}\n{policy.rstrip()}\n{END}'
    if START in existing or END in existing:
        if existing.count(START) != 1 or existing.count(END) != 1 or existing.index(START) > existing.index(END):
            raise ValueError('Malformed Undex instruction markers; restore or repair AGENTS.md')
        before, rest = existing.split(START, 1)
        _, after = rest.split(END, 1)
        updates[agents] = before + block + after
    else:
        updates[agents] = (existing.rstrip() + '\n\n' if existing.strip() else '') + block + '\n'
    for role in sorted((bundle_root/'config/agents').glob('*.toml')):
        tomlkit.parse(role.read_text())
        updates[codex_home/'agents'/role.name] = role.read_text()
    # Validate all targets before the first write.
    for path in updates:
        check_destination(path)
    hooks = codex_home/'hooks.json'
    check_destination(hooks)
    if hooks.exists():
        json.loads(hooks.read_text())
    for path, content in updates.items():
        write_managed_text(path, content, backup_root)


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply', 'snapshot', 'graphify', 'state-get', 'state-set', 'plugins', 'context7-check', 'backup-file', 'check-graph', 'launcher'])
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
        text = '#!/usr/bin/env bash\nexec ' + shlex.quote(str(ROOT/'bin/undex-graphify')) + ' "$@"\n'
        write_managed_text(args.command, text, args.backup_root)
        args.command.chmod(0o700)
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
    elif args.action == 'graphify':
        if not all([args.repo, args.command, args.graph, args.backup_root]):
            parser.error('graphify requires --repo, --command, --graph, --backup-root')
        configure_graphify(args.repo, args.command, args.graph, args.backup_root)
    elif args.action == 'context7-check':
        if not args.codex_home:
            parser.error('--codex-home is required')
        path = args.codex_home/'config.toml'
        document = tomlkit.parse(path.read_text()) if path.exists() else {}
        server = document.get('mcp_servers', {}).get('context7', {})
        enabled = server.get('enabled', True)
        supported = server.get('url', '').startswith('https://mcp.context7.com/') or any('@upstash/context7-mcp' in str(a) for a in server.get('args', []))
        sys.exit(0 if enabled and supported else 1)
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
