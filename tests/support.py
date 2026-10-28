import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ShellTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='undex shell space ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base/'home'
        self.home.mkdir()
        self.bin = self.base/'bin'
        self.bin.mkdir()
        dispatcher = ROOT/'tests/fixtures/command.py'
        for name in ['node','npm','npx','uv','codex','rtk','playwright-cli','graphify','graphify-mcp','curl','sudo','apt-get','uname']:
            (self.bin/name).symlink_to(dispatcher)
        self.state = self.base/'fake.json'
        self.state.write_text(json.dumps({'installed': ['node','uv','codex','rtk','playwright-cli','graphify','graphify-mcp'], 'plugins': [], 'login': True}))
        self.log = self.base/'calls.jsonl'
        nvm = self.home/'.nvm'
        nvm.mkdir()
        (nvm/'nvm.sh').write_text('''nvm() {
  case "$1" in
    current) node --version ;;
    version) node --version ;;
    use) npm activate-node "$@" >/dev/null ;;
    install) npm install-node ;;
    --version) echo 0.40.8 ;;
    *) return 0 ;;
  esac
}
''')
        self.env = {**os.environ, 'HOME': str(self.home), 'PATH': str(self.bin)+':/usr/bin:/bin',
                    'UNDEX_ROOT': str(ROOT), 'FAKE_STATE': str(self.state), 'FAKE_LOG': str(self.log),
                    'FAKE_PYTHON': sys.executable, 'XDG_STATE_HOME': str(self.home/'.local/state'),
                    'NVM_DIR': str(nvm), 'CODEX_HOME': str(self.home/'.codex')}
        for key in ['BASH_ENV','ENV','CONTEXT7_API_KEY','UV_PROJECT_ENVIRONMENT']:
            self.env.pop(key, None)

    def change(self, **values):
        state = json.loads(self.state.read_text())
        state.update(values)
        self.state.write_text(json.dumps(state))

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def shell(self, body, modules=('common','tools')):
        sources = '\n'.join(f'source "$UNDEX_ROOT/lib/{name}.sh"' for name in modules)
        return subprocess.run(['bash','-c','set -euo pipefail\n'+sources+'\n'+body], env=self.env,
                              cwd=ROOT, capture_output=True, text=True, timeout=30)

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
