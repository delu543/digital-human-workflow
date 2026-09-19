"""Chinese caption timing comes from acoustics, never estimated reading speed."""
import math
import json
import os
import re
import unicodedata
from pathlib import Path
from . import media
from .storage import ROOT, WorkflowError, read, write

def read_transcript(path):
    # whisper.cpp can emit incomplete UTF-8 punctuation bytes in token JSON.
    # Replacement characters are non-alphanumeric and never invent a spoken word;
    # lost word bytes still fail the exact normalized-script check below.
    return json.loads(Path(path).read_bytes().decode('utf-8',errors='replace'))

def normalize(text):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKC',text) if c.isalnum())

def whisper_tokens(raw):
    chars, times = [], []
    for segment in raw.get('transcription', []):
        for token in segment.get('tokens', []):
            if token['text'].startswith('[_'):
                continue
            text = normalize(token['text'])
            if not text:
                continue
            dtw = token.get('t_dtw', -1)
            if not isinstance(dtw, (int,float)) or dtw < 0:
                raise WorkflowError('转写缺少真实 DTW 时间；whisper.cpp 必须使用 --no-flash-attn')
            chars.extend(text); times.extend([dtw / 100] * len(text))
    return ''.join(chars), times

def captions_from_tokens(script, text, times, duration, max_chars=14):
    if normalize(script) != text:
        raise WorkflowError('转写与原稿不一致。请核对读音或修正有音频依据的转写，不使用估算时间')
    if len(text) != len(times) or not times or any(not math.isfinite(t) for t in times):
        raise WorkflowError('声学时间数据无效')
    if any(b < a for a,b in zip(times,times[1:])) or min(times)<0 or max(times)>duration+.12:
        raise WorkflowError('转写时间倒退或超出真实音频')
    if len(text)>8 and times[-1] - times[0] < .2:
        raise WorkflowError('转写时间异常集中，不能作为逐句字幕')
    pieces = [s.strip() for s in re.split(r'[，。！？；：,!?;:\n]+', script) if normalize(s)]
    groups = []
    for piece in pieces:
        # Split at a character limit; timing still uses original acoustic anchors.
        while len(normalize(piece)) > max_chars:
            count, end = 0, 0
            for end,c in enumerate(piece,1):
                count += len(normalize(c))
                if count >= max_chars: break
            groups.append(piece[:end]); piece=piece[end:].strip()
        if normalize(piece): groups.append(piece)
    cues, cursor = [], 0
    for group in groups:
        start = max(0., times[cursor]-.10)
        if start >= duration:
            raise WorkflowError('最后台词缺少有效时间')
        cues.append({'text':group,'start':round(start,3)})
        cursor += len(normalize(group))
    for i,cue in enumerate(cues):
        cue['end'] = cues[i+1]['start'] if i+1<len(cues) else duration
        if cue['end'] - cue['start'] < .20:
            raise WorkflowError('字幕过短或声学边界重叠；请按真实转写合并短句')
    return cues

def align(job, transcript=None, model='base'):
    if existing := job.artifact('captions'):
        return read(existing)
    audio = media.narration(job)
    duration = media.seconds(job.artifact('avatar'))
    if transcript:
        raw = read_transcript(transcript)
        write(job.path/'evidence/alignment-input.json',raw)
    else:
        if model not in ['base','small','medium','large-v3']:
            raise WorkflowError('中文对齐请选择受支持的多语言模型')
        exe = os.environ.get('DH_WHISPER_PATH')
        runtime = ROOT/'.runtime/whisper.json'
        settings = read(runtime) if runtime.exists() else {}
        exe = exe or settings.get('executable')
        model_path = os.environ.get('DH_WHISPER_MODEL') or settings.get('models',{}).get(model)
        if not exe or not Path(exe).is_file() or not model_path or not Path(model_path).is_file():
            raise WorkflowError('先运行 scripts/setup_whisper.py，或提供真实词级转写 JSON')
        wav = media.extract_audio(audio, job.path/'assets/alignment.wav',16000)
        base = job.path/'evidence/whisper'
        media.run([exe,'--model',model_path,'--language','zh','--dtw',model,
            '--no-flash-attn','--output-json-full','--suppress-nst','--output-file',str(base),wav],
            job.path/'evidence/whisper.log', timeout=max(120, int(duration*20)))
        raw = read_transcript(base.with_suffix('.json'))
    if isinstance(raw, dict) and 'transcription' in raw:
        text, times = whisper_tokens(raw)
    elif isinstance(raw, list):
        # Reviewed timestamped tokens, or provider words normalized to this schema.
        text, times = '', []
        for item in raw:
            word = normalize(item['text'])
            if not isinstance(item.get('start'), (int,float)):
                raise WorkflowError('转写 token 需要真实 start 秒数')
            text += word; times += [item['start']]*len(word)
    else:
        raise WorkflowError('不支持的真实时间戳格式')
    cues = captions_from_tokens(job.script(),text,times,duration)
    write(job.path/'captions.json',{'duration':duration,'source':'acoustic_token_alignment','captions':cues})
    job.record('captions','captions.json')
    return read(job.path/'captions.json')

def srt(cues):
    def stamp(t):
        ms=round(t*1000)
        return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    return '\n'.join(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}\n' for i,c in enumerate(cues))
