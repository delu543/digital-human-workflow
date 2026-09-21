"""Render the neutral timeline without requiring an installed video editor."""
import html
import json
import shutil
from .storage import ROOT, WorkflowError, read, write

def compose(job):
    if job.artifact('composition'): raise WorkflowError('此修订已有工程；另建修订，不覆盖')
    timeline=read(job.artifact('edit_timeline'));fmt=timeline['format']
    width,height=fmt['width'],fmt['height'];project=job.path/'project';assets=project/'assets'
    assets.mkdir(exist_ok=True)
    sources={}
    for aid,item in timeline['assets'].items():
        source=job.path/item['path'];name=source.name
        shutil.copy2(source,assets/name);sources[aid]='assets/'+name
    for name in ['NotoSansCJKsc-Regular.otf','OFL.txt']:shutil.copy2(ROOT/'templates/assets'/name,assets/name)
    gsap=ROOT/'node_modules/gsap/dist/gsap.min.js'
    if not gsap.is_file(): raise WorkflowError('先安装固定版本本地渲染依赖')
    shutil.copy2(gsap,assets/'gsap.min.js')
    body=[];animation=[];esc=html.escape
    for clip in timeline['clips']:
        cid=clip['id'];start=clip['start_us']/1e6;duration=clip['duration_us']/1e6
        attrs=f'id="{cid}" data-start="{start}" data-duration="{duration}" data-track-index="{clip["track"]}"'
        if clip['kind']!='text':
            attrs+=f' src="{esc(sources[clip["asset"]],quote=True)}" data-media-start="{clip["source_start"]}" data-playback-rate="{clip["speed"]}"'
        if clip['kind']=='audio':
            gain=clip['volume'];points=[{'t':0,'v':0 if clip['fade_in'] else gain}]
            if clip['fade_in']:points.append({'t':clip['fade_in'],'v':gain})
            if clip['fade_out']:
                if duration-clip['fade_out']>points[-1]['t']:points.append({'t':duration-clip['fade_out'],'v':gain})
                points.append({'t':duration,'v':0})
            elif points[-1]['t']<duration:points.append({'t':duration,'v':gain})
            automation=json.dumps({'version':1,'lanes':[{'target':'volume','points':points}]},separators=(',',':'))
            body.append(f'<audio {attrs} data-volume="{gain}" data-automation=\'{automation}\'></audio>')
            continue
        style=clip['visual'];wrapper='wrap-'+cid
        if clip['kind']=='text':
            content=f'<div {attrs} class="clip text-slot"><div class="words" style="font-size:{style["font_size"]}px;color:{style["color"]}">{esc(clip["text"])}</div></div>'
        else:
            tag='video' if clip['kind']=='video' else 'img'
            extra=' muted playsinline' if tag=='video' else ' alt=""'
            # Percent ellipses stretch with a portrait canvas. A pixel radius
            # keeps equal axes before the wrapper's uniform scale is applied.
            mask=f'clip-path:circle({min(width,height)/2}px at 50% 50%);' if style['mask']=='circle' else ''
            content=f'<{tag} {attrs} class="clip picture" style="object-fit:{style["fit"]};{mask}"{extra}>'
            if tag=='video':content+='</video>'
        body.append(f'<div id="{wrapper}" class="visual" style="z-index:{clip["track"]}">{content}</div>')
        convert={'x':lambda v:v*width/2,'y':lambda v:-v*height/2,
                 'scale':lambda v:v,'rotation':lambda v:-v,'opacity':lambda v:v}
        initial={key:convert[key](style[key]) for key in convert}
        animation.append(f'tl.set("#{wrapper}",{json.dumps(initial)},0);')
        for channel,points in style['keyframes'].items():
            for a,b in zip(points,points[1:]):
                before={channel:convert[channel](a['value'])}
                after={channel:convert[channel](b['value']),'duration':b['time']-a['time'],'ease':'none','immediateRender':False}
                animation.append(f'tl.fromTo("#{wrapper}",{json.dumps(before)},{json.dumps(after)},{start+a["time"]});')
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>数字人 · 独立后期</title><script src="assets/gsap.min.js"></script><style>
@font-face{{font-family:Narrator;src:url('assets/NotoSansCJKsc-Regular.otf')}}
*{{box-sizing:border-box}}body{{margin:0;background:#101316;color:white;font-family:Narrator,sans-serif}}
#root{{position:relative;width:100%;height:100%;overflow:hidden}}
.visual{{position:absolute;inset:0;transform-origin:center center;pointer-events:none}}
.picture{{position:absolute;inset:0;width:100%;height:100%}}
.text-slot{{position:absolute;inset:0;display:flex;justify-content:center;align-items:center}}
.words{{max-width:84%;line-height:1.4;text-align:center;white-space:pre-wrap;overflow-wrap:anywhere;
padding:6px 12px;background:rgba(0,0,0,.82);border-radius:5px}}
</style></head><body><div id="root" data-composition-id="main" data-width="{width}" data-height="{height}" data-duration="{timeline['duration']}">
{''.join(body)}</div><script>const tl=gsap.timeline({{paused:true}});
{''.join(animation)}
window.__timelines=window.__timelines||{{}};window.__timelines.main=tl;</script></body></html>'''
    (project/'index.html').write_text(page,encoding='utf-8')
    write(project/'hyperframes.json',{'name':job.path.name})
    job.record('composition','project/index.html')
    return {'project':str(project),'backend':'hyperframes','editor_required':False}
