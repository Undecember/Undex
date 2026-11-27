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
        self.assertEqual(d["model"], "old")
        self.assertEqual(d["agents"], {"enabled": True})
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
        self.assertNotIn('pstack:poteto-mode', p.read_text())
        self.assertFalse((self.home / 'agents').exists())

    def test_upgrade_retires_legacy_routing_and_backs_up_stock_profiles(self):
        path = self.home / 'config.toml'
        path.write_text(
            'model = "personal"\n[agents]\ndefault_subagent_model = "gpt-6.1-sol"\n'
            'default_subagent_reasoning_effort = "medium"\nmax_concurrent_threads_per_session = 3\n'
        )
        instructions = self.home / 'AGENTS.md'
        instructions.write_text(
            f'{config.START}\n## Agent Routing and Cost Policy\nUse Superpowers.\n{config.END}\n'
            'swarm workers: personal @high\n'
        )
        profiles = self.home / 'agents'
        profiles.mkdir()
        stock = (
            'name = "triage"\ndescription = "Quick read-only triage of bounded tasks."\n'
            'model = "gpt-6-luna"\nmodel_reasoning_effort = "low"\ndeveloper_instructions = """\n'
            'Classify the issue, give 1-3 relevant next actions, and cite exact file pointers if available. '
            'Do not edit files. Avoid broad scans, extra agents, and long output.\n"""\n'
        )
        (profiles / 'triage.toml').write_text(stock)
        (profiles / 'reviewer.toml').write_text('name = "personal-reviewer"\n')
        config.apply_personal_config(ROOT, self.home, self.backups)
        data = tomllib.loads(path.read_text())
        self.assertEqual(data['model'], 'personal')
        self.assertEqual(data['agents'], {'enabled': True})
        self.assertIn('swarm workers: personal @high', instructions.read_text())
        self.assertNotIn('Superpowers', instructions.read_text())
        self.assertFalse((profiles / 'triage.toml').exists())
        self.assertTrue((profiles / 'reviewer.toml').exists())
        self.assertEqual([p.read_text() for p in self.backups.rglob('triage.toml')], [stock])

    def test_upgrade_preserves_custom_fallback_and_concurrency(self):
        path = self.home / 'config.toml'
        path.write_text(
            '[agents]\ndefault_subagent_model = "custom"\n'
            'default_subagent_reasoning_effort = "low"\nmax_concurrent_threads_per_session = 6\n'
        )
        (self.home / 'AGENTS.md').write_text(
            f'{config.START}\n## Agent Routing and Cost Policy\n{config.END}\n'
        )
        config.apply_personal_config(ROOT, self.home, self.backups)
        self.assertEqual(tomllib.loads(path.read_text())['agents'], {
            'enabled': True,
            'default_subagent_model': 'custom',
            'default_subagent_reasoning_effort': 'low',
            'max_concurrent_threads_per_session': 6,
        })

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

    def test_launcher_backs_up_old_undex_launcher_from_another_checkout(self):
        launcher = self.home/'undex-project-setup'
        legacy = self.home/'undex-graphify'
        old_text = config.launcher_text(Path('/old checkout/bin/undex-graphify'))
        legacy.write_text(old_text)
        config.install_project_launcher(launcher, self.backups)
        self.assertFalse(legacy.exists())
        self.assertEqual([p.read_text() for p in self.backups.rglob('undex-graphify')], [old_text])
        self.assertEqual(launcher.read_text(), config.launcher_text(ROOT/'bin/undex-project-setup'))
        self.assertEqual(launcher.stat().st_mode & 0o777, 0o700)

    def test_launcher_preserves_custom_legacy_command(self):
        legacy = self.home/'undex-graphify'
        legacy.write_text('#!/bin/sh\nprintf "custom command\\n"\n')
        config.install_project_launcher(self.home/'undex-project-setup', self.backups)
        self.assertIn('custom command', legacy.read_text())

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
