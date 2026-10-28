import json
from support import ShellTest, ROOT


class IntegrationTests(ShellTest):
    modules = ('common','tools','integrations')

    def test_context7_runs_mcp_setup_once_with_recorded_version(self):
        result = self.shell('configure_context7; configure_context7', self.modules)
        self.assert_ok(result)
        calls = [c for c in self.calls() if c[0]=='npx']
        self.assertEqual(calls, [['npx','--yes','ctx7@0.6.0','setup','--codex','--mcp']])
        state = json.loads((self.home/'.local/state/undex/state.json').read_text())
        self.assertEqual(state['ctx7_version'], '0.6.0')
        self.assertNotIn('token',json.dumps(state))

    def test_context7_unattended_leaves_auth_pending(self):
        self.assert_ok(self.shell('UNDEX_NONINTERACTIVE=1; configure_context7; test "$UNDEX_PENDING" = 1', self.modules))
        self.assertFalse(any(c[0]=='npx' for c in self.calls()))

    def test_setup_failure_does_not_record_completion(self):
        self.change(fail='npx')
        self.assertNotEqual(self.shell('configure_context7',self.modules).returncode,0)
        state = json.loads((self.home/'.local/state/undex/state.json').read_text())
        self.assertNotIn('context7_ready',state)

    def test_custom_codex_home_rejects_context7_without_touching_standard_home(self):
        self.env['CODEX_HOME'] = str(self.home/'custom')
        self.assertNotEqual(self.shell('configure_context7',self.modules).returncode,0)
        self.assertFalse((self.home/'.codex').exists())

    def test_rtk_honors_custom_codex_home(self):
        self.env['CODEX_HOME'] = str(self.home/'custom')
        self.assert_ok(self.shell('configure_rtk',self.modules))
        self.assertTrue((self.home/'custom/RTK.md').exists())
        self.assertFalse((self.home/'.codex').exists())

    def test_browser_and_skill_are_provisioned_and_rerun_reuses_browser(self):
        self.assert_ok(self.shell('configure_playwright; configure_playwright', self.modules))
        installs = [c for c in self.calls() if c[:2]==['playwright-cli','install-browser'] and '--with-deps' in c]
        self.assertEqual(installs, [['playwright-cli','install-browser','chrome','--with-deps']])
        self.assertIn(['playwright-cli','install','--skills=agents','--global'],self.calls())

    def test_rtk_runs_global_codex_initialization(self):
        self.assert_ok(self.shell('configure_rtk', self.modules))
        self.assertIn(['rtk','init','-g','--codex'],self.calls())
