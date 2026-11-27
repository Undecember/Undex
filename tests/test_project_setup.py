import subprocess
import tomllib
from support import ROOT, ShellTest


class ProjectSetupTests(ShellTest):
    def setUp(self):
        super().setUp()
        self.repo = self.base/'repo space'
        self.repo.mkdir()
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.helper = ROOT/'bin/undex-project-setup'

    def run_helper(self, *args, cwd=None):
        return subprocess.run(['bash',str(self.helper),*map(str,args)],cwd=cwd or self.repo,env=self.env,capture_output=True,text=True,timeout=30)

    def test_nested_directory_indexes_root_and_only_configures_project(self):
        nested=self.repo/'src'
        nested.mkdir()
        self.assert_ok(self.run_helper(cwd=nested))
        d=tomllib.loads((self.repo/'.codex/config.toml').read_text())
        self.assertEqual(d['mcp_servers']['graphify']['args'],[str(self.repo/'graphify-out/graph.json')])
        self.assertIn('pstack:poteto-mode', (self.repo/'AGENTS.md').read_text())
        self.assertFalse((self.home/'.codex/config.toml').exists())
        self.assertFalse((self.home/'.codex/AGENTS.md').exists())
        self.assertIn(['graphify', 'extract', '.', '--code-only'], self.calls())

    def test_rerun_keeps_one_pstack_block_and_preserves_existing_config(self):
        (self.repo/'graphify-out').mkdir()
        (self.repo/'graphify-out/graph.json').write_text('{"nodes":[],"edges":[]}')
        (self.repo/'.codex').mkdir()
        (self.repo/'.codex/config.toml').write_text('[mcp_servers.other]\nurl="https://example.test"\n')
        agents = self.repo/'AGENTS.md'
        agents.write_text('# Existing instructions\n')
        self.assert_ok(self.run_helper(self.repo, cwd=self.home))
        instructions = agents.read_text()
        self.assert_ok(self.run_helper())
        self.assertEqual(self.calls().count(['graphify', 'extract', '.', '--code-only']), 2)
        d=tomllib.loads((self.repo/'.codex/config.toml').read_text())
        self.assertIn('other',d['mcp_servers'])
        self.assertTrue(instructions.startswith('# Existing instructions\n\n'))
        self.assertEqual(instructions.count('undex:project-pstack:start'), 1)
        self.assertEqual(agents.read_text(), instructions)

    def test_failed_index_does_not_write_project_configuration(self):
        self.change(fail='graphify')
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertFalse((self.repo/'.codex/config.toml').exists())
        self.assertFalse((self.repo/'AGENTS.md').exists())

    def test_outside_repository_is_rejected(self):
        self.assertNotEqual(self.run_helper(cwd=self.home).returncode,0)
        self.assertFalse((self.home/'graphify-out').exists())

    def test_extract_preserves_graph_backup(self):
        (self.repo/'graphify-out').mkdir()
        original='{"nodes":[{"id":"before"}],"edges":[]}'
        (self.repo/'graphify-out/graph.json').write_text(original)
        self.assert_ok(self.run_helper())
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
