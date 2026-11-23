"""Reject tags outside trusted main before any release-owned code executes."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.git('init','-b','main');self.git('config','user.email','test@example.com');self.git('config','user.name','Test')
        (self.root/'file').write_text('reviewed');self.git('add','.');self.git('commit','-m','Reviewed')
        self.git('update-ref','refs/remotes/origin/main','HEAD')
    def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.root,text=True,stderr=subprocess.DEVNULL).strip()
    def verify(self):return subprocess.run(['bash',str(ROOT/'scripts/verify-source.sh'),'kong-v1.0.0'],cwd=self.root,capture_output=True,text=True)
    def test_annotated_main_tag_accepted(self):
        self.git('tag','-a','kong-v1.0.0','-m','release');r=self.verify()
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),self.git('rev-parse','HEAD'))
    def test_lightweight_tag_rejected(self):
        self.git('tag','kong-v1.0.0');self.assertNotEqual(self.verify().returncode,0)
    def test_unreviewed_tag_rejected(self):
        self.git('checkout','-b','unreviewed');(self.root/'file').write_text('unreviewed');self.git('commit','-am','Unreviewed')
        self.git('tag','-a','kong-v1.0.0','-m','unsafe');self.assertNotEqual(self.verify().returncode,0)
