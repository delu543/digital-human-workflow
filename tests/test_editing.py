from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from digital_human import editing
from digital_human.edit_timeline import compile_plan, SCHEMA
from digital_human.storage import Workspace, WorkflowError, file_hash, write

FMT={'width':1080,'height':1920,'fps':25}
CUES=[{'start':.2,'end':1.8,'text':'第一句。'},{'start':2.2,'end':3.8,'text':'第二句。'}]

def assets():
    base={'path':'assets/test.mp4','kind':'video','duration':4,'width':1080,'height':1920,
          'has_audio':False,'sha256':'fixture','source':'synthetic test','rights':'original fixture'}
    return {'avatar':deepcopy(base),'narration':{**base,'path':'assets/test.wav','kind':'audio','has_audio':True},
            'broll':deepcopy(base),'music':{**base,'kind':'audio','has_audio':True}}

class TimelineTests(unittest.TestCase):
    def compile(self, **kwargs):return compile_plan({'schema':SCHEMA,**kwargs},4,CUES,FMT,assets())

    def test_reorder_and_speed_keep_voice_picture_caption_mapping(self):
        t=self.compile(ranges=[{'start':2,'end':4,'speed':2},{'start':0,'end':2}])
        self.assertEqual(t['duration_us'],3_000_000)
        self.assertEqual([c['text'] for c in t['captions']],['第二句。','第一句。'])
        self.assertEqual(t['captions'][0]['start'],.1)
        self.assertEqual(t['captions'][1]['start'],1.2)
        v=[c for c in t['clips'] if c['role']=='avatar'];a=[c for c in t['clips'] if c['role']=='narration']
        for x,y in zip(v,a):
            self.assertEqual([x[k] for k in ['start_us','duration_us','speed','source_start']],
                             [y[k] for k in ['start_us','duration_us','speed','source_start']])

    def test_cut_inside_speech_is_rejected(self):
        with self.assertRaises(WorkflowError):self.compile(ranges=[{'start':1,'end':4}])

    def test_out_of_bounds_broll_is_rejected(self):
        with self.assertRaises(WorkflowError):self.compile(overlays=[{'kind':'video','asset':'broll','start':1,'duration':3,'source_start':2}])

    def test_avatar_source_duration_cannot_be_inferred_from_captions(self):
        shorter=assets();shorter['avatar']['duration']=3.9
        with self.assertRaises(WorkflowError):compile_plan({'schema':SCHEMA},4,CUES,FMT,shorter)

    def test_overlays_preserve_continuous_voice_and_own_text(self):
        t=self.compile(overlays=[{'id':'insert','kind':'video','asset':'broll','start':1,'duration':2},
                                {'id':'title','kind':'text','text':'独立标题','start':0,'duration':1}])
        self.assertEqual(len([c for c in t['clips'] if c['role']=='narration']),1)
        self.assertEqual(next(c for c in t['clips'] if c['id']=='insert')['volume'],0)

    def test_unknown_effect_is_not_silently_dropped(self):
        with self.assertRaises(WorkflowError):self.compile(presenter={'unimplemented_effect':'magic'})

    def test_overlapping_track_rejected(self):
        with self.assertRaises(WorkflowError):self.compile(overlays=[
            {'kind':'video','asset':'broll','start':0,'duration':3,'track':1},
            {'kind':'video','asset':'broll','start':1,'duration':3,'track':1}])

    def test_invalid_keyframe_or_nonfinite_value_rejected(self):
        for style in [{'scale':float('nan')},{'keyframes':{'scale':[{'time':1,'value':1},{'time':2,'value':2}]}}]:
            with self.assertRaises(WorkflowError):self.compile(presenter=style)

class RevisionTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        w=Workspace(Path(t.name)/'data');w.initialize();self.job=w.prepare('纯测试文案。')
        for name,suffix in [('avatar','.mp4'),('narration','.wav')]:
            p=self.job.path/'assets'/(name+suffix);p.write_bytes(name.encode());self.job.record(name,str(p.relative_to(self.job.path)))
        write(self.job.path/'captions.json',{'duration':4,'captions':CUES,'source':'synthetic unit fixture'})
        self.job.record('captions','captions.json')
        def describe(path,kind):return {**assets()['avatar'],'kind':kind,'sha256':file_hash(path),'has_audio':kind=='audio'}
        patcher=patch('digital_human.editing.describe',side_effect=describe);patcher.start();self.addCleanup(patcher.stop)

    def build(self,name='v1',plan=None):
        return editing.build(self.job,plan or {'schema':SCHEMA},name)

    def test_revision_is_immutable_and_parent_cloud_state_unchanged(self):
        before=(self.job.path/'job.json').read_bytes();self.build()
        self.assertEqual(before,(self.job.path/'job.json').read_bytes())
        with self.assertRaises(WorkflowError):self.build()
        self.assertEqual(editing.revision(self.job,'v1').load()['operations'],{})

    def test_bad_plan_leaves_no_revision(self):
        with self.assertRaises(WorkflowError):self.build(plan={'schema':SCHEMA,'ranges':[{'start':1,'end':4}]})
        self.assertFalse((self.job.path/'edits/v1').exists())

    def test_asset_and_timeline_tampering_rejected(self):
        self.build();child=editing.revision(self.job,'v1')
        child.artifact('avatar').write_bytes(b'changed')
        with self.assertRaises(WorkflowError):editing.revision(self.job,'v1')

    def test_hyperframes_keeps_video_muted_and_captions_outside_source(self):
        self.build();child=editing.revision(self.job,'v1')
        # Composition serialization is independent of npm in unit CI; real GSAP is tested by smoke_edit.
        root=self.job.path/'test-runtime'
        for name in ['templates/assets/NotoSansCJKsc-Regular.otf','templates/assets/OFL.txt','node_modules/gsap/dist/gsap.min.js']:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic unit dependency; not executed')
        with patch('digital_human.edit_hyperframes.ROOT',root):editing.compose(child)
        text=child.artifact('composition').read_text(encoding='utf-8')
        self.assertIn('muted playsinline',text);self.assertIn('data-media-start=',text)
        self.assertIn('第一句。',text);self.assertEqual(child.artifact('avatar').read_bytes(),b'avatar')

if __name__=='__main__':unittest.main()
