#!/usr/bin/env python3
"""Install/update our own Skill; preserve other installations and local backups."""
import argparse
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,default=Path.home()/'.agents/skills')
    p.add_argument('--copy',action='store_true',help='Use a copy with a local locator when symlinks are unavailable')
    p.add_argument('--update',action='store_true',help='Update an owned copy after preserving a full local backup')
    a=p.parse_args();source=ROOT/'skills/digital-human-workflow';target=a.destination.expanduser().resolve()/source.name
    if target.exists() or target.is_symlink():
        if target.resolve()==source.resolve():
            print(json.dumps({'ok':True,'already_installed':True,'path':str(target)},ensure_ascii=True));return
        locator=target/'installation.json'
        if locator.is_file() and json.loads(locator.read_text(encoding='utf-8')).get('repository')==str(ROOT):
            if a.update:
                if target.is_symlink() or any(x.is_symlink() for x in target.rglob('*')):
                    raise SystemExit('复制安装含符号链接；请检查，不覆盖链接目标')
                backup=target.with_name('.'+target.name+'.backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
                shutil.copytree(target,backup)
                shutil.copytree(source,target,dirs_exist_ok=True)
                print(json.dumps({'ok':True,'updated':True,'path':str(target),'backup':str(backup)},ensure_ascii=True));return
            print(json.dumps({'ok':True,'already_installed':True,'path':str(target)},ensure_ascii=True));return
        raise SystemExit('同名 Skill 已存在；请先检查，不覆盖其他安装')
    target.parent.mkdir(parents=True,exist_ok=True)
    if a.copy or os.name=='nt':
        shutil.copytree(source,target)
        (target/'installation.json').write_text(json.dumps({'repository':str(ROOT)},ensure_ascii=False),encoding='utf-8')
    else: target.symlink_to(source,target_is_directory=True)
    print(json.dumps({'ok':True,'display_name':'数字人工作流','path':str(target)},ensure_ascii=True))

if __name__=='__main__': main()
