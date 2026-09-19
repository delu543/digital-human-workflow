"""A small, editable Hyperframes renderer for speech, illustrations and diagrams."""
import html
import math
import re
import shutil
from pathlib import Path
from . import media
from .alignment import srt
from .storage import ROOT, WorkflowError, read, write, within

def scene_times(plan, cues, duration):
    scenes=plan.get('scenes',[])
    if not scenes: raise WorkflowError('需要 Codex 按语义编排 storyboard.json，不自动把段落当成分镜')
    result=[];previous=-1
    for i,scene in enumerate(scenes):
        at=scene.get('start_caption')
        if type(at) is not int or not 0<=at<len(cues) or at<=previous:
            raise WorkflowError('分镜 start_caption 必须是递增的有效字幕序号（从0开始）')
        previous=at
        if scene.get('kind','title') not in ['title','steps','bars','image']:
            raise WorkflowError('不支持的分镜类型；复杂动画可在已生成 Hyperframes 工程中继续编辑')
        result.append({**scene,'start':0 if i==0 else cues[at]['start']})
    for i,scene in enumerate(result):
        scene['end']=result[i+1]['start'] if i+1<len(result) else duration
    return result

def compose(job, storyboard):
    if job.artifact('composition'): raise WorkflowError('工程版本已存在；请新建任务或手动保留新版本后修改')
    captions=job.artifact('captions');avatar=job.artifact('avatar')
    if not captions or not avatar: raise WorkflowError('需要真人视频和真实时间轴字幕')
    timed=read(captions);cues=timed['captions'];duration=timed['duration']
    plan=read(storyboard);scenes=scene_times(plan,cues,duration)
    profile=job.profile()
    layout=plan.get('layout',{});top=layout.get('title_top',.11)
    caption_top=layout.get('caption_top',.60 if profile['style']['caption_position']=='middle' else .79)
    if any(type(v) not in [int,float] or not math.isfinite(v) for v in [top,caption_top]) or not 0<=top<=.65 or not .2<=caption_top<=.85:
        raise WorkflowError('分镜布局坐标必须是有效画面比例')
    fmt=profile['format'];width,height=fmt['width'],fmt['height']
    project=job.path/'project';assets=project/'assets';assets.mkdir(exist_ok=True)
    # Dense keyframes make deterministic frame-by-frame seeking reliable.
    editable=assets/'presenter.mp4'
    if not editable.exists():
        media.run([media.binary('ffmpeg'),'-v','error','-nostdin','-i',avatar,'-an','-c:v','libx264','-preset','fast',
            '-crf','18','-pix_fmt','yuv420p','-g',str(fmt['fps']),'-keyint_min',str(fmt['fps']),'-sc_threshold','0',
            '-movflags','+faststart',editable],job.path/'evidence/prepare-video.log',timeout=max(600,int(duration*10)))
    shutil.copy2(media.narration(job),assets/'narration.wav')
    for name in ['NotoSansCJKsc-Regular.otf','OFL.txt']:
        shutil.copy2(ROOT/'templates/assets'/name,assets/name)
    gsap=ROOT/'node_modules/gsap/dist/gsap.min.js'
    if not gsap.exists(): raise WorkflowError('先安装固定版本的本地 Node 依赖')
    shutil.copy2(gsap,assets/'gsap.min.js')
    esc=html.escape
    parts=[f'<video id="presenter" class="clip presenter" src="assets/presenter.mp4" muted playsinline data-start="0" data-duration="{duration}" data-track-index="0"></video>',
        f'<audio id="narration" src="assets/narration.wav" data-start="0" data-duration="{duration}" data-track-index="1"></audio>']
    animations=[];sources=read(job.path/'sources.json')
    credited={s['path'] for s in sources if s.get('rights') and s.get('source')}
    for i,scene in enumerate(scenes):
        kind=scene.get('kind','title');start,end=scene['start'],scene['end']
        title=esc(str(scene.get('title','')));body=''
        if kind=='image':
            relative=scene.get('image','')
            if relative not in credited: raise WorkflowError('配图缺少来源和使用权记录：'+relative)
            source=within(job.path,relative)
            if source.suffix.lower() not in ['.png','.jpg','.jpeg','.webp','.svg'] or not source.is_file():
                raise WorkflowError('配图格式或文件无效')
            name=f'visual-{i}'+source.suffix.lower();shutil.copy2(source,assets/name)
            body=f'<img class="illustration" src="assets/{name}" alt="">'
        elif kind=='steps':
            items=scene.get('items',[])
            if not 1<=len(items)<=4: raise WorkflowError('步骤图需要1至4项')
            body='<div class="steps">'+''.join(f'<div class="step"><b>{n+1:02}</b><span>{esc(str(t))}</span></div>' for n,t in enumerate(items))+'</div>'
        elif kind=='bars':
            items=scene.get('items',[])
            if not 1<=len(items)<=4 or not scene.get('source'): raise WorkflowError('图表需要1至4项及数据来源')
            values=[x['value'] for x in items]
            if any(type(v) not in [int,float] or not math.isfinite(v) or v<0 for v in values) or max(values)<=0:
                raise WorkflowError('柱形图数值无效，不能编造或默认为0')
            body='<div class="bars">'+''.join(f'<div class="bar-row"><span>{esc(str(x["label"]))}</span><div class="bar" style="width:{x["value"]/max(values)*100:.2f}%"></div><b>{esc(str(x["value"]))}</b></div>' for x in items)+'</div>'
        title=title.replace('\n','<br>')
        content=f'<div class="eyebrow">{esc(str(scene.get("label","")))}</div><h1>{title}</h1><div class="accent"></div>{body}<p>{esc(str(scene.get("detail","")))}</p>'
        parts.append(f'<section id="scene-{i}" class="clip scene {kind}" data-start="{start}" data-duration="{end-start}" data-track-index="2"><div class="scene-inner" id="inner-{i}">{content}</div></section>')
        animations.append(f'tl.fromTo("#inner-{i}",{{y:18,opacity:0}},{{y:0,opacity:1,duration:.3,ease:"power3.out"}},{start});')
        animations.append(f'tl.fromTo("#inner-{i} .accent",{{scaleX:0}},{{scaleX:1,duration:.4,ease:"power3.out"}},{start+.08});')
        if kind in ['steps','bars']:
            selector='.step' if kind=='steps' else '.bar'
            animations.append(f'tl.fromTo("#inner-{i} {selector}",{{opacity:0,x:-12}},{{opacity:1,x:0,duration:.3,stagger:.08}},{start+.15});')
    keywords=plan.get('keywords',[])
    for i,cue in enumerate(cues):
        text=esc(cue['text'])
        for word in sorted(keywords,key=len,reverse=True):
            if word and word in cue['text']:
                text=text.replace(esc(word),'<em>'+esc(word)+'</em>',1);break
        start,end=cue['start'],cue['end']
        parts.append(f'<div id="caption-{i}" class="clip caption" data-start="{start}" data-duration="{end-start}" data-track-index="3"><div id="caption-inner-{i}" class="caption-inner">{text}</div></div>')
        animations.append(f'tl.fromTo("#caption-inner-{i}",{{y:7,opacity:0}},{{y:0,opacity:1,duration:.1,ease:"power2.out"}},{start});')
    parts.append('<div id="progress"></div>')
    animations.append(f'tl.fromTo("#progress",{{scaleX:0}},{{scaleX:1,duration:{duration},ease:"none"}},0);')
    page=(ROOT/'templates/portrait.html').read_text(encoding='utf-8')
    values={'WIDTH':width,'HEIGHT':height,'DURATION':duration,'ACCENT':profile['style']['accent'],
        'TITLE_TOP':top*height,'CAPTION_TOP':caption_top*height,'SCALE':width/720,
        'PRESET':profile['style']['preset'],'CONTENT':'\n'.join(parts),'ANIMATION':'\n'.join(animations)}
    for key,value in values.items(): page=page.replace('%%'+key+'%%',str(value))
    (project/'index.html').write_text(page,encoding='utf-8')
    write(project/'hyperframes.json',{'name':job.path.name})
    write(job.path/'storyboard.json',plan)
    write(job.path/'timeline.json',{'duration':duration,'narration':'assets/narration.wav','avatar':str(avatar.relative_to(job.path)),
        'captions':cues,'scenes':scenes})
    (job.path/'subtitles.srt').write_text(srt(cues),encoding='utf-8')
    job.record('composition','project/index.html')
    return str(project)
