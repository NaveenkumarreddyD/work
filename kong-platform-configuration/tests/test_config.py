import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from kong_config import build,check

class Tests(unittest.TestCase):
    def test_all_envs_render(self):
        for env in ('dev','uat','training','preprod','prod'):
            state,meta=build('example-orders',env)
            self.assertEqual(state['_info']['select_tags'],['owner-example-orders'])
            self.assertEqual(state['services'][0]['plugins'][0]['name'],'openid-connect')
            self.assertEqual(meta['environment'],env)
    def test_placeholders_fail_closed(self):
        with self.assertRaises(ValueError):
            check('example-orders','dev',True)
    def test_invalid_api_fails(self):
        with self.assertRaises(ValueError):
            build('../etc','dev')
    def test_no_diff_parser(self):
        import tempfile,subprocess
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'diff.txt'
            p.write_text('Summary:\n  Created: 0\n  Updated: 0\n  Deleted: 0\n')
            result=subprocess.run([sys.executable,str(root/'scripts/assert_no_diff.py'),str(p)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            p.write_text('Summary:\n  Created: 1\n  Updated: 0\n  Deleted: 0\n')
            self.assertNotEqual(subprocess.run([sys.executable,str(root/'scripts/assert_no_diff.py'),str(p)],capture_output=True).returncode,0)
if __name__=='__main__': unittest.main()
