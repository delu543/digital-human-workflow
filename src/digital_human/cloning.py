"""Optional one-time voice setup with independent explicit consent and receipts."""
from pathlib import Path
from . import media
from .budget import quote, require_consent, reserve, settle, unresolved, check_budget
from .cloud import speech
from .network import download
from .providers.minimax import MiniMax
from .storage import WorkflowError, file_hash, read, write

def clone_voice(job, sample, provider=None):
    p=require_consent(job,['minimax'],cloning=True)
    if p['minimax']['voice_id']:
        raise WorkflowError('已配置音色；直接复用，不重复克隆')
    if len(job.script())>500:
        raise WorkflowError('声音校准使用500字符以内的短试听文案')
    sample=Path(sample).resolve()
    if not sample.is_file(): raise WorkflowError('缺少本人授权的声音样本')
    duration=media.seconds(sample)
    if not 10<=duration<=300: raise WorkflowError('克隆样本需要10秒至5分钟')
    wav=job.path/'assets/voice-sample.wav'
    if wav.exists():
        source=read(job.path/'receipts/clone-source.json')
        if source['sha256']!=file_hash(sample): raise WorkflowError('克隆样本发生变化，请创建新任务')
    else:
        write(job.path/'receipts/clone-source.json',{'sha256':file_hash(sample)})
        media.extract_audio(sample,wav,44100)
    if wav.stat().st_size>20*1024*1024: raise WorkflowError('克隆样本超过20MB，请先压缩授权样本')
    api=provider or MiniMax(job.workspace,job.profile())
    voice_id='DHVoice'+job.path.name.replace('-','')
    costs=quote(p,'minimax',cloning=True)
    # Preview returned by the clone endpoint is billable too.
    costs['usd']+=quote(p,'minimax',len(job.script().encode('utf-8')))['usd']
    if 'clone' not in job.load()['operations']:
        check_budget(job,{'usd':costs['usd']+quote(p,'minimax',len(job.script().encode('utf-8')))['usd']})
    op,fresh=reserve(job,'clone','minimax',{'sample_sha256':file_hash(wav),'voice_id':voice_id,'text':job.script()},costs,cloning=True)
    receipt=job.path/'receipts/clone.json'
    if receipt.exists(): result=read(receipt)
    elif fresh:
        file_id=api.upload_voice(wav)
        write(job.path/'receipts/clone-upload.json',{'file_id':file_id})
        result=api.clone(file_id,voice_id,job.script());write(receipt,result)
    else: unresolved('声音克隆')
    if result.get('input_sensitive'):
        raise WorkflowError('服务未接受该样本，停止克隆，不自动重试')
    settle(job,'clone','complete',voice_id=voice_id)
    demo=result.get('demo_audio')
    if demo and not (job.path/'assets/clone-preview.mp3').exists():
        download(demo,job.path/'assets/clone-preview.mp3',20*1024*1024)
    # A separate successful synthesis activates the voice; restart reuses both receipts.
    path=speech(job,api,voice_id=voice_id)
    write(job.path/'voice-candidate.json',{'voice_id':voice_id,'audition':path,'user_approved':False})
    return {'voice_id':voice_id,'audition':path,'next':'本人试听认可后，再写入用户 profile 的 voice_id 和 approvals.voice；不要重新克隆。'}
