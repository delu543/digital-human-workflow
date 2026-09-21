from copy import deepcopy
import unittest
from digital_human.coverage import plan
from digital_human.storage import WorkflowError

BASE = {'duration':30, 'mode':'continuous_pip', 'main_speech':[[0,12],[16,30]],
        'full_screen':[[0,5],[25,30]], 'available':[[0,5],[25,30]],
        'generation_units':[[0,5],[5,9],[9,12],[16,21],[21,25],[25,30]], 'max_reel_seconds':12}


class CoverageTests(unittest.TestCase):
    def test_missing_windows_are_not_silently_treated_as_no_speech(self):
        for data in [{'duration':30, 'mode':'continuous_pip'},
                     {'duration':30, 'mode':'selective', 'main_speech':[[0,30]]}]:
            with self.assertRaises(WorkflowError):plan(data)
        self.assertEqual(plan({'duration':30,'mode':'continuous_pip','main_speech':[]})['reels'],[])

    def test_pip_counts_missing_speech_not_silent_or_other_speaker(self):
        p = plan(BASE)
        self.assertEqual(p['missing'], [[5,12],[16,25]])
        self.assertEqual(p['generation_seconds'], 16)
        self.assertEqual([r['samples']/48000 for r in p['reels']], [12,4])
        self.assertFalse(p['generation_authorized'])

    def test_selective_does_not_regenerate_covered_avatar(self):
        p = plan({**BASE, 'mode':'selective'})
        self.assertEqual(p['reels'], [])

    def test_phrase_expansion_and_sample_mapping(self):
        p = plan({**BASE, 'available':[[0,6],[25,30]]})
        self.assertEqual(p['missing_visible_seconds'], 15)
        self.assertEqual(p['generation_seconds'], 16)
        for r in p['reels']:
            end = 0
            for s in r['segments']:
                self.assertEqual(s['reel_start_sample'], end)
                self.assertEqual(s['timeline_end_sample']-s['timeline_start_sample'], s['sample_count'])
                end += s['sample_count']

    def test_union_prevents_double_billing(self):
        p = plan({**BASE, 'main_speech':[[0,10],[5,12],[16,30]]})
        self.assertEqual(p['required_seconds'],26)

    def test_missing_acoustic_boundaries_fail_closed(self):
        for extra in [{'generation_units':[]}, {'max_reel_seconds':3},
                      {'main_speech':[[0,31]]}, {'duration':float('nan')},
                      {'generation_units':[[0,12],[10,30]]}]:
            with self.subTest(extra=extra), self.assertRaises(WorkflowError):
                plan({**deepcopy(BASE), **extra})


if __name__ == '__main__':
    unittest.main()
