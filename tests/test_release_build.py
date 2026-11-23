"""Real Git and pinned decK integration in a disposable repository, with no network."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('deck'),'pinned decK required for real package integration')
class PackageBuildTests(unittest.TestCase):
    def test_tag_and_dev_packages_freeze_identical_environment_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'repo';shutil.copytree(ROOT,p,ignore=shutil.ignore_patterns('.git','.venv','build','evidence','releases','__pycache__'))
            def run(*args):
                r=subprocess.run(args,cwd=p,capture_output=True,text=True,env={**os.environ,'PYTHON':sys.executable,'REQUIRE_SIGNED_TAG':'false'})
                self.assertEqual(r.returncode,0,r.stderr);return r.stdout.strip()
            run('git','init','-b','main');run('git','config','user.name','Offline Test');run('git','config','user.email','test@example.invalid')
            run('git','add','.');run('git','commit','-m','Offline fixture')
            commit=run('git','rev-parse','HEAD');run('git','update-ref','refs/remotes/origin/main',commit)
            run('git','tag','-a','kong-v1.0.0','-m','Offline tag fixture')
            run('bash','scripts/release.sh','kong-v1.0.0','invoices','releases/tag/invoices')
            run('bash','scripts/release.sh','dev-'+commit,'invoices','releases/dev/invoices')
            tagged=json.loads((p/'releases/tag/invoices/manifest.json').read_text())
            dev=json.loads((p/'releases/dev/invoices/manifest.json').read_text())
            self.assertEqual(tagged['commit'],commit);self.assertEqual(dev['commit'],commit)
            self.assertEqual(tagged['files'],dev['files']);self.assertEqual(len(tagged['environments']),5)
            for relative,digest in tagged['files'].items():
                self.assertEqual(hashlib.sha256((p/'releases/tag/invoices'/relative).read_bytes()).hexdigest(),digest)
            self.assertTrue(all(not x['enabled'] for x in tagged['environments'].values()))
            self.assertEqual(tagged['tag_object'],run('git','rev-parse','refs/tags/kong-v1.0.0'))
