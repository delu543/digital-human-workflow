#!/usr/bin/env python3
"""Prepare and submit one anonymous four-second export; no provider or editor calls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from digital_human import editing, media
from digital_human.config import configure
from digital_human.storage import ROOT, Workspace, write


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=ROOT/'.runtime/export-smoke')
    p.add_argument('--background',action='store_true')
    a=p.parse_args();w=Workspace(a.workspace);w.initialize()
    configure(w,{'heygen':{'transport':'import'}})
    job=w.prepare('匿名技术测试，不是人物样片。',{'purpose':'synthetic export regression'},new=True)
    source=job.path/'assets/fixture.mp4'
    media.run([media.binary('ffmpeg'),'-v','error','-nostdin','-f','lavfi','-i',
               'testsrc2=size=1080x1920:rate=25:duration=4','-f','lavfi','-i',
               'sine=frequency=440:sample_rate=48000:duration=4','-c:v','libx264',
               '-preset','ultrafast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-shortest',source])
    media.import_media(job,'avatar',source)
    write(job.path/'captions.json',{'duration':4,'source':'synthetic_not_acoustic',
        'captions':[{'start':.2,'end':1.8,'text':'匿名技术测试'},{'start':2.2,'end':3.8,'text':'检查竖屏、真圆与独立导出'}]})
    job.record('captions','captions.json')
    plan={'schema':'digital-human-edit/v1','presenter':{'scale':.7},
          'overlays':[{'id':'circle-test','kind':'video','asset':'avatar','start':1,'duration':2,
                       'track':8,'visual':{'mask':'circle','fit':'cover','scale':.25,'x':.65,'y':-.55}}]}
    editing.build(job,plan,'proof');child=editing.revision(job,'proof');editing.compose(child)
    # Geometry/export regression only; this fixture does not enable motion audit.
    state=child.path/'system-export-1'
    command=[sys.executable,str(ROOT/'scripts/export_project.py'),'--project',str(child.path/'project'),
             '--output',str(child.path/'exports/final.mp4'),'--state',str(state),'--timeout','600']
    if a.background:command.append('--macos-background')
    subprocess.run(command,check=True)
    result={'job':job.path.name,'revision':'proof','workspace':str(w.path),'state':str(state),
            'cloud_calls':0,'subjective_avatar_test':False}
    write(w.path/'last-result.json',result);print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
