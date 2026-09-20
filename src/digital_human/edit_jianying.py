"""Optional native draft handoff using two attributed, pure MIT serializers.

Does not launch an editor, modify its index, decrypt drafts, or call native libraries.
"""
from copy import deepcopy
from pathlib import Path
import shutil
import uuid
from .edit_timeline import require
from .storage import file_hash, read, write, within
from .vendor.jianying.native import build_native

def native_plan(timeline, name):
    fmt=timeline['format'];clips=[]
    for clip in timeline['clips']:
        kind=clip['kind'];duration=clip['duration_us']/1e6
        item={'id':clip['id'],'kind':kind,'track':f'{clip["track"]:03d}-{clip["role"]}',
              'start':clip['start_us']/1e6,'duration':duration,'source_start':clip.get('source_start',0),
              'speed':clip.get('speed',1),'volume':clip.get('volume',0),'x':0,'y':0}
        if kind=='text':item.update(text=clip['text'],font_size=clip['visual']['font_size'],color=clip['visual']['color'],
            text_style={'background_color':'#000000','background_opacity':.82,'alignment':'center'})
        else:
            asset=timeline['assets'][clip['asset']]
            item.update(path=asset['path'],media_duration=asset['duration'],media_width=asset['width'],
                        media_height=asset['height'],has_audio=asset['has_audio'])
        if kind=='audio': item['audio_fade']={'in':clip['fade_in'],'out':clip['fade_out']}
        else:
            style=clip['visual']
            require(style['mask']=='none','此剪映适配器未验证蒙版资源；使用 Hyperframes 或明确改为无蒙版的新修订')
            item['transform']={key:style[key] for key in ['x','y','rotation','opacity']}
            item['transform'].update(scale_x=style['scale'],scale_y=style['scale'])
            item['keyframes']={}
            for channel,points in style['keyframes'].items():
                for prop in (['scale_x','scale_y'] if channel=='scale' else [channel]):item['keyframes'][prop]=deepcopy(points)
            if kind in ['video','image'] and style['fit']=='cover':
                aspect=asset['width']/asset['height'];target=fmt['width']/fmt['height']
                x=max(0,(1-target/aspect)/2);y=max(0,(1-aspect/target)/2)
                item['crop']={'left':x,'right':1-x,'top':y,'bottom':1-y}
        clips.append(item)
    return {'id':str(uuid.uuid4()),'name':name,'width':fmt['width'],'height':fmt['height'],'fps':fmt['fps'],'clips':clips}

def create_files(portable, root):
    plan=deepcopy(portable)
    for clip in plan['clips']:
        if 'path' in clip:clip['path']=str(within(root,clip['path']))
    files=build_native(plan,root.resolve())
    for name,data in files.items():write(root/name,data)
    write(root/'portable-plan.json',portable)
    entries=[{'path':str(p.relative_to(root)),'sha256':file_hash(p)} for p in sorted(root.rglob('*')) if p.is_file()]
    report={'schema':'digital-human-jianying-handoff/v1','files':entries,'native_app_verified':False,
        'compatibility':'experimental; exact Mac Jianying version needs open/edit/save/reopen/export acceptance',
        'limits':['No GUI bidirectional sync or arbitrary encrypted draft editing.',
                  'Native text is editable; font/layout may differ from Hyperframes. Inspect the native export.',
                  'No account, effect cache, member resource or native application is distributed.'],
        'registration':'New draft directory only; Codex must use the target editor UI to import/open it.',
        'relocation':'After moving, use relink-draft --source <this directory> --out <new directory>.'}
    write(root/'draft-manifest.json',report)
    return report

def export(job):
    require(not job.artifact('delivery'),'此修订已交付；另建修订添加剪映工程，旧素材包不会自动更新')
    require(not job.load().get('custom_hyperframes'),'HTML 自定义效果未映射到共享时间轴；选择本地成片或在新剪辑计划中表达对应效果')
    timeline=read(job.artifact('edit_timeline'));portable=native_plan(timeline,job.path.name)
    root=job.path/'exports/jianying';require(not root.exists(),'剪映交接目录已存在，不覆盖')
    # Validate the serializer before any material copies, using future absolute paths.
    check=deepcopy(portable)
    for c in check['clips']:
        if 'path' in c:c['path']=str((job.path/c['path']).resolve())
    build_native(check,root.resolve())
    (root/'Resources').mkdir(parents=True,exist_ok=False)
    paths={}
    for c in portable['clips']:
        if 'path' not in c:continue
        original=c['path']
        if original not in paths:
            source=within(job.path,original);relative='Resources/'+source.name
            shutil.copy2(source,root/relative);paths[original]=relative
        c['path']=paths[original]
    report=create_files(portable,root)
    job.record('jianying_draft','exports/jianying/draft-manifest.json')
    return {'directory':str(root),'native_app_verified':False,'clips':len(portable['clips']),'limits':report['limits']}

def relink(source, target):
    """Rebuild paths in a NEW copied handoff; never overwrite a manually edited draft."""
    source=Path(source).expanduser().resolve();target=Path(target).expanduser().resolve()
    require(source!=target and not target.is_relative_to(source) and not target.exists(),'重定位须使用全新独立目录')
    report=read(source/'draft-manifest.json')
    require(report.get('schema')=='digital-human-jianying-handoff/v1','不是本工具的剪映交接包')
    for item in report['files']:
        require(file_hash(within(source,item['path']))==item['sha256'],'草稿或素材已经手改；不能用旧计划覆盖，请在剪映继续编辑')
    plan=read(source/'portable-plan.json');target.mkdir(parents=True,exist_ok=False)
    for path in {c['path'] for c in plan['clips'] if 'path' in c}:
        original=within(source,path);dest=within(target,path);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dest)
    plan['id']=str(uuid.uuid4());plan['name']=target.name
    create_files(plan,target)
    return {'directory':str(target),'native_app_verified':False,'source_unchanged':True}
