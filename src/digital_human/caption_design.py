"""Build bilingual SRT and a seekable caption layer from the same acoustic cues."""
import html
import json
import re
from pathlib import PurePosixPath
from .production_audit import number, records
from .storage import WorkflowError


def local_path(value):
    if not isinstance(value, str) or not value or not re.fullmatch(r'[A-Za-z0-9_./-]+', value):
        raise WorkflowError('Use a portable local font path')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts:
        raise WorkflowError('Font path must stay inside project')
    return value


def timestamp(value):
    ms = round(value*1000)
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def build(value):
    duration = number(value.get('duration'), 'duration', .001)
    width, height = value.get('width'), value.get('height')
    if any(type(n) is not int or n < 64 for n in (width, height)):
        raise WorkflowError('Canvas dimensions required')
    fps = number(value.get('fps', 25), 'fps', 1)
    cid = value.get('composition_id', 'captions')
    if not isinstance(cid, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', cid):
        raise WorkflowError('Invalid composition_id')
    cues = sorted(records(value, 'cues', duration), key=lambda x: x['start'])
    if any(a['end'] > b['start'] for a, b in zip(cues, cues[1:])):
        raise WorkflowError('Caption cues overlap; fix acoustic segmentation before layout')
    scale = min(width, height)/1080
    style = value.get('style', {})
    psize = number(style.get('primary_size', 40*scale), 'primary_size', 1)
    ssize = number(style.get('secondary_size', 31*scale), 'secondary_size', 1)
    bottom = number(style.get('bottom', 62*scale), 'bottom')
    safe = number(style.get('side_safe', width*.055), 'side_safe')
    if safe*2 >= width or bottom >= height*.5 or max(psize, ssize) > min(width, height)*.15:
        raise WorkflowError('Caption style exceeds usable frame')
    fonts = value.get('fonts', {})
    primary = local_path(fonts.get('primary', 'assets/NotoSansCJKsc-Regular.otf'))
    secondary = local_path(fonts.get('secondary', primary))
    body, motion, srt, points = [], [], [], []
    for i, cue in enumerate(cues):
        first, second = cue.get('primary'), cue.get('secondary', '')
        if not isinstance(first, str) or not first.strip() or not isinstance(second, str):
            raise WorkflowError('Each cue requires primary text; secondary may be empty')
        if any('\n\n' in t or '\r' in t for t in (first, second)):
            raise WorkflowError('Use single newlines only for reviewed line breaks')
        if timestamp(cue['start']) == timestamp(cue['end']):
            raise WorkflowError('Cue is shorter than SRT resolution')
        theme = cue.get('theme', 'dark')
        if theme not in ('dark', 'light'):
            raise WorkflowError('Caption theme must match a dark or light background')
        identity = cid+'-'+cue['id']; content = identity+'-text'
        body.append(f'<div id="{identity}" class="clip caption {theme}" data-start="{cue["start"]}" '
                    f'data-duration="{cue["end"]-cue["start"]}" data-track-index="30">'
                    f'<div class="caption-text" id="{content}"><div class="primary">{html.escape(first)}</div>'
                    + (f'<div class="secondary">{html.escape(second)}</div>' if second else '') + '</div></div>')
        fade = min(2/fps, (cue['end']-cue['start'])/4)
        motion.append(f'tl.fromTo("#{content}",{{opacity:0,y:2}},'
                      f'{{opacity:1,y:0,duration:{fade},ease:"power1.out"}},{cue["start"]});')
        motion.append(f'tl.to("#{content}",{{opacity:0,duration:{fade}}},{cue["end"]-fade});')
        srt.append(f'{i+1}\n{timestamp(cue["start"])} --> {timestamp(cue["end"])}\n'
                   + first + ('\n'+second if second else '')+'\n')
        points.append({'id': cue['id'], 'at': cue['start']+min(.45, (cue['end']-cue['start'])/2),
                       'primary': first, 'secondary': second})
    page = f'''<template><div id="{cid}" data-composition-id="{cid}" data-width="{width}" data-height="{height}" data-duration="{duration}">
<style>
@font-face{{font-family:CaptionPrimary;src:url('{primary}');font-weight:400}}
@font-face{{font-family:CaptionSecondary;src:url('{secondary}');font-weight:400}}
#{cid}{{position:relative;width:100%;height:100%;pointer-events:none}}
#{cid} *{{box-sizing:border-box}}
#{cid} .caption{{position:absolute;inset:0;display:flex;align-items:flex-end;justify-content:center;padding:0 {safe}px {bottom}px}}
#{cid} .caption-text{{max-width:100%;text-align:center;opacity:0;font-kerning:normal}}
#{cid} .primary{{font:400 {psize}px/1.32 CaptionPrimary;letter-spacing:{.5*scale}px;white-space:pre-wrap}}
#{cid} .secondary{{font:400 {ssize}px/1.38 CaptionSecondary;letter-spacing:0;margin-top:{12*scale}px;white-space:pre-wrap}}
#{cid} .dark{{color:#faf8f2;text-shadow:0 2px 8px rgba(0,0,0,.8)}}
#{cid} .light{{color:#202c28;text-shadow:none}}
</style>
{''.join(body)}
<script>const tl=gsap.timeline({{paused:true}});{''.join(motion)}
window.__timelines=window.__timelines||{{}};window.__timelines[{json.dumps(cid)}]=tl;</script>
</div></template>'''
    return {'html': page, 'srt': '\n'.join(srt), 'sample_points': points,
            'fonts_required': list(dict.fromkeys([primary, secondary]))}
