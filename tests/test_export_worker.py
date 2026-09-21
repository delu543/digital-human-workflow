import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from digital_human.export_worker import claim, launch_plist, make_spec, execute
from digital_human.storage import WorkflowError


class ExportWorkerTests(unittest.TestCase):
    def test_once_marker_blocks_relaunch_even_after_failure(self):
        with tempfile.TemporaryDirectory() as d:
            claim(d, 1, 1)
            with self.assertRaises(WorkflowError):
                claim(d, 1, 1)
            with self.assertRaises(WorkflowError):
                claim(Path(d)/'invalid', 2, 1)

    def test_launchd_does_not_restart_and_keeps_paths_as_arguments(self):
        with tempfile.TemporaryDirectory(prefix='export space ') as d:
            p = launch_plist(Path(d)/'spec.json', 'test.label', '/python path', '/script path')
            self.assertFalse(p['KeepAlive'])
            self.assertTrue(p['RunAtLoad'])
            self.assertEqual(p['ProgramArguments'][0], '/python path')
            self.assertNotIn('MINIMAX_API_KEY',p['EnvironmentVariables'])

    @patch('digital_human.export_worker.shutil.which', return_value='/node')
    def test_changed_project_fails_before_any_command(self, _):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'project';project.mkdir()
            (project/'index.html').write_text('original',encoding='utf-8')
            spec=make_spec(project,root/'out.mp4',root/'state',25,1,1,30)
            (project/'index.html').write_text('changed',encoding='utf-8')
            with patch('digital_human.export_worker.command') as command:
                with self.assertRaises(WorkflowError):execute(spec)
                command.assert_not_called()
            self.assertEqual(json.loads((root/'state/status.json').read_text())['stage'],'failed')

    @patch('digital_human.export_worker.shutil.which', return_value='/node')
    def test_outputs_cannot_contaminate_project_or_overwrite(self, _):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'index.html').write_text('fixture',encoding='utf-8')
            with self.assertRaises(WorkflowError):make_spec(p,p/'out.mp4',p.parent/'s',25,1,1,30)
            with self.assertRaises(WorkflowError):make_spec(p,p.parent/'out.mp4',p/'state',25,1,1,30)


if __name__ == '__main__':
    unittest.main()
