"""Immutable local postproduction revisions; never submit generation requests."""
import json
from pathlib import Path
import re
import shutil
from . import media
from .alignment import srt
from .edit_timeline import compile_plan, require
from .storage import Job, WorkflowError, file_hash, now, read, write, within

def describe(path, kind):
    path=Path(path)
    info=json.loads(media.run([media.binary('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',path]))
    wanted='audio' if kind=='audio' else 'video'
    stream=next((s for s in info.get('streams',[]) if s.get('codec_type')==wanted),None)
    require(stream is not None,'素材缺少所需音视频轨道')
    require(not stream.get('tags',{}).get('rotate') and not any(abs(s.get('rotation',0))>.01 for s in stream.get('side_data_list',[])), '素材有旋转元数据，请先规范方向并检查')
    duration=0 if kind=='image' else float(info['format']['duration'])
    require(kind=='image' or duration>0,'素材时长无效')
    return {'kind':kind,'duration':duration,'width':stream.get('width',0),'height':stream.get('height',0),
            'sha256':file_hash(path),'has_audio':any(s.get('codec_type')=='audio' for s in info['streams'])}

def add_asset(job, filename, kind, source, rights):
    path=Path(filename).expanduser().resolve()
    extensions={'video':{'.mp4','.mov','.webm'},'audio':{'.wav','.mp3','.m4a'},'image':{'.png','.jpg','.jpeg','.webp'}}
    require(kind in extensions and path.is_file() and path.suffix.lower() in extensions[kind],'素材格式无效')
    require(source.strip() and rights.strip(),'需要素材来源和使用权记录')
    meta=describe(path,kind);aid='asset-'+meta['sha256'][:20]
    relative='assets/'+aid+path.suffix.lower();target=within(job.path,relative)
    if target.exists(): require(file_hash(target)==meta['sha256'],'已登记素材内容变化')
    else: shutil.copy2(path,target)
    registry=read(job.path/'edit-assets.json') if (job.path/'edit-assets.json').exists() else {}
    meta.update(path=relative,source=source,rights=rights);registry[aid]=meta
    write(job.path/'edit-assets.json',registry)
    sources=read(job.path/'sources.json')
    if not any(s['path']==relative for s in sources):
        sources.append({'path':relative,'source':source,'rights':rights});write(job.path/'sources.json',sources)
    return {'asset':aid,**meta}

def revision(job, name):
    require(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,49}',name),'修订名需为简短英文/数字标识')
    root=within(job.path,'edits/'+name)
    require((root/'job.json').is_file(),'未找到剪辑修订')
    result=Job(root,job.workspace)
    require(result.load().get('edit_version')==1,'不是剪辑修订')
    result.artifact('edit_timeline');result.artifact('edit_plan')
    for item in read(result.artifact('edit_timeline'))['assets'].values():
        require(file_hash(within(root,item['path']))==item['sha256'],'剪辑素材已变化，不能复用旧检查')
    return result

def build(job, plan, name):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,49}',name) is not None,'无效剪辑修订名')
    target=within(job.path,'edits/'+name);require(not target.exists(),'修订已存在；使用新名称，保留原交付')
    avatar=job.artifact('avatar');captions=job.artifact('captions')
    require(avatar is not None and captions is not None,'先准备干净数字人视频与真实音频对齐字幕')
    voice=media.narration(job);timed=read(captions);duration=timed['duration']
    registry=read(job.path/'edit-assets.json') if (job.path/'edit-assets.json').exists() else {}
    assets={key:{**describe(path,kind),'path':str(path.relative_to(job.path)),
                 'source':'parent job '+key,'rights':'same authorized digital-human job'}
            for key,path,kind in [('avatar',avatar,'video'),('narration',voice,'audio')]}
    require(all(abs(assets[k]['duration']-duration)<=.15 for k in assets),'人物、配音与字幕时长不一致')
    for key,item in registry.items():
        require(key not in assets,'素材 ID 冲突')
        path=within(job.path,item['path'])
        require(path.is_file() and file_hash(path)==item['sha256'],'补充素材已变化，请重新登记')
        assets[key]=item
    timeline=compile_plan(plan,duration,timed['captions'],job.profile()['format'],assets)
    used={c['asset'] for c in timeline['clips'] if 'asset' in c}
    timeline['assets']={k:v for k,v in assets.items() if k in used}
    for folder in ['assets','project','exports','evidence']:(target/folder).mkdir(parents=True,exist_ok=False)
    for key,item in timeline['assets'].items():
        path=within(job.path,item['path']);relative='assets/'+key+path.suffix.lower()
        shutil.copy2(path,target/relative);item['path']=relative
    shutil.copy2(job.path/'script.txt',target/'script.txt');shutil.copy2(job.path/'profile.json',target/'profile.json')
    write(target/'job.json',{'schema_version':1,'quality_version':job.load().get('quality_version',1),'edit_version':1,
        'id':name,'created_at':now(),'script_sha256':file_hash(target/'script.txt'),
        'profile_sha256':file_hash(target/'profile.json'),'stage':'edit_ready','artifacts':{},'operations':{},'remote':{}})
    child=Job(target,job.workspace)
    for key in ['avatar','narration']:child.record(key,timeline['assets'][key]['path'])
    write(target/'edit-plan.json',plan);write(target/'timeline.json',timeline)
    write(target/'edit-lineage.json',{'parent_job':job.path.name,'parent_avatar_sha256':file_hash(avatar),
        'parent_captions_sha256':file_hash(captions),'source_script_unchanged':True,'cloud_calls':0})
    write(target/'brief.json',{**read(job.path/'brief.json'),'postproduction':{'mode':'independent'}})
    write(target/'storyboard.json',{'kind':'compiled-edit-plan','plan':'edit-plan.json'})
    write(target/'captions.json',{'duration':timeline['duration'],'source':'mapped-parent-acoustic-cues','captions':timeline['captions']})
    write(target/'sources.json',[{'path':v['path'],'source':v['source'],'rights':v['rights']} for v in timeline['assets'].values()])
    (target/'subtitles.srt').write_text(srt(timeline['captions']),encoding='utf-8')
    child.record('edit_plan','edit-plan.json');child.record('edit_timeline','timeline.json');child.record('captions','captions.json')
    return {'revision':name,'path':str(target),'duration':timeline['duration'],'clips':len(timeline['clips']),
            'cloud_calls':0,'next':'edit-compose, edit-render, edit-verify, then review and deliver'}

def compose(child):
    from .edit_hyperframes import compose as render_project
    return render_project(child)
