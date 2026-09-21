"""Bounded renderer processes and structured reports amid diagnostic logging."""
import json
from pathlib import Path
import subprocess
import time
import psutil
from .storage import WorkflowError


def _remember(owned):
    # Retain Process identities (PID + create time), including detached children.
    # Re-scan captured descendants if their original parent has already exited.
    for process in list(owned.values()):
        try:
            if process.is_running():
                for child in process.children(recursive=True):
                    owned[(child.pid, child.create_time())] = child
        except psutil.NoSuchProcess:
            pass


def _live(owned):
    result = []
    for process in owned.values():
        try:
            if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                result.append(process)
        except psutil.NoSuchProcess:
            pass
    return result


def _stop(owned):
    _remember(owned)
    for method, grace in (('terminate', 3), ('kill', 3)):
        # Children first; never kill by a name shared with the user's browser.
        for process in reversed(_live(owned)):
            try:
                getattr(process, method)()
            except psutil.NoSuchProcess:
                pass
        deadline = time.monotonic() + grace
        while _live(owned) and time.monotonic() < deadline:
            _remember(owned)
            time.sleep(.05)
    if _live(owned):
        raise WorkflowError('导出子进程未全部停止；保留现场，不启动下一次导出')


def run_logged(args, log, timeout, env):
    """Track our non-adversarial renderer tree, including new browser sessions."""
    with Path(log).open('wb') as output:
        child = psutil.Popen(list(map(str, args)), stdout=output, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env)
        owned = {(child.pid, child.create_time()): child}
        expired = False
        deadline = time.monotonic() + timeout
        try:
            while True:
                _remember(owned)
                code = child.poll()
                if code is not None:
                    break
                if time.monotonic() >= deadline:
                    expired = True
                    break
                time.sleep(.05)
        finally:
            # Clean captured orphans even if the wrapper exits ahead of Chrome.
            _stop(owned)
            child.wait(timeout=6)
    if expired:
        raise WorkflowError('本地步骤超时；已停止本次进程树，不自动重试')
    if code:
        raise WorkflowError('本地步骤失败；检查日志，不重放生成或导出')


def check_report(log):
    """Accept one terminal JSON report; retain all preceding diagnostics verbatim."""
    text = Path(log).read_text(encoding='utf-8')
    decoder = json.JSONDecoder()
    candidates = []
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.startswith('{'):
            try:
                value, end = decoder.raw_decode(text, offset)
                if not text[end:].strip() and isinstance(value, dict) and type(value.get('ok')) is bool:
                    candidates.append(value)
            except json.JSONDecodeError:
                pass
        offset += len(line)
    if len(candidates) != 1:
        raise WorkflowError('检查日志缺少唯一完整 JSON 结果；不绕过检查')
    return candidates[0]
