"""Regressions from independent review: process tree, publication race, recovery."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from digital_human import export_worker as ew
from digital_human.storage import WorkflowError, Workspace, file_hash, write
from digital_human.processes import check_report


class ExportRecoveryTests(unittest.TestCase):
    def test_timeout_stops_grandchild(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);marker=p/'late'
            payload=f'import time;from pathlib import Path;time.sleep(.8);Path({str(marker)!r}).write_text("late")'
            parent=f'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",{payload!r}],start_new_session=True);time.sleep(10)'
            with self.assertRaises(WorkflowError):
                ew.command([sys.executable,'-c',parent],p/'run.log',.2,dict(os.environ))
            time.sleep(1)
            self.assertFalse(marker.exists())

    def test_target_created_during_check_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);project=p/'project';project.mkdir();(project/'index.html').write_text('fixture')
            with patch('digital_human.export_worker.shutil.which',return_value=sys.executable):
                spec=ew.make_spec(project,p/'out.mp4',p/'state',25,1,1,30)
            def fake(args,log,timeout,env):
                if 'check' in args:
                    write(log,{'ok':True});(p/'out.mp4').write_bytes(b'other owner')
                elif 'render' in args:
                    Path(args[-1]).write_bytes(b'new render')
            with patch.object(ew,'command',side_effect=fake), patch.object(ew,'probe',return_value={}), patch.object(ew,'binary',return_value='ffmpeg'):
                with self.assertRaises(WorkflowError):ew.execute(spec)
            self.assertEqual((p/'out.mp4').read_bytes(),b'other owner')
            self.assertTrue((p/'.out.mp4.pending.mp4').exists())

    def test_different_state_cannot_claim_same_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);project=p/'project';project.mkdir();(project/'index.html').write_text('fixture')
            with patch('digital_human.export_worker.shutil.which',return_value=sys.executable):
                spec=ew.make_spec(project,p/'out.mp4',p/'state1',25,1,1,30)
            with patch.object(ew,'command',side_effect=WorkflowError('first interrupted')):
                with self.assertRaises(WorkflowError):ew.execute(spec)
            with patch.object(ew,'command') as command:
                with self.assertRaises(WorkflowError):ew.execute({**spec,'state':str(p/'state2')})
                command.assert_not_called()

    def test_register_repairs_evidence_before_render_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workspace(Path(d)/'workspace');w.initialize();job=w.prepare('匿名登记测试')
            p=job.path;project=p/'project';(project/'index.html').write_text('fixture')
            video=p/'exports/out.mp4';video.write_bytes(b'fixture')
            state=p/'state';state.mkdir();sha=ew.fingerprint(project)
            write(state/'spec.json',{'project':str(project),'project_sha256':sha})
            write(state/'status.json',{'stage':'encoded'});write(state/'check.log',{'ok':True})
            write(state/'result.json',{'video':str(video),'project_sha256':sha,'video_sha256':file_hash(video),'full_decode':'passed'})
            # Simulate a legacy interrupted registration with render pointer but no provenance.
            job.record('render','exports/out.mp4')
            data=job.load();data['stage']='delivered';job.save(data)
            self.assertFalse((p/'render-provenance.json').exists())
            self.assertTrue(ew.register(job,state)['registered'])
            self.assertEqual(json.loads((p/'render-provenance.json').read_text())['video_sha256'],file_hash(video))
            self.assertEqual(job.load()['stage'],'delivered')

    def test_diagnostics_do_not_replace_check_result(self):
        with tempfile.TemporaryDirectory() as d:
            log=Path(d)/'check.log'
            log.write_text('[Browser] diagnostic {not JSON}\n'+json.dumps({'ok':False,'lint':{'ok':False}}),encoding='utf-8')
            self.assertFalse(check_report(log)['ok'])
            log.write_text('[Browser] no result',encoding='utf-8')
            with self.assertRaises(WorkflowError):check_report(log)
            log.write_text('{"ok":true}\ntruncated subsequent result',encoding='utf-8')
            with self.assertRaises(WorkflowError):check_report(log)

    def test_unsupported_filesystem_fails_before_render(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);project=p/'project';project.mkdir();(project/'index.html').write_text('fixture')
            with patch('digital_human.export_worker.shutil.which',return_value=sys.executable):
                spec=ew.make_spec(project,p/'out.mp4',p/'state',25,1,1,30)
            with patch.object(ew.os,'link',side_effect=OSError('no hardlinks')),patch.object(ew,'command') as command:
                with self.assertRaises(WorkflowError):ew.execute(spec)
                command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
