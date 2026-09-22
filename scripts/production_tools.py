#!/usr/bin/env python3
"""Optional local tools for Codex-authored advertising projects; no network or spend."""
import argparse
import json
from pathlib import Path
from digital_human import caption_design, framing, production_audit
from digital_human.storage import WorkflowError


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['audit', 'captions', 'crop'])
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    try:
        value = json.loads(args.plan.read_text(encoding='utf-8'))
        if args.out.exists():
            raise WorkflowError('Output exists; preserve the previous revision')
        if args.operation == 'captions':
            result = caption_design.build(value)
            args.out.mkdir(parents=True, exist_ok=False)
            for name, body in [('captions.html', result['html']), ('subtitles.srt', result['srt']),
                               ('sample-points.json', json.dumps(result['sample_points'], ensure_ascii=False, indent=2))]:
                with (args.out/name).open('x', encoding='utf-8') as f:
                    f.write(body+'\n')
            result = {'output': str(args.out), 'fonts_required': result['fonts_required'],
                      'next': 'Wire captions.html at start=0; install licensed local fonts and inspect actual rendering'}
        else:
            result = (production_audit.audit if args.operation == 'audit' else framing.plan_crop)(value)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
    except (WorkflowError, ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=True))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get('ok') is False:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
