#!/usr/bin/env python3
"""Install the generic Codex skill without replacing any existing skill."""
import argparse
import json
import os
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,default=Path.home()/'.agents/skills')
    p.add_argument('--copy',action='store_true',help='Use a copy with a local locator when symlinks are unavailable')
    a=p.parse_args();source=ROOT/'skills/digital-human-workflow';target=a.destination.expanduser().resolve()/source.name
    if target.exists() or target.is_symlink():
        if target.resolve()==source.resolve():
            print(json.dumps({'ok':True,'already_installed':True,'path':str(target)},ensure_ascii=False));return
        locator=target/'installation.json'
        if locator.is_file() and json.loads(locator.read_text()).get('repository')==str(ROOT):
            print(json.dumps({'ok':True,'already_installed':True,'path':str(target)},ensure_ascii=False));return
        raise SystemExit('同名 Skill 已存在；请先检查，不覆盖其他安装')
    target.parent.mkdir(parents=True,exist_ok=True)
    if a.copy or os.name=='nt':
        shutil.copytree(source,target)
        (target/'installation.json').write_text(json.dumps({'repository':str(ROOT)},ensure_ascii=False),encoding='utf-8')
    else: target.symlink_to(source,target_is_directory=True)
    print(json.dumps({'ok':True,'display_name':'数字人工作流','path':str(target)},ensure_ascii=False))

if __name__=='__main__': main()
