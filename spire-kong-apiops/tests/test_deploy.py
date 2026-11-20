"""Run real orchestration against an external decK test double; never contact Konnect."""
import hashlib
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_validation as fixtures

ROOT=Path(__file__).resolve().parents[1]
class DeployTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.package=self.base/'package';self.package.mkdir();(self.package/'dev').mkdir()
        fixtures.PolicyTests.setUpClass();fixture=fixtures.PolicyTests();fixture.setUp()
        import yaml
        state=yaml.safe_dump(fixture.state)
        (self.package/'dev/state.yaml').write_text(state)
        tests=[{'name':a,'method':'GET','path':'/sales/orders/v1','auth':a,'expected_status':200 if a=='valid' else 401,'body_contains':'orders' if a=='valid' else ''} for a in ('valid','none','invalid')]
        test_text=json.dumps(tests)
        (self.package/'tests.json').write_text(test_text)
        m={'schema':1,'api':'orders-api','tier':'internal','tag':'kong-v1.0.0','tag_object':'c'*40,'commit':'a'*40,'deck':'1.70.0','files':{'dev/state.yaml':hashlib.sha256(state.encode()).hexdigest(),'tests.json':hashlib.sha256(test_text.encode()).hexdigest()},'environments':{'dev':{'enabled':True,'control_plane':'dev-internal','konnect_addr':'https://us.api.konghq.com','gateway_url':'https://dev.example.com','state':'dev/state.yaml'}}}
        (self.package/'manifest.json').write_text(json.dumps(m))
        self.bin=self.base/'bin';self.bin.mkdir();self.calls=self.base/'calls'
        (self.bin/'deck').write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
a=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f:f.write(' '.join(a)+'\\n')
if a==['version']:print('decK v1.70.0');sys.exit()
if a[:2]==['gateway','diff']:
 n=int(os.environ.get('DELETIONS','0'));u=int(os.environ.get('UPDATES','1'))
 if 'gateway sync' in Path(os.environ['CALLS']).read_text():n=0;u=0
 if Path(os.environ['CALLS']).read_text().count('gateway diff')>1:u+=int(os.environ.get('CHANGED','0'))
 print(json.dumps({'summary':{'creating':0,'updating':u,'deleting':n,'total':u+n},'changes':{'creating':[],'updating':[{'kind':'service','name':'orders-api'}]*u,'deleting':[{'kind':'route'}]*n},'warnings':[],'errors':[]}))
 sys.exit(2 if '--non-zero-exit-code' in a and u+n else 0)
if a[:2]==['gateway','sync']:
 if '--yes' not in a:sys.exit(99)
 sys.exit(int(os.environ.get('SYNC_FAIL','0')))
if a[:2]==['gateway','dump']:
 Path(a[a.index('-o')+1]).write_text('snapshot')
''');(self.bin/'deck').chmod(0o755)
        self.env={**os.environ,'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],'PYTHON':sys.executable,'CALLS':str(self.calls),'DECK_KONNECT_TOKEN':'test-only','SMOKE_BEARER_TOKEN':'test-only','EXPECTED_CP':'dev-internal','EXPECTED_ADDR':'https://us.api.konghq.com'}
        self.evidence=self.base/'evidence'
        (self.bin/'curl').write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
a=sys.argv[1:]; header=Path(a[a.index('--header')+1][1:]).read_text()
Path(a[a.index('--output')+1]).write_text('{"orders":[]}')
print(os.environ.get('HTTP_FAILURE') or ('200' if 'test-only' in header else '401'),end='')
''');(self.bin/'curl').chmod(0o755)
    def run_phase(self,phase,**env):
        return subprocess.run(['bash',str(ROOT/'scripts/deploy.sh'),phase,str(self.package),'orders-api','dev',str(self.evidence)],env={**self.env,**env},capture_output=True,text=True)
    def plan(self,**env):
        r=self.run_phase('plan',**env);self.assertEqual(r.returncode,0,r.stderr)
    def approve(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/release.py'),'approve',str(self.package),str(self.evidence),'orders-api','dev','dev-internal','https://us.api.konghq.com','reviewer','CHG-123'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
    def test_successful_deploy_runs_http_checks(self):
        self.plan();self.approve();r=self.run_phase('apply')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('Passed 3 HTTP tests',(self.evidence/'http-tests.txt').read_text())
    def test_failed_http_check_preserves_failure(self):
        self.plan();self.approve();r=self.run_phase('apply',HTTP_FAILURE='503')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('actual=503',(self.evidence/'http-tests.txt').read_text())
        self.assertNotIn('exit_code=0',(self.evidence/'apply-status.txt').read_text())
    def test_missing_approval_never_syncs(self):
        self.plan();r=self.run_phase('apply');self.assertNotEqual(r.returncode,0)
        self.assertNotIn('gateway sync',self.calls.read_text())
    def test_changed_plan_never_syncs(self):
        self.plan();self.approve();r=self.run_phase('apply',CHANGED='1')
        self.assertNotEqual(r.returncode,0);self.assertNotIn('gateway sync',self.calls.read_text())
    def test_deletions_require_snapshot_before_sync(self):
        self.plan(DELETIONS='1');self.approve();r=self.run_phase('apply',DELETIONS='1',ALLOW_DELETIONS='true')
        self.assertNotEqual(r.returncode,0);self.assertNotIn('gateway sync',self.calls.read_text())
    def test_reviewed_deletions_without_authorization_never_sync(self):
        self.plan(DELETIONS='1');self.approve();r=self.run_phase('apply',DELETIONS='1')
        self.assertNotEqual(r.returncode,0);self.assertNotIn('gateway sync',self.calls.read_text())
    def test_authorized_deletion_snapshots_before_sync(self):
        backup=self.base/'backups';backup.mkdir()
        self.plan(DELETIONS='1');self.approve()
        r=self.run_phase('apply',DELETIONS='1',ALLOW_DELETIONS='true',BACKUP_DIR=str(backup),BACKUP_STORAGE_APPROVED='true')
        self.assertEqual(r.returncode,0,r.stderr)
        calls=self.calls.read_text()
        self.assertLess(calls.index('gateway dump'),calls.index('gateway sync'))
        self.assertEqual(len(list(backup.glob('*.yaml'))),1)
    def test_sync_failure_is_retained(self):
        self.plan();self.approve();r=self.run_phase('apply',SYNC_FAIL='7')
        self.assertNotEqual(r.returncode,0);self.assertIn('gateway sync',self.calls.read_text())
        self.assertTrue((self.evidence/'apply-status.txt').exists())
    def test_tampered_approved_state_never_syncs(self):
        self.plan();self.approve();(self.evidence/'state.yaml').write_text('altered')
        r=self.run_phase('apply');self.assertNotEqual(r.returncode,0);self.assertNotIn('gateway sync',self.calls.read_text())
    def test_drift_is_read_only_and_reports_difference(self):
        r=self.run_phase('drift');self.assertNotEqual(r.returncode,0);self.assertNotIn('gateway sync',self.calls.read_text())
if __name__=='__main__':unittest.main()
