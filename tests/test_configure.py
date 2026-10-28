import importlib.util
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("configure", ROOT / "lib/configure.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="undex space ")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "codex home"
        self.home.mkdir()
        self.backups = Path(self.tmp.name) / "backups"

    def test_merge_preserves_comments_and_unrelated_values_and_backs_up(self):
        p = self.home / "config.toml"
        original = '# personal comment\nmodel="old"\n[mcp_servers.other]\nurl="https://example.test"\n'
        p.write_text(original)
        config.apply_personal_config(ROOT, self.home, self.backups)
        d = tomllib.loads(p.read_text())
        self.assertEqual(d["model"], "gpt-6.1-sol")
        self.assertEqual(d["agents"]["max_concurrent_threads_per_session"], 3)
        self.assertEqual(d["approval_policy"], "never")
        self.assertEqual(d["sandbox_mode"], "danger-full-access")
        self.assertEqual(d["mcp_servers"]["other"]["url"], "https://example.test")
        self.assertIn('# personal comment', p.read_text())
        self.assertIn(original, [x.read_text() for x in self.backups.rglob('*') if x.is_file()])
        self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_apply_is_idempotent_and_preserves_generated_blocks(self):
        p = self.home / "AGENTS.md"
        p.write_text('My existing policy\n<!-- context7 -->\nGenerated rule\n<!-- context7 -->\n')
        config.apply_personal_config(ROOT, self.home, self.backups)
        first = {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        count = len(list(self.backups.rglob('*')))
        config.apply_personal_config(ROOT, self.home, self.backups)
        self.assertEqual(first, {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        self.assertEqual(count, len(list(self.backups.rglob('*'))))
        self.assertIn('Generated rule', p.read_text())
        self.assertIn('My existing policy', p.read_text())
        self.assertIn(str(self.home / 'RTK.md'), p.read_text())
        for role in (ROOT / 'config/agents').glob('*.toml'):
            self.assertEqual(role.read_bytes(), (self.home / 'agents' / role.name).read_bytes())
        self.assertEqual(len(list((self.home / 'agents').glob('*.toml'))), 10)

    def test_malformed_config_leaves_all_originals_untouched(self):
        p = self.home / "config.toml"
        p.write_text('[invalid')
        with self.assertRaises(Exception):
            config.apply_personal_config(ROOT, self.home, self.backups)
        self.assertEqual(p.read_text(), '[invalid')
        self.assertFalse((self.home / 'AGENTS.md').exists())

    def test_managed_symlink_is_rejected_without_touching_target(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.write_text('model="old"\n')
        (self.home / 'config.toml').symlink_to(outside)
        with self.assertRaises(ValueError):
            config.apply_personal_config(ROOT, self.home, self.backups)
        self.assertEqual(outside.read_text(), 'model="old"\n')

    def test_project_graphify_merge_does_not_touch_global_config(self):
        repo = Path(self.tmp.name) / 'repo space'
        repo.mkdir()
        config.configure_graphify(repo, Path('/example bin/graphify-mcp'), repo/'graphify-out/graph.json', self.backups)
        d = tomllib.loads((repo/'.codex/config.toml').read_text())
        self.assertEqual(d['mcp_servers']['graphify']['args'], [str(repo/'graphify-out/graph.json')])
        self.assertFalse((self.home/'config.toml').exists())

    def test_backup_snapshot_includes_hook_and_roles_without_overwriting_backup(self):
        (self.home/'hooks.json').write_text('{"other":true}')
        config.snapshot(self.home, self.backups)
        (self.home/'hooks.json').write_text('{"changed":true}')
        config.snapshot(self.home, self.backups)
        values = [p.read_text() for p in self.backups.rglob('hooks.json')]
        self.assertIn('{"other":true}', values)
        self.assertIn('{"changed":true}', values)
        manifests = [json.loads(p.read_text()) for p in self.backups.rglob('source.json')]
        self.assertTrue(any(m['source'] == str(self.home/'hooks.json') for m in manifests))

    def test_project_graphify_replaces_incompatible_http_transport(self):
        repo = Path(self.tmp.name)/'transport repo'
        (repo/'.codex').mkdir(parents=True)
        path=repo/'.codex/config.toml'
        path.write_text('[mcp_servers.graphify]\nurl="https://old.example/mcp"\nhttp_headers={Authorization="old"}\n[mcp_servers.other]\nurl="https://keep.example/mcp"\n')
        config.configure_graphify(repo,Path('/bin/graphify-mcp'),repo/'graphify-out/graph.json',self.backups)
        servers=tomllib.loads(path.read_text())['mcp_servers']
        self.assertNotIn('url',servers['graphify'])
        self.assertNotIn('http_headers',servers['graphify'])
        self.assertEqual(servers['other']['url'],'https://keep.example/mcp')


if __name__ == '__main__':
    unittest.main()
