import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from digital_human import cloud, quality, runner
from digital_human.cli import parser, execute
from digital_human.config import configure, validate
from digital_human.budget import require_consent
from digital_human.storage import Workspace, WorkflowError, read, write, file_hash
from digital_human.providers.heygen import avatar_payload
from digital_human.providers.minimax import MiniMax
from test_state_budget import ready
from test_cloud_recovery import FakeAvatar, FakeVoice
from quality_fixtures import plan, voice_review, ready_avatar, baseline_review


class QualityTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.w=ready(Workspace(Path(temp.name)/'data'));self.job=self.w.prepare('测试素材。')
        mock=patch('digital_human.media.probe',return_value={'format':{'duration':'18.5'},'streams':[{'codec_type':'audio'}]})
        mock.start();self.addCleanup(mock.stop)
        cloud.speech(self.job,FakeVoice())

    def test_api_missing_plan_or_voice_review_never_uploads(self):
        p=FakeAvatar()
        with self.assertRaises(WorkflowError):cloud.submit_avatar(self.job,p)
        quality.save_plan(self.job,plan(self.job))
        with self.assertRaises(WorkflowError):cloud.submit_avatar(self.job,p)
        self.assertEqual((p.calls,p.uploads),(0,0))

    def test_mcp_cannot_skip_reviews_even_with_registered_asset(self):
        configure(self.w,{'heygen':{'transport':'mcp'}})
        job=self.w.prepare('MCP 测试。');cloud.speech(job,FakeVoice())
        cloud.record_remote(job,asset_id='example_asset')
        with self.assertRaises(WorkflowError):cloud.mcp_begin(job)
        self.assertNotIn('avatar',job.load()['operations'])

    def test_direct_upload_also_requires_review(self):
        args=parser().parse_args(['--workspace',str(self.w.path),'put-upload',self.job.path.name,'--receipt','unused.json'])
        with patch('digital_human.network.put_presigned') as upload:
            with self.assertRaises(WorkflowError):execute(args)
            upload.assert_not_called()

    def test_runner_returns_next_codex_action(self):
        self.assertEqual(runner.run(self.job)['status'],'needs_quality_plan')
        quality.save_plan(self.job,plan(self.job))
        self.assertEqual(runner.run(self.job)['status'],'needs_voice_review')

    def test_fresh_run_stops_after_voice_before_avatar_call(self):
        job=self.w.prepare('新校准文案。');quality.save_plan(job,plan(job))
        p=FakeVoice()
        with patch('digital_human.cloud.MiniMax',return_value=p), patch('digital_human.cloud.submit_avatar') as submit:
            self.assertEqual(runner.run(job)['status'],'needs_voice_review')
            self.assertEqual(p.calls,1);submit.assert_not_called()

    def test_direct_upload_budget_is_checked_before_transfer(self):
        ready_avatar(self.job)
        configure(self.w,{'authorization':{'max_usd_per_job':.001}})
        args=parser().parse_args(['--workspace',str(self.w.path),'put-upload',self.job.path.name,'--receipt','unused.json'])
        with patch('digital_human.network.put_presigned') as upload:
            with self.assertRaises(WorkflowError):execute(args)
            upload.assert_not_called()

    def test_pose_or_engine_mismatch_stops_before_spend(self):
        p=plan(self.job);p['motion_review']['pose_matches']=False
        with self.assertRaises(WorkflowError):quality.save_plan(self.job,p)
        p=plan(self.job);p['capability']['supported_api_engines']=[]
        with self.assertRaises(WorkflowError):quality.save_plan(self.job,p)
        self.assertNotIn('avatar',self.job.load()['operations'])

    def test_review_for_other_audio_or_asr_only_is_rejected(self):
        r=voice_review(self.job);r['voice_sha256']='0'*64
        with self.assertRaises(WorkflowError):quality.review_voice(self.job,r)
        r=voice_review(self.job);r['method']='asr'
        with self.assertRaises(WorkflowError):quality.review_voice(self.job,r)

    def test_replaced_voice_invalidates_saved_review(self):
        ready_avatar(self.job)
        self.job.artifact('voice').write_bytes(b'another-voice')
        self.job.record('voice','assets/voice.mp3')
        with self.assertRaises(WorkflowError):quality.require_avatar_ready(self.job)

    def test_overlong_calibration_blocks(self):
        p=plan(self.job);p['sample_max_seconds']=10;quality.save_plan(self.job,p)
        quality.review_voice(self.job,voice_review(self.job))
        with self.assertRaises(WorkflowError):quality.require_avatar_ready(self.job)

    def test_stale_capability_requires_read_only_refresh(self):
        p=plan(self.job);p['capability']['checked_at']=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        with self.assertRaises(WorkflowError):quality.save_plan(self.job,p)

    def test_legacy_inflight_can_resume_after_generation_revoked(self):
        meta=self.job.load();meta.pop('quality_version',None)
        meta['operations']['avatar']={'status':'submitted','video_id':'example_video','reserved':{'usd':1}}
        meta['remote']['video_id']='example_video';self.job.save(meta)
        configure(self.w,{'authorization':{'generation':False}})
        p=FakeAvatar();self.assertEqual(cloud.submit_avatar(self.job,p)['video_id'],'example_video')
        cloud.poll_avatar(self.job,p);self.assertEqual((p.calls,p.uploads),(0,0))

    def test_ready_plan_does_not_override_revoked_authorization(self):
        ready_avatar(self.job);configure(self.w,{'authorization':{'generation':False}})
        p=FakeAvatar()
        with self.assertRaises(WorkflowError):cloud.submit_avatar(self.job,p)
        self.assertEqual(p.uploads,0)

    def test_production_requires_matching_accepted_baseline(self):
        p=plan(self.job);p['mode']='production'
        with self.assertRaises(WorkflowError):quality.save_plan(self.job,p)
        ready_avatar(self.job)
        (self.job.path/'assets/avatar.mp4').write_bytes(b'fixture-avatar');self.job.record('avatar','assets/avatar.mp4')
        r=baseline_review(self.job);r['user_accepted']=False
        with self.assertRaises(WorkflowError):quality.accept_baseline(self.job,r)
        bid=quality.accept_baseline(self.job,baseline_review(self.job))['baseline_id']
        next_job=self.w.prepare('另一条文案。');quality.save_plan(next_job,reuse_baseline=bid)
        self.assertEqual(quality.plan(next_job)['mode'],'production')
        configure(self.w,{'heygen':{'motion_prompt':'A small nod.'}})
        changed=self.w.prepare('已变更动作。')
        with self.assertRaises(WorkflowError):quality.save_plan(changed,reuse_baseline=bid)

    def test_v01_profile_load_does_not_rewrite_job_hash(self):
        p=self.w.profile()
        p['heygen'].pop('motion_prompt');p['heygen'].pop('reference_look_id');p['minimax'].pop('emotion')
        write(self.w.path/'profile.json',p);validate(p)
        old=self.w.prepare('旧配置保持兼容。');sha=file_hash(old.path/'profile.json')
        self.assertEqual(old.profile(),p);self.assertEqual(file_hash(old.path/'profile.json'),sha)
        configure(self.w,{'minimax':{'emotion':None},'heygen':{'motion_prompt':None,'reference_look_id':None}})
        require_consent(old,['heygen'])
        configure(self.w,{'minimax':{'emotion':'calm'}})
        self.assertEqual(file_hash(old.path/'profile.json'),sha)

    def test_emotion_compatibility_is_explicit(self):
        with self.assertRaises(WorkflowError):configure(self.w,{'minimax':{'emotion':'fluent'}})
        configure(self.w,{'minimax':{'model':'speech-2.6-hd','emotion':'fluent'}})
        p=MiniMax(self.w,self.w.profile(),client=object()).speech_payload('测试。')
        self.assertEqual(p['voice_setting']['emotion'],'fluent')

    def test_default_voice_emotion_and_motion_are_omitted(self):
        p=MiniMax(self.w,self.w.profile(),client=object()).speech_payload('测试。')
        self.assertNotIn('emotion',p['voice_setting'])
        self.assertNotIn('motion_prompt',avatar_payload(self.w.profile(),'asset','job'))

    def test_v_payload_and_mcp_nested_reference_match_official_schema(self):
        configure(self.w,{'heygen':{'engine':'avatar_v','reference_look_id':'example_reference','motion_prompt':'A small nod.'}})
        p=self.w.profile();api=avatar_payload(p,'asset','job');mcp=avatar_payload(p,'asset','job',True)
        self.assertEqual(api['engine'],mcp['engine'])
        self.assertEqual(api['engine']['reference_look_id'],'example_reference')
        self.assertEqual(api['motion_prompt'],mcp['motionPrompt'])
        for value in [api,mcp]:
            self.assertNotIn('expressiveness',value);self.assertNotIn('expressiveness',value['engine'])
            self.assertNotIn('script',value)
        with self.assertRaises(WorkflowError):configure(self.w,{'heygen':{'engine':'avatar_iv'}})

if __name__=='__main__':unittest.main()
