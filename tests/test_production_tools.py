"""Regression cases for omitted captions, staged delays, reel drift and framing."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from digital_human.caption_design import build
from digital_human.framing import plan_crop
from digital_human.production_audit import audit
from digital_human.storage import ROOT, WorkflowError


def plan():
    return {'schema': 'production-audit/v1', 'duration': 8, 'fps': 25,
            'utterances': [{'id': 'u1', 'start': 1, 'end': 3, 'speaker': 'host',
                            'primary': '表达清楚', 'secondary': 'Make it clear.'}],
            'captions': [{'id': 'c1', 'utterance_id': 'u1', 'start': 1, 'end': 3,
                          'primary': '表达清楚', 'secondary': 'Make it clear.'}],
            'audio_spans': [{'id': 'a1', 'start': 0, 'end': 8, 'audio_id': 'accepted-audio-hash',
                             'speaker': 'host', 'source_start': 20}],
            'presenter_spans': [{'id': 'p1', 'start': 1, 'end': 3, 'audio_id': 'accepted-audio-hash',
                                 'speaker': 'host', 'source_start': 21}]}


class ProductionAudit(unittest.TestCase):
    def codes(self, p):
        return {row['code'] for row in audit(p)['errors']}

    def test_valid_plan_never_claims_actual_delivery(self):
        result = audit(plan())
        self.assertTrue(result['ok'])
        self.assertFalse(result['ready_for_delivery'])

    def test_missing_and_hidden_captions_are_detected(self):
        p = plan(); p['captions'] = []
        self.assertIn('caption_missing_or_duplicate', self.codes(p))
        p = plan(); p['captions'][0]['visible'] = False
        self.assertIn('caption_hidden', self.codes(p))

    def test_art_directed_delay_is_not_allowed(self):
        p = plan(); p['captions'][0]['start'] += .64
        self.assertIn('caption_clock_mismatch', self.codes(p))

    def test_missing_translation_is_detected(self):
        p = plan(); p['captions'][0]['secondary'] = ''
        self.assertIn('caption_text_changed', self.codes(p))

    def test_overlapping_caption_is_detected(self):
        p = plan(); row = copy.deepcopy(p['captions'][0]); row['id'] = 'c2'; p['captions'].append(row)
        self.assertIn('caption_overlap', self.codes(p))

    def test_wrong_demo_utterance_is_detected(self):
        p = plan(); p['presenter_spans'][0]['source_start'] = 40
        self.assertIn('presenter_clock_mismatch', self.codes(p))

    def test_wrong_speaker_or_voice_is_detected(self):
        for field, value in [('speaker', 'guest'), ('audio_id', 'different-audio-hash')]:
            p = plan(); p['presenter_spans'][0][field] = value
            self.assertIn('presenter_wrong_voice', self.codes(p))

    def test_rate_drift_at_end_is_detected(self):
        p = plan(); p['presenter_spans'][0]['rate'] = 1.1
        self.assertIn('presenter_clock_mismatch', self.codes(p))

    def test_continuous_mode_checks_all_speech_but_selective_does_not(self):
        p = plan(); p['presenter_spans'] = []
        self.assertTrue(audit(p)['ok'])
        p.update(coverage_mode='continuous_pip', main_speaker='host')
        self.assertIn('continuous_presenter_gap', self.codes(p))

    def test_reel_crossing_validates_both_clocks(self):
        p = plan(); p['audio_spans'] = [
            {**p['audio_spans'][0], 'end': 2},
            {**p['audio_spans'][0], 'id': 'a2', 'start': 2, 'source_start': 22}]
        self.assertTrue(audit(p)['ok'])
        p['audio_spans'][1]['source_start'] = 30
        self.assertIn('presenter_clock_mismatch', self.codes(p))

    def test_bad_numbers_and_duplicates_fail_closed(self):
        for value in (True, float('nan'), -1):
            p = plan(); p['fps'] = value
            with self.assertRaises(WorkflowError): audit(p)
        p = plan(); p['captions'].append(copy.deepcopy(p['captions'][0]))
        with self.assertRaises(WorkflowError): audit(p)


class Captions(unittest.TestCase):
    def value(self):
        return {'width': 1920, 'height': 1080, 'duration': 8,
                'cues': [{'id': 'c1', 'start': 1.125, 'end': 3.5, 'primary': '清楚\n表达',
                          'secondary': 'A <script> & a voice.'}]}

    def test_same_cues_feed_srt_html_and_sample_points(self):
        result = build(self.value())
        self.assertIn('00:00:01,125 --> 00:00:03,500', result['srt'])
        self.assertIn('data-start="1.125"', result['html'])
        self.assertIn('清楚\n表达', result['html'])
        self.assertIn('&lt;script&gt; &amp;', result['html'])
        self.assertEqual(result['sample_points'][0]['at'], 1.575)

    def test_bilingual_order_is_configurable_not_fixed_to_english_audio(self):
        p = self.value(); p['cues'][0].update(primary='English on top', secondary='中文在下')
        result = build(p)
        self.assertLess(result['srt'].index('English'), result['srt'].index('中文'))

    def test_no_missing_translation_row_when_monolingual(self):
        p = self.value(); p['cues'][0].pop('secondary')
        self.assertNotIn('<div class="secondary">', build(p)['html'])

    def test_overlaps_and_font_path_escape_rejected(self):
        p = self.value(); p['cues'].append({**p['cues'][0], 'id': 'c2'})
        with self.assertRaises(WorkflowError): build(p)
        for path in ('../font.ttf', 'https://example.com/f.ttf', '/font.ttf', 'bad\".ttf'):
            p = self.value(); p['fonts'] = {'primary': path}
            with self.assertRaises(WorkflowError): build(p)

    def test_two_aspect_ratios_and_long_word_are_not_force_wrapped(self):
        for width, height in [(1920, 1080), (1080, 1920)]:
            p = self.value(); p.update(width=width, height=height)
            result = build(p)
            self.assertIn(f'data-width="{width}"', result['html'])
            self.assertNotIn('overflow-wrap:anywhere', result['html'])


class Framing(unittest.TestCase):
    def test_crop_centers_head_not_canvas(self):
        p = {'width': 1920, 'height': 1080, 'head_bounds': [[430, 80, 180, 210], [450, 90, 180, 210]]}
        result = plan_crop(p); crop = result['crop']
        self.assertAlmostEqual(crop['x']+crop['width']/2, 530, delta=1)
        self.assertFalse(result['retime'])
        self.assertEqual(crop['width'], crop['height'])

    def test_edge_crop_retains_every_box(self):
        boxes = [[0, 0, 80, 100], [8, 4, 90, 100]]
        result = plan_crop({'width': 640, 'height': 360, 'head_bounds': boxes})['crop']
        for x, y, w, h in boxes:
            self.assertLessEqual(result['x'], x); self.assertLessEqual(result['y'], y)
            self.assertGreaterEqual(result['x']+result['width'], x+w)
            self.assertGreaterEqual(result['y']+result['height'], y+h)

    def test_missing_or_impossible_headroom_is_rejected(self):
        for boxes in ([], [[0, 0, 1800, 1000]], [[1900, 0, 100, 100]]):
            with self.assertRaises(WorkflowError):
                plan_crop({'width': 1920, 'height': 1080, 'head_bounds': boxes})


class Command(unittest.TestCase):
    def test_utf8_output_and_previous_result_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); p = folder/'plan.json'; out = folder/'审核.json'
            p.write_text(json.dumps(plan(), ensure_ascii=False), encoding='utf-8')
            args = [sys.executable, str(ROOT/'scripts/production_tools.py'), 'audit', '--plan', str(p), '--out', str(out)]
            first = subprocess.run(args, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = out.read_bytes()
            second = subprocess.run(args, capture_output=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(before, out.read_bytes())


if __name__ == '__main__':
    unittest.main()
