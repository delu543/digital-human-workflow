"""Provider selection and credentials; no account-specific defaults."""
import math
import os
import re
from .storage import ROOT, WorkflowError, read, write

HOSTS = {'international': 'https://api.minimax.io', 'china': 'https://api.minimaxi.com'}

def number(value, minimum=0, maximum=1e9):
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum

def validate(profile):
    template = read(ROOT / 'config/profile.example.json')
    if set(profile) != set(template) or profile['schema_version'] != 1:
        raise WorkflowError('配置版本或字段无效')
    for key in template:
        if isinstance(template[key], dict) and set(profile[key]) != set(template[key]):
            raise WorkflowError('配置字段无效：' + key)
    f = profile['format']; m = profile['minimax']; h = profile['heygen']
    if any(type(f[k]) is not int for k in f) or not (240 <= f['width'] <= 3840 and 240 <= f['height'] <= 3840):
        raise WorkflowError('视频尺寸无效')
    if f['width'] % 2 or f['height'] % 2 or f['fps'] not in [24, 25, 30, 60] or not 1 <= f['target_seconds'] <= 1800:
        raise WorkflowError('帧率、时长或尺寸无效')
    if m['region'] not in HOSTS or not number(m['speed'], .5, 2) or not re.fullmatch(r'[a-zA-Z0-9_.-]+', m['model']):
        raise WorkflowError('MiniMax 区域、模型或语速无效')
    if h['transport'] not in [None, 'mcp', 'api', 'import'] or h['engine'] not in ['avatar_iv','avatar_v','avatar_iii']:
        raise WorkflowError('请选择 HeyGen MCP、API 或导入方式，并设置有效模型')
    if h['resolution'] not in ['720p', '1080p', '4k']:
        raise WorkflowError('HeyGen 分辨率无效')
    for value in [m['voice_id'], h['avatar_id']]:
        if value is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,150}', value):
            raise WorkflowError('声音或形象 ID 格式无效')
    style = profile['style']
    if style['preset'] not in ['editorial', 'minimal'] or not re.fullmatch(r'#[0-9A-Fa-f]{6}', style['accent']):
        raise WorkflowError('视觉预设或颜色无效')
    if style['caption_position'] not in ['lower', 'middle']:
        raise WorkflowError('字幕位置无效')
    a = profile['authorization']
    if any(type(v) is not bool for v in profile['approvals'].values()) or type(a['generation']) is not bool or type(a['voice_clone']) is not bool:
        raise WorkflowError('验收与授权必须使用布尔值')
    if not isinstance(a['destinations'], list) or any(v not in ['minimax_international','minimax_china','heygen'] for v in a['destinations']):
        raise WorkflowError('数据去向无效')
    if not all(number(a[k]) for k in ['max_usd_per_job','max_heygen_credits_per_job']) or not number(a['price_buffer'], 1, 3):
        raise WorkflowError('预算或估价余量无效')
    for key, value in profile['rates'].items():
        if key != 'verified_at' and value is not None and not number(value):
            raise WorkflowError('价格必须是有限非负数或 null')

def configure(workspace, patch):
    p = workspace.profile()
    for section, values in patch.items():
        if section not in p or not isinstance(p[section], dict) or not isinstance(values, dict):
            raise WorkflowError('仅支持已定义配置分区')
        for key, value in values.items():
            if key not in p[section]:
                raise WorkflowError('未知配置字段：' + key)
            p[section][key] = value
    validate(p); write(workspace.path / 'profile.json', p)
    return {'configured': list(patch), 'workspace': str(workspace.path)}

def credential(workspace, service):
    env = {'minimax':'MINIMAX_API_KEY', 'heygen':'HEYGEN_API_KEY'}[service]
    values = read(workspace.path / 'secrets.json') if (workspace.path / 'secrets.json').exists() else {}
    value = os.environ.get(env) or values.get(env)
    if not value:
        raise WorkflowError(env + ' 未配置，请使用 secrets 命令在本地隐藏输入')
    return value

def save_credential(workspace, service, value):
    env = {'minimax':'MINIMAX_API_KEY','heygen':'HEYGEN_API_KEY'}[service]
    if not value or any(c.isspace() for c in value):
        raise WorkflowError('密钥不能为空或包含空白')
    path = workspace.path / 'secrets.json'
    values = read(path) if path.exists() else {}
    values[env] = value; write(path, values)
    return {'saved': env, 'value_disclosed': False}
