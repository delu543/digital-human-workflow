"""Reserve estimated spend before submission; never retry ambiguous paid calls."""
from datetime import datetime, timezone
import math
from .storage import WorkflowError, digest, now

def require_consent(job, services, cloning=False):
    saved, current = job.profile(), job.workspace.profile()
    from .config import OPTIONAL
    for provider in ['minimax', 'heygen']:
        defaults = {key: None for key in OPTIONAL.get(provider, set())}
        if {**defaults, **saved[provider]} != {**defaults, **current[provider]}:
            raise WorkflowError('账号路径、声音或形象配置已变化，请创建新任务')
    auth = current['authorization']
    if not auth['generation'] or (cloning and not auth['voice_clone']):
        raise WorkflowError('尚未授权此范围的生成或声音克隆')
    for service in services:
        destination = 'minimax_' + saved['minimax']['region'] if service == 'minimax' else service
        if destination not in auth['destinations']:
            raise WorkflowError('尚未授权数据发送到：' + destination)
    return current

def quote(profile, service, amount=0, cloning=False):
    rates = profile['rates']
    try:
        checked = datetime.fromisoformat(rates['verified_at'].replace('Z','+00:00'))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        if not -86400 <= age <= 31*86400:
            raise ValueError()
    except (AttributeError, TypeError, ValueError):
        raise WorkflowError('请先核对当前账户价格，并设置 rates.verified_at（31 天内）') from None
    if cloning:
        key, unit, multiplier = 'voice_clone_usd', 'usd', 1
    elif service == 'minimax':
        key, unit, multiplier = 'minimax_usd_per_1000_chars', 'usd', amount / 1000
    elif profile['heygen']['transport'] == 'api':
        key, unit, multiplier = 'heygen_usd_per_minute', 'usd', amount / 60
    elif profile['heygen']['transport'] == 'mcp':
        key, unit, multiplier = 'heygen_credits_per_minute', 'heygen_credits', amount / 60
    else:
        raise WorkflowError('当前路径不支持自动云端生成')
    if rates[key] is None:
        raise WorkflowError('缺少账户报价：' + key)
    value = rates[key] * multiplier * profile['authorization']['price_buffer']
    if not math.isfinite(value) or value < 0:
        raise WorkflowError('费用估算无效')
    return {unit: round(value, 6)}

def check_budget(job, costs):
    """Preflight the whole operation before sending even its input assets."""
    current = job.workspace.profile()
    meta = job.load()
    totals = {'usd': 0., 'heygen_credits': 0.}
    for op in meta['operations'].values():
        for unit, value in op['reserved'].items():
            totals[unit] += value
    caps = {'usd': current['authorization']['max_usd_per_job'],
            'heygen_credits': current['authorization']['max_heygen_credits_per_job']}
    for unit, value in costs.items():
        if unit not in caps or type(value) not in [int, float] or not math.isfinite(value) or value < 0:
            raise WorkflowError('无效费用单位或数值')
        if totals[unit] + value > caps[unit] + 1e-8:
            raise WorkflowError('超过单条预算：' + unit + '；不提交生成')

def reserve(job, name, service, payload, costs, cloning=False):
    require_consent(job, [service], cloning)
    meta = job.load()
    existing = meta['operations'].get(name)
    fingerprint = digest(payload)
    if existing:
        if existing['payload_sha256'] != fingerprint:
            raise WorkflowError('已有收费请求与当前输入不符；不能复用或覆盖')
        return existing, False
    check_budget(job, costs)
    operation = {'status': 'uncertain', 'service': service, 'started_at': now(),
                 'payload_sha256': fingerprint, 'reserved': costs}
    meta['operations'][name] = operation
    job.save(meta)  # durable BEFORE the network side effect
    return operation, True

def settle(job, name, status, **fields):
    if status not in ['submitted', 'complete', 'failed', 'uncertain']:
        raise WorkflowError('无效远端请求状态')
    meta = job.load(); op = meta['operations'][name]
    op.update(status=status, **fields); job.save(meta)

def unresolved(name):
    raise WorkflowError(name + ' 的请求结果不确定。先核对供应商记录并恢复远端 ID；禁止盲目重试收费请求')
