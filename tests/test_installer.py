import json
from pathlib import Path
import subprocess
import tomllib
import shutil
from support import ROOT, ShellTest


class InstallerTests(ShellTest):
    def install(self,*args):
        return subprocess.run(['bash',str(ROOT/'install.sh'),*args],env=self.env,capture_output=True,text=True,timeout=40)

    def test_complete_simulation_and_rerun_preserve_settings_versions_and_helpers(self):
        home = self.home/'.codex'
        home.mkdir()
        (home/'config.toml').write_text('[mcp_servers.other]\nurl="https://example.test"\n')
        self.assert_ok(self.install('--non-interactive'))
        data=tomllib.loads((home/'config.toml').read_text())
        self.assertIn('other',data['mcp_servers'])
        self.assertEqual(data['model'],'gpt-6.1-sol')
        self.assertTrue((self.home/'.local/bin/undex-graphify').is_file())
        before=len(self.calls())
        self.assert_ok(self.install('--non-interactive'))
        after=self.calls()[before:]
        self.assertFalse(any(c[0]=='npm' and '-g' in c for c in after))
        self.assertFalse(any(c[:3]==['codex','plugin','add'] and '--help' not in c for c in after))

    def test_core_failure_returns_nonzero_and_summary(self):
        self.change(installed=['node','uv'],fail='npm')
        result=self.install('--non-interactive')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('failed',result.stdout)

    def test_no_login_reports_pending_but_configuration_is_installed(self):
        self.change(login=False)
        result=self.install('--non-interactive')
        self.assert_ok(result)
        self.assertIn('pending',result.stdout)
        self.assertTrue((self.home/'.codex/agents/code_explorer.toml').exists())

    def test_unknown_options_do_not_mutate_home(self):
        before=sorted(p.relative_to(self.home) for p in self.home.rglob('*'))
        result=self.install('--invalid')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(before,sorted(p.relative_to(self.home) for p in self.home.rglob('*')))

    def test_explicit_plugin_choice_installs_selected_optional(self):
        self.assert_ok(self.install('--non-interactive','--plugins','sites,gmail'))
        self.assertIn(['codex','plugin','add','sites@openai-curated-remote'],self.calls())

    def test_fresh_tool_bootstrap_simulation(self):
        self.change(installed=[])
        shutil.rmtree(self.home/'.nvm')
        self.assert_ok(self.install('--non-interactive'))
        state=json.loads(self.state.read_text())
        for name in ['node','uv','codex','rtk','playwright-cli','graphify','graphify-mcp']:
            self.assertIn(name,state['installed'])
        self.assertTrue((self.home/'.codex/config.toml').exists())
