#!/usr/bin/env python3
"""Local synthetic renderer test. No voice clone, person, cloud call or paid API."""
import argparse
from pathlib import Path
from digital_human import media,composition,delivery
from digital_human.config import configure
from digital_human.storage import ROOT,Workspace,write

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=int,default=12)
    p.add_argument('--workspace',type=Path,default=ROOT/'.runtime/synthetic-smoke')
    a=p.parse_args()
    if not 6<=a.seconds<=300: raise SystemExit('Use 6–300 seconds')
    w=Workspace(a.workspace);w.initialize()
    configure(w,{'heygen':{'transport':'import'}})
    script='技术测试。使用合成画面和测试音。验证本地渲染。不是本人数字人样片。'
    j=w.prepare(script,{'purpose':'synthetic technical fixture; NOT a real avatar or acoustic alignment test','seconds':a.seconds},new=True)
    print('Fixture job: '+j.path.name,flush=True)
    video=j.path/'assets/synthetic-source.mp4'
    media.run([media.binary('ffmpeg'),'-v','error','-nostdin',
        '-f','lavfi','-i',f'color=c=0x17304a:s=1080x1920:r=25:d={a.seconds}',
        '-f','lavfi','-i',f'sine=frequency=440:sample_rate=48000:duration={a.seconds}',
        '-c:v','libx264','-preset','ultrafast','-crf','24','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','96k','-shortest',video],j.path/'evidence/fixture.log',max(120,a.seconds*3))
    media.import_media(j,'avatar',video)
    n=12;step=a.seconds/n
    cues=[{'text':f'技术测试 · 第{i+1}阶段','start':round(i*step,3),'end':round((i+1)*step,3)} for i in range(n)]
    # Deliberate test fixture, never represented as speech-derived timing.
    write(j.path/'captions.json',{'duration':a.seconds,'source':'synthetic_fixture_not_acoustic','captions':cues})
    j.record('captions','captions.json')
    image=j.path/'assets/diagram.svg'
    image.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" rx="30" fill="#183a53"/><path d="M100 200H500" stroke="#f7d478" stroke-width="12"/><g fill="#f7d478"><circle cx="100" cy="200" r="42"/><circle cx="300" cy="200" r="42"/><circle cx="500" cy="200" r="42"/></g></svg>',encoding='utf-8')
    write(j.path/'sources.json',[{'path':'assets/diagram.svg','source':'original synthetic test diagram','rights':'MIT, original repository fixture'}])
    plan={'layout':{'title_top':.12,'caption_top':.79},'keywords':['技术测试'],'scenes':[
        {'start_caption':0,'kind':'title','label':'本地渲染测试 · 非真人','title':'字幕与时间轴','detail':'合成测试音，不调用云端服务'},
        {'start_caption':3,'kind':'steps','label':'本地渲染测试 · 非真人','title':'动画步骤','items':['准备素材','组合画面','校验成片']},
        {'start_caption':6,'kind':'bars','label':'虚构测试数据','title':'图表动画','source':'synthetic fixture values, not real-world claims','items':[{'label':'A','value':20},{'label':'B','value':50},{'label':'C','value':80}]},
        {'start_caption':9,'kind':'image','label':'本地渲染测试 · 非真人','title':'配图组合','image':'assets/diagram.svg','detail':'原创测试图解'}]}
    write(j.path/'plan.json',plan)
    composition.compose(j,j.path/'plan.json');print('Composed',flush=True)
    check=media.hf(j,'check');print('Checked: '+str(check['ok']),flush=True)
    media.hf(j,'render',timeout=3600);print('Rendered',flush=True)
    report=delivery.verify(j)
    write(w.path/'last-result.json',{'job_id':j.path.name,'technical':report,'cloud_called':False,
        'voice_identity_tested':False,'bundle_review_approved':False})
    print(str(j.path/'exports/final.mp4'),flush=True)
    print(report,flush=True)

if __name__=='__main__':main()
