#!/usr/bin/env python3
"""Render anonymous bilingual/framing fixtures; never synthesize or upload a person."""
import argparse
import json
from pathlib import Path
import shutil
from digital_human import caption_design, framing, media
from digital_human.storage import ROOT, WorkflowError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'.runtime/production-smoke')
    a = parser.parse_args(); base = a.out.resolve()
    if base.exists():
        raise WorkflowError('Smoke directory exists; inspect previous output before a new test')
    project = base/'project'; assets = project/'assets'; assets.mkdir(parents=True)
    ff = media.binary('ffmpeg')
    source, proxy = base/'synthetic-source.mp4', assets/'crop.mp4'
    media.run([ff, '-v', 'error', '-nostdin', '-f', 'lavfi', '-i',
               'testsrc2=size=1920x1080:rate=25:duration=8', '-c:v', 'libx264',
               '-preset', 'ultrafast', '-crf', '26', '-pix_fmt', 'yuv420p', source])
    crop = framing.plan_crop(json.loads((ROOT/'examples/presenter-framing.json').read_text(encoding='utf-8')))
    media.run([ff, '-v', 'error', '-nostdin', '-i', source, '-vf', crop['ffmpeg_filter'],
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-an', proxy])
    media.run([ff, '-v', 'error', '-nostdin', '-f', 'lavfi', '-i',
               'sine=frequency=440:sample_rate=48000:duration=8', assets/'test.wav'])
    for name in ['NotoSansCJKsc-Regular.otf', 'OFL.txt']:
        shutil.copy2(ROOT/'templates/assets'/name, assets/name)
    shutil.copy2(ROOT/'node_modules/gsap/dist/gsap.min.js', assets/'gsap.min.js')
    value = json.loads((ROOT/'examples/caption-design.json').read_text(encoding='utf-8'))
    value.update(width=1280, height=720)
    captions = caption_design.build(value)
    (project/'compositions').mkdir()
    (project/'compositions/captions.html').write_text(captions['html'], encoding='utf-8')
    (base/'subtitles.srt').write_text(captions['srt'], encoding='utf-8')
    (project/'index.html').write_text('''<!doctype html><html><head><meta charset="utf-8">
<script src="assets/gsap.min.js"></script><style>
*{box-sizing:border-box}body{margin:0;background:#182220}#fixture{width:100%;height:100%;position:relative;overflow:hidden}
#light{position:absolute;inset:0;background:#efede5;opacity:0}.slot{position:absolute;inset:0;width:100%;height:100%;z-index:20}
#circle{position:absolute;left:1030px;top:340px;width:170px;height:170px;border-radius:50%;border:2px solid #bbb;overflow:hidden}
#crop{width:100%;height:100%;object-fit:cover}#marker{position:absolute;left:70px;top:70px;width:710px;height:160px;color:#8d744a;font:400 34px/1.4 TestFont}
@font-face{font-family:TestFont;src:url('assets/NotoSansCJKsc-Regular.otf');font-weight:400}
</style></head><body><div id="fixture" data-composition-id="fixture" data-width="1280" data-height="720" data-duration="8">
<div id="light"></div><div id="marker">匿名技术测试 · 非真人样片\nBilingual caption / square crop fixture</div>
<div id="circle"><video id="crop" class="clip" src="assets/crop.mp4" data-start="0" data-duration="8" data-track-index="2" muted playsinline></video></div>
<audio id="tone" src="assets/test.wav" data-start="0" data-duration="8" data-volume="0.12"></audio>
<div id="captions" class="clip slot" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="8" data-width="1280" data-height="720" data-track-index="30"></div>
</div><script>const tl=gsap.timeline({paused:true});tl.to('#light',{opacity:1,duration:.2},4);
window.__timelines=window.__timelines||{};window.__timelines.fixture=tl;</script></body></html>''', encoding='utf-8')
    raw = media.run(['node', ROOT/'scripts/hf.mjs', 'check', project, '--json'], base/'check.log')
    check = json.loads(raw)
    if not check.get('ok'):
        raise WorkflowError('Composition check failed; inspect check.log')
    output = base/'final.mp4'
    media.run(['node', ROOT/'scripts/hf.mjs', 'render', project, '--fps', '25', '--workers', '1',
               '--quality', 'delivery', '--frames-cache-dir', 'off', '--output', output], base/'render.log', 1800)
    media.run([ff, '-v', 'error', '-i', output, '-f', 'null', '-'], base/'decode.log')
    src, dst, final = media.probe(source), media.probe(proxy), media.probe(output)
    for name in ['nb_frames', 'avg_frame_rate', 'duration']:
        if src['streams'][0][name] != dst['streams'][0][name]:
            raise WorkflowError('Square crop changed source frame timing')
    for i, point in enumerate(captions['sample_points']):
        media.run([ff, '-v', 'error', '-ss', str(point['at']), '-i', output, '-frames:v', '1', base/f'caption-{i}.png'])
    report = {'output': str(output), 'duration': final['format']['duration'],
              'caption_count': len(value['cues']), 'source_frames': src['streams'][0]['nb_frames'],
              'proxy_frame_timing_preserved': True, 'crop': crop, 'full_decode': True,
              'cloud_calls': 0, 'visual_review': 'pending actual frames', 'naturalness_tested': False}
    (base/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
