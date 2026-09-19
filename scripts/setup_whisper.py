#!/usr/bin/env python3
"""Install pinned local acoustic alignment, or register an existing verified runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE_SHA='57e280cee375ab02425b806ad5146b99f6eb9357e3c2b31357c8a6af2e2e44ae'
MODEL_SHA='60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def fetch(url,path,expected):
    if not path.exists():
        partial=path.with_suffix(path.suffix+'.partial')
        with urlopen(url,timeout=90) as response, partial.open('wb') as out:
            shutil.copyfileobj(response,out)
        if sha(partial)!=expected: raise SystemExit('下载校验不符，保留文件供检查，未执行')
        os.replace(partial,path)
    if sha(path)!=expected: raise SystemExit('已有文件校验不符，不覆盖或执行')
    return path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executable');p.add_argument('--model-file')
    a=p.parse_args();runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
    if bool(a.executable)!=bool(a.model_file): raise SystemExit('同时提供 --executable 和 --model-file')
    if a.executable:
        executable=Path(a.executable).expanduser().resolve();model=Path(a.model_file).expanduser().resolve()
        if not executable.is_file() or not model.is_file() or sha(model)!=MODEL_SHA:
            raise SystemExit('缺少可执行文件或 base 模型校验不符')
    else:
        if not (shutil.which('c++') or shutil.which('clang++') or shutil.which('g++') or shutil.which('cl')):
            raise SystemExit('需要 C++ 编译器。macOS 安装 Xcode Command Line Tools；Linux 安装 build-essential；Windows 建议 WSL2。')
        archive=fetch('https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v1.9.4',runtime/'whisper-v1.9.4.tar.gz',ARCHIVE_SHA)
        source=runtime/'whisper.cpp-1.9.4'
        if not source.exists():
            with tarfile.open(archive) as tar:
                for member in tar.getmembers():
                    dest=(runtime/member.name).resolve()
                    if not dest.is_relative_to(runtime.resolve()) or member.issym() or member.islnk():
                        raise SystemExit('源代码压缩包包含不安全路径')
                tar.extractall(runtime,filter='data')
        cmake=shutil.which('cmake')
        with (runtime/'whisper-install.log').open('ab') as log:
            def run(command):
                subprocess.run([str(x) for x in command],check=True,stdout=log,stderr=log,timeout=1200)
            if not cmake:
                run([sys.executable,'-m','pip','install','cmake==4.1.0'])
                cmake=Path(sys.executable).parent/('cmake.exe' if os.name=='nt' else 'cmake')
            run([cmake,'-S',source,'-B',source/'build','-DCMAKE_BUILD_TYPE=Release','-DWHISPER_BUILD_TESTS=OFF'])
            run([cmake,'--build',source/'build','--config','Release','--target','whisper-cli','-j','4'])
        options=[source/'build/bin/whisper-cli',source/'build/bin/Release/whisper-cli.exe',source/'build/bin/whisper-cli.exe']
        executable=next((x for x in options if x.is_file()),None)
        if not executable: raise SystemExit('编译完成但未找到 whisper-cli；检查安装日志')
        model=fetch('https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin',runtime/'ggml-base.bin',MODEL_SHA)
    check=subprocess.run([str(executable),'--help'],capture_output=True,timeout=30)
    if b'--dtw' not in check.stdout+check.stderr or b'--no-flash-attn' not in check.stdout+check.stderr:
        raise SystemExit('whisper-cli 缺少本工作流所需 DTW 参数')
    result={'version':'1.9.4','executable':str(executable),'models':{'base':str(model)},'base_sha256':MODEL_SHA}
    (runtime/'whisper.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'local_alignment':'base DTW','cloud_upload':False}))

if __name__=='__main__': main()
