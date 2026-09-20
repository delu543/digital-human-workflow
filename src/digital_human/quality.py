"""Evidence gates before new avatar requests; never a synthetic realism score."""
import copy
import re
from datetime import datetime, timezone
from . import media
from .storage import WorkflowError, digest, file_hash, now, read, write


def evidence(value, name):
    if not isinstance(value, str) or len(value.strip()) < 8:
        raise WorkflowError('请记录实际检查依据：' + name)


def signature(profile):
    """Ignore billing, script length and graphics; bind every presenter setting."""
    h, m, f = profile['heygen'], profile['minimax'], profile['format']
    return digest({'heygen': {k: h.get(k) for k in
        ['avatar_id', 'engine', 'resolution', 'reference_look_id', 'motion_prompt']},
        'minimax': {k: m.get(k) for k in ['region', 'voice_id', 'model', 'speed', 'emotion']},
        'frame': [f['width'], f['height']]})


def baseline(job, baseline_id):
    if not isinstance(baseline_id, str) or not re.fullmatch(r'[a-f0-9]{24}', baseline_id):
        raise WorkflowError('缺少有效的已验收真人感基线')
    path = job.workspace.path / 'baselines' / (baseline_id + '.json')
    if not path.exists():
        raise WorkflowError('真人感基线不存在')
    value = read(path)
    if digest(value)[:24] != baseline_id:
        raise WorkflowError('基线记录已修改；请恢复原记录或重新记录真实验收')
    if value.get('signature') != signature(job.profile()):
        raise WorkflowError('声像、动作或画幅已变化，需要重新做短样片验收')
    source = job.workspace.job(value['job_id'])
    avatar = source.artifact('avatar')
    if not avatar or file_hash(avatar) != value.get('avatar_sha256'):
        raise WorkflowError('基线视频已变化或缺失；不能假定原验收仍有效')
    return value


def validate_plan(job, value, fresh_capability=True):
    if value.get('schema_version') != 1 or value.get('mode') not in ['calibration', 'production']:
        raise WorkflowError('质量计划需要 schema_version=1 与 calibration/production 模式')
    if value.get('profile_signature') != signature(job.profile()):
        raise WorkflowError('质量计划不属于当前声像配置')
    source = value.get('source_review', {})
    for key in ['provenance', 'observations', 'evidence']:
        evidence(source.get(key), 'source_review.' + key)
    for group, keys in [('look_review', ['identity', 'eyes', 'hands', 'lighting', 'contact']),
                        ('motion_review', ['pose_matches', 'camera_angle_matches'])]:
        item = value.get(group, {})
        if any(item.get(k) is not True for k in keys):
            raise WorkflowError('素材检查未通过：' + group + '；先修正素材或选用匹配的参考')
        evidence(item.get('evidence'), group)
    cap, h = value.get('capability', {}), job.profile()['heygen']
    if not h['avatar_id']:
        raise WorkflowError('质量计划需要实际的本人 look ID，不能使用未配置形象')
    if cap.get('avatar_id') != h['avatar_id'] or cap.get('engine') != h['engine']:
        raise WorkflowError('能力检查必须对应当前 look 与模型')
    if not isinstance(cap.get('supported_api_engines'), list) or h['engine'] not in cap['supported_api_engines']:
        raise WorkflowError('当前 look 未确认支持所选引擎，不自动降级或切换')
    if cap.get('reference_look_id') != h.get('reference_look_id'):
        raise WorkflowError('动作参考检查与配置不符')
    if h.get('reference_look_id') and cap.get('reference_eligible') is not True:
        raise WorkflowError('需核对参考为同组 digital twin，且已满足平台同意要求')
    evidence(cap.get('evidence'), 'capability')
    if fresh_capability:
        try:
            stamp = datetime.fromisoformat(cap['checked_at'].replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
            if not -300 <= age <= 86400:
                raise ValueError()
        except (KeyError, ValueError, TypeError, AttributeError):
            raise WorkflowError('提交前需刷新 look/模型能力检查（24小时内），只读查询即可') from None
    if value['mode'] == 'production':
        baseline(job, value.get('baseline_id'))
    else:
        limit = value.get('sample_max_seconds')
        if type(limit) not in [int, float] or not 1 <= limit <= 60:
            raise WorkflowError('校准计划需要明确的短样片时长上限（1–60秒，建议10–15秒）')
    return value


def save_plan(job, value=None, reuse_baseline=None):
    if 'avatar' in job.load()['operations'] or job.artifact('avatar'):
        raise WorkflowError('已提交或已有视频，不重写生成计划；恢复原任务或建立新版本')
    if reuse_baseline:
        value = copy.deepcopy(baseline(job, reuse_baseline)['plan'])
        value.update(mode='production', baseline_id=reuse_baseline)
    else:
        value = copy.deepcopy(value)
    value['profile_signature'] = signature(job.profile())
    validate_plan(job, value)
    write(job.path / 'quality-plan.json', value)
    job.record('quality_plan', 'quality-plan.json')
    return {'saved': True, 'mode': value['mode']}


def plan(job):
    path = job.artifact('quality_plan')
    if not path:
        raise WorkflowError('先完成 quality-plan：检查原素材、静态形象、动作参考和模型能力')
    return validate_plan(job, read(path))


def review_voice(job, value):
    voice = job.artifact('voice')
    if not voice or value.get('voice_sha256') != file_hash(voice):
        raise WorkflowError('试听记录必须绑定当前最终配音的 SHA256')
    if 'avatar' in job.load()['operations']:
        raise WorkflowError('已提交口型视频，不改写配音验收')
    if value.get('method') not in ['listened', 'user_confirmation']:
        raise WorkflowError('需要实际试听或用户对这份配音的确认，转写不能代替试听')
    for key in ['wording', 'pronunciation', 'pauses', 'naturalness']:
        item = value.get(key, {})
        if item.get('status') != 'passed':
            raise WorkflowError('配音验收未通过：' + key)
        evidence(item.get('evidence'), key)
    value = dict(value, recorded_at=now())
    write(job.path / 'voice-review.json', value)
    job.record('voice_review', 'voice-review.json')
    return {'review_recorded': True, 'voice_sha256': value['voice_sha256']}


def require_avatar_ready(job):
    value = plan(job)
    voice, review = job.artifact('voice'), job.artifact('voice_review')
    if not voice or not review or read(review).get('voice_sha256') != file_hash(voice):
        raise WorkflowError('先用 voice-review 验收这段最终配音，再上传生成口型')
    duration = media.seconds(voice)
    if value['mode'] == 'calibration' and duration > value['sample_max_seconds']:
        raise WorkflowError('实际配音超过校准时长上限；不能把完整长片当短样片提交')
    return value


def next_gate(job):
    if job.artifact('avatar') or 'avatar' in job.load()['operations']:
        return None  # recovery is not a new generation
    if not job.artifact('quality_plan'):
        return {'status': 'needs_quality_plan', 'next': 'Codex inspects source/look/motion and records quality-plan; see references/realism.md.'}
    plan(job)
    if job.artifact('voice') and not job.artifact('voice_review'):
        return {'status': 'needs_voice_review', 'voice': str(job.artifact('voice')),
                'voice_sha256': file_hash(job.artifact('voice')),
                'next': 'Listen to this exact file and record voice-review. If listening is unavailable, ask for this audition only.'}
    return None


def accept_baseline(job, value):
    avatar = job.artifact('avatar')
    path = job.artifact('quality_plan')
    if not avatar or not path:
        raise WorkflowError('先保存质量计划并取得短样片；已有认可样片可导入，不必重新付费')
    validate_plan(job, read(path), fresh_capability=False)
    if value.get('avatar_sha256') != file_hash(avatar) or value.get('user_accepted') is not True:
        raise WorkflowError('基线需用户对当前视频的真实认可，技术检查不能代替')
    evidence(value.get('user_evidence'), 'user_evidence')
    for key in ['identity', 'gaze', 'motion', 'scene', 'sync', 'voice']:
        item = value.get(key, {})
        if item.get('status') != 'passed':
            raise WorkflowError('真人感基线未通过：' + key)
        evidence(item.get('evidence'), key)
    from .delivery import validate_motion_review
    validate_motion_review(value, media.seconds(avatar))
    result = {'signature': signature(job.profile()), 'job_id': job.path.name,
              'avatar_sha256': file_hash(avatar), 'plan': read(path), 'review': value, 'accepted_at': now()}
    baseline_id = digest(result)[:24]
    write(job.workspace.path / 'baselines' / (baseline_id + '.json'), result)
    return {'baseline_id': baseline_id, 'reusable_for_matching_presenter': True}
