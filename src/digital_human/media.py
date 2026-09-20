"""Portable local media operations. No shell interpolation or cloud calls."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from .storage import ROOT, WorkflowError, file_hash, read, write, digest

def project_hash(job):
    entries=[]
    for path in sorted((job.path/'project').rglob('*')):
        if path.is_symlink(): raise WorkflowError('工程含符号链接，请使用本任务内的实际素材')
        if path.is_file(): entries.append([str(path.relative_to(job.path/'project')),file_hash(path)])
    return digest(entries)

def binary(name):
    env = os.environ.get('DH_' + name.upper() + '_PATH')
    suffix = '.exe' if os.name == 'nt' else ''
    candidates = [env, str(ROOT / '.runtime/bin' / (name + suffix)), shutil.which(name)]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
    raise WorkflowError('缺少本地工具 ' + name + '；运行 scripts/bootstrap.py 或设置对应 DH_*_PATH')

def run(args, log=None, timeout=600):
    try:
        result = subprocess.run([str(a) for a in args], capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise WorkflowError('本地处理未完成；已保存远端结果，不需要重新生成') from None
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        Path(log).write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise WorkflowError('本地命令失败；请检查对应 evidence 日志')
    return result.stdout

def probe(path):
    result = json.loads(run([binary('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',path], timeout=60))
    if not result.get('streams') or float(result['format']['duration']) <= 0:
        raise WorkflowError('无效媒体或零时长')
    return result

def seconds(path):
    return float(probe(path)['format']['duration'])

def extract_audio(source, target, sample_rate=48000):
    if not Path(target).exists():
        run([binary('ffmpeg'),'-v','error','-nostdin','-i',source,'-vn','-ac','1','-ar',str(sample_rate),'-c:a','pcm_s16le',target])
    return Path(target)

def import_media(job, kind, source):
    if kind not in ['voice','avatar']:
        raise WorkflowError('只能导入配音或数字人视频')
    source = Path(source).resolve()
    if not source.is_file() or source.suffix.lower() not in ['.wav','.mp3','.m4a','.mp4','.webm']:
        raise WorkflowError('不支持的本地媒体文件')
    info = probe(source)
    required = 'video' if kind == 'avatar' else 'audio'
    if not any(s['codec_type'] == required for s in info['streams']):
        raise WorkflowError('文件缺少所需媒体轨道')
    if existing := job.artifact(kind):
        if file_hash(existing) != file_hash(source):
            raise WorkflowError('已有不同版本素材；请使用新任务保留旧交付')
        return existing
    target = job.path / 'assets' / (kind + source.suffix.lower())
    if target.exists() and file_hash(target) != file_hash(source):
        raise WorkflowError('目标素材存在不同内容，不覆盖')
    if not target.exists():
        shutil.copy2(source, target)
    job.record(kind, str(target.relative_to(job.path)))
    sources = read(job.path / 'sources.json')
    sources.append({'path':str(target.relative_to(job.path)), 'source':'user-provided local '+kind,
                    'rights':'user-authorized personal material; ownership/consent verified during onboarding'})
    write(job.path / 'sources.json', sources)
    return target

def narration(job):
    if existing := job.artifact('narration'):
        return existing
    avatar, voice = job.artifact('avatar'), job.artifact('voice')
    if not avatar:
        raise WorkflowError('缺少本人数字人素材，不能使用占位图冒充')
    info = probe(avatar)
    has_audio = any(s['codec_type']=='audio' for s in info['streams'])
    if not has_audio and not voice:
        raise WorkflowError('数字人视频无音轨，且未提供配音')
    if voice and abs(seconds(voice) - seconds(avatar)) > .35:
        raise WorkflowError('数字人与配音时长相差超过350ms，需检查原任务，不能静默裁剪')
    target = extract_audio(avatar if has_audio else voice, job.path / 'assets/narration.wav')
    job.record('narration','assets/narration.wav')
    return target

def frame(job, times=None):
    avatar = job.artifact('avatar')
    if not avatar:
        raise WorkflowError('先导入或生成数字人视频')
    duration = seconds(avatar)
    times = times or [min(duration*.15,2), duration*.5, duration*.85]
    results = []
    for i, t in enumerate(times):
        path = job.path / 'evidence' / f'presenter-{i}.png'
        if not path.exists():
            run([binary('ffmpeg'),'-v','error','-nostdin','-ss',str(t),'-i',avatar,'-frames:v','1','-vf','scale=540:-2',path])
        results.append(str(path))
    return results

def inspect_source(job, source):
    """Local evidence, not an automatic face/exposure or training-data diagnosis."""
    source = Path(source).expanduser().resolve()
    if not source.is_file(): raise WorkflowError('源媒体不存在')
    info = probe(source); sha = file_hash(source)
    folder = job.path/'evidence'/('source-'+sha[:16]);folder.mkdir(parents=True, exist_ok=True)
    duration = float(info['format']['duration'])
    video = next((s for s in info['streams'] if s['codec_type']=='video'), None)
    result = {'source_sha256':sha, 'source_path':str(source), 'duration':duration,
        'streams':[{k:s[k] for k in ['codec_type','codec_name','width','height','avg_frame_rate',
                    'pix_fmt','color_space','color_transfer','color_primaries','sample_rate','channels'] if k in s}
                   for s in info['streams']], 'frames':[], 'clips':[],
        'scope':'Local file only; provenance, face lighting, motion and training suitability require actual inspection.'}
    if video:
        result['hdr_preview_caution'] = video.get('color_transfer') in ['smpte2084','arib-std-b67']
        for i, fraction in enumerate([.05, .45, .8]):
            start = max(0, min(duration * fraction, duration - .05))
            still, clip = folder/f'frame-{i}.jpg', folder/f'clip-{i}.mp4'
            if not still.exists():
                run([binary('ffmpeg'),'-v','error','-nostdin','-ss',str(start),'-i',source,
                     '-frames:v','1','-vf','scale=720:-2',still])
            end = min(duration, start+3)
            if not clip.exists():
                run([binary('ffmpeg'),'-v','error','-nostdin','-ss',str(start),'-i',source,
                     '-t',str(end-start),'-vf','scale=720:-2','-c:v','libx264','-crf','20',
                     '-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',clip])
            result['frames'].append(str(still))
            result['clips'].append({'path':str(clip),'start':start,'end':end})
    write(folder/'inspection.json',result)
    return result

def hf(job, command, output=None, timeout=1800):
    node = shutil.which('node')
    if not node:
        raise WorkflowError('需要 Node.js 22 或以上')
    args = [node, ROOT/'scripts/hf.mjs', command, job.path/'project']
    if command == 'check':
        raw = run(args+['--json'], job.path/'evidence/check-command.log', timeout)
        value = json.loads(raw); value['project_sha256']=project_hash(job)
        write(job.path/'checks.json',value)
        if not value.get('ok'):
            raise WorkflowError('Hyperframes 检查未通过，不导出正式交付')
        return value
    if command == 'render':
        checks=read(job.path/'checks.json');fingerprint=project_hash(job)
        if not checks.get('ok') or checks.get('project_sha256')!=fingerprint:
            raise WorkflowError('工程在检查后发生变化，请对当前版本重新 check')
        target = Path(output) if output else job.path/'exports/final.mp4'
        if target.exists():
            raise WorkflowError('渲染输出已存在；核验已有结果或使用新版本文件名')
        run(args+['--quality','delivery','--fps',str(job.profile()['format']['fps']),
                  '--workers','1','--output',str(target)],job.path/'evidence/render.log',timeout)
        job.record('render', str(target.relative_to(job.path)))
        write(job.path/'render-provenance.json',{'project_sha256':fingerprint,'video_sha256':file_hash(target)})
        return str(target)
    raise WorkflowError('不支持的 Hyperframes 命令')
