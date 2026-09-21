#!/usr/bin/env python3
"""Codex writes the acoustic plan; this command checks coverage without spending."""
import argparse
import json
from pathlib import Path
from digital_human.coverage import plan

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = plan(json.loads(a.plan.read_text(encoding='utf-8')))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'output':str(a.out), 'generation_seconds':result['generation_seconds'],
                      'reels':len(result['reels']), 'cloud_calls':0}, ensure_ascii=True))
