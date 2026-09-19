from pathlib import Path
import tempfile
import unittest
from digital_human.alignment import captions_from_tokens, whisper_tokens
from digital_human.composition import scene_times
from digital_human.storage import WorkflowError, within

class AlignmentTests(unittest.TestCase):
    def test_true_anchors_survive_caption_grouping(self):
        cues=captions_from_tokens('你好。欢迎。','你好欢迎',[.2,.6,1.2,1.7],2)
        self.assertEqual(cues,[{'text':'你好','start':.1,'end':1.1},{'text':'欢迎','start':1.1,'end':2}])

    def test_missing_dtw_is_not_accepted(self):
        raw={'transcription':[{'tokens':[{'text':'你好','t_dtw':-1}]}]}
        with self.assertRaises(WorkflowError):whisper_tokens(raw)

    def test_mismatched_script_stops_instead_of_fabricating_time(self):
        with self.assertRaises(WorkflowError):captions_from_tokens('停顿自然','评论自然',[0,.3,.6,.9],1.2)

    def test_truncated_or_backward_tail_stops(self):
        for anchors in [[0,.2,2,2],[0,.4,.3,.6]]:
            with self.assertRaises(WorkflowError):captions_from_tokens('你好欢迎','你好欢迎',anchors,1)

    def test_scenes_use_actual_cue_times(self):
        cues=[{'start':.2},{'start':1.8},{'start':3.1}]
        result=scene_times({'scenes':[{'start_caption':0},{'start_caption':2}]},cues,4)
        self.assertEqual([(x['start'],x['end']) for x in result],[(0,3.1),(3.1,4)])

    def test_scene_order_is_checked(self):
        with self.assertRaises(WorkflowError):scene_times({'scenes':[{'start_caption':1},{'start_caption':0}]},[{'start':0},{'start':2}],4)

    def test_asset_path_escape_and_symlink_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'job';root.mkdir()
            with self.assertRaises(WorkflowError):within(root,'../secret')
            with self.assertRaises(WorkflowError):within(root,'/etc/passwd')
            try:(root/'escape').symlink_to(Path(temp),target_is_directory=True)
            except OSError:return
            with self.assertRaises(WorkflowError):within(root,'escape/data')

if __name__=='__main__':unittest.main()
