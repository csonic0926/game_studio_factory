"""Synthetic historical contracts only; never real USER approval or UI evidence."""
import hashlib
import json
import unittest
from unittest.mock import patch

from factory_core import continuation as api
from factory_core.refs import FactoryError, digest, encoded, read_json, sha
from factory_core.state import (approval_action, checkpoint, latest, load_design,
                                requirement_ids, verify_record)
from factory_core.tests import test_gpt6_gameplay as gameplay_fixtures


class PreUiExperienceContinuationTests(unittest.TestCase):
    write = gameplay_fixtures.NativeGameplayTests.write
    req = gameplay_fixtures.NativeGameplayTests.req
    authorize = gameplay_fixtures.NativeGameplayTests.authorize

    def setUp(self):
        gameplay_fixtures.NativeGameplayTests.setUp(self)
        out, reviews, ruling = self.authorize()
        checkpoint(self.roots, self.req('PRODUCING', out['checkpoint']['sha256'],
                                        reviews=reviews, ruling=ruling))
        self.record, _ = latest(self.game, 'unit-one')
        self.snapshot = {r['path']: (self.roots['factory'] / r['path']).read_bytes()
                         for r in self.record['dependencies']['references']
                         if r['scope'] == 'factory'}
        frozen = self.snapshot

        class Frozen:
            def __init__(inner, root, path, revision):
                inner.path = path

            def read_bytes(inner):
                return frozen[inner.path]

            def read_text(inner, encoding='utf-8'):
                return inner.read_bytes().decode(encoding)

        for target in ('factory_core.continuation.GitFile', 'factory_core.refs.GitFile'):
            mock = patch(target, Frozen)
            mock.start()
            self.addCleanup(mock.stop)
        self._make_pre_feature()
        self.user = 'design/UI_COMPATIBILITY_USER.json'
        self.quote = 'Select explicit pre-UI production compatibility.'
        self.write(self.user, {'role': 'user', 'content': self.quote})

    def _make_pre_feature(self, *, remove_player_text=False):
        """Build old bytes in memory, never edit the live Factory/test inputs."""
        old_ref = self.record['design']
        design = read_json(self.game / old_ref['path'])
        rules = json.loads(self.snapshot['factory_core/rule_map.json'])
        removed = set(api.UI_EXPERIENCE_RULES)
        schema_path = 'factory_core/schemas/design_v3.schema.json'
        schema = json.loads(self.snapshot[schema_path])
        schema.get('properties', {}).get('ui', {}).get('properties', {}).pop('experience', None)
        if remove_player_text:
            design.pop('player_text')
            schema['properties'].pop('player_text')
            removed.add(api.PLAYER_TEXT_RULE)
        design_ref = self.write(old_ref['path'], design)
        rules['rules'] = [r for r in rules['rules'] if r['id'] not in removed]
        self.snapshot['factory_core/rule_map.json'] = encoded(rules)
        self.snapshot[schema_path] = encoded(schema)
        refs = []
        for old in self.record['dependencies']['references']:
            if old['scope'] == 'factory' and (old['path'] in api.UI_EXPERIENCE_SOURCES
                    or (remove_player_text and old['path'].startswith('player_text/'))):
                continue
            ref = dict(design_ref if old == old_ref else old)
            if ref['scope'] == 'factory':
                ref['sha256'] = hashlib.sha256(self.snapshot[ref['path']]).hexdigest()
            refs.append(ref)
        binding = dict(algorithm='sha256-content-closure.v2', references=refs,
                       fingerprint=digest(refs))
        reviews = []
        for ref in self.record['reviews']:
            review = read_json(self.game / ref['path'])
            review.update(design=design_ref, dependency_fingerprint=binding['fingerprint'])
            for rule in removed:
                review['findings'].pop(rule, None)
            reviews.append(self.write(ref['path'], review))
        ruling = read_json(self.game / self.record['ruling']['path'])
        quote = approval_action(design_ref, binding)
        ruling.update(design=design_ref, dependency_fingerprint=binding['fingerprint'], quote=quote,
                      source=self.write(ruling['source']['path'], {'role': 'user', 'content': quote}))
        self.record.update(design=design_ref, dependencies=binding, reviews=reviews,
                           ruling=self.write(self.record['ruling']['path'], ruling))
        path = sorted((self.game / 'design/factory/checkpoints/unit-one').glob('*.json'))[-1]
        self.write(path.relative_to(self.game).as_posix(), self.record)

    def publish(self):
        preview = api.preview(self.roots, 'unit-one')
        return api.apply(self.roots, 'unit-one', preview['expected'], self.user,
                         self.quote, 'Synthetic pre-feature UI continuation only.')

    def historical_rules(self):
        return json.loads(self.snapshot['factory_core/rule_map.json'])

    def test_full_old_closure_and_proof_unchanged_with_explicit_ui_obligations(self):
        before = {str(p): sha(p) for folder in ('checkpoints',) for p in
                  (self.game / 'design/factory' / folder).rglob('*.json')}
        proofs = {r['path']: sha(self.game / r['path']) for r in
                  [self.record['design'], self.record['ruling'], *self.record['reviews']]}
        preview = api.preview(self.roots, 'unit-one')['preview']
        obligation = preview['ui_compatibility_obligations']
        self.assertEqual(obligation['deferred_current_review_requirements'], [api.UI_GENRE_RULE])
        self.assertEqual(obligation['historical_applicability'], 'UNDECLARED_PRE_FEATURE_NOT_REVIEWED_NONE')
        self.assertEqual(obligation['allowed_stage'], 'PRODUCING')
        self.assertEqual(obligation['current_adoption_required_before'],
                         ['NEW_DESIGN', 'EVIDENCE_READY', 'COMPLETE', 'WHOLE_GAME_HANDOFF'])
        self.publish()
        verified = api.verify(self.roots, 'unit-one')
        self.assertEqual(verified['ui_compatibility_obligations'], obligation)
        self.assertFalse(verified['historical_reviews_are_current'])
        self.assertFalse(verified['delivery_eligible'])
        self.assertFalse(verified['acceptance_authority_granted'])
        self.assertEqual(before, {str(p): sha(p) for p in
                         (self.game / 'design/factory/checkpoints').rglob('*.json')})
        self.assertEqual(proofs, {path: sha(self.game / path) for path in proofs})
        self.assertNotIn('ui', read_json(self.game / self.record['design']['path']))
        from factory_core.context import inspect, context
        self.assertEqual(inspect(self.roots, 'unit-one')['blockers'], [])
        view = context(self.roots, 'studio', 'objective', task_id='unit-one')
        self.assertEqual(view['work_status'], 'HISTORICAL_CONTRACT_CONTINUATION')
        self.assertEqual(view['continuation']['ui_compatibility_obligations'], obligation)
        self.assertNotIn('approval_action', view)

    def test_player_text_and_ui_exceptions_qualify_independently(self):
        self._make_pre_feature(remove_player_text=True)
        self.publish()
        value = api.verify(self.roots, 'unit-one')
        self.assertEqual(value['compatibility_obligations']['deferred_current_review_requirements'],
                         [api.PLAYER_TEXT_RULE])
        self.assertEqual(value['ui_compatibility_obligations']['deferred_current_review_requirements'],
                         [api.UI_GENRE_RULE])
        with self.assertRaisesRegex(FactoryError, 'declare ALL, CHANGED or reviewed NONE'):
            load_design(self.roots, self.record['design'])

    def test_old_schema_support_refuses_exception(self):
        path = 'factory_core/schemas/design_v3.schema.json'
        schema = json.loads(self.snapshot[path])
        schema['properties'].setdefault('ui', {}).setdefault('properties', {})['experience'] = {}
        self.snapshot[path] = encoded(schema)
        self.assertIsNone(api._legacy_ui_experience_contract(self.roots, self.record,
                                                            self.historical_rules()))

    def test_indirect_or_compound_old_schema_is_not_proven_feature_absence(self):
        path = 'factory_core/schemas/design_v3.schema.json'
        original = self.snapshot[path]
        for key in ('$ref', 'allOf', 'anyOf', 'oneOf'):
            with self.subTest(key=key):
                schema = json.loads(original)
                schema['properties']['ui'] = {key: 'synthetic-unresolved-shape'}
                self.snapshot[path] = encoded(schema)
                self.assertIsNone(api._legacy_ui_experience_contract(self.roots, self.record,
                                                                    self.historical_rules()))

    def test_any_existing_ui_feature_rule_refuses_exception(self):
        old = self.historical_rules()
        for rule in api.UI_EXPERIENCE_RULES:
            with self.subTest(rule=rule):
                rules = {'rules': [*old['rules'], {'id': rule}]}
                self.assertIsNone(api._legacy_ui_experience_contract(self.roots, self.record, rules))

    def test_any_existing_ui_feature_source_refuses_exception(self):
        original = list(self.record['dependencies']['references'])
        for path in api.UI_EXPERIENCE_SOURCES:
            with self.subTest(path=path):
                self.record['dependencies']['references'] = [*original,
                    dict(scope='factory', path=path, sha256='recognizer-unit-test-not-proof')]
                self.assertIsNone(api._legacy_ui_experience_contract(self.roots, self.record,
                                                                    self.historical_rules()))

    def test_explicit_ui_binding_and_non_studio_gameplay_never_receive_exception(self):
        original = read_json(self.game / self.record['design']['path'])
        for binding in (None, {'experience': None}, {'experience': {'path': 'missing'}}):
            with self.subTest(binding=binding):
                design = dict(original, ui=binding)
                record = dict(self.record, design=self.write('design/EXPLICIT.json', design))
                self.assertIsNone(api._legacy_ui_experience_contract(self.roots, record,
                                                                    self.historical_rules()))
                with self.assertRaises(FactoryError):
                    load_design(self.roots, record['design'], _legacy_player_text=True)
        for capability in ('asset', 'sound', 'story', 'ui'):
            record = dict(self.record, design=self.write('design/OTHER.json',
                                                         dict(original, capability=capability)))
            self.assertIsNone(api._legacy_ui_experience_contract(self.roots, record,
                                                                self.historical_rules()))

    def test_bad_historical_bytes_rejected_before_recognizer(self):
        self.snapshot['factory_core/state.py'] += b'\nchanged original bytes\n'
        with patch.object(api, '_legacy_ui_experience_contract') as recognize:
            with self.assertRaisesRegex(FactoryError, 'historical Factory bytes mismatch'):
                self.publish()
            recognize.assert_not_called()

    def test_only_exact_new_genre_rule_addition_is_deferred_no_removals(self):
        original = api.requirement_ids
        design = read_json(self.game / self.record['design']['path'])
        existing = next(x for x in original(self.roots['factory'], design, 'intent_experience')
                        if x != api.UI_GENRE_RULE)
        for change in (lambda *a: original(*a) | {'unrelated.new.rule'},
                       lambda *a: original(*a) - {existing}):
            with patch.object(api, 'requirement_ids', side_effect=change):
                with self.assertRaisesRegex(FactoryError, 'rule membership'):
                    self.publish()

    def test_explicit_user_and_exact_preview_still_required(self):
        with self.assertRaisesRegex(FactoryError, 'no explicit production continuation'):
            api.verify(self.roots, 'unit-one')
        preview = api.preview(self.roots, 'unit-one')
        with self.assertRaisesRegex(FactoryError, 'preview changed'):
            api.apply(self.roots, 'unit-one', 'wrong', self.user, self.quote, 'test')
        self.write(self.user, {'role': 'assistant', 'content': self.quote})
        with self.assertRaisesRegex(FactoryError, 'raw USER'):
            api.apply(self.roots, 'unit-one', preview['expected'], self.user, self.quote, 'test')

    def test_obligations_cannot_be_erased_or_normal_completion_bypassed(self):
        self.publish()
        with self.assertRaises(FactoryError):
            verify_record(self.roots, self.record)
        for stage in ('EVIDENCE_READY', 'COMPLETE'):
            with self.subTest(stage=stage), self.assertRaises(FactoryError):
                checkpoint(self.roots, self.req(stage, latest(self.game, 'unit-one')[1],
                    reviews=self.record['reviews'], ruling=self.record['ruling']))
        design = load_design(self.roots, self.record['design'])
        self.assertIn(api.UI_GENRE_RULE, requirement_ids(self.roots['factory'], design,
                                                       'intent_experience', 'COLLABORATIVE'))
        receipt, _ = api.latest_receipt(self.roots, 'unit-one')
        receipt['preview']['ui_compatibility_obligations']['current_adoption_required_before'] = []
        self.write('design/factory/continuations/unit-one/000001.json', receipt)
        with self.assertRaisesRegex(FactoryError, 'closure changed'):
            api.verify(self.roots, 'unit-one')

    def test_changed_current_resolution_revokes_receipt(self):
        self.publish()
        original = api.dependencies

        def changed(*args):
            result = original(*args)
            result['fingerprint'] = 'changed-current-ui-resolution'
            return result

        with patch.object(api, 'dependencies', side_effect=changed):
            with self.assertRaisesRegex(FactoryError, 'closure changed'):
                api.verify(self.roots, 'unit-one')

    def test_changed_project_authority_still_rejected(self):
        # This fixture adopts a bound gameplay project standard; its explicit
        # authority_paths list is intentionally empty after migration.
        path = self.game / self.standard['path']
        path.write_bytes(path.read_bytes() + b'\nChanged synthetic project authority.\n')
        with self.assertRaises(FactoryError):
            self.publish()

    def test_noncollaborative_and_nonproducing_never_receive_exception(self):
        with patch('factory_core.authorship.mode', return_value='AUTONOMOUS'):
            with self.assertRaisesRegex(FactoryError, 'collaborative v3'):
                self.publish()
        path = sorted((self.game / 'design/factory/checkpoints/unit-one').glob('*.json'))[-1]
        for stage in ('DRAFT', 'AUTHORIZED', 'EVIDENCE_READY', 'COMPLETE'):
            record = dict(self.record, stage=stage)
            self.write(path.relative_to(self.game).as_posix(), record)
            with self.subTest(stage=stage), self.assertRaisesRegex(FactoryError, 'latest unblocked PRODUCING'):
                self.publish()


if __name__ == '__main__':
    unittest.main()
