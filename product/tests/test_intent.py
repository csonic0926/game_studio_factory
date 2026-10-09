"""Synthetic planning contracts; no verdict about real game/player value."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from factory_core.catalog import factory_dependencies
from factory_core.refs import FactoryError, encoded, read_json, reference
from product import intent, value

ROOT = Path(__file__).resolve().parents[2]


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name).resolve()
        subprocess.run(['git', 'init', '-q', str(self.game)], check=True)
        self.roots = dict(game=self.game, factory=ROOT)

    def write(self, path, data):
        target = self.game / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encoded(data) if isinstance(data, dict) else data.encode())
        return reference(self.game, path)

    def seed(self):
        intent.start(self.roots)
        return read_json(self.game / intent.PATH)

    def test_seed_schema_and_fixed_nonclaim_markers(self):
        import jsonschema
        data = self.seed()
        jsonschema.validate(data, read_json(ROOT / 'product/schemas/intent.schema.json'))
        self.assertIsNone(data['buying_reason'])
        self.assertIsNone(data['offer']['amount'])
        self.assertEqual(data['current_build_assessment'], 'NOT_ASSESSED')
        self.assertFalse(data['value_claim_eligible'])
        self.assertFalse(data['authority_granted'])

    def test_forged_assessment_authority_or_unknown_shape_fails(self):
        data = self.seed()
        for key, val in [('state', 'PASS'), ('current_build_assessment', 'SUPPORTED'),
                         ('value_claim_eligible', True), ('authority_granted', True),
                         ('judgment', 'SUPPORTED')]:
            with self.subTest(key=key):
                changed = {**data, key: val}
                with self.assertRaises(FactoryError): intent.validate(self.roots, changed)

    def test_scenario_learning_has_no_build_or_adoption_requirement(self):
        data = self.seed()
        data.update(state='DRAFTED', buying_reason='A compact beautiful strategy toy for short reflective sessions',
                    adequacy_case='Hypothesis: meaningful reconsideration within a satisfying self-contained play')
        data['offer'].update(status='SCENARIO', grounding='HYPOTHESIS', amount='4.99', currency='USD',
                             rationale='AI benchmark scenario, not an adopted or actual selling price')
        data['audience'].update(grounding='HYPOTHESIS', description='Players seeking that bounded experience',
                                rationale='Creative audience hypothesis, not established demand')
        data['value_hypotheses']=[dict(id='reconsider', statement='A changing constraint may make a second choice rewarding', source_refs=[])]
        data['next_move']='Build the authorized smallest experiment and observe whether choices meaningfully change'
        self.write(intent.PATH, data)
        intent.validate(self.roots, data)
        view=intent.start(self.roots)
        self.assertEqual(view['status'], 'PRODUCT_INTENT_DRAFTED')
        self.assertEqual(view['created_paths'], [])
        self.assertFalse(view['value_claim_eligible'])
        self.assertFalse((self.game/'design/factory/PROJECT.json').exists())
        self.assertFalse(list(self.game.glob('design/product_value/*/PRODUCT_VALUE_RESULT.json')))

    def test_wrong_user_adoption_cannot_be_laundered_through_intent(self):
        data = self.seed()
        source = self.write('proposal.json', dict(role='assistant', content='Set price to 4.99 USD'))
        data['offer'].update(status='ADOPTED_OFFER', grounding='GROUNDED', amount='4.99', currency='USD',
                             provenance=[source], adoption=dict(source=source, quote='Set price to 4.99 USD'))
        with self.assertRaisesRegex(FactoryError, 'raw USER source'): intent.validate(self.roots, data)

    def test_changed_new_removed_sources_are_visible_and_preserved(self):
        source=intent.IDEA_PATHS[0]
        self.write(source, dict(schema_version='synthetic-probe', state='open'))
        self.seed()
        original=(self.game/intent.PATH).read_bytes()
        self.write(source, dict(schema_version='synthetic-probe', state='changed'))
        view=intent.inspect(self.roots)
        self.assertEqual(view['status'], 'RECONCILIATION_REQUIRED')
        self.assertEqual(view['intent']['source_refs'][0]['path'], source)
        intent.start(self.roots)
        self.assertEqual(original, (self.game/intent.PATH).read_bytes())
        (self.game/source).unlink()
        self.assertEqual(intent.inspect(self.roots)['status'], 'RECONCILIATION_REQUIRED')

    def test_source_order_is_not_a_content_change(self):
        self.write(intent.IDEA_PATHS[0], dict(schema_version='synthetic-probe'))
        self.write(intent.IDEA_PATHS[1], dict(schema_version='synthetic-exploration'))
        data=self.seed(); data['source_refs'].reverse(); self.write(intent.PATH,data)
        self.assertEqual(intent.inspect(self.roots)['status'],'PRODUCT_INTENT_OPEN')

    def test_intent_never_serves_as_value_result(self):
        self.seed();self.write('build.bin','Synthetic build')
        with self.assertRaises(FactoryError): value.gate(self.roots,intent.PATH,'build.bin')

    def test_context_dependencies_include_intent_owner(self):
        required={'product/intent.py','product/value.py','product/schemas/intent.schema.json',
                  'product/templates/PRODUCT_VALUE_INTENT.json','product/docs/PROJECT_INITIALIZATION_WORKFLOW.md'}
        for version in (2,3):
            for capability in ('idea','studio','gameplay','product'):
                with self.subTest(version=version, capability=capability):
                    refs=factory_dependencies(ROOT,capability,'planning',version)
                    self.assertTrue(required.issubset({r['path'] for r in refs}))


if __name__ == '__main__': unittest.main()
