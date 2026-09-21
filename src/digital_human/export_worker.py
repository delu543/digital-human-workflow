"""Bounded local export independent of the chat process. Never calls cloud APIs."""
import json
import os
from pathlib import Path
import shutil
import sys
import time
from .storage import ROOT, WorkflowError, digest, file_hash, read, write, within
from .media import binary, probe
from .processes import run_logged, check_report


def fingerprint(project):
    paths = sorted(Path(project).rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise WorkflowError('工程含符号链接；先整理为可核验的本地素材')
    return digest([[str(p.relative_to(project)), file_hash(p)] for p in paths if p.is_file()])


def claim(state, attempt, maximum):
    if type(attempt) is not int or type(maximum) is not int or not 1 <= attempt <= maximum:
        raise WorkflowError('导出次数超出本次约定范围')
    state = Path(state);state.mkdir(parents=True, exist_ok=True)
    try:
        with (state/'execution.started.json').open('x', encoding='utf-8') as f:
            json.dump({'attempt':attempt, 'pid':os.getpid(), 'started':time.time()}, f)
    except FileExistsError:
        raise WorkflowError('此执行已开始过；检查状态和已有文件，禁止自动重启') from None


def launch_plist(spec_path, label, python, script):
    """No KeepAlive/repeating schedule; absolute paths, no shell interpolation."""
    state = Path(spec_path).parent
    env = {'PATH':os.environ.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')}
    for key in ('PUPPETEER_EXECUTABLE_PATH', 'HYPERFRAMES_BROWSER_PATH'):
        if os.environ.get(key):
            env[key] = os.environ[key]
    return {'Label':label, 'RunAtLoad':True, 'KeepAlive':False,
            'ProgramArguments':[str(python), str(script), '--execute-spec', str(spec_path)],
            'WorkingDirectory':str(ROOT), 'EnvironmentVariables':env,
            'StandardOutPath':str(state/'launcher.log'),
            'StandardErrorPath':str(state/'launcher-error.log')}


def command(args, log, timeout, env):
    run_logged(args, log, timeout, env)


def execute(spec):
    state = Path(spec['state']);project = Path(spec['project']);target = Path(spec['output'])
    claim(state, spec['attempt'], spec['max_attempts'])
    status = {'stage':'preflight', 'cloud_calls':0, 'retry':False}
    write(state/'status.json', status)
    try:
        if target.exists():
            raise WorkflowError('输出已存在；核验现有结果，不覆盖')
        if fingerprint(project) != spec['project_sha256']:
            raise WorkflowError('工程在计划后变化；重新检查，不能导出旧快照')
        target.parent.mkdir(parents=True, exist_ok=True)
        lock = target.with_name('.'+target.name+'.export-lock.json')
        try:
            with lock.open('x', encoding='utf-8') as f:
                json.dump({'state':str(state), 'pid':os.getpid()}, f)
        except FileExistsError:
            raise WorkflowError('同一输出已有导出记录；核对原任务，禁止并行重做') from None
        # Verify same-filesystem no-clobber publication before expensive rendering.
        # This tiny hardlink is retained with the claim as recovery evidence.
        try:
            os.link(lock, lock.with_name(lock.name+'.link-probe'))
        except OSError:
            raise WorkflowError('输出文件系统不支持安全硬链接发布；改用本地支持的磁盘，再交付复制') from None
        staging = target.with_name('.'+target.name+'.pending.mp4')
        if staging.exists():
            raise WorkflowError('存在待核对的部分导出，不覆盖')
        env = dict(os.environ, HYPERFRAMES_RENDER_DETACHED='1',
                   DO_NOT_TRACK='1', HYPERFRAMES_NO_TELEMETRY='1')
        for key in ('MINIMAX_API_KEY', 'HEYGEN_API_KEY', 'PEXELS_API_KEY'):
            env.pop(key, None)
        base = [spec['node'], str(ROOT/'scripts/hf.mjs')]
        status['stage'] = 'checking';write(state/'status.json', status)
        command(base+['check', project, '--json'], state/'check.log', spec['timeout'], env)
        checks = check_report(state/'check.log')
        write(state/'check.json', checks)
        if not checks.get('ok'):
            raise WorkflowError('工程检查未通过')
        if fingerprint(project) != spec['project_sha256']:
            raise WorkflowError('检查时工程发生变化')
        target.parent.mkdir(parents=True, exist_ok=True)
        status['stage'] = 'rendering';write(state/'status.json', status)
        command(base+['render', project, '--quality','delivery','--fps',spec['fps'],
                     '--workers','1','--low-memory-mode','--frames-cache-dir','off',
                     '--output',staging], state/'render.log', spec['timeout'], env)
        status['stage'] = 'verifying';write(state/'status.json', status)
        command([binary('ffmpeg'),'-v','error','-xerror','-nostdin','-i',staging,'-f','null','-'],
                state/'decode.log', spec['timeout'], env)
        info = probe(staging)
        if fingerprint(project) != spec['project_sha256']:
            raise WorkflowError('渲染期间工程变化；不得绑定旧检查')
        # Same-directory hardlink publishes without overwriting any existing file.
        # Retain the pending alias as recovery evidence; it uses no second data copy.
        try:
            os.link(staging, target)
        except FileExistsError:
            raise WorkflowError('输出被其他任务创建，已保留本次暂存成片，不覆盖') from None
        result = {'project_sha256':spec['project_sha256'], 'video_sha256':file_hash(target),
                  'video':str(target), 'probe':info, 'full_decode':'passed',
                  'visual_review_pending':True, 'audio_review_pending':True}
        write(state/'result.json', result)
        status.update(stage='encoded', output=str(target), perceptual_review_pending=True)
        write(state/'status.json', status)
        return result
    except Exception as error:
        status.update(stage='failed', error_type=type(error).__name__,
                      message=str(error) if isinstance(error, WorkflowError) else '检查步骤日志')
        write(state/'status.json', status)
        raise


def make_spec(project, output, state, fps, attempt, maximum, timeout):
    project, output, state = (Path(p).expanduser().resolve() for p in (project, output, state))
    if not (project/'index.html').is_file() or output.exists():
        raise WorkflowError('需要现有工程和未占用的输出路径')
    if output.is_relative_to(project) or state.is_relative_to(project):
        raise WorkflowError('状态和导出必须位于 project 外，避免改变工程哈希')
    if type(fps) is not int or not 1 <= fps <= 120 or timeout <= 0 or not 1 <= attempt <= maximum:
        raise WorkflowError('帧率、超时或尝试范围无效')
    node = shutil.which('node')
    if not node:
        raise WorkflowError('缺少 Node.js')
    return {'project':str(project), 'output':str(output), 'state':str(state), 'fps':fps,
            'node':str(Path(node).resolve()), 'project_sha256':fingerprint(project),
            'attempt':attempt, 'max_attempts':maximum, 'timeout':timeout}


def register(job, state_path):
    """Bind an independently rendered artifact back into normal DH verification."""
    state_path = Path(state_path).expanduser().resolve()
    spec = read(state_path/'spec.json');result = read(state_path/'result.json')
    status = read(state_path/'status.json')
    project = (job.path/'project').resolve();video = Path(result['video']).resolve()
    if status.get('stage') != 'encoded' or Path(spec['project']).resolve() != project:
        raise WorkflowError('不是该任务的已完成独立导出')
    if not video.is_relative_to((job.path/'exports').resolve()):
        raise WorkflowError('独立导出必须写入此任务的 exports 目录')
    sha = fingerprint(project)
    if sha != spec['project_sha256'] or sha != result['project_sha256'] or file_hash(video) != result['video_sha256']:
        raise WorkflowError('导出文件或工程版本变化，不能登记旧检查')
    checks = check_report(state_path/'check.log')
    if not checks.get('ok') or result.get('full_decode') != 'passed':
        raise WorkflowError('独立导出检查未通过')
    existing = job.artifact('render')
    if existing:
        if existing.resolve() != video:
            raise WorkflowError('任务已有其他渲染，不能覆盖')
    checks['project_sha256'] = sha
    write(job.path/'checks.json', checks)
    write(job.path/'render-provenance.json', {'project_sha256':sha, 'video_sha256':result['video_sha256']})
    if not existing:
        job.record('render', str(video.relative_to(job.path.resolve())))
    return {'registered':True, 'next':'verify, actual visual/audio review, optional bundle',
            'visual_review_pending':True}
