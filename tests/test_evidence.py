import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class EvidenceTests(unittest.TestCase):
    def test_live_secrets_are_removed_from_review_report(self):
        spec=importlib.util.spec_from_file_location('evidence',ROOT/'scripts/evidence.py')
        e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
        value={'summary':{'creating':1},'changes':{'old':{'redis':{'password':'must-not-escape'},'client_secret':['also-secret']},'new':{'host':'backend.example.com'}}}
        safe=e.redact(value)
        self.assertNotIn('must-not-escape',str(safe));self.assertNotIn('also-secret',str(safe))
        self.assertEqual(safe['summary'],value['summary'])
        self.assertEqual(safe['changes']['new']['host'],'backend.example.com')
