"""Rejection invalidates future generation without destroying source or paid recovery."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from digital_human import cloud, quality
from digital_human.cli import execute, parser
from digital_human.storage import Workspace, WorkflowError, file_hash
from test_state_budget import ready
from test_cloud_recovery import FakeVoice, FakeAvatar
from quality_fixtures import ready_avatar, baseline_review


class BaselineRevocationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.w = ready(Workspace(Path(temp.name) / 'data'))
        probe = patch('digital_human.media.probe', return_value={
            'format': {'duration': '18.5'}, 'streams': [{'codec_type': 'audio'}]})
        probe.start(); self.addCleanup(probe.stop)
        self.source = self.w.prepare('校准样片。')
        cloud.speech(self.source, FakeVoice()); ready_avatar(self.source)
        (self.source.path / 'assets/avatar.mp4').write_bytes(b'fixture-avatar')
        self.source.record('avatar', 'assets/avatar.mp4')
        self.bid = quality.accept_baseline(self.source, baseline_review(self.source))['baseline_id']
        self.target = self.w.prepare('后续正式文案。')
        cloud.speech(self.target, FakeVoice())
        quality.save_plan(self.target, reuse_baseline=self.bid)

    def test_cli_revokes_before_paid_submission_and_preserves_evidence(self):
        source_path = self.w.path / 'baselines' / (self.bid + '.json')
        before = file_hash(source_path)
        args = parser().parse_args(['--workspace', str(self.w.path), 'revoke-baseline',
                                   self.bid, '--reason', '用户否定长片中的周期摇头与口型表现。'])
        self.assertTrue(execute(args)['revoked'])
        self.assertTrue(execute(args)['already_recorded'])
        self.assertEqual(file_hash(source_path), before)
        self.assertTrue(self.source.artifact('avatar').exists())
        with self.assertRaises(WorkflowError): quality.save_plan(self.target, reuse_baseline=self.bid)
        provider = FakeAvatar()
        with self.assertRaises(WorkflowError): cloud.submit_avatar(self.target, provider)
        self.assertEqual((provider.calls, provider.uploads), (0, 0))
        self.assertNotIn('avatar', self.target.load()['operations'])

    def test_revocation_keeps_paid_recovery_available(self):
        state = self.target.load()
        state['operations']['avatar'] = {'status': 'submitted', 'video_id': 'existing_video',
                                         'reserved': {'usd': 1}}
        state['remote']['video_id'] = 'existing_video'; self.target.save(state)
        quality.revoke_baseline(self.w, self.bid, '用户反馈表情失真，需要下一版重新校准。')
        provider = FakeAvatar()
        self.assertEqual(cloud.submit_avatar(self.target, provider)['video_id'], 'existing_video')
        self.assertEqual((provider.calls, provider.uploads), (0, 0))

    def test_invalid_or_missing_baseline_cannot_be_revoked(self):
        for bid in ['../outside', 'a' * 24]:
            with self.assertRaises(WorkflowError): quality.revoke_baseline(self.w, bid, '用户要求停止复用这个基线。')


if __name__ == '__main__': unittest.main()
