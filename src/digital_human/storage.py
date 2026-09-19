"""Atomic local state, immutable job inputs, and cross-process locking."""
import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class WorkflowError(Exception):
    """A user-actionable error that contains no credential or response body."""

def now():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()

def within(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise WorkflowError('素材路径必须位于当前任务内部')
    path = root / rel
    if any(p.is_symlink() for p in [path, *path.parents] if p != root and p.is_relative_to(root)):
        raise WorkflowError('任务素材不能使用符号链接')
    if not path.resolve().is_relative_to(root):
        raise WorkflowError('素材路径越界')
    return path

@contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as f:
        try:
            if os.name == 'nt':
                import msvcrt
                f.seek(0); f.write(b'0'); f.flush(); f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            raise WorkflowError('该任务正被另一个进程使用；不要重复提交') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)

class Workspace:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        if self.path == ROOT:
            raise WorkflowError('请选择独立的用户数据目录，不要使用代码仓库根目录')

    def initialize(self):
        self.path.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':
            self.path.chmod(0o700)
        profile = self.path / 'profile.json'
        if not profile.exists():
            write(profile, read(ROOT / 'config/profile.example.json'))
        return {'workspace': str(self.path), 'profile': str(profile)}

    def profile(self):
        p = self.path / 'profile.json'
        if not p.exists():
            raise WorkflowError('先运行 init 初始化用户工作区')
        from .config import validate
        value = read(p); validate(value)
        return value

    def job(self, job_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,90}', job_id):
            raise WorkflowError('无效任务 ID')
        path = within(self.path, 'jobs/' + job_id)
        if not (path / 'job.json').exists():
            raise WorkflowError('未找到该任务')
        return Job(path, self)

    def prepare(self, script, brief=None, new=False):
        script = script.strip()
        if not script or len(script) > 10000:
            raise WorkflowError('请提供 1–10000 字符的纯文本口播文案')
        profile = self.profile()
        brief = brief or {}
        key = digest({'script': script, 'brief': brief, 'profile': profile})
        with lock(self.path / 'prepare.lock'):
            if not new:
                for p in sorted((self.path / 'jobs').glob('*/job.json')):
                    if read(p).get('fingerprint') == key:
                        return self.job(p.parent.name)
            job_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
            path = self.path / 'jobs' / job_id
            for name in ['assets', 'receipts', 'project', 'exports', 'evidence']:
                (path / name).mkdir(parents=True, exist_ok=True)
            (path / 'script.txt').write_text(script, encoding='utf-8')
            write(path / 'profile.json', profile); write(path / 'brief.json', brief)
            write(path / 'sources.json', [])
            write(path / 'job.json', {'schema_version': 1, 'id': job_id, 'created_at': now(),
                'fingerprint': key, 'script_sha256': file_hash(path / 'script.txt'),
                'profile_sha256': file_hash(path / 'profile.json'), 'stage': 'prepared',
                'operations': {}, 'artifacts': {}, 'remote': {}})
            return Job(path, self)

class Job:
    def __init__(self, path, workspace):
        self.path, self.workspace = Path(path), workspace

    def load(self):
        value = read(self.path / 'job.json')
        for name in ['script', 'profile']:
            filename = 'script.txt' if name == 'script' else 'profile.json'
            if file_hash(self.path / filename) != value[name + '_sha256']:
                raise WorkflowError('任务输入已修改；请创建新任务，不能复用旧收费结果')
        return value

    def save(self, value):
        value['updated_at'] = now()
        write(self.path / 'job.json', value)

    def profile(self):
        self.load()
        return read(self.path / 'profile.json')

    def script(self):
        self.load()
        return (self.path / 'script.txt').read_text(encoding='utf-8')

    def artifact(self, name):
        entry = self.load()['artifacts'].get(name)
        if not entry:
            return None
        path = within(self.path, entry['path'])
        if not path.is_file() or file_hash(path) != entry['sha256']:
            raise WorkflowError('已有素材缺失或发生变化，请恢复文件；不自动重新付费生成：' + name)
        return path

    def record(self, name, relative):
        p = within(self.path, relative)
        meta = self.load()
        meta['artifacts'][name] = {'path': relative, 'sha256': file_hash(p)}
        meta['stage'] = name + '_ready'; self.save(meta)

    def locked(self):
        return lock(self.path / 'job.lock')
