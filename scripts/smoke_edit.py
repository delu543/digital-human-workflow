#!/usr/bin/env python3
"""Exercise digital-avatar postproduction using synthetic media, without cloud calls."""
from pathlib import Path
import argparse
from digital_human import editing, media, delivery
from digital_human.config import configure
from digital_human.storage import ROOT, Workspace, write, read

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=ROOT/'.runtime/edit-smoke')
    args=parser.parse_args();workspace=Workspace(args.workspace);workspace.initialize()
    configure(workspace,{'heygen':{'transport':'import'}})
    job=workspace.prepare('合成测试画面，不是数字人样片。',{'purpose':'synthetic technical fixture'},new=True)
    print('Job '+job.path.name,flush=True)
    ff=media.binary('ffmpeg');video=job.path/'assets/fixture.mp4'
    media.run([ff,'-v','error','-nostdin','-f','lavfi','-i','testsrc2=size=1080x1920:rate=25:duration=8',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=8',
        '-c:v','libx264','-preset','ultrafast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-shortest',video])
    media.import_media(job,'avatar',video)
    cues=[{'start':i*2+.2,'end':i*2+1.6,'text':f'合成测试 · 原片第{i+1}段'} for i in range(4)]
    write(job.path/'captions.json',{'duration':8,'captions':cues,'source':'synthetic_fixture_not_acoustic'})
    job.record('captions','captions.json')
    insert=job.path/'assets/insert.mp4';music=job.path/'assets/music.wav'
    media.run([ff,'-v','error','-nostdin','-f','lavfi','-i','color=c=0x345445:s=1080x1920:r=25:d=3',
               '-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',insert])
    media.run([ff,'-v','error','-nostdin','-f','lavfi','-i','sine=frequency=220:sample_rate=48000:duration=8',music])
    a=editing.add_asset(job,insert,'video','synthetic local test','original test fixture')['asset']
    b=editing.add_asset(job,music,'audio','synthetic local test','original test fixture')['asset']
    plan={'schema':'digital-human-edit/v1','ranges':[
        {'start':4,'end':8,'visual':{'keyframes':{'scale':[{'time':0,'value':1},{'time':4,'value':1.06}]}}},
        {'start':0,'end':4}],
        'overlays':[{'id':'broll','kind':'video','asset':a,'start':2,'duration':2},
            {'id':'title','kind':'text','text':'独立后期 · 技术测试','start':.2,'duration':1.5,'visual':{'y':.55,'font_size':55}},
            {'id':'insert-title','kind':'text','text':'插片期间，人声保持连续','start':2,'duration':2,'visual':{'y':.35}}],
        'audio':[{'asset':b,'start':0,'duration':8,'volume':.15,'fade_in':.5,'fade_out':.5}]}
    write(job.path/'requested-edit.json',plan);editing.build(job,plan,'v1')
    child=editing.revision(job,'v1');editing.compose(child)
    print('Built local timeline and Hyperframes project',flush=True)
    native=editing.export(child);print('Native draft structure generated; application NOT verified',flush=True)
    checks=media.hf(child,'check');print('Check '+str(checks['ok']),flush=True)
    media.hf(child,'render',timeout=3600);result=delivery.verify(child)
    report={'job_id':job.path.name,'revision':'v1','technical':result,'native_draft':native,
            'cloud_calls':0,'identity_or_naturalness_tested':False,'native_app_verified':False}
    write(workspace.path/'last-result.json',report)
    print(str(child.artifact('render')),flush=True)

if __name__=='__main__':main()
