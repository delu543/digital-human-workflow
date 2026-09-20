from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from digital_human.storage import Workspace, WorkflowError, write
from digital_human import cloud
from digital_human.config import configure
from digital_human.network import Client, ProviderError
from test_state_budget import ready
from quality_fixtures import ready_avatar

class FakeVoice:
    def __init__(self,fail=False):self.calls=0;self.fail=fail
    def speech_payload(self,text,voice_id=None):return {'text':text,'voice_id':voice_id or 'example_voice'}
    def speech(self,payload):
        self.calls+=1
        if self.fail:raise ProviderError('timeout')
        return {'data':{'audio':b'fixture-audio'.hex()},'extra_info':{'usage_characters':12}}

class FakeAvatar:
    def __init__(self,fail=False):self.uploads=0;self.calls=0;self.fail=fail
    def upload(self,path):self.uploads+=1;return 'example_asset'
    def payload(self,asset,job):return {'audio_asset_id':asset,'avatar_id':'example_avatar','job':job}
    def create(self,payload):
        self.calls+=1
        if self.fail:raise ProviderError('connection closed')
        return {'data':{'video_id':'example_video','status':'waiting'}}
    def get(self,video):return {'data':{'id':video,'status':'processing'}}

class CloudTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.w=ready(Workspace(Path(t.name)/'data'));self.job=self.w.prepare('测试一个新的表达。')
        self.probe=patch('digital_human.media.probe',return_value={'format':{'duration':'18.5'},'streams':[{'codec_type':'audio'}]})
        self.probe.start();self.addCleanup(self.probe.stop)

    def voice(self):
        cloud.speech(self.job,FakeVoice());ready_avatar(self.job)

    def test_paid_voice_called_once(self):
        p=FakeVoice();cloud.speech(self.job,p);cloud.speech(self.job,p)
        self.assertEqual(p.calls,1)

    def test_timeout_stops_duplicate_voice(self):
        p=FakeVoice(fail=True)
        with self.assertRaises(WorkflowError):cloud.speech(self.job,p)
        with self.assertRaises(WorkflowError):cloud.speech(self.job,p)
        self.assertEqual(p.calls,1)

    def test_saved_response_recovers_without_request(self):
        p=FakeVoice(fail=True)
        with self.assertRaises(WorkflowError):cloud.speech(self.job,p)
        write(self.job.path/'receipts/minimax-speech.json',{'data':{'audio':b'recovered'.hex()}})
        cloud.speech(self.job,p);self.assertEqual(p.calls,1)

    def test_avatar_submit_and_resume_preserve_one_request(self):
        self.voice();p=FakeAvatar()
        cloud.submit_avatar(self.job,p);cloud.submit_avatar(self.job,p);cloud.poll_avatar(self.job,p)
        self.assertEqual((p.uploads,p.calls),(1,1))

    def test_avatar_timeout_does_not_resubmit(self):
        self.voice();p=FakeAvatar(True)
        with self.assertRaises(WorkflowError):cloud.submit_avatar(self.job,p)
        with self.assertRaises(WorkflowError):cloud.submit_avatar(self.job,p)
        self.assertEqual(p.calls,1)

    def test_budget_rejection_precedes_upload(self):
        self.voice();configure(self.w,{'authorization':{'max_usd_per_job':.001}})
        p=FakeAvatar()
        with self.assertRaises(WorkflowError):cloud.submit_avatar(self.job,p)
        self.assertEqual((p.uploads,p.calls),(0,0))

    def test_mcp_never_falls_back_to_api(self):
        self.voice()
        with self.assertRaises(WorkflowError):cloud.mcp_begin(self.job)

    def test_mcp_crash_after_reservation_requires_reconciliation(self):
        configure(self.w,{'heygen':{'transport':'mcp'}})
        job=self.w.prepare('另一个测试。');cloud.speech(job,FakeVoice())
        ready_avatar(job)
        cloud.record_remote(job,asset_id='example_asset')
        result=cloud.mcp_begin(job);self.assertEqual(result['arguments']['audioAssetId'],'example_asset')
        self.assertNotIn('script',result['arguments'])
        with self.assertRaises(WorkflowError):cloud.mcp_begin(job)
        cloud.record_remote(job,video_id='example_video')
        self.assertEqual(cloud.mcp_begin(job)['action'],'resume_existing')

    def test_wrong_video_receipt_rejected(self):
        self.voice();cloud.submit_avatar(self.job,FakeAvatar())
        with self.assertRaises(WorkflowError):cloud.receive_avatar(self.job,{'id':'another_video','status':'completed','video_url':'https://example.org/a.mp4'})

    def test_provider_error_does_not_echo_response_or_key(self):
        class Response:
            status_code=401
            text='private-response-content'
        class Session:
            def request(self,*a,**kw):
                assert kw['allow_redirects'] is False
                return Response()
        c=Client('https://api.minimax.io',{'Authorization':'private-key'},Session())
        with self.assertRaises(ProviderError) as e:c.call('POST','/v1/t2a_v2',{})
        self.assertNotIn('private',str(e.exception))

if __name__=='__main__':unittest.main()
