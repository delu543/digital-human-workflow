#!/usr/bin/env python3
"""Install this repository's isolated local runtime; never read user credentials."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-npm',action='store_true',help='Use only when npm ci already succeeded')
    args=parser.parse_args()
    if sys.version_info < (3,11): raise SystemExit('需要 Python 3.11+；请安装后再运行')
    node=shutil.which('node'); npm=shutil.which('npm.cmd' if os.name=='nt' else 'npm')
    if not node or not npm: raise SystemExit('需要 Node.js 22.15+（包含 npm）：https://nodejs.org/')
    version=subprocess.check_output([node,'--version'],text=True).strip()
    if tuple(map(int,version.lstrip('v').split('.')[:2]))<(22,15): raise SystemExit('Node.js 版本须为22.15或以上')
    runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
    env={**os.environ,'DO_NOT_TRACK':'1','HYPERFRAMES_NO_TELEMETRY':'1'}
    env.pop('MINIMAX_API_KEY',None);env.pop('HEYGEN_API_KEY',None)
    python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists(): venv.EnvBuilder(with_pip=True).create(ROOT/'.venv')
    with (runtime/'bootstrap.log').open('ab') as log:
        def run(command,timeout=600):
            result=subprocess.run([str(x) for x in command],cwd=ROOT,env=env,stdout=log,stderr=log,timeout=timeout)
            if result.returncode: raise SystemExit('安装未完成；查看 .runtime/bootstrap.log，先修复原因，不重复生成视频')
        run([python,'-m','pip','install','-e','.'])
        if not args.skip_npm:
            run([npm,'ci','--ignore-scripts','--no-audit','--no-fund'],timeout=900)
    ffmpeg=subprocess.check_output([str(python),'-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],text=True).strip()
    ffprobe=subprocess.check_output([node,'-e',"process.stdout.write(require('@ffprobe-installer/ffprobe').path)"],cwd=ROOT,text=True).strip()
    bindir=runtime/'bin';bindir.mkdir(exist_ok=True)
    for name,source in [('ffmpeg',ffmpeg),('ffprobe',ffprobe)]:
        target=bindir/(name+('.exe' if os.name=='nt' else ''))
        if not target.exists(): shutil.copy2(source,target)
        if os.name!='nt': target.chmod(target.stat().st_mode | 0o111)
        subprocess.run([str(target),'-version'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    report={'python':str(python),'node':version,'hyperframes':'0.8.48','credentials_read':False,
            'next':'运行 digital-human init 和 doctor；按 INSTALL_FOR_CODEX.md 继续。需要本地字幕时运行 setup_whisper.py。'}
    (runtime/'bootstrap.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__': main()
