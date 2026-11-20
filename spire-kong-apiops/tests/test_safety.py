import unittest
from test_validation import PolicyTests
class ScopeTests(PolicyTests):
    def test_multiple_owner_tags_rejected(self):
        self.state['services'][0]['tags'].append('owner-other-api')
        with self.assertRaisesRegex(ValueError,'ownership'):self.check()
    def test_write_smoke_is_not_allowed(self):
        s=self.state['services'][0]['routes'][0];s['methods']=['POST']
        tests=[{'name':'smoke','method':'POST','path':'/sales/orders/v1','auth':'valid','expected_status':200,'body_contains':''}]
        with self.assertRaisesRegex(ValueError,'read-only'):
            self.v.contract(self.state,{'openapi':'3.0.3','paths':{'/sales/orders/v1':{'post':{}}}},tests)

def load_tests(loader,tests,pattern):
    return unittest.TestSuite(ScopeTests(n) for n in ScopeTests.__dict__ if n.startswith('test_'))
