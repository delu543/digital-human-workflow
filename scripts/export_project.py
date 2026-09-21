#!/usr/bin/env python3
"""Export a checked Hyperframes project once; optional macOS launchd execution."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
from digital_human.export_worker import execute, make_spec, launch_plist
from digital_human.storage import WorkflowError, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-spec', type=Path)
    p.add_argument('--project', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--state', type=Path)
    p.add_argument('--fps', type=int, default=25)
    p.add_argument('--attempt', type=int, default=1)
    p.add_argument('--max-attempts', type=int, default=1)
    p.add_argument('--timeout', type=int, default=7200)
    p.add_argument('--macos-background', action='store_true')
    a = p.parse_args()
    if a.execute_spec:
        execute(json.loads(a.execute_spec.read_text(encoding='utf-8')))
        return
    if not all((a.project, a.output, a.state)):
        p.error('需要 --project --output --state')
    if a.macos_background and sys.platform != 'darwin':
        raise WorkflowError('macOS 后台模式仅支持 macOS；其他系统使用前台或用户批准的系统任务')
    spec = make_spec(a.project, a.output, a.state, a.fps, a.attempt, a.max_attempts, a.timeout)
    state = Path(spec['state']);state.mkdir(parents=True, exist_ok=True)
    path = state/'spec.json'
    with path.open('x', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    if not a.macos_background:
        execute(spec)
        return
    label = 'com.digitalhuman.export.'+digest(str(state))[:20]
    # Keep the venv entrypoint: resolving its symlink would lose installed dependencies.
    payload = launch_plist(path, label, Path(sys.executable).absolute(), Path(__file__).resolve())
    plist = state/'export.plist'
    with plist.open('xb') as f:
        plistlib.dump(payload, f)
    domain = f'gui/{os.getuid()}'
    subprocess.run(['/bin/launchctl','bootstrap',domain,str(plist)], check=True)
    print(json.dumps({'submitted_once':True, 'label':label, 'domain':domain,
                      'state':str(state), 'no_keepalive':True,
                      'stop_or_unload':['/bin/launchctl','bootout',domain+'/'+label]}, ensure_ascii=True))


if __name__ == '__main__':
    main()
