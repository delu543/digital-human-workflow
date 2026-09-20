import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from digital_human.storage import ROOT

class SkillUpgradeTests(unittest.TestCase):
    def test_owned_copy_updates_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            args=[sys.executable,str(ROOT/'scripts/install_skill.py'),'--destination',folder,'--copy']
            subprocess.run(args,check=True,capture_output=True)
            skill=Path(folder)/'digital-human-workflow'/'SKILL.md'
            skill.write_text('Local previous version to preserve.',encoding='utf-8')
            out=subprocess.run(args+['--update'],check=True,capture_output=True,text=True)
            result=json.loads(out.stdout)
            self.assertTrue(result['updated'])
            self.assertEqual((Path(result['backup'])/'SKILL.md').read_text(),'Local previous version to preserve.')
            self.assertEqual(skill.read_bytes(),(ROOT/'skills/digital-human-workflow/SKILL.md').read_bytes())

    def test_foreign_same_name_skill_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'digital-human-workflow';target.mkdir()
            (target/'SKILL.md').write_text('Foreign skill.',encoding='utf-8')
            out=subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),'--destination',folder,'--update'],capture_output=True)
            self.assertNotEqual(out.returncode,0)
            self.assertEqual((target/'SKILL.md').read_text(),'Foreign skill.')
