"""Exercise the newcomer command against isolated repository copies."""
import importlib.util
import contextlib
import io
from unittest.mock import patch
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
class NewApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('new_api',ROOT/'scripts/new_api.py')
        cls.n=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.n)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo';shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('.git','.venv','build','evidence','releases','__pycache__','.DS_Store'))
    def create(self,**kw):
        values=dict(name='customer-api',path='/crm/customer-api/v1',owner='customers@example.com',team='integrations',tier='internal',body_contains='customers')
        values.update(kw);return self.n.create_api(self.root,**values)
    def test_creates_nine_consistent_disabled_files(self):
        before={p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file()}
        created=self.create();self.assertEqual(len(created),9)
        after={p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(len(after-before),9)
        d=yaml.safe_load((self.root/'apis/crm/customer-api/kong.yaml').read_text())
        self.assertEqual(d['_info']['select_tags'],['owner-customer-api'])
        self.assertEqual(d['services'][0]['routes'][0]['paths'],['/crm/customer-api/v1'])
        self.assertEqual(d['services'][0]['name'],'customer-api-service')
        salts=[]
        for env in ('dev','uat','training','preprod','prod'):
            group='prod' if env in ('preprod','prod') else 'nonprod'
            v=yaml.safe_load((self.root/f'environments/{group}/{env}/apis/crm/customer-api.yaml').read_text())
            self.assertIs(v['enabled'],False);salts.append(v['variables']['DECK_CACHE_TOKENS_SALT'])
        self.assertEqual(len(set(salts)),5)
    def test_api_overlay_enables_api_while_disabled_target_blocks_deployment(self):
        from validate import settings
        self.create()
        overlay = self.root/'environments/nonprod/dev/apis/crm/customer-api.yaml'
        overlay.write_text(overlay.read_text().replace('enabled: false','enabled: true'))
        _, target, values = settings(self.root,'customer-api','dev')
        self.assertTrue(values['enabled'])
        self.assertFalse(target['enabled'])
        with self.assertRaisesRegex(ValueError,'deployment disabled'):
            settings(self.root,'customer-api','dev',strict=True)

    def test_same_api_name_in_another_domain_is_rejected(self):
        self.create()
        with self.assertRaisesRegex(ValueError,'already exists'):
            self.create(path='/billing/customer-api/v1')
        self.assertFalse((self.root/'apis/billing/customer-api').exists())

    def test_both_policy_profiles_use_one_target(self):
        from validate import settings
        self.create(name='partner-api',tier='external')
        internal = settings(self.root,'invoices','dev')[1]
        external = settings(self.root,'partner-api','dev')[1]
        self.assertEqual(internal,external)

    def test_duplicate_path_across_profiles_is_rejected(self):
        self.create()
        with self.assertRaisesRegex(ValueError,'path already used'):
            self.create(name='partner-api',tier='external')

    def test_existing_api_is_never_overwritten(self):
        self.create();p=self.root/'apis/crm/customer-api/kong.yaml';p.write_text('keep my changes')
        with self.assertRaisesRegex(ValueError,'exists'):self.create()
        self.assertEqual(p.read_text(),'keep my changes')
    def test_orphan_environment_file_blocks_all_creation(self):
        p=self.root/'environments/prod/prod/apis/crm/customer-api.yaml';p.parent.mkdir(parents=True);p.write_text('existing')
        with self.assertRaisesRegex(ValueError,'exists'):self.create()
        self.assertEqual(p.read_text(),'existing')
    def test_unsafe_name_rejected_without_files(self):
        with self.assertRaises(ValueError):self.create(name='../escape')
        self.assertFalse((self.root.parent/'escape').exists())
    def test_wrong_path_convention_rejected(self):
        with self.assertRaises(ValueError):self.create(path='/customers')
        self.assertFalse((self.root/'apis/crm/customer-api').exists())
    def test_parent_symlink_rejected(self):
        p=self.root/'environments/nonprod/dev/apis/crm';external=self.root.parent/'outside';external.mkdir();p.symlink_to(external,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'exists|symlink'):self.create()
        self.assertEqual(list(external.iterdir()),[])
    def test_target_enablement_not_changed(self):
        before=(self.root/'environments/nonprod/dev/target.yaml').read_bytes();self.create()
        self.assertEqual((self.root/'environments/nonprod/dev/target.yaml').read_bytes(),before)
    def test_external_spec_and_test_paths_agree(self):
        self.create(name='partner-api',tier='external')
        spec=yaml.safe_load((self.root/'apis/crm/partner-api/openapi.yaml').read_text())
        native=yaml.safe_load((self.root/'apis/crm/partner-api/kong.yaml').read_text())
        plugins=native['services'][0]['plugins'];oas=next(p for p in plugins if p['name']=='oas-validation')
        self.assertEqual(oas['config']['api_spec'],'${{ env "DECK_OPENAPI_SPEC" }}')
        self.assertIn('ip-restriction',[p['name'] for p in plugins])
    @unittest.skipUnless(shutil.which('deck'),'real decK not installed')
    def test_new_api_passes_real_native_rendering(self):
        self.create()
        r=subprocess.run(['bash','scripts/build.sh','customer-api','dev','build/customer-api/dev'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
    def test_cli_without_input_has_actionable_error(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/new_api.py')],input='',capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0);self.assertIn('--name',r.stderr)
    @unittest.skipUnless(shutil.which('deck'),'real decK not installed')
    def test_external_contract_has_one_editable_source(self):
        self.create(name='partner-api',tier='external')
        p=self.root/'apis/crm/partner-api/openapi.yaml';spec=yaml.safe_load(p.read_text())
        spec['info']['description']='Contract changed after onboarding'
        p.write_text(yaml.safe_dump(spec,sort_keys=False))
        r=subprocess.run(['bash','scripts/build.sh','partner-api','dev','build/partner-api/dev'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        state=yaml.safe_load((self.root/'build/partner-api/dev/state.yaml').read_text())
        oas=next(p for p in state['services'][0]['plugins'] if p['name']=='oas-validation')
        self.assertEqual(yaml.safe_load(oas['config']['api_spec']),spec)

    def test_guided_questions_create_actual_files(self):
        answers=['guided-api','/crm/guided/v1','team@example.com','','','customers']
        with patch.object(self.n,'ROOT',self.root), patch.object(sys,'argv',['new_api.py']), patch.object(sys.stdin,'isatty',return_value=True), patch('builtins.input',side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            self.n.main()
        self.assertTrue((self.root/'apis/crm/guided-api/kong.yaml').is_file())
        values=yaml.safe_load((self.root/'environments/nonprod/dev/apis/crm/guided-api.yaml').read_text())
        self.assertIs(values['enabled'],False)
