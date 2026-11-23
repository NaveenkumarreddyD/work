"""Delivery gates operate on retained state and receipts, not mutable branch names."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from test_deploy import DeployTests
from test_release import ReleaseTests

ROOT=Path(__file__).resolve().parents[1]
class ReceiptTests(ReleaseTests):
    def receipt(self,env='dev'):
        return {'schema':1,'status':'success','api':'orders-api','environment':env,'commit':'a'*40,
                'tag':'kong-v1.0.0','manifest_sha256':self.r.sha(self.p/'manifest.json'),
                'control_plane':'dev-internal','konnect_addr':'https://us.api.konghq.com',
                'build_url':'https://jenkins.example.invalid/job/Deploy-dev/1/'}
    def test_same_commit_predecessor_accepted(self):
        self.r.check_receipt(self.manifest,'uat',self.receipt(),'DEPLOY',self.p)
    def test_wrong_commit_cannot_promote(self):
        r=self.receipt();r['commit']='b'*40
        with self.assertRaisesRegex(ValueError,'commit'):self.r.check_receipt(self.manifest,'uat',r,'DEPLOY',self.p)
    def test_cannot_skip_uat_before_preprod(self):
        with self.assertRaisesRegex(ValueError,'predecessor'):self.r.check_receipt(self.manifest,'preprod',self.receipt(),'DEPLOY',self.p)
    def test_failed_predecessor_rejected(self):
        r=self.receipt();r['status']='failed'
        with self.assertRaises(ValueError):self.r.check_receipt(self.manifest,'uat',r,'DEPLOY',self.p)
    def test_rollback_requires_known_good_destination_package(self):
        r=self.receipt();self.r.check_receipt(self.manifest,'dev',r,'ROLLBACK',self.p)
        r['manifest_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'package'):self.r.check_receipt(self.manifest,'dev',r,'ROLLBACK',self.p)
    def test_release_identity_checks_tag_and_object(self):
        self.manifest['tag_object']='c'*40;self.save()
        self.r.check_identity(self.p,'kong-v1.0.0','a'*40,'c'*40)
        with self.assertRaisesRegex(ValueError,'identity'):self.r.check_identity(self.p,'kong-v1.0.0','a'*40,'d'*40)
    def test_dev_package_cannot_deploy_to_higher_environment(self):
        self.manifest['tag']='dev-'+'a'*40;self.save()
        with self.assertRaisesRegex(ValueError,'DEV'):self.r.check_receipt(self.manifest,'uat',self.receipt(),'DEPLOY',self.p)

class AutomaticDevTests(DeployTests):
    def test_automatic_dev_applies_without_human_approval(self):
        self.plan();r=self.run_phase('auto-dev',TRUSTED_AUTO_DEV='true')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('gateway sync',self.calls.read_text())
    def test_auto_dev_requires_trusted_job_gate(self):
        self.plan();r=self.run_phase('auto-dev')
        self.assertNotEqual(r.returncode,0);self.assertNotIn('gateway sync',self.calls.read_text())
    def test_auto_dev_cannot_delete(self):
        self.plan(DELETIONS='1');r=self.run_phase('auto-dev',TRUSTED_AUTO_DEV='true',DELETIONS='1',ALLOW_DELETIONS='true')
        self.assertNotEqual(r.returncode,0);self.assertNotIn('gateway sync',self.calls.read_text())

class EnabledValidationTests(unittest.TestCase):
    def test_enabled_placeholder_cannot_pass_draft_build(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'repo';shutil.copytree(ROOT,p,ignore=shutil.ignore_patterns('.venv','build','evidence','__pycache__'))
            for f in ['konnect/nonprod/dev/internal.yaml','konnect/nonprod/dev/apis/billing/invoices.yaml']:
                q=p/f;q.write_text(q.read_text().replace('enabled: false','enabled: true'))
            import subprocess
            r=subprocess.run(['bash','scripts/build.sh','invoices','dev','build/state'],cwd=p,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('placeholder',r.stderr.lower())

# Inherited fixture methods already run in their own modules; collect only these new regressions.
def load_tests(loader, tests, pattern):
    suite=unittest.TestSuite()
    for cls in (ReceiptTests,AutomaticDevTests,EnabledValidationTests):
        for name in cls.__dict__:
            if name.startswith('test_'):suite.addTest(cls(name))
    return suite
