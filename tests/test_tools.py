from support import ShellTest


class ToolTests(ShellTest):
    def test_rerun_keeps_installed_tools(self):
        result = self.shell('ensure_node; ensure_uv; ensure_codex; ensure_rtk; ensure_playwright; ensure_graphify')
        self.assert_ok(result)
        self.assertFalse(any((c[0]=='curl' or 'install' in c or 'upgrade' in c) and '--help' not in c for c in self.calls()))

    def test_missing_npm_tools_are_installed(self):
        self.change(installed=['node','uv','rtk','graphify','graphify-mcp'])
        self.assert_ok(self.shell('ensure_codex; ensure_playwright'))
        self.assertIn(['npm','i','-g','@openai/codex'],self.calls())
        self.assertIn(['npm','install','-g','@playwright/cli@latest'],self.calls())

    def test_missing_graphify_uses_uv_mcp_extra(self):
        self.change(installed=['node','uv'])
        self.assert_ok(self.shell('ensure_graphify'))
        self.assertIn(['uv','tool','install','graphifyy[mcp]'],self.calls())

    def test_explicit_update_updates_owned_tools(self):
        self.assert_ok(self.shell('UNDEX_UPDATE=1; ensure_codex; ensure_playwright; ensure_graphify'))
        self.assertIn(['npm','i','-g','@openai/codex'],self.calls())
        self.assertIn(['uv','tool','upgrade','graphifyy'],self.calls())

    def test_failed_install_propagates_failure(self):
        self.change(installed=['node','uv'],fail='npm')
        self.assertNotEqual(self.shell('ensure_codex').returncode,0)

    def test_unsupported_platform_rejected(self):
        self.change(os='Darwin')
        result = self.shell('undex_preflight')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(any(c[0] in ['apt-get','sudo','curl'] for c in self.calls()))

    def test_latest_lts_when_node_missing(self):
        self.change(installed=['uv'])
        self.assert_ok(self.shell('ensure_node'))
        self.assertIn(['npm','install-node'],self.calls())

    def test_update_does_not_hide_invalid_global_package_inventory(self):
        self.change(npm_json='{')
        self.assertNotEqual(self.shell('UNDEX_UPDATE=1; ensure_node').returncode,0)

    def test_update_restores_inactive_nvm_before_migrating_globals(self):
        self.change(node_active=False,npm_json='{"dependencies":{"unrelated":{"version":"1.2.3"}}}')
        self.assert_ok(self.shell('UNDEX_UPDATE=1; ensure_node'))
        self.assertIn(['npm','install','-g','unrelated@1.2.3'],self.calls())
