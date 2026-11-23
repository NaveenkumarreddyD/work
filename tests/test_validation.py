"""Company-policy regressions: every case changes real configuration input."""
import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('validator', ROOT/'scripts/validate.py')
        cls.v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.v)

    def setUp(self):
        self.state = {'_format_version':'3.0', '_info':{'select_tags':['owner-orders-api']}, 'services':[{
            'name':'orders-api', 'tags':['owner-orders-api'], 'host':'backend.example.com','protocol':'https','port':443,'tls_verify':True,
            'connect_timeout':5000,'read_timeout':30000,'write_timeout':30000,'retries':0,
            'routes':[{'name':'orders-api-v1','paths':['/sales/orders/v1'],'methods':['GET'],'protocols':['https'],'strip_path':False,'preserve_host':False,'tags':['owner-orders-api']}],
            'plugins':[
                {'name':'openid-connect','tags':['owner-orders-api'],'config':{'issuer':'https://login.microsoftonline.com/tenant/v2.0','auth_methods':['bearer'],'audience_required':['api://orders'],'roles_required':['Orders.Read']}},
                {'name':'rate-limiting','tags':['owner-orders-api'],'config':{'minute':60,'policy':'local','limit_by':'service'}},
                {'name':'correlation-id','tags':['owner-orders-api'],'config':{'header_name':'X-Correlation-ID','generator':'uuid','echo_downstream':True}},
                {'name':'request-size-limiting','tags':['owner-orders-api'],'config':{'allowed_payload_size':1,'size_unit':'megabytes'}}]}]}

    def check(self):
        self.v.validate_state(self.state, 'orders-api', 'internal', 'dev')

    def test_valid_native_configuration(self): self.check()
    def test_missing_auth_fails(self):
        self.state['services'][0]['plugins'].pop(0)
        with self.assertRaisesRegex(ValueError,'openid-connect'): self.check()
    def test_authorization_required(self):
        del self.state['services'][0]['plugins'][0]['config']['roles_required']
        with self.assertRaisesRegex(ValueError,'authorization'): self.check()
    def test_audience_not_equal_to_audience_required(self):
        c=self.state['services'][0]['plugins'][0]['config']; c['audience']=c.pop('audience_required')
        with self.assertRaisesRegex(ValueError,'audience_required'): self.check()
    def test_wrong_ownership_fails(self):
        self.state['services'][0]['routes'][0]['tags']=[]
        with self.assertRaisesRegex(ValueError,'ownership'): self.check()
    def test_wrong_numeric_type_fails(self):
        self.state['services'][0]['port']='443'
        with self.assertRaisesRegex(ValueError,'port'): self.check()
    def test_shared_entities_cannot_enter_api_scope(self):
        self.state['consumers']=[{'username':'shared'}]
        with self.assertRaisesRegex(ValueError,'top-level'): self.check()
    def test_external_requires_network_and_schema(self):
        with self.assertRaisesRegex(ValueError,'ip-restriction'):
            self.v.validate_state(self.state,'orders-api','external','dev')
    def test_unresolved_template_fails(self):
        self.state['services'][0]['host']='${{ env "DECK_HOST" }}'
        with self.assertRaisesRegex(ValueError,'unresolved'): self.check()
    def test_unknown_environment_key_fails(self):
        with self.assertRaisesRegex(ValueError,'unknown'):
            self.v.check_keys({'enabled':False,'typo':1},{'enabled'},'environment')
    def test_disabled_target_cannot_deploy(self):
        with self.assertRaisesRegex(ValueError,'disabled'):
            self.v.require_enabled({'enabled':False},{'enabled':True})
    def test_duplicate_yaml_keys_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.v.parse_yaml('enabled: false\nenabled: true\n')


    def test_disabled_auth_plugin_rejected(self):
        self.state['services'][0]['plugins'][0]['enabled']=False
        with self.assertRaisesRegex(ValueError,'disabled'):self.check()
    def test_unapproved_plugin_rejected(self):
        self.state['services'][0]['plugins'].append({'name':'pre-function','tags':['owner-orders-api'],'config':{'access':['return']}})
        with self.assertRaisesRegex(ValueError,'approved'):self.check()
    def test_backend_tls_verification_required(self):
        self.state['services'][0]['tls_verify']=False
        with self.assertRaisesRegex(ValueError,'TLS'):self.check()
    def test_plaintext_client_secret_rejected(self):
        self.state['services'][0]['plugins'][0]['config']['client_secret']=['do-not-store-this']
        with self.assertRaisesRegex(ValueError,'secret'):self.check()
    def test_test_redirect_path_rejected(self):
        tests=[{'name':a,'method':'GET','path':'/sales/orders/v1','auth':a,'expected_status':200 if a=='valid' else 401,'body_contains':''} for a in ('valid','none','invalid')]
        tests[0]['path']='//evil.example.com'
        with self.assertRaises(ValueError):self.v.contract(self.state,{'openapi':'3.0.3','paths':{'/sales/orders/v1':{'get':{}}}},tests)
    def test_auth_plugin_must_cover_https(self):
        self.state['services'][0]['plugins'][0]['protocols']=['http']
        with self.assertRaisesRegex(ValueError,'HTTPS'):self.check()
    def test_consumer_scoped_auth_cannot_replace_service_baseline(self):
        self.state['services'][0]['plugins'][0]['consumer']='selected-caller'
        with self.assertRaisesRegex(ValueError,'scope'):self.check()
    def test_redis_policy_requires_real_tls_configuration(self):
        self.state['services'][0]['plugins'][1]['config']['policy']='redis'
        with self.assertRaisesRegex(ValueError,'Redis'):self.check()
    def test_embedded_oas_cannot_drift_from_contract(self):
        self.state['services'][0]['plugins'].append({'name':'oas-validation','tags':['owner-orders-api'],'config':{'api_spec':'openapi: 3.0.3\npaths: {}\n','validate_request_body':True}})
        with self.assertRaisesRegex(ValueError,'embedded OpenAPI'):
            self.v.contract(self.state,{'openapi':'3.0.3','paths':{'/sales/orders/v1':{'get':{}}}},[])
