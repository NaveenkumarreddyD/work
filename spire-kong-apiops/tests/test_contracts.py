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
