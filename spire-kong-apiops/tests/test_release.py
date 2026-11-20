"""Release integrity tests reject altered files and unsafe package metadata."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('release',ROOT/'scripts/release.py')
        cls.r=importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.r)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)
        (self.p/'dev').mkdir(); (self.p/'dev/state.yaml').write_text('state')
        (self.p/'tests.json').write_text('[]')
        self.manifest={'schema':1,'api':'orders-api','tier':'internal','tag':'kong-v1.0.0','tag_object':'c'*40,'commit':'a'*40,'deck':'1.70.0','files':{'dev/state.yaml':hashlib.sha256(b'state').hexdigest(),'tests.json':hashlib.sha256(b'[]').hexdigest()},'environments':{'dev':{'enabled':True,'control_plane':'dev-internal','konnect_addr':'https://us.api.konghq.com','gateway_url':'https://dev.example.com','state':'dev/state.yaml'}}}
        self.save()
    def save(self): (self.p/'manifest.json').write_text(json.dumps(self.manifest))
    def verify(self): return self.r.verify_package(self.p,'orders-api','dev','dev-internal','https://us.api.konghq.com')
    def test_valid_package(self): self.assertEqual(self.verify()['commit'],'a'*40)
    def test_tampered_state_rejected(self):
        (self.p/'dev/state.yaml').write_text('altered')
        with self.assertRaisesRegex(ValueError,'checksum'):self.verify()
    def test_wrong_target_rejected(self):
        with self.assertRaisesRegex(ValueError,'target'):self.r.verify_package(self.p,'orders-api','dev','prod-internal','https://us.api.konghq.com')
    def test_disabled_target_rejected(self):
        self.manifest['environments']['dev']['enabled']=False;self.save()
        with self.assertRaisesRegex(ValueError,'disabled'):self.verify()
    def test_traversal_rejected(self):
        self.manifest['files']['../escape']='0'*64;self.save()
        with self.assertRaises(ValueError):self.verify()
    def test_symlink_rejected(self):
        (self.p/'dev/state.yaml').unlink();(self.p/'dev/state.yaml').symlink_to(self.p/'tests.json')
        with self.assertRaisesRegex(ValueError,'symlink'):self.verify()
    def test_unlisted_file_rejected(self):
        (self.p/'extra').write_text('unreviewed')
        with self.assertRaisesRegex(ValueError,'unexpected'):self.verify()
    def test_missing_manifest_entry_rejected(self):
        del self.manifest['files']['dev/state.yaml'];self.save()
        with self.assertRaises(ValueError):self.verify()
    def test_diff_deletion_gate(self):
        with self.assertRaisesRegex(ValueError,'deletion'):
            self.r.check_diff({'summary':{'creating':0,'updating':0,'deleting':1,'total':1},'changes':{'creating':[],'updating':[],'deleting':[{'kind':'service'}]},'errors':[],'warnings':[]},False)
    def test_missing_diff_summary_fails_closed(self):
        with self.assertRaises(ValueError):self.r.check_diff({},True)
    def test_changed_plan_rejected(self):
        with self.assertRaisesRegex(ValueError,'changed'):
            self.r.compare_plans({'summary':{'creating':1}},{'summary':{'creating':2}})
    def test_plan_key_order_does_not_change_meaning(self):
        self.r.compare_plans({'a':1,'b':2},{'b':2,'a':1})
if __name__=='__main__':unittest.main()
