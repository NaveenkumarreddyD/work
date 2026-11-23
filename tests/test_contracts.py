import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('validator',ROOT/'scripts/validate.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class ContractTests(unittest.TestCase):
    def test_invalid_openapi_document_rejected(self):
        with self.assertRaises(ValueError):v.validate_openapi({'openapi':'3.0.3','paths':{}})
    def test_remote_refs_never_fetched(self):
        with self.assertRaisesRegex(ValueError,'local'):
            v.validate_openapi({'openapi':'3.0.3','info':{'title':'a','version':'1'},'paths':{},'components':{'schemas':{'A':{'$ref':'https://outside.example.invalid/secret'}}}})
    def test_valid_contract_accepted(self):
        v.validate_openapi(v.load(ROOT/'apis/billing/invoices/openapi.yaml'))

    def setUp(self):
        folder = ROOT/'apis/billing/payments'
        self.state = v.load(folder/'kong.yaml')
        self.spec = v.load(folder/'openapi.yaml')
        self.tests = v.load(folder/'tests.yaml')['tests']
        self.route = self.state['services'][0]['routes'][0]
        self.path = self.route['paths'][0]

    def check(self):
        v.contract(self.state, self.spec, self.tests)

    def test_documented_method_requires_matching_kong_method(self):
        self.spec['paths'][self.path]['post'] = {}
        with self.assertRaisesRegex(ValueError, f'Kong route missing: POST {self.path}'):
            self.check()

    def test_kong_method_requires_matching_openapi_method(self):
        self.route['methods'].append('POST')
        with self.assertRaisesRegex(ValueError, f'OpenAPI operation missing: POST {self.path}'):
            self.check()

    def test_each_read_operation_needs_its_own_positive_check(self):
        for method in ('GET', 'HEAD'):
            with self.subTest(method=method):
                path = self.path + '/' + method.lower()
                self.state['services'][0]['routes'].append({'paths':[path], 'methods':[method]})
                self.spec['paths'][path] = {method.lower():{}, 'parameters':[]}
                self.tests.append(dict(self.tests[1], method=method, path=path))
                with self.assertRaisesRegex(ValueError, f'successful smoke test missing: {method} {path}'):
                    self.check()
                self.tests.append(dict(self.tests[0], method=method, path=path, body_contains=''))
                self.check()

    def test_local_path_item_reference_is_checked(self):
        self.spec['components']['pathItems'] = {'read': self.spec['paths'][self.path]}
        self.spec['paths'][self.path] = {'$ref':'#/components/pathItems/read'}
        self.check()
        self.spec['components']['pathItems']['read']['head'] = {}
        with self.assertRaisesRegex(ValueError, f'Kong route missing: HEAD {self.path}'):
            self.check()
