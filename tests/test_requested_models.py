"""Explicit model requirements must survive preparation and block wrong paid calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from digital_human import cloud, quality
from digital_human.config import configure
from digital_human.storage import Workspace, WorkflowError, read, write
from test_state_budget import ready
from test_cloud_recovery import FakeVoice, FakeAvatar
from quality_fixtures import plan, ready_avatar


class RequestedModelTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.w = ready(Workspace(Path(temp.name) / 'data'))
        probe = patch('digital_human.media.probe', return_value={
            'format': {'duration': '18.5'}, 'streams': [{'codec_type': 'audio'}]})
        probe.start(); self.addCleanup(probe.stop)

    def test_profile_downgrade_cannot_pass_quality_plan(self):
        configure(self.w, {'heygen': {'engine': 'avatar_iii'}})
        job = self.w.prepare('模型要求测试。', {'model_requirements': {'heygen_engine': 'avatar_v'}})
        with self.assertRaises(WorkflowError): quality.save_plan(job, plan(job))
        self.assertNotIn('avatar', job.load()['operations'])

    def test_voice_adapter_cannot_silently_change_model(self):
        required = self.w.profile()['minimax']['model']
        job = self.w.prepare('声音模型测试。', {'model_requirements': {'minimax_model': required}})
        p = FakeVoice()  # Omits the required outgoing model.
        with self.assertRaises(WorkflowError): cloud.speech(job, p)
        self.assertEqual(p.calls, 0)
        self.assertNotIn('voice', job.load()['operations'])

    def test_matching_voice_request_is_allowed_and_recovers_once(self):
        required = self.w.profile()['minimax']['model']
        job = self.w.prepare('正确模型测试。', {'model_requirements': {'minimax_model': required}})
        class MatchingVoice(FakeVoice):
            def speech_payload(self, text, voice_id=None):
                return {'model': required, 'text': text}
        p = MatchingVoice(); cloud.speech(job, p); cloud.speech(job, p)
        self.assertEqual(p.calls, 1)

    def test_changing_or_removing_model_requirement_invalidates_job(self):
        job = self.w.prepare('固定模型测试。', {'model_requirements': {'heygen_engine': 'avatar_v'}})
        write(job.path / 'brief.json', {})
        with self.assertRaises(WorkflowError): job.load()

    def test_api_wrong_payload_is_blocked_before_paid_create(self):
        configure(self.w, {'heygen': {'engine': 'avatar_v'}})
        job = self.w.prepare('数字人口型测试。', {'model_requirements': {'heygen_engine': 'avatar_v'}})
        cloud.speech(job, FakeVoice()); ready_avatar(job)
        cloud.record_remote(job, asset_id='example_asset')
        p = FakeAvatar()  # No engine in the outgoing payload.
        with self.assertRaises(WorkflowError): cloud.submit_avatar(job, p)
        self.assertEqual((p.calls, p.uploads), (0, 0))
        self.assertNotIn('avatar', job.load()['operations'])

    def test_mcp_returns_the_required_engine(self):
        configure(self.w, {'heygen': {'engine': 'avatar_v', 'transport': 'mcp'}})
        job = self.w.prepare('会员模型测试。', {'model_requirements': {'heygen_engine': 'avatar_v'}})
        cloud.speech(job, FakeVoice()); ready_avatar(job)
        cloud.record_remote(job, asset_id='example_asset')
        self.assertEqual(cloud.mcp_begin(job)['arguments']['engine']['type'], 'avatar_v')


if __name__ == '__main__': unittest.main()
