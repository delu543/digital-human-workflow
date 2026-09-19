import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import unittest
from digital_human.storage import Workspace, WorkflowError, lock, read
from digital_human.config import configure, save_credential, credential
from digital_human.budget import reserve, quote

def ready(workspace, mode='api', cap=20):
    workspace.initialize()
    configure(workspace, {'minimax':{'voice_id':'example_voice'},
        'heygen':{'transport':mode,'avatar_id':'example_avatar'},
        'authorization':{'generation':True,'destinations':['minimax_international','heygen'],
                         'max_usd_per_job':cap,'max_heygen_credits_per_job':1000},
        'rates':{'minimax_usd_per_1000_chars':.1,'heygen_usd_per_minute':3,'heygen_credits_per_minute':31,
                 'verified_at':datetime.now(timezone.utc).isoformat()}})
    return workspace

class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.w=ready(Workspace(Path(self.temp.name)/'data'))
        self.job=self.w.prepare('这是一条虚构测试文案。')

    def test_prepare_deduplicates_even_after_restart(self):
        self.assertEqual(self.job.path,self.w.prepare(self.job.script()).path)
        self.assertNotEqual(self.job.path,self.w.prepare(self.job.script(),new=True).path)

    def test_modified_input_blocks_resume(self):
        (self.job.path/'script.txt').write_text('其他文案',encoding='utf-8')
        with self.assertRaises(WorkflowError):self.job.load()

    def test_process_lock_rejects_second_owner(self):
        with self.job.locked():
            with self.assertRaises(WorkflowError):
                with self.job.locked():pass

    def test_artifact_tampering_is_not_silently_regenerated(self):
        p=self.job.path/'assets/test.mp3';p.write_bytes(b'one')
        self.job.record('voice','assets/test.mp3');p.write_bytes(b'two')
        with self.assertRaises(WorkflowError):self.job.artifact('voice')

    def test_cost_limit_prevents_new_operation(self):
        with self.assertRaises(WorkflowError):reserve(self.job,'voice','minimax',{}, {'usd':21})
        self.assertEqual(self.job.load()['operations'],{})

    def test_two_operations_share_job_budget(self):
        reserve(self.job,'voice','minimax',{}, {'usd':15})
        with self.assertRaises(WorkflowError):reserve(self.job,'avatar','heygen',{}, {'usd':6})

    def test_uncertain_submission_is_not_new(self):
        op,fresh=reserve(self.job,'voice','minimax',{'text':'test'},{'usd':1})
        self.assertTrue(fresh);self.assertEqual(op['status'],'uncertain')
        self.assertFalse(reserve(self.job,'voice','minimax',{'text':'test'},{'usd':1})[1])
        with self.assertRaises(WorkflowError):reserve(self.job,'voice','minimax',{'text':'changed'},{'usd':1})

    def test_revocation_applies_to_existing_job(self):
        configure(self.w,{'authorization':{'generation':False}})
        with self.assertRaises(WorkflowError):reserve(self.job,'voice','minimax',{}, {'usd':1})

    def test_route_switch_needs_new_job(self):
        configure(self.w,{'heygen':{'transport':'mcp'}})
        with self.assertRaises(WorkflowError):reserve(self.job,'voice','minimax',{}, {'usd':1})

    def test_credentials_are_outside_profile_and_not_printed(self):
        result=save_credential(self.w,'minimax','example-not-a-real-key')
        self.assertEqual(credential(self.w,'minimax'),'example-not-a-real-key')
        self.assertNotIn('example-not-a-real-key',str(result)+str(self.w.profile()))
        if __import__('os').name!='nt':self.assertEqual((self.w.path/'secrets.json').stat().st_mode & 0o777,0o600)

    def test_nonfinite_config_and_spend_rejected(self):
        with self.assertRaises(WorkflowError):configure(self.w,{'authorization':{'max_usd_per_job':float('nan')}})
        with self.assertRaises(WorkflowError):reserve(self.job,'voice','minimax',{}, {'usd':float('inf')})

    def test_stale_prices_do_not_guess_cost(self):
        p=self.w.profile();p['rates']['verified_at']=(datetime.now(timezone.utc)-timedelta(days=40)).isoformat()
        with self.assertRaises(WorkflowError):quote(p,'minimax',100)

if __name__=='__main__':unittest.main()
