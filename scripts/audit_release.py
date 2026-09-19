#!/usr/bin/env python3
"""Fail closed on private paths, secrets, media, or unreviewed binaries in the index."""
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    if Path(git('rev-parse','--show-toplevel').decode().strip()).resolve()!=ROOT:
        raise SystemExit('请先在产品目录初始化独立 Git 仓库；禁止审计/提交父项目')
    files=[x.decode() for x in git('ls-files','--cached','-z').split(b'\0') if x]
    if not files: raise SystemExit('暂存集合为空')
    forbidden_parts={'.runtime','.venv','.digital-human','node_modules','__pycache__','jobs','outputs','inputs','evidence','receipts','.codex'}
    text_ext={'.py','.mjs','.js','.json','.md','.txt','.html','.css','.yaml','.yml','.toml','.svg'}
    font='templates/assets/NotoSansCJKsc-Regular.otf'
    patterns=[r'sk-api-[A-Za-z0-9_-]{20,}',r'gh[pousr]_[A-Za-z0-9_]{25,}',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)(?:X-Amz-Signature|X-Goog-Signature)=[a-z0-9]{20,}',
        r'/Users/[A-Za-z0-9_.-]+/',r'(?i)[A-Z]:\\Users\\[A-Za-z0-9_.-]+\\']
    problems=[]
    for name in files:
        p=Path(name)
        if any(part in forbidden_parts for part in p.parts) or p.name in {'profile.json','secrets.json','.env'} or p.name.startswith('.env.'):
            problems.append(name+': private path');continue
        if p.suffix not in text_ext and name not in {font,'LICENSE','.gitignore'}:
            problems.append(name+': unreviewed binary/type');continue
        body=git('show',':'+name)
        if name==font:
            import hashlib
            if hashlib.sha256(body).hexdigest()!='2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b':
                problems.append(name+': font differs from licensed allowlist')
            continue
        try: content=body.decode('utf-8')
        except UnicodeDecodeError: problems.append(name+': nontext content');continue
        if any(re.search(pattern,content) for pattern in patterns):problems.append(name+': sensitive marker; value omitted')
    print(json.dumps({'ok':not problems,'staged_files':len(files),'problems':problems},ensure_ascii=False,indent=2))
    if problems: raise SystemExit(2)

if __name__=='__main__':main()
