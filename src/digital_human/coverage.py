"""Plan paid presenter coverage from acoustic windows; no network or generation."""
import math
from .storage import WorkflowError


def samples(value, rate):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise WorkflowError('时间必须是非负有限秒数')
    return round(value * rate)


def union(spans):
    result = []
    for a, b in sorted(spans):
        if result and a <= result[-1][1]:
            result[-1][1] = max(result[-1][1], b)
        else:
            result.append([a, b])
    return result


def subtract(required, available):
    result = []
    for a, b in required:
        cursor = a
        for x, y in available:
            if y <= cursor or x >= b:
                continue
            if x > cursor:
                result.append([cursor, min(x, b)])
            cursor = max(cursor, y)
        if cursor < b:
            result.append([cursor, b])
    return result


def plan(value):
    """All windows refer to the final, approved audio clock, before any paid call.

    main_speech excludes other speakers/silence. generation_units are complete
    speech phrases with safe silence boundaries. Never split an utterance merely
    to fit a provider duration limit. Existing windows must be already verified.
    """
    rate = value.get('sample_rate', 48000)
    if type(rate) is not int or not 8000 <= rate <= 192000:
        raise WorkflowError('sample_rate 无效')
    total = samples(value['duration'], rate)
    if total <= 0:
        raise WorkflowError('duration 必须大于零')
    mode = value.get('mode')
    if mode not in ('selective', 'continuous_pip'):
        raise WorkflowError('mode 需要 selective 或 continuous_pip')
    required_keys = ['main_speech'] + (['full_screen'] if mode == 'selective' else [])
    if any(key not in value or not isinstance(value[key], list) for key in required_keys):
        raise WorkflowError('缺少明确的主讲/出镜窗口；确实没有时才写空数组')

    def windows(key):
        spans = []
        for span in value.get(key, []):
            if not isinstance(span, list) or len(span) != 2:
                raise WorkflowError(key + ' 需要 [开始秒, 结束秒]')
            a, b = (samples(t, rate) for t in span)
            if not 0 <= a < b <= total:
                raise WorkflowError(key + ' 时间范围无效')
            spans.append([a, b])
        return union(spans)

    speech = windows('main_speech')
    visible = windows('full_screen')
    required = speech if mode == 'continuous_pip' else union([
        [max(a, x), min(b, y)] for a, b in speech for x, y in visible
        if max(a, x) < min(b, y)])
    missing = subtract(required, windows('available'))
    # Adjacent generation units must remain separate as legal split boundaries.
    units = []
    for span in value.get('generation_units', []):
        if not isinstance(span, list) or len(span) != 2:
            raise WorkflowError('generation_units 需要成对时间')
        a, b = (samples(t, rate) for t in span)
        if not 0 <= a < b <= total:
            raise WorkflowError('generation_units 越界')
        units.append([a, b])
    units.sort()
    if any(a[1] > b[0] for a, b in zip(units, units[1:])):
        raise WorkflowError('generation_units 不得重叠')
    chosen = [u for u in units if any(max(u[0], a) < min(u[1], b) for a, b in missing)]
    if subtract(missing, union(chosen)):
        raise WorkflowError('缺失口型未被完整语句覆盖；补充真实音频边界，不能任意切词')
    limit = samples(value.get('max_reel_seconds', 60), rate)
    if limit <= 0 or any(b-a > limit for a, b in chosen):
        raise WorkflowError('完整语句超过单次上限；需在真实停顿处划分，不能自动截断')
    reels = []
    for a, b in chosen:
        if not reels or reels[-1]['samples'] + b-a > limit:
            reels.append({'index':len(reels)+1, 'samples':0, 'segments':[]})
        reel = reels[-1]
        reel['segments'].append({'timeline_start_sample':a, 'timeline_end_sample':b,
                                'reel_start_sample':reel['samples'], 'sample_count':b-a})
        reel['samples'] += b-a
    seconds = lambda spans: [[a/rate, b/rate] for a, b in spans]
    return {'schema':'presenter-coverage/v1', 'mode':mode, 'sample_rate':rate,
            'duration':total/rate, 'required':seconds(required), 'missing':seconds(missing),
            'required_seconds':sum(b-a for a, b in required)/rate,
            'missing_visible_seconds':sum(b-a for a, b in missing)/rate,
            'generation_seconds':sum(b-a for a, b in chosen)/rate, 'reels':reels,
            'billing_note':'Price each actual reel using current provider rounding and rate, including buffers.',
            'generation_authorized':False}
