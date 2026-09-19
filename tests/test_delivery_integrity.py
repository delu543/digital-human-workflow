from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from digital_human import delivery,media
from digital_human.storage import Workspace,WorkflowError,write,read,file_hash

class DeliveryIntegrity(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        w=Workspace(Path(t.name)/'data');w.initialize();self.job=w.prepare('虚构的交付测试。')
        j=self.job
        (j.path/'project/index.html').write_text('<html>fixture</html>')
        (j.path/'exports/final.mp4').write_bytes(b'fixture-video')
        j.record('composition','project/index.html');j.record('render','exports/final.mp4')
        write(j.path/'checks.json',{'ok':True,'project_sha256':media.project_hash(j)})
        write(j.path/'render-provenance.json',{'project_sha256':media.project_hash(j),'video_sha256':file_hash(j.artifact('render'))})
        write(j.path/'technical-checks.json',{'ok':True,'video_sha256':file_hash(j.artifact('render'))})
        (j.path/'evidence/frame.png').write_bytes(b'fixture-png')

    def test_changed_secondary_asset_invalidates_render(self):
        (self.job.path/'project/assets.css').write_text('changed')
        with self.assertRaises(WorkflowError):delivery.verify(self.job)

    def test_review_requires_real_evidence_fields(self):
        p=self.job.path/'review-input.json';write(p,{'identity':{'status':'passed','evidence':''}})
        with self.assertRaises(WorkflowError):delivery.accept_review(self.job,p)

    def test_review_is_bound_to_video(self):
        value={k:{'status':'passed','evidence':'Explicit synthetic unit fixture, not a real perceptual review.'} for k in ['identity','voice','captions','visuals','sync']}
        value['inspected_frames']=['evidence/frame.png']
        p=self.job.path/'review-input.json';write(p,value)
        delivery.accept_review(self.job,p)
        self.assertEqual(read(self.job.path/'review.json')['video_sha256'],file_hash(self.job.artifact('render')))
        (self.job.path/'exports/final.mp4').write_bytes(b'changed')
        with self.assertRaises(WorkflowError):delivery.bundle(self.job)

    def test_sensitive_content_is_not_packed(self):
        p=self.job.path/'project/config.json';p.write_text('token='+('sk-'+'api-')+'x'*40)
        with self.assertRaises(WorkflowError):delivery.safe_text(p)

    def test_symlink_asset_rejected_in_project_hash(self):
        path=self.job.path/'project/ref'
        try:path.symlink_to(self.job.path/'script.txt')
        except OSError:self.skipTest('symlinks unavailable')
        with self.assertRaises(WorkflowError):media.project_hash(self.job)

if __name__=='__main__':unittest.main()
