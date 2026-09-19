"""Technical verification, explicit perceptual review, and an allowlisted asset ZIP."""
import json
import re
import zipfile
from fractions import Fraction
from pathlib import Path
from . import media
from .storage import WorkflowError, file_hash, read, write, within

def verify(job):
    video=job.artifact('render')
    if not video: raise WorkflowError('没有已完成的本地渲染')
    job.artifact('composition')
    checks=read(job.path/'checks.json')
    if not checks.get('ok'): raise WorkflowError('Hyperframes 检查未通过')
    provenance=read(job.path/'render-provenance.json')
    if provenance.get('project_sha256')!=media.project_hash(job) or provenance.get('project_sha256')!=checks.get('project_sha256') or provenance.get('video_sha256')!=file_hash(video):
        raise WorkflowError('工程、检查与渲染版本不一致，请保留已有版本并重新制作')
    info=media.probe(video);fmt=job.profile()['format'];timed=read(job.path/'timeline.json')
    v=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    a=next((s for s in info['streams'] if s['codec_type']=='audio'),None)
    if not v or not a: raise WorkflowError('成片缺少视频或音轨')
    if (v['width'],v['height']) != (fmt['width'],fmt['height']) or Fraction(v['avg_frame_rate']) != fmt['fps']:
        raise WorkflowError('成片尺寸或帧率不符')
    duration=float(info['format']['duration'])
    if abs(duration-timed['duration'])>.15: raise WorkflowError('成片与真实时间轴时长不符')
    media.run([media.binary('ffmpeg'),'-v','error','-nostdin','-i',video,'-f','null','-'],
              job.path/'evidence/full-decode.log',max(120,int(duration*3)))
    frames=[]
    for i,fraction in enumerate([.07,.25,.45,.65,.85,.96]):
        path=job.path/'evidence'/f'final-{i}.png'
        if not path.exists():
            media.run([media.binary('ffmpeg'),'-v','error','-nostdin','-ss',str(duration*fraction),
                '-i',video,'-frames:v','1','-vf','scale=540:-2',path])
        frames.append(str(path.relative_to(job.path)))
    result={'ok':True,'video_sha256':file_hash(video),'width':v['width'],'height':v['height'],
        'fps':v['avg_frame_rate'],'duration':duration,'audio_present':True,'decode':'passed',
        'frames':frames,'perceptual_review_required':['identity','voice','captions','visuals','sync']}
    write(job.path/'technical-checks.json',result)
    return result

def accept_review(job, path):
    value=read(path);technical=read(job.path/'technical-checks.json')
    if not technical.get('ok') or technical['video_sha256']!=file_hash(job.artifact('render')):
        raise WorkflowError('技术检查与当前成片不一致')
    for name in ['identity','voice','captions','visuals','sync']:
        item=value.get(name,{})
        if item.get('status')!='passed' or len(item.get('evidence','').strip())<8:
            raise WorkflowError('缺少真实验收依据：'+name)
    for ref in value.get('inspected_frames',[]):
        if not within(job.path,ref).is_file(): raise WorkflowError('验收截帧不存在')
    if not value.get('inspected_frames'):
        raise WorkflowError('必须实际查看成片截帧并记录 inspected_frames')
    value['video_sha256']=technical['video_sha256']
    write(job.path/'review.json',value)
    return {'review_recorded':True}

def safe_text(path):
    if path.suffix.lower() not in ['.html','.js','.css','.json','.txt','.md','.svg','.srt']:
        return
    text=path.read_text(encoding='utf-8')
    forbidden=[r'sk-api-[A-Za-z0-9_-]{20,}',r'gh[pousr]_[A-Za-z0-9_]{25,}',
        r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',r'(?i)X-Amz-Signature=[a-f0-9]{20,}']
    if any(re.search(pattern,text) for pattern in forbidden):
        raise WorkflowError('交付文件检测到密钥或签名URL风险：'+path.name)

def bundle(job):
    if existing:=job.artifact('delivery'): return str(existing)
    video=job.artifact('render');review=read(job.path/'review.json')
    if not video or review.get('video_sha256')!=file_hash(video):
        raise WorkflowError('验收结果不属于当前视频')
    for name in ['identity','voice','captions','visuals','sync']:
        if review.get(name,{}).get('status')!='passed': raise WorkflowError('尚未通过验收：'+name)
    mandatory=['script.txt','brief.json','storyboard.json','captions.json','timeline.json','sources.json',
        'subtitles.srt','checks.json','technical-checks.json','review.json','render-provenance.json']
    paths=set(mandatory+[str(video.relative_to(job.path))])
    for kind in ['voice','avatar','narration']:
        if artifact:=job.artifact(kind): paths.add(str(artifact.relative_to(job.path)))
    allowed={'.html','.js','.css','.json','.otf','.woff2','.txt','.svg','.png','.jpg','.jpeg','.webp','.mp3','.wav','.mp4','.webm'}
    for path in (job.path/'project').rglob('*'):
        if path.is_file() and path.suffix.lower() in allowed:
            rel=path.relative_to(job.path)
            if path.name in ['profile.json','secrets.json'] or any(x.startswith('.') for x in rel.parts):
                raise WorkflowError('工程包含私人配置或隐藏文件，不能打包')
            paths.add(str(rel))
    manifest=[]
    for rel in sorted(paths):
        p=within(job.path,rel)
        if not p.is_file(): raise WorkflowError('交付所需文件缺失：'+rel)
        safe_text(p)
        manifest.append({'path':rel,'bytes':p.stat().st_size,'sha256':file_hash(p)})
    write(job.path/'delivery-manifest.json',{'files':manifest,'video_sha256':file_hash(video)})
    target=job.path/'exports/完整素材包.zip'
    if target.exists(): raise WorkflowError('素材包已存在，请检查中断前的结果，不覆盖')
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
        for rel in sorted(paths | {'delivery-manifest.json'}): archive.write(job.path/rel,rel)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None: raise WorkflowError('素材包完整性校验失败')
    job.record('delivery',str(target.relative_to(job.path)))
    meta=job.load();meta['stage']='delivered';job.save(meta)
    return str(target)
