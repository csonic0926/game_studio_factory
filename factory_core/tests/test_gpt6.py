"""Explicit adaptation contracts. All fixture rulings are synthetic, not USER acceptance."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from factory import parser
from factory_core import migration_gpt6 as migration
from factory_core.astra import catalog, selected_methods
from factory_core.catalog import factory_dependencies
from factory_core.context import context, inspect
from factory_core.refs import FactoryError, read_json, reference, sha, digest
from factory_core.state import checkpoint, latest, load_design, project, verify_record
from factory_core.tests import test_core as core
ROOT = core.ROOT


class Gpt6Tests(unittest.TestCase):
    setUp = core.CoreTests.setUp
    write = core.CoreTests.write
    request = core.CoreTests.request
    reviews = core.CoreTests.reviews

    def migrate(self):
        preview = migration.preview(self.game, ROOT, 'fixture', ['RULES.md'])
        return migration.apply(self.game, ROOT, 'fixture', preview['source_digest'], ['RULES.md'])

    def design(self):
        self.migrate()
        body = 'The lantern is warm.\nIts alpha border stays transparent.\n'
        artifact = self.write('design/assets/DESIGN.md', body)
        d = dict(schema_version='factory_design.v3', design_id='lantern', capability='asset', task='prop',
            author_context_id='author', intent='Readable lantern.', artifacts=[artifact], inputs=[],
            decisions=[dict(id='light', source=artifact, excerpt='The lantern is warm.', consequence='Its alpha border stays transparent.')],
            decision_sections=[dict(id='appearance', source=artifact, text=body, decision_ids=['light'])],
            requirements={}, production_scope=['texture/lantern.png'], acceptance=['Technical and visual quality.'], methods=[],
            player_text=dict(scope='NONE', scope_evidence=artifact, receipt_path=None))
        return d, self.write('design/assets/PACKAGE.json', d)

    def test_cli_alias_and_explicit_default(self):
        a = parser().parse_args(['inspect', '--project-root', str(self.game)])
        self.assertEqual(a.game_repo, str(self.game))
        self.assertEqual(parser().parse_args(['migrate', '--project-id', 'fixture']).workflow, 'v2')

    def test_fresh_opt_in_idempotent_and_pointer(self):
        before = sha(self.game / 'RULES.md')
        self.migrate()
        self.assertEqual(project(self.game)['workflow_version'], 3)
        self.assertEqual(inspect(self.roots)['workflow'], 'gpt6')
        self.assertIn(str(ROOT), (self.game / migration.POINTER).read_text())
        self.assertEqual(self.migrate()['status'], 'ALREADY_MIGRATED')
        self.assertEqual(sha(self.game / 'RULES.md'), before)

    def test_default_v2_does_not_downgrade(self):
        self.migrate()
        from factory_core.migration import preview
        with self.assertRaisesRegex(FactoryError, 'no implicit downgrade'):
            preview(self.game, ROOT, 'fixture', ['RULES.md'])

    def test_wrong_checkout_and_relink_fail_before_writes(self):
        self.migrate()
        from setup import link_game_repo
        before = sha(self.game / migration.POINTER)
        with self.assertRaises(FactoryError):
            link_game_repo(str(self.game.parent / 'other-factory'), str(self.game))
        self.assertEqual(sha(self.game / migration.POINTER), before)
        self.write(migration.POINTER, 'STUDIO_ROOT: /wrong\n')
        self.assertEqual(inspect(self.roots)['status'], 'FACTORY_SOURCE_MISMATCH')

    def test_full_preflight_rejects_changed_source(self):
        preview = migration.preview(self.game, ROOT, 'fixture')
        self.write('AGENTS.md', 'Concurrent USER edit\n')
        with self.assertRaisesRegex(FactoryError, 'preview/source digest changed'):
            migration.apply(self.game, ROOT, 'fixture', preview['source_digest'])
        self.assertFalse((self.game / migration.JOURNAL).exists())
        self.assertFalse((self.game / migration.POINTER).exists())

    def test_partial_upgrade_blocks_then_recovers_without_history_rewrite(self):
        from factory_core.migration import preview, apply, routing_reference_valid
        old_agents = sha(self.game / 'AGENTS.md')
        p = preview(self.game, ROOT, 'fixture', ['RULES.md'])
        apply(self.game, ROOT, 'fixture', p['source_digest'], ['RULES.md'])
        out = checkpoint(self.roots, self.request())
        old_head = out['checkpoint']
        p = migration.preview(self.game, ROOT, 'fixture', ['RULES.md'])
        replace = migration.replace_checked
        def crash(path, before, data):
            if path.name == 'PROJECT.json': raise RuntimeError('interrupted activation')
            return replace(path, before, data)
        with patch.object(migration, 'replace_checked', side_effect=crash):
            with self.assertRaises(RuntimeError):
                migration.apply(self.game, ROOT, 'fixture', p['source_digest'], ['RULES.md'])
        self.assertEqual(inspect(self.roots)['status'], 'MIGRATION_RECOVERY_REQUIRED')
        self.assertEqual(migration.apply(self.game, ROOT, 'fixture', p['source_digest'], ['RULES.md'])['status'], 'MIGRATED')
        self.assertEqual(sha(self.game / old_head['path']), old_head['sha256'])
        self.assertTrue(routing_reference_valid(self.game, 'AGENTS.md', old_agents))
        with self.assertRaisesRegex(FactoryError, 'create a new task'):
            checkpoint(self.roots, self.request(previous=old_head['sha256']))
        self.assertEqual(inspect(self.roots, 'lantern')['tasks'][0]['status'], 'HISTORICAL_WORKFLOW_REQUIRED')

    def test_authority_changed_during_writes_blocks_activation(self):
        p=migration.preview(self.game, ROOT, 'fixture', ['RULES.md'])
        original=migration.replace_checked
        def competing_editor(path, before, data):
            original(path, before, data)
            if path.name == 'STUDIO_FACTORY.local.md':
                self.write('RULES.md', 'Concurrent new authority.')
        with patch.object(migration, 'replace_checked', side_effect=competing_editor):
            with self.assertRaisesRegex(FactoryError, 'source changed'):
                migration.apply(self.game, ROOT, 'fixture', p['source_digest'], ['RULES.md'])
        self.assertFalse((self.game/'design/factory/PROJECT.json').exists())
        self.assertTrue((self.game/migration.JOURNAL).exists())

    def test_interrupted_target_conflict_is_not_overwritten(self):
        p = migration.preview(self.game, ROOT, 'fixture')
        replace = migration.replace_checked
        def crash(path, before, data):
            if path.name == 'PROJECT.json': raise RuntimeError('stop')
            return replace(path, before, data)
        with patch.object(migration, 'replace_checked', side_effect=crash):
            with self.assertRaises(RuntimeError): migration.apply(self.game, ROOT, 'fixture', p['source_digest'])
        self.write(migration.POINTER, 'STUDIO_ROOT: /concurrent\n')
        with self.assertRaisesRegex(FactoryError, 'source changed'):
            migration.apply(self.game, ROOT, 'fixture', p['source_digest'])
        self.assertIn('/concurrent', (self.game / migration.POINTER).read_text())

    def test_existing_authorities_cannot_be_dropped(self):
        self.migrate()
        with self.assertRaisesRegex(FactoryError, 'already adopted authorities'):
            migration.preview(self.game, ROOT, 'fixture', [])

    def test_native_context_preserves_authority_and_deduplicates(self):
        d, ref = self.design()
        c = context(self.roots, 'asset', 'prop', design=ref)
        bodies = '\n'.join(x.get('text', '') for x in c['constraints'])
        self.assertIn('Never change the bridge mystery.', bodies)
        self.assertIn('No hidden character knowledge.', bodies)
        self.assertNotIn('benchmark uses fixed', bodies)
        self.assertEqual(c['decision_sections'], d['decision_sections'])
        self.assertEqual(c['selected_methods'], [])
        with self.assertRaisesRegex(FactoryError, 'generic project context is forbidden'):
            context(self.roots, 'asset', 'prop', 'blind_observer')

    def test_optional_method_is_explicit_and_bound_at_design(self):
        d, ref = self.design()
        c = context(self.roots, 'asset', 'prop', methods=['asset.production'])
        self.assertEqual(len(c['selected_methods']), 1)
        with self.assertRaisesRegex(FactoryError, 'new draft'):
            context(self.roots, 'asset', 'prop', design=ref, methods=['asset.production'])
        d['methods'] = ['asset.production']; ref = self.write('design/assets/PACKAGE.json', d)
        self.assertEqual(len(context(self.roots, 'asset', 'prop', design=ref)['selected_methods']), 1)
        d['methods'] = ['story.chapter-branch']; ref = self.write('design/assets/PACKAGE.json', d)
        with self.assertRaises(FactoryError): load_design(self.roots, ref)

    def test_unused_method_is_not_a_dependency_but_selected_is(self):
        bare = {r['path'] for r in factory_dependencies(ROOT, 'story', 'character', 3)}
        selected = {r['path'] for r in factory_dependencies(ROOT, 'story', 'character', 3, ['story.world-character'])}
        path = 'story/core/methods/world-character.md'
        self.assertNotIn(path, bare); self.assertIn(path, selected)
        self.assertFalse(any('/core/steps/' in p for p in bare))
        self.assertFalse(any('benchmark' in p for p in bare))
        legacy = {r['path'] for r in factory_dependencies(ROOT, 'story', 'character')}
        self.assertTrue(any('/core/steps/character/' in p for p in legacy))
        self.assertNotIn('factory_core/astra.py', legacy)
        self.assertFalse(any('_v3.schema' in p for p in legacy))

    def test_old_method_map_complete_and_all_new_sources_exist(self):
        data = read_json(ROOT / 'factory_core/knowledge.json')
        mapped = {x['source'] for x in data['obligation_map']}
        expected = {str(p.relative_to(ROOT)) for p in (ROOT / 'story/core/steps').glob('*/*.md')}
        self.assertEqual(mapped, expected)
        for item in data['methods']:
            self.assertTrue((ROOT / item['source']).is_file())
            for source in item['legacy_sources']: self.assertTrue((ROOT / source).is_file())

    def test_v3_schema_and_exact_sections_fail_closed(self):
        d, ref = self.design()
        d['decision_sections'][0]['text'] = 'A rewritten favorable summary.'
        with self.assertRaisesRegex(FactoryError, 'exact original'):
            load_design(self.roots, self.write('design/assets/PACKAGE.json', d))
        d['schema_version'] = 'factory_design.v2'
        with self.assertRaisesRegex(FactoryError, 'historical'):
            load_design(self.roots, self.write('design/assets/PACKAGE.json', d))

    def test_two_reviews_do_not_automatically_authorize_v3(self):
        d, ref = self.design()
        out = checkpoint(self.roots, self.request('DESIGN_COMPLETE', design=ref))
        record, _ = latest(self.game, 'lantern')
        refs = self.reviews(d, ref, record['dependencies'])
        out = checkpoint(self.roots, self.request('REVIEWED', out['checkpoint']['sha256'], design=ref, reviews=refs))
        c = context(self.roots, 'asset', 'prop', 'human', 'lantern')
        self.assertIn('approval_action', c)
        self.assertEqual(c['decision_sections'], d['decision_sections'])
        with self.assertRaises(FactoryError):
            checkpoint(self.roots, self.request('AUTHORIZED', out['checkpoint']['sha256'], design=ref, reviews=refs))
        with self.assertRaisesRegex(FactoryError, 'one verified boundary'):
            checkpoint(self.roots, self.request('PRODUCING', out['checkpoint']['sha256'], design=ref, reviews=refs))

    def test_no_fit_still_needs_no_design(self):
        self.migrate()
        req = self.request(); req.update(capability='idea', task='exploration', unresolved=['Reference has no productive fit.'])
        checkpoint(self.roots, req)
        c = context(self.roots, 'idea', 'exploration', task_id='lantern')
        self.assertEqual(c['work']['stage'], 'DRAFT')
        self.assertNotIn('design', c)

    def test_resume_context_reports_current_stage_and_wrong_task(self):
        self.migrate()
        checkpoint(self.roots, self.request())
        c = context(self.roots, 'asset', 'prop', task_id='lantern')
        self.assertEqual(c['work_status'], 'CURRENT_CHECKPOINT')
        self.assertEqual(c['next_action'], 'continue authoring')
        self.assertFalse(c['blockers'])
        with self.assertRaisesRegex(FactoryError, 'checkpoint capability/task mismatch'):
            context(self.roots, 'idea', 'exploration', task_id='lantern')

    def test_resume_context_never_refreshes_stale_design_work(self):
        d, ref = self.design()
        checkpoint(self.roots, self.request('DESIGN_COMPLETE', design=ref))
        self.write('RULES.md', 'A new USER constraint applies.')
        c = context(self.roots, 'asset', 'prop', task_id='lantern')
        self.assertEqual(c['work_status'], 'REVALIDATION_REQUIRED')
        self.assertTrue(c['blockers'])
        self.assertIn('new draft', c['next_action'])
        self.assertNotIn('dependency_fingerprint', c)
        self.assertIn('A new USER constraint applies.', '\n'.join(x.get('text', '') for x in c['constraints']))

    def test_proposed_design_view_is_not_old_authorization(self):
        d, ref = self.design()
        checkpoint(self.roots, self.request('DESIGN_COMPLETE', design=ref))
        d['intent'] = 'A revised proposal, not an approved update.'
        proposed = self.write('design/assets/PROPOSED.json', d)
        c = context(self.roots, 'asset', 'prop', task_id='lantern', design=proposed)
        self.assertEqual(c['work_status'], 'CURRENT_CHECKPOINT')
        self.assertIn('proposed design as a new draft', c['next_action'])
        self.assertEqual(c['design'], proposed)


if __name__ == '__main__': unittest.main()
