"""Paid boundaries and recovery from saved receipts; no implicit submission retry."""
import os
from .budget import quote, reserve, settle, unresolved, require_consent, check_budget
from . import media
from .network import download
from .storage import WorkflowError, read, write
from .providers.minimax import MiniMax
from .providers.heygen import HeyGen

def unwrap(result):
    if 'content' in result:
        import json
        blocks = [b for b in result['content'] if b.get('type')=='text']
        if not blocks: raise WorkflowError('MCP 回执中没有 JSON 结果')
        result=json.loads(blocks[0]['text'])
    return result.get('data',result)

def speech(job, provider=None, voice_id=None):
    if existing := job.artifact('voice'):
        return str(existing)
    p = require_consent(job,['minimax'])
    api = provider or MiniMax(job.workspace,job.profile())
    payload=api.speech_payload(job.script(),voice_id)
    costs=quote(p,'minimax',len(job.script().encode('utf-8')))
    op, fresh=reserve(job,'voice','minimax',payload,costs)
    receipt=job.path/'receipts/minimax-speech.json'
    if receipt.exists(): result=read(receipt)
    elif fresh:
        result=api.speech(payload); write(receipt,result)
    else: unresolved('配音')
    try: audio=bytes.fromhex(result['data']['audio'])
    except (KeyError,ValueError,TypeError):
        raise WorkflowError('配音回执无有效音频；保留请求，不重复计费') from None
    if not audio: raise WorkflowError('配音为空')
    target=job.path/'assets/voice.mp3'
    partial=target.with_suffix('.mp3.partial'); partial.write_bytes(audio); os.replace(partial,target)
    media.probe(target)
    settle(job,'voice','complete',usage_characters=result.get('extra_info',{}).get('usage_characters'))
    job.record('voice','assets/voice.mp3')
    return str(target)

def submit_avatar(job, provider=None):
    if existing:=job.artifact('avatar'): return {'status':'completed','path':str(existing)}
    p=require_consent(job,['heygen'])
    api=provider or HeyGen(job.workspace,job.profile())
    voice=job.artifact('voice')
    if not voice: raise WorkflowError('必须先取得最终配音')
    duration=media.seconds(voice)
    if duration>1800: raise WorkflowError('当前接口一次最多30分钟，请分任务处理')
    # Check generation affordability before uploading the user's audio.
    costs=quote(p,'heygen',duration)
    current=job.load()
    if 'avatar' not in current['operations']: check_budget(job,costs)
    elif current['operations']['avatar']['status']=='failed':
        raise WorkflowError('远端任务已失败，请核对账单与失败原因，不自动重新提交')
    asset_id=current['remote'].get('audio_asset_id')
    if not asset_id:
        op,fresh=reserve(job,'avatar_upload','heygen',{'voice_sha256':current['artifacts']['voice']['sha256']},{})
        receipt=job.path/'receipts/heygen-upload.json'
        if receipt.exists(): asset_id=read(receipt)['asset_id']
        elif fresh:
            asset_id=api.upload(voice); write(receipt,{'asset_id':asset_id})
        else: unresolved('音频上传')
        current=job.load();current['remote']['audio_asset_id']=asset_id;job.save(current)
        settle(job,'avatar_upload','complete',asset_id=asset_id)
    payload=api.payload(asset_id,job.path.name)
    op,fresh=reserve(job,'avatar','heygen',payload,costs)
    receipt=job.path/'receipts/heygen-create.json'
    if receipt.exists(): result=unwrap(read(receipt))
    elif fresh:
        response=api.create(payload);write(receipt,response);result=unwrap(response)
    elif op.get('video_id'): return {'status':op['status'],'video_id':op['video_id']}
    else: unresolved('数字人生成')
    video_id=result.get('video_id') or result.get('id')
    if not video_id: unresolved('数字人生成（返回缺少 ID）')
    settle(job,'avatar','submitted',video_id=video_id)
    meta=job.load();meta['remote']['video_id']=video_id;meta['stage']='avatar_submitted';job.save(meta)
    return {'status':'submitted','video_id':video_id}

def receive_avatar(job, response):
    result=unwrap(response)
    known=job.load()['remote'].get('video_id')
    returned=result.get('video_id') or result.get('id')
    if returned and known and returned != known:
        raise WorkflowError('回执视频 ID 与本任务不一致')
    status=result.get('status')
    if status in ['failed','error']:
        if 'avatar' in job.load()['operations']: settle(job,'avatar','failed')
        raise WorkflowError('远端生成失败；保留原任务和费用记录，不自动收费重试')
    if status!='completed': return {'status':status or 'unknown','video_id':known}
    url=result.get('video_url')
    if not url: raise WorkflowError('已完成但缺少视频地址，请刷新同一任务回执')
    write(job.path/'receipts/heygen-completed.json',response)
    target=job.path/'assets/avatar.mp4'
    if not target.exists(): download(url,target)
    media.probe(target);job.record('avatar','assets/avatar.mp4')
    if 'avatar' in job.load()['operations']: settle(job,'avatar','complete')
    return {'status':'completed','path':str(target)}

def poll_avatar(job, provider=None):
    if existing:=job.artifact('avatar'): return {'status':'completed','path':str(existing)}
    if job.profile()['heygen']['transport']!='api':
        raise WorkflowError('会员 MCP 的状态查询由 Codex 按插件权限执行；不会切换到 API')
    video_id=job.load()['remote'].get('video_id')
    if not video_id: raise WorkflowError('没有已提交任务 ID，先检查原请求')
    api=provider or HeyGen(job.workspace,job.profile())
    return receive_avatar(job,api.get(video_id))

def record_remote(job, video_id=None, asset_id=None):
    import re
    meta=job.load()
    for key,value in [('video_id',video_id),('audio_asset_id',asset_id)]:
        if value:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,150}',value): raise WorkflowError('无效远端 ID')
            if meta['remote'].get(key) not in [None,value]: raise WorkflowError('不能覆盖已有远端 ID')
            if key=='video_id' and 'avatar' not in meta['operations']:
                raise WorkflowError('先通过 mcp-begin 保留请求与预算，再登记视频 ID')
            meta['remote'][key]=value
    job.save(meta)
    if video_id: settle(job,'avatar','submitted',video_id=video_id)
    return {'recorded':{k:v for k,v in meta['remote'].items() if k in ['video_id','audio_asset_id']}}

def mcp_begin(job):
    if job.profile()['heygen']['transport']!='mcp': raise WorkflowError('当前不是会员 MCP 路径')
    p=require_consent(job,['heygen']);voice=job.artifact('voice')
    if not voice: raise WorkflowError('先完成配音')
    meta=job.load();asset=meta['remote'].get('audio_asset_id')
    costs=quote(p,'heygen',media.seconds(voice))
    if 'avatar' not in meta['operations']: check_budget(job,costs)
    if not asset:
        return {'action':'upload_audio_with_official_mcp','path':str(voice),
            'size_bytes':voice.stat().st_size,'content_type':'audio/mpeg',
            'next':'Record the returned asset ID using record-remote, then call mcp-begin again.'}
    h=p['heygen'];fmt=p['format']
    if not h['avatar_id']: raise WorkflowError('没有确认的本人数字人 look ID')
    args={'avatarId':h['avatar_id'],'audioAssetId':asset,'engine':{'type':h['engine']},
        'resolution':h['resolution'],'aspectRatio':'9:16' if fmt['height']>fmt['width'] else ('16:9' if fmt['width']>fmt['height'] else '1:1'),
        'fit':'contain','outputFormat':'mp4','title':'Digital Human '+job.path.name,'callbackId':job.path.name}
    op,fresh=reserve(job,'avatar','heygen',args,costs)
    if not fresh:
        if op.get('video_id'): return {'action':'resume_existing','video_id':op['video_id']}
        unresolved('会员数字人请求')
    write(job.path/'receipts/mcp-request.json',args)
    return {'action':'call_official_create_video_from_avatar_once','arguments':args,
        'after':'Immediately record video_id, then follow the tool instruction to show the video. Do not poll if the connector forbids it.'}
