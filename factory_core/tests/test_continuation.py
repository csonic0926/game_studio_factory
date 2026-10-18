"""Synthetic approvals only. Never represent these fixtures as USER acceptance."""
import hashlib
import json
import unittest
from unittest.mock import patch

from factory_core import continuation as api
from factory_core.refs import FactoryError, read_json, reference, sha, digest
from factory_core.state import checkpoint, latest, approval_action, verify_record
from factory_core.tests import test_gpt6 as fixtures


class ContinuationTests(unittest.TestCase):
    setUpBase = fixtures.Gpt6Tests.setUp
    write = fixtures.Gpt6Tests.write
    request = fixtures.Gpt6Tests.request
    reviews = fixtures.Gpt6Tests.reviews
    migrate = fixtures.Gpt6Tests.migrate
    design = fixtures.Gpt6Tests.design

    def setUp(self):
        self.setUpBase()
        d, ref = self.design()
        out = checkpoint(self.roots, self.request('DESIGN_COMPLETE', design=ref))
        record, _ = latest(self.game, 'lantern')
        reviews = self.reviews(d, ref, record['dependencies'])
        factory_evidence = next(r for r in record['dependencies']['references']
                                if r['scope'] == 'factory' and r['path'] == 'factory_core/state.py')
        body = read_json(self.game / reviews[0]['path'])
        next(iter(body['findings'].values()))['evidence'].append(factory_evidence)
        reviews[0] = self.write(reviews[0]['path'], body)
        out = checkpoint(self.roots, self.request('REVIEWED', out['checkpoint']['sha256'], design=ref, reviews=reviews))
        quote = approval_action(ref, record['dependencies'])
        source = self.write('design/source.json', {'role': 'user', 'content': quote})
        ruling = self.write('design/ruling.json', dict(schema_version='factory_ruling.v2', owner='USER',
            decision='APPROVE', design=ref, dependency_fingerprint=record['dependencies']['fingerprint'], source=source, quote=quote))
        for stage in ('AUTHORIZED', 'PRODUCING'):
            request = self.request(stage, out['checkpoint']['sha256'], design=ref, reviews=reviews, ruling=ruling)
            if stage == 'PRODUCING':
                request['artifacts'] = [self.write('design/progress.txt', 'historical progress output')]
            out = checkpoint(self.roots, request)
        self.record, _ = latest(self.game, 'lantern')
        # Historical source fixtures are in memory. This permits testing an
        # uncommitted development tree without falsely claiming Git durability.
        snapshot = {r['path']: (self.roots['factory'] / r['path']).read_bytes()
                    for r in self.record['dependencies']['references'] if r['scope'] == 'factory'}
        snapshot['factory_core/rule_map.json'] = (self.roots['factory'] / 'factory_core/rule_map.json').read_bytes()
        class Frozen:
            def __init__(s, root, path, revision):
                s.path = path
            def read_bytes(s):
                return snapshot[s.path]
            def read_text(s, encoding='utf-8'):
                return s.read_bytes().decode(encoding)
        self.snapshot = snapshot
        self.patch = patch.object(api, 'GitFile', Frozen)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        historical_evidence = patch('factory_core.refs.GitFile', Frozen)
        historical_evidence.start()
        self.addCleanup(historical_evidence.stop)
        self.user = 'design/compatibility-user.json'
        self.write(self.user, {'role': 'user', 'content': 'Select unchanged-contract production continuation.'})
        self.quote = 'Select unchanged-contract production continuation.'

    def publish(self, **kw):
        p = api.preview(self.roots, 'lantern')
        return api.apply(self.roots, 'lantern', p['expected'], self.user, self.quote, 'Synthetic continuation.', **kw)

    def test_preview_is_read_only_and_receipt_is_separate(self):
        before = {str(p):sha(p) for p in self.game.rglob('*') if p.is_file() and '.git' not in p.parts}
        p = api.preview(self.roots, 'lantern')
        self.assertFalse(p['preview']['historical_reviews_are_current'])
        after = {str(p):sha(p) for p in self.game.rglob('*') if p.is_file() and '.git' not in p.parts}
        self.assertEqual(before, after)
        original, original_hash = latest(self.game, 'lantern')
        self.publish()
        self.assertEqual((original, original_hash), latest(self.game, 'lantern'))
        value = api.verify(self.roots, 'lantern')
        self.assertFalse(value['delivery_eligible'])
        self.assertFalse(value['acceptance_authority_granted'])
        self.assertEqual(value['stage'], 'PRODUCING')

    def test_bad_historical_factory_bytes_rejected(self):
        self.snapshot['factory_core/state.py'] += b'\nchanged historical fixture\n'
        with self.assertRaisesRegex(FactoryError, 'historical Factory bytes mismatch'):
            api.preview(self.roots, 'lantern')

    def test_game_authority_mutation_rejected(self):
        self.write('RULES.md', 'Changed project rule.')
        with self.assertRaises(FactoryError): self.publish()

    def test_changed_design_rejected(self):
        self.write('design/assets/DESIGN.md', 'Different lamp.')
        with self.assertRaises(FactoryError): self.publish()

    def test_wrong_source_and_preview_rejected(self):
        p = api.preview(self.roots, 'lantern')
        with self.assertRaisesRegex(FactoryError, 'preview changed'):
            api.apply(self.roots, 'lantern', 'wrong', self.user, self.quote, 'test')
        self.write(self.user, {'role': 'assistant', 'content': self.quote})
        with self.assertRaisesRegex(FactoryError, 'raw USER'):
            api.apply(self.roots, 'lantern', p['expected'], self.user, self.quote, 'test')

    def test_artifact_scope_and_exact_output(self):
        self.write('out-of-scope.txt', 'not allowed')
        with self.assertRaisesRegex(FactoryError, 'approved production outputs'):
            self.publish(artifacts=['out-of-scope.txt'])
        self.write('texture/lantern.png', 'synthetic output bytes, not actual PNG')
        self.publish(artifacts=['texture/lantern.png'])
        api.verify(self.roots, 'lantern')
        self.write('texture/lantern.png', 'mutated output')
        with self.assertRaises(FactoryError): api.verify(self.roots, 'lantern')

    def test_receipts_append_and_tampered_chain_rejected(self):
        one = self.publish()
        first = (self.game / one['receipt']['path']).read_bytes()
        self.publish()
        self.assertEqual(first, (self.game / one['receipt']['path']).read_bytes())
        value, _ = api.latest_receipt(self.roots, 'lantern')
        self.assertEqual(value['generation'], 2)
        path = 'design/factory/continuations/lantern/000002.json'
        value['previous'] = 'tampered'
        self.write(path, value)
        with self.assertRaisesRegex(FactoryError, 'broken append-only'):
            api.verify(self.roots, 'lantern')

    def test_changed_applicable_membership_and_new_project_source_rejected(self):
        original = api.requirement_ids
        with patch.object(api, 'requirement_ids', side_effect=lambda *a: original(*a) | {'new.rule'}):
            with self.assertRaisesRegex(FactoryError, 'rule membership'):
                self.publish()
        original = api.dependencies
        extra = self.write('NEW_AUTHORITY.md', 'new obligation')
        def added(*a):
            b = original(*a)
            b['references'].append(extra)
            b['fingerprint'] = digest(b['references'])
            return b
        with patch.object(api, 'dependencies', side_effect=added):
            with self.assertRaisesRegex(FactoryError, 'new project authority'):
                self.publish()

    def test_receipt_invalidated_by_current_resolver_change(self):
        self.publish()
        original = api.dependencies
        def changed(*a):
            b = original(*a)
            b['fingerprint'] = 'different-current-resolution'
            return b
        with patch.object(api, 'dependencies', side_effect=changed):
            with self.assertRaisesRegex(FactoryError, 'closure changed'):
                api.verify(self.roots, 'lantern')

    def test_archived_product_cannot_be_revived(self):
        self.write('design/product/PRODUCT_AUTHORITY_REGISTER.json', {'status': 'NO_ACTIVE_PRODUCT_AUTHORITY'})
        with self.assertRaisesRegex(FactoryError, 'never revives archived'):
            self.publish()

    def test_normal_checkpoint_validator_not_bypassed(self):
        self.publish()
        original = self.record['dependencies']
        self.record['dependencies'] = dict(original, fingerprint='stale-normal-record')
        with self.assertRaisesRegex(FactoryError, 'relevant dependencies changed'):
            verify_record(self.roots, self.record)

    def test_context_distinguishes_old_output_from_current_continuation(self):
        from factory_core.context import inspect, context
        self.publish()
        self.write('design/progress.txt', 'new progress, historical output no longer current')
        with self.assertRaises(FactoryError): verify_record(self.roots, self.record)
        result = inspect(self.roots, 'lantern')
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['tasks'][0]['status'], 'HISTORICAL_CONTRACT_CONTINUATION')
        self.assertFalse(result['delivery_eligible'])
        result = context(self.roots, 'asset', 'prop', task_id='lantern')
        self.assertEqual(result['work_status'], 'HISTORICAL_CONTRACT_CONTINUATION')
        self.assertFalse(result['authority'])
        self.assertNotIn('dependency_fingerprint', result)
        self.assertNotIn('approval_action', result)

    def test_new_task_boundary_and_revoked_original_user_source_rejected(self):
        self.publish()
        ruling = read_json(self.game / self.record['ruling']['path'])
        self.write(ruling['source']['path'], {'role': 'user', 'content': 'I reject this design.'})
        with self.assertRaises(FactoryError): api.verify(self.roots, 'lantern')

    def test_later_draft_blocks_historical_continuation(self):
        self.publish()
        _, previous = latest(self.game, 'lantern')
        checkpoint(self.roots, self.request('DRAFT', previous, design=self.record['design']))
        with self.assertRaisesRegex(FactoryError, 'latest unblocked PRODUCING'):
            api.verify(self.roots, 'lantern')

