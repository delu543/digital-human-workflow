"""Report actual readiness without equating installed packages with video quality."""
import os
import shutil
from pathlib import Path
from . import media
from .config import credential
from .storage import ROOT, WorkflowError

def doctor(workspace, online=False):
    p=workspace.profile();pending=[];local={}
    for name in ['ffmpeg','ffprobe']:
        try: local[name]=media.binary(name)
        except WorkflowError: local[name]=False;pending.append('安装本地 '+name)
    local['node']=shutil.which('node')
    local['hyperframes']=(ROOT/'node_modules/hyperframes/bin/hyperframes.mjs').is_file()
    local['font']=(ROOT/'templates/assets/NotoSansCJKsc-Regular.otf').is_file()
    local['whisper_config']=(ROOT/'.runtime/whisper.json').is_file() or bool(os.environ.get('DH_WHISPER_PATH'))
    for name in ['node','hyperframes','font','whisper_config']:
        if not local[name]: pending.append('准备本地 '+name)
    keys={}
    for service in ['minimax','heygen']:
        try: credential(workspace,service);keys[service]=True
        except WorkflowError: keys[service]=False
    if not p['minimax']['voice_id']: pending.append('设置并试听认可本人 MiniMax 音色')
    if not keys['minimax']: pending.append('本地配置 MiniMax API Key')
    if not p['heygen']['transport']: pending.append('用户选择 HeyGen 会员 MCP、API 或导入')
    if p['heygen']['transport']=='api' and not keys['heygen']: pending.append('本地配置 HeyGen API Key')
    if p['heygen']['transport']!='import' and not p['heygen']['avatar_id']: pending.append('绑定已创建的本人 HeyGen look ID')
    for name,value in p['approvals'].items():
        if not value: pending.append('首次验收：'+name)
    if not p['authorization']['generation']: pending.append('设置生成范围、数据去向和单条预算')
    result={'workspace':str(workspace.path),'local':local,'credentials_present':keys,
        'heygen_transport':p['heygen']['transport'],'pending':pending,
        'configuration_ready':not pending,'production_quality_guaranteed':False,'online_checks':{}}
    if online:
        if keys['minimax']:
            from .providers.minimax import MiniMax
            data=MiniMax(workspace,p).voices()
            result['online_checks']['minimax']='authenticated'
            if p['minimax']['voice_id']:
                def contains(value):
                    if isinstance(value,dict): return value.get('voice_id')==p['minimax']['voice_id'] or any(contains(v) for v in value.values())
                    if isinstance(value,list): return any(contains(v) for v in value)
                    return False
                result['online_checks']['voice_visible']=contains(data)
        if p['heygen']['transport']=='api' and keys['heygen']:
            from .providers.heygen import HeyGen
            HeyGen(workspace,p).me();result['online_checks']['heygen']='authenticated'
        elif p['heygen']['transport']=='mcp':
            result['online_checks']['heygen']='Codex must call official get_current_user and verify the selected look; no API fallback'
    return result
