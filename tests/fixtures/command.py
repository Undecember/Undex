#!/usr/bin/python3
"""External command boundary double; all state and effects stay in a temp home."""
import json
import os
from pathlib import Path
import sys
import shlex

name = Path(sys.argv[0]).name
args = sys.argv[1:]
state_path = Path(os.environ['FAKE_STATE'])
s = json.loads(state_path.read_text())
with open(os.environ['FAKE_LOG'], 'a') as stream:
    stream.write(json.dumps([name, *args])+'\n')
if s.get('fail') == name or s.get('fail_command') == [name, *args]:
    sys.exit(1)
installed = s['installed']
if args in [['--version'], ['-V']]:
    if name not in installed or (name=='node' and not s.get('node_active',True)):
        sys.exit(1)
    print({'node':'v24.14.1','codex':'codex-cli 0.165.0','rtk':'rtk 1.1.0',
           'graphify':'graphify 0.9.97','playwright-cli':'Version 0.1.22'}.get(name,'1.0.0'))
elif name == 'uname':
    print(s.get('os','Linux'))
elif name == 'uv' and args and args[0]=='run':
    pos = args.index('python') if 'python' in args else args.index('python3')
    os.execv(os.environ['FAKE_PYTHON'], [os.environ['FAKE_PYTHON'], *args[pos+1:]])
elif name == 'npm':
    if args[:2] == ['view','ctx7']:
        print('0.6.0')
    elif args and args[0] == 'install-node':
        installed.append('node')
        s['node_active']=True
    elif args and args[0] == 'activate-node':
        if 'node' not in installed: sys.exit(1)
        s['node_active']=True
    elif args and args[0] in ['i','install']:
        for arg in args:
            if '@openai/codex' in arg and 'codex' not in installed: installed.append('codex')
            if '@playwright/cli' in arg and 'playwright-cli' not in installed: installed.append('playwright-cli')
    elif args[:2] == ['list','-g']:
        print(s.get('npm_json','{}'))
    else:
        print('{}')
elif name == 'uv' and args[:2] == ['tool','install']:
    installed.extend(['graphify','graphify-mcp'])
elif name == 'codex':
    if args == ['login','status']:
        sys.exit(0 if s.get('login') else 1)
    elif args == ['login','--device-auth']:
        s['login'] = True
    elif args == ['plugin','list','--json']:
        print(json.dumps({'installed':[{'pluginId': x, 'installed':True, 'enabled':x not in s.get('disabled_plugins',[]), 'version':'1.0.0'} for x in s['plugins']], 'available':[]}))
    elif args[:2] == ['plugin','add']:
        s['plugins'].append(args[2])
    elif '--help' in args:
        print('plugin add --json install --skills')
elif name == 'npx':
    config = Path(os.environ['CODEX_HOME'])/'config.toml'
    config.parent.mkdir(parents=True, exist_ok=True)
    existing = config.read_text() if config.exists() else ''
    if '[mcp_servers.context7]' not in existing:
        config.write_text(existing+'\n[mcp_servers.context7]\nurl="https://mcp.context7.com/mcp"\n')
elif name == 'rtk' and args[:1] == ['init']:
    if '--codex' in args and '--auto-patch' in args:
        sys.exit('rtk: --codex cannot be combined with --auto-patch')
    folder = Path(os.environ['CODEX_HOME'])
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'RTK.md').write_text('RTK generated instructions\n')
elif name == 'playwright-cli':
    if args[:1] == ['install-browser'] and '--list' in args:
        if s.get('browser'): print('chrome /opt/google/chrome/chrome')
    elif args[:1] == ['install-browser']:
        s['browser'] = True
    elif '--help' in args:
        print('--skills --global --with-deps')
elif name == 'graphify':
    if args[:1] == ['update']:
        graph = Path(args[1])/'graphify-out/graph.json'
        graph.parent.mkdir(parents=True, exist_ok=True)
        graph.write_text('{"nodes":[{"id":"hello"}],"edges":[]}')
    elif '--help' in args:
        print('--no-cluster --no-label --no-viz')
elif name == 'curl':
    if 'api.github.com/repos/nvm-sh/nvm/releases/latest' in ' '.join(args):
        print('{"tag_name":"v0.40.8"}')
    else:
        url=' '.join(args)
        # Emulate only the files/executables an official installer makes available.
        code='import os,json; from pathlib import Path; p=Path(os.environ["FAKE_STATE"]); s=json.loads(p.read_text()); '
        if 'astral.sh' in url:
            code+='s["installed"].append("uv"); p.write_text(json.dumps(s))'
        elif 'rtk-ai/rtk' in url:
            code+='s["installed"].append("rtk"); p.write_text(json.dumps(s))'
        elif 'nvm-sh/nvm' in url:
            nvm_script='nvm() { case "$1" in install) npm install-node ;; use) npm activate-node "$@" ;; current|version) node --version ;; *) return 0 ;; esac; }\n'
            code+='d=Path(os.environ["NVM_DIR"]); d.mkdir(parents=True,exist_ok=True); (d/"nvm.sh").write_text('+repr(nvm_script)+')'
        else:
            sys.exit('Unrecognized installer URL in command double')
        print(shlex.quote(os.environ['FAKE_PYTHON'])+' -c '+shlex.quote(code))
elif name in ['sudo','apt-get']:
    pass
else:
    if name not in installed:
        sys.exit(1)
state_path.write_text(json.dumps(s))
