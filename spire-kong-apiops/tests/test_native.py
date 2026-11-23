"""Optional real decK contract test; skipped explicitly when the pinned CLI is absent."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('deck'),'real decK not installed; CLI integration not verified')
class NativeTests(unittest.TestCase):
    def test_native_render_preserves_scope_types_and_vault_reference(self):
        with tempfile.TemporaryDirectory() as d:
            r=subprocess.run(['bash',str(ROOT/'scripts/build.sh'),'invoices','dev',d],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            state=yaml.safe_load((Path(d)/'state.yaml').read_text())
            self.assertEqual(state['_info']['select_tags'],['owner-invoices'])
            self.assertIs(type(state['services'][0]['port']),int)
            rate=next(p for p in state['services'][0]['plugins'] if p['name']=='rate-limiting')
            self.assertEqual(rate['config']['redis']['password'],'{vault://REPLACE_VAULT_PREFIX/redis-dev-password}')
    def test_checked_in_deck_config_does_not_pollute_json_output(self):
        with tempfile.TemporaryDirectory() as d:
            r=subprocess.run(['bash',str(ROOT/'scripts/build.sh'),'invoices','dev',d],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run(['deck','file','validate','--config',str(ROOT/'pipelines/deck.yaml'),str(Path(d)/'state.yaml')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(r.stdout,'')
