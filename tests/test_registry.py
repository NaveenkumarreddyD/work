import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class RegistryTests(unittest.TestCase):
    def test_ref_binding_is_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);pkg=p/'pkg';pkg.mkdir();reg=p/'registry';reg.mkdir()
            m={'api':'orders-api','tag':'kong-v1.0.0','commit':'a'*40,'tag_object':'b'*40}
            (pkg/'manifest.json').write_text(json.dumps(m))
            run=lambda:subprocess.run([sys.executable,str(ROOT/'scripts/registry.py'),str(reg),str(pkg)],capture_output=True,text=True)
            self.assertEqual(run().returncode,0)
            self.assertEqual(run().returncode,0)
            m['tag_object']='c'*40;(pkg/'manifest.json').write_text(json.dumps(m))
            self.assertNotEqual(run().returncode,0)
    def test_registry_directory_must_be_provisioned(self):
        with tempfile.TemporaryDirectory() as d:
            r=subprocess.run([sys.executable,str(ROOT/'scripts/registry.py'),d+'/missing',d],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
