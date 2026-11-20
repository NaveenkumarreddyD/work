"""Inherited tool environment cannot silently change the ownership boundary."""
import unittest
from test_deploy import DeployTests
class DeckEnvironmentTests(DeployTests):
    def test_inherited_selection_tag_is_removed(self):
        p=self.bin/'deck'
        s=p.read_text().replace("a=sys.argv[1:]", "a=sys.argv[1:]\nif os.environ.get('DECK_SELECT_TAG'):sys.exit(88)")
        p.write_text(s)
        self.plan(DECK_SELECT_TAG='owner-unrelated')

def load_tests(loader,tests,pattern):
    return unittest.TestSuite([DeckEnvironmentTests('test_inherited_selection_tag_is_removed')])
