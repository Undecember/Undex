from support import ShellTest
import os
import pty
import subprocess


class PluginTests(ShellTest):
    modules = ('common','plugins')

    def test_defaults_install_once_and_no_optional_plugins(self):
        self.assert_ok(self.shell('select_optional_plugins; install_plugins; install_plugins', self.modules))
        adds = [c for c in self.calls() if c[:2]==['codex','plugin'] and c[2]=='add']
        self.assertEqual(adds,[['codex','plugin','add','superpowers@openai-curated-remote'], ['codex','plugin','add','github@openai-curated-remote']])

    def test_named_optional_choices_are_allowed_but_other_plugins_rejected(self):
        self.assert_ok(self.shell('UNDEX_PLUGIN_SELECTION=gmail,sites; select_optional_plugins; install_plugins',self.modules))
        self.assertIn(['codex','plugin','add','sites@openai-curated-remote'],self.calls())
        self.assertNotEqual(self.shell('UNDEX_PLUGIN_SELECTION=unapproved; select_optional_plugins',self.modules).returncode,0)

    def test_unattended_no_login_reports_pending_without_plugins(self):
        self.change(login=False)
        self.assert_ok(self.shell('UNDEX_NONINTERACTIVE=1; ensure_codex_login; select_optional_plugins; install_plugins; test "$UNDEX_PENDING" = 1',self.modules))
        self.assertFalse(any(c[0:2]==['codex','plugin'] for c in self.calls()))
        self.assertFalse(any(c==['codex','login','--device-auth'] for c in self.calls()))

    def test_plugin_listing_failure_is_not_success(self):
        self.change(fail_command=['codex','plugin','list','--json'])
        self.assertNotEqual(self.shell('select_optional_plugins; install_plugins',self.modules).returncode,0)

    def test_optional_failure_is_reported_and_does_not_fail_core(self):
        self.change(fail_command=['codex','plugin','add','gmail@openai-curated-remote'])
        result=self.shell('UNDEX_PLUGIN_SELECTION=gmail; select_optional_plugins; install_plugins; test "$UNDEX_PENDING" = 1',self.modules)
        self.assert_ok(result)
        self.assertIn('gmail',result.stdout)
        self.assertIn('failed',result.stdout)

    def test_device_login_is_started_with_terminal(self):
        self.change(login=False)
        master,slave=pty.openpty()
        try:
            result=subprocess.run(['bash','-c','set -euo pipefail; source "$UNDEX_ROOT/lib/common.sh"; source "$UNDEX_ROOT/lib/plugins.sh"; ensure_codex_login'],env=self.env,stdin=slave,capture_output=True,text=True,timeout=15)
        finally:
            os.close(master)
            os.close(slave)
        self.assert_ok(result)
        self.assertIn(['codex','login','--device-auth'],self.calls())

    def test_explicit_update_plugin_choices_override_previous_selection(self):
        self.assert_ok(self.shell('state_set optional_plugins gmail; UNDEX_UPDATE=1; UNDEX_PLUGIN_SELECTION=sites; select_optional_plugins; install_plugins',self.modules))
        self.assertIn(['codex','plugin','add','sites@openai-curated-remote'],self.calls())
        self.assertNotIn(['codex','plugin','add','gmail@openai-curated-remote'],self.calls())

    def test_disabled_installed_plugin_is_reported_pending_without_upgrade(self):
        self.change(plugins=['github@openai-curated-remote'],disabled_plugins=['github@openai-curated-remote'])
        result=self.shell('select_optional_plugins; install_plugins',self.modules)
        self.assert_ok(result)
        self.assertIn('disabled',result.stdout)
        self.assertNotIn(['codex','plugin','add','github@openai-curated-remote'],self.calls())
