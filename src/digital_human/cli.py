"""CLI used by Codex. People provide scripts and preferences, not these commands."""
import argparse
import getpass
import json
from pathlib import Path
import shutil
import sys
from . import alignment, cloud, composition, delivery, media
from .config import configure, save_credential
from .storage import WorkflowError, Workspace, file_hash, read, write, within

def parser():
    p=argparse.ArgumentParser(description='数字人工作流：本地任务与云端生成协调')
    p.add_argument('--workspace',default=str(Path.cwd()/'.digital-human'))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    s=sub.add_parser('doctor');s.add_argument('--online',action='store_true')
    s=sub.add_parser('configure');s.add_argument('--file',required=True)
    s=sub.add_parser('secrets');s.add_argument('service',choices=['minimax','heygen'])
    s=sub.add_parser('prepare');s.add_argument('--script',required=True);s.add_argument('--brief');s.add_argument('--new',action='store_true')
    for name in ['status','speech','submit','poll','mcp-begin','frames','check','render','verify','bundle','seal-project']:
        s=sub.add_parser(name);s.add_argument('job')
    s=sub.add_parser('run');s.add_argument('job');s.add_argument('--storyboard');s.add_argument('--wait-seconds',type=int,default=0)
    s=sub.add_parser('import');s.add_argument('job');s.add_argument('--voice');s.add_argument('--avatar')
    s=sub.add_parser('clone-voice');s.add_argument('job');s.add_argument('--sample',required=True)
    s=sub.add_parser('record-remote');s.add_argument('job');s.add_argument('--video-id');s.add_argument('--asset-id')
    for name in ['receive','put-upload']:
        s=sub.add_parser(name);s.add_argument('job');s.add_argument('--receipt',required=True)
    s=sub.add_parser('align');s.add_argument('job');s.add_argument('--transcript');s.add_argument('--model',default='base')
    s=sub.add_parser('compose');s.add_argument('job');s.add_argument('--storyboard',required=True)
    s=sub.add_parser('review');s.add_argument('job');s.add_argument('--file',required=True)
    s=sub.add_parser('add-image');s.add_argument('job');s.add_argument('--file',required=True)
    s.add_argument('--source',required=True);s.add_argument('--rights',required=True)
    return p

def add_image(job,args):
    source=Path(args.file).resolve()
    if source.suffix.lower() not in ['.png','.jpg','.jpeg','.webp','.svg'] or not source.is_file():
        raise WorkflowError('仅接受本地图片或 SVG')
    if source.suffix.lower()=='.svg':
        import re
        text=source.read_text(encoding='utf-8')
        if re.search(r'<script|<foreignObject|\bon\w+\s*=|(?:href|src)\s*=\s*["\'](?:https?:|file:|javascript:)',text,re.I):
            raise WorkflowError('SVG 包含脚本或外部引用，请先转换为静态图片')
    if not args.source.strip() or not args.rights.strip(): raise WorkflowError('必须记录来源与使用权')
    relative='assets/image-'+file_hash(source)[:16]+source.suffix.lower()
    target=within(job.path,relative)
    if not target.exists(): shutil.copy2(source,target)
    sources=read(job.path/'sources.json')
    if not any(s['path']==relative for s in sources):
        sources.append({'path':relative,'source':args.source,'rights':args.rights});write(job.path/'sources.json',sources)
    return {'path':relative}

def execute(args):
    w=Workspace(args.workspace)
    if args.command=='init': return w.initialize()
    if args.command=='doctor':
        from .doctor import doctor
        return doctor(w,args.online)
    if args.command=='configure': return configure(w,read(args.file))
    if args.command=='secrets':
        if not sys.stdin.isatty(): raise WorkflowError('请在用户本地终端运行 secrets 命令；不要把密钥放入聊天或命令参数')
        return save_credential(w,args.service,getpass.getpass('API Key（输入隐藏）: ').strip())
    if args.command=='prepare':
        job=w.prepare(Path(args.script).read_text(encoding='utf-8'),read(args.brief) if args.brief else {},args.new)
        return {'job_id':job.path.name,'path':str(job.path),'state':job.load()['stage']}
    job=w.job(args.job)
    with job.locked():
        return execute_job(job,args)

def execute_job(job,args):
    c=args.command
    if c=='status': return job.load()
    if c=='speech': return cloud.speech(job)
    if c=='submit': return cloud.submit_avatar(job)
    if c=='poll': return cloud.poll_avatar(job)
    if c=='mcp-begin': return cloud.mcp_begin(job)
    if c=='record-remote': return cloud.record_remote(job,args.video_id,args.asset_id)
    if c=='receive': return cloud.receive_avatar(job,read(args.receipt))
    if c=='put-upload':
        from .budget import require_consent
        from .network import put_presigned
        require_consent(job,['heygen'])
        slot=cloud.unwrap(read(args.receipt));voice=job.artifact('voice')
        if not voice: raise WorkflowError('无配音素材')
        result=put_presigned(slot['upload_url'],voice,slot.get('upload_headers',{'Content-Type':'audio/mpeg'}))
        return {**result,'asset_id':slot['asset_id'],'next':'Call official complete_asset_upload, then record-remote --asset-id.'}
    if c=='import':
        if not args.voice and not args.avatar: raise WorkflowError('至少提供 voice 或 avatar')
        return {kind:str(media.import_media(job,kind,path)) for kind,path in [('voice',args.voice),('avatar',args.avatar)] if path}
    if c=='clone-voice':
        from .cloning import clone_voice
        return clone_voice(job,args.sample)
    if c=='frames': return media.frame(job)
    if c=='align': return alignment.align(job,args.transcript,args.model)
    if c=='add-image': return add_image(job,args)
    if c=='compose': return composition.compose(job,args.storyboard)
    if c=='seal-project':
        if job.artifact('render'): raise WorkflowError('已渲染的版本不能覆盖，请新建任务并导入已有音视频')
        job.record('composition','project/index.html');return {'saved':True}
    if c=='check': return media.hf(job,'check')
    if c=='render':
        if existing:=job.artifact('render'): return str(existing)
        job.artifact('composition')
        if not (job.path/'checks.json').exists() or not read(job.path/'checks.json').get('ok'):
            raise WorkflowError('先通过 check')
        return media.hf(job,'render',timeout=3600)
    if c=='verify': return delivery.verify(job)
    if c=='review': return delivery.accept_review(job,args.file)
    if c=='bundle': return delivery.bundle(job)
    if c=='run':
        from .runner import run
        return run(job,args.storyboard,args.wait_seconds)
    raise WorkflowError('未知命令')

def main(argv=None):
    args=parser().parse_args(argv)
    try:
        result=execute(args)
    except WorkflowError as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));raise SystemExit(2)
    except (FileNotFoundError,KeyError,TypeError,ValueError):
        print(json.dumps({'ok':False,'error':'输入文件缺失或格式不符；检查当前阶段所需文件，不重放付费请求。'},ensure_ascii=False));raise SystemExit(2)
    print(json.dumps({'ok':True,'result':result},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
