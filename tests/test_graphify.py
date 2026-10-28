import json
import subprocess
import tomllib
from support import ROOT, ShellTest


class GraphifyTests(ShellTest):
    def setUp(self):
        super().setUp()
        self.repo = self.base/'repo space'
        self.repo.mkdir()
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.helper = ROOT/'bin/undex-graphify'

    def run_helper(self, *args, cwd=None):
        return subprocess.run(['bash',str(self.helper),*map(str,args)],cwd=cwd or self.repo,env=self.env,capture_output=True,text=True,timeout=30)

    def test_nested_directory_indexes_root_and_only_configures_project(self):
        nested=self.repo/'src'
        nested.mkdir()
        self.assert_ok(self.run_helper(cwd=nested))
        d=tomllib.loads((self.repo/'.codex/config.toml').read_text())
        self.assertEqual(d['mcp_servers']['graphify']['args'],[str(self.repo/'graphify-out/graph.json')])
        self.assertFalse((self.home/'.codex/config.toml').exists())
        self.assertIn(['graphify','update',str(self.repo),'--no-cluster'],self.calls())

    def test_existing_graph_reused_and_unrelated_config_preserved(self):
        (self.repo/'graphify-out').mkdir()
        (self.repo/'graphify-out/graph.json').write_text('{"nodes":[],"edges":[]}')
        (self.repo/'.codex').mkdir()
        (self.repo/'.codex/config.toml').write_text('[mcp_servers.other]\nurl="https://example.test"\n')
        self.assert_ok(self.run_helper())
        self.assertFalse(any(c[:2]==['graphify','update'] for c in self.calls()))
        d=tomllib.loads((self.repo/'.codex/config.toml').read_text())
        self.assertIn('other',d['mcp_servers'])

    def test_failed_index_does_not_write_mcp_config(self):
        self.change(fail='graphify')
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertFalse((self.repo/'.codex/config.toml').exists())

    def test_outside_repository_is_rejected(self):
        self.assertNotEqual(self.run_helper(cwd=self.home).returncode,0)
        self.assertFalse((self.home/'graphify-out').exists())

    def test_refresh_preserves_graph_backup(self):
        (self.repo/'graphify-out').mkdir()
        original='{"nodes":[{"id":"before"}],"edges":[]}'
        (self.repo/'graphify-out/graph.json').write_text(original)
        self.assert_ok(self.run_helper('--refresh'))
        backup_root=self.home/'.local/state/undex/backups'
        self.assertIn(original,[p.read_text() for p in backup_root.rglob('graph.json')])

    def test_symlinked_lock_is_rejected_without_truncating_target(self):
        state=self.home/'.local/state/undex'
        state.mkdir(parents=True)
        victim=self.base/'victim'
        victim.write_text('keep me')
        (state/'graphify.lock').symlink_to(victim)
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertEqual(victim.read_text(),'keep me')
        self.assertFalse((self.repo/'graphify-out').exists())

    def test_symlinked_state_directory_is_rejected(self):
        actual=self.base/'state-target'
        actual.mkdir()
        (self.home/'.local').mkdir()
        (self.home/'.local/state').symlink_to(actual)
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertEqual(list(actual.iterdir()),[])
