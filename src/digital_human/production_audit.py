"""Audit declared acoustic, caption and speaking-avatar clocks; never claim visual QA."""
import math
import re
from .coverage import subtract, union
from .storage import WorkflowError


def number(value, name, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise WorkflowError(name + ' requires a finite number in range')
    return value


def records(value, name, duration):
    rows = value.get(name)
    if not isinstance(rows, list):
        raise WorkflowError(name + ' must be an explicit list')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', row.get('id', '')):
            raise WorkflowError(name + ': invalid id')
        if row['id'] in seen:
            raise WorkflowError(name + ': duplicate id')
        seen.add(row['id'])
        a = number(row.get('start'), name + '.start')
        b = number(row.get('end'), name + '.end')
        if not a < b <= duration:
            raise WorkflowError(name + ': invalid interval')
    return rows


def audit(value):
    if value.get('schema') != 'production-audit/v1':
        raise WorkflowError('Expected production-audit/v1')
    duration = number(value.get('duration'), 'duration', .001)
    fps = number(value.get('fps'), 'fps', 1)
    tolerance = 1 / fps  # One output frame, not a user-controlled waiver.
    utterances = records(value, 'utterances', duration)
    captions = records(value, 'captions', duration)
    audio = records(value, 'audio_spans', duration)
    presenters = records(value, 'presenter_spans', duration)
    errors = []

    def error(code, identity, **details):
        errors.append({'code': code, 'id': identity, **details})

    def uncovered(start, end, spans):
        return [[a, b] for a, b in subtract([[start, end]], union(spans)) if b-a > tolerance + 1e-9]

    for row in audio + presenters:
        for key in ('audio_id', 'speaker'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise WorkflowError(row['id'] + ': missing ' + key)
        number(row.get('source_start'), 'source_start')
        number(row.get('rate', 1), 'rate', .001)
    ordered_audio = sorted(audio, key=lambda x: x['start'])
    if any(a['end'] > b['start'] + 1e-9 for a, b in zip(ordered_audio, ordered_audio[1:])):
        raise WorkflowError('audio_spans must describe one non-overlapping narration bus')
    known = {row['id']: row for row in utterances}
    for row in utterances + captions:
        if any(not isinstance(row.get(key, ''), str) for key in ('primary', 'secondary')):
            raise WorkflowError(row['id'] + ': caption language slots must be strings')
    for row in utterances:
        if not isinstance(row.get('primary'), str) or not row['primary'].strip():
            raise WorkflowError(row['id'] + ': primary text required')
        if not isinstance(row.get('speaker'), str) or not row['speaker'].strip():
            raise WorkflowError(row['id'] + ': speaker required')
        matches = [c for c in captions if c.get('utterance_id') == row['id']]
        if len(matches) != 1:
            error('caption_missing_or_duplicate', row['id'], count=len(matches))
            continue
        cue = matches[0]
        if cue.get('visible', True) is not True:
            error('caption_hidden', cue['id'])
        for key in ('primary', 'secondary'):
            if cue.get(key, '').strip() != row.get(key, '').strip():
                error('caption_text_changed', cue['id'], language_slot=key)
        if max(abs(cue['start']-row['start']), abs(cue['end']-row['end'])) > tolerance + 1e-9:
            error('caption_clock_mismatch', cue['id'])
        spans = [[a['start'], a['end']] for a in audio if a['speaker'] == row.get('speaker')]
        if uncovered(row['start'], row['end'], spans):
            error('utterance_without_matching_audio', row['id'])
    ordered_captions = sorted(captions, key=lambda x: x['start'])
    for a, b in zip(ordered_captions, ordered_captions[1:]):
        if a['end'] > b['start'] + 1e-9:
            error('caption_overlap', b['id'], previous=a['id'])
    for cue in captions:
        if cue.get('utterance_id') not in known:
            error('caption_without_utterance', cue['id'])
    for clip in presenters:
        mapped = []
        for sound in audio:
            a, b = max(clip['start'], sound['start']), min(clip['end'], sound['end'])
            if a >= b:
                continue
            if (sound['audio_id'], sound['speaker']) != (clip['audio_id'], clip['speaker']):
                error('presenter_wrong_voice', clip['id'], audio_span=sound['id'])
                continue
            delta = max(abs((clip['source_start'] + (t-clip['start'])*clip.get('rate', 1)) -
                            (sound['source_start'] + (t-sound['start'])*sound.get('rate', 1)))
                        for t in (a, b))
            if delta > tolerance + 1e-9:
                error('presenter_clock_mismatch', clip['id'], delta_seconds=round(delta, 6))
            else:
                mapped.append([a, b])
        gaps = uncovered(clip['start'], clip['end'], mapped)
        if gaps:
            error('unmapped_speaking_presenter', clip['id'], intervals=gaps)
    mode = value.get('coverage_mode', 'selective')
    if mode not in ('selective', 'continuous_pip'):
        raise WorkflowError('Unknown coverage_mode')
    if mode == 'continuous_pip':
        speaker = value.get('main_speaker')
        if not isinstance(speaker, str) or not speaker:
            raise WorkflowError('continuous_pip requires main_speaker')
        for row in utterances:
            if row.get('speaker') == speaker:
                visible = [[p['start'], p['end']] for p in presenters if p['speaker'] == speaker]
                if gaps := uncovered(row['start'], row['end'], visible):
                    error('continuous_presenter_gap', row['id'], intervals=gaps)
    return {'schema': 'production-audit-result/v1', 'ok': not errors,
            'scope': 'declared_plan_only', 'ready_for_delivery': False,
            'caption_count': len(captions), 'presenter_count': len(presenters),
            'tolerance_seconds': tolerance, 'errors': errors,
            'required_next': ['Verify plan against final rendered text and source frames',
                              'Review actual motion, voice and lip performance',
                              'Decode full output; verify audio, dimensions and hashes']}
