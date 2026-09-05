from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from factory_core.catalog import factory_dependencies
from factory_core.context import context, inspect
from factory_core.migration import apply, inventory, preview, routed, routing_reference_valid
from factory_core.refs import FactoryError, confined, digest, encoded, read_json, reference, sha
from factory_core.state import checkpoint, dependencies, latest, load_design, requirement_ids, verify_record

ROOT = Path(__file__).resolve().parents[2]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name).resolve() / 'game'
        self.game.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.game)], check=True)
        self.roots = dict(game=self.game, factory=ROOT)
        self.write('AGENTS.md', '# Project\nNever change the bridge mystery.\n')
        self.write('RULES.md', 'No hidden character knowledge.\n')

    def write(self, name, body):
        path = self.game / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded(body) if isinstance(body, dict) else body.encode())
        return reference(self.game, name)

    def migrate(self):
        p = preview(self.game, ROOT, 'fixture', ['RULES.md'])
        apply(self.game, ROOT, 'fixture', p['source_digest'], ['RULES.md'])

    def design(self):
        self.migrate()
        artifact = self.write('design/assets/DESIGN.md', 'The lantern is warm.\nIts alpha border stays transparent.\n')
        d = dict(schema_version='factory_design.v2', design_id='lantern', capability='asset', task='prop',
                 author_context_id='author', intent='A readable lantern, no changed story.', artifacts=[artifact], inputs=[],
                 decisions=[dict(id='light',source=artifact,excerpt='The lantern is warm.',consequence='Its alpha border stays transparent.')],
                 requirements={}, production_scope=['texture/lantern.png'], acceptance=['Engineering alpha validation plus visual review.'])
        ref = self.write('design/assets/PACKAGE.json',d)
        return d, ref

    def request(self, stage='DRAFT', previous=None, **kw):
        return dict(task_id='lantern',previous=previous,capability='asset',task='prop',stage=stage,
                    summary='Full lantern design; no new story.',unresolved=[],artifacts=[],**kw)

    def save_design(self):
        d,ref=self.design()
        out=checkpoint(self.roots,self.request('DESIGN_COMPLETE',design=ref))
        record,_=latest(self.game,'lantern')
        return d,ref,out,record

    def reviews(self,d,ref,binding):
        result=[]
        for role in ('intent_experience','completeness_project'):
            r=dict(schema_version='factory_review.v2',role=role,reviewer_context_id=role,fresh=True,peer_reviews_read=[],design=ref,
                   dependency_fingerprint=binding['fingerprint'],verdict='PASS',
                   findings={key:dict(status='PASS',evidence=[d['artifacts'][0]],rationale='Synthetic fixture satisfies the stated requirement.')
                             for key in requirement_ids(ROOT,d,role)},
                   source_coverage=[r['scope']+':'+r['path'] for r in binding['references'] if r['scope']=='game'],
                   decision_coverage=['light'])
            result.append(self.write(f'design/reviews/{role}.json',r))
        return result

    def test_inspect_unmigrated_is_read_only(self):
        before=list(self.game.rglob('*'))
        self.assertEqual(inspect(self.roots)['status'],'MIGRATION_REQUIRED')
        self.assertEqual(before,list(self.game.rglob('*')))

    def test_migration_preflight_idempotent_history_not_reissued(self):
        self.write('design/studio/STUDIO_DECISION_CARD_REGISTER.json',dict(schema_version='studio_decision_card_register.v1',
            entries=[dict(card_id='one',state='USER_REJECTED'),dict(card_id='two',state='PENDING')]))
        before=inventory(self.game)
        oldsha=sha(self.game/'AGENTS.md')
        self.migrate()
        self.assertEqual(before,inventory(self.game))
        self.assertTrue(routing_reference_valid(self.game,'AGENTS.md',oldsha))
        self.assertEqual(preview(self.game,ROOT,'fixture',['RULES.md'])['status'],'ALREADY_MIGRATED')
        self.assertFalse((self.game/'design/factory/.migration.json').exists())

    def test_migration_concurrent_change_rejected(self):
        p=preview(self.game,ROOT,'fixture')
        self.write('AGENTS.md','# Concurrent user changes\n')
        with self.assertRaisesRegex(FactoryError,'preview/source digest changed'):
            apply(self.game,ROOT,'fixture',p['source_digest'])
        self.assertEqual((self.game/'AGENTS.md').read_text(),'# Concurrent user changes\n')
        self.assertFalse((self.game/'design/factory/PROJECT.json').exists())

    def test_malformed_marker_no_writes(self):
        self.write('AGENTS.md','<!-- game_ai_factory:routing:begin -->')
        with self.assertRaises(FactoryError): preview(self.game,ROOT,'fixture')
        self.assertFalse((self.game/'design/factory').exists())

    def test_migration_recovers_exact_partial_outputs(self):
        p=preview(self.game,ROOT,'fixture')
        from factory_core import migration
        original=migration.exclusive_json
        def crash(path,payload):
            if path.name=='PROJECT.json': raise RuntimeError('crash')
            return original(path,payload)
        with patch.object(migration,'exclusive_json',side_effect=crash):
            with self.assertRaises(RuntimeError): apply(self.game,ROOT,'fixture',p['source_digest'])
        self.assertEqual(preview(self.game,ROOT,'fixture')['status'],'MIGRATION_RECOVERY_REQUIRED')
        self.assertEqual(apply(self.game,ROOT,'fixture',p['source_digest'])['status'],'MIGRATED')

    def test_migration_recovery_preserves_conflicting_partial_output(self):
        p=preview(self.game,ROOT,'fixture')
        from factory_core import migration
        original=migration.exclusive_json
        def crash(path,payload):
            if path.name=='PROJECT.json': raise RuntimeError('crash')
            return original(path,payload)
        with patch.object(migration,'exclusive_json',side_effect=crash):
            with self.assertRaises(RuntimeError): apply(self.game,ROOT,'fixture',p['source_digest'])
        self.write('design/factory/ROUTING_RECEIPT.json',{'user':'concurrent'})
        with self.assertRaises(FactoryError): apply(self.game,ROOT,'fixture',p['source_digest'])
        self.assertEqual(read_json(self.game/'design/factory/ROUTING_RECEIPT.json'),{'user':'concurrent'})
        self.assertFalse((self.game/'design/factory/PROJECT.json').exists())

    def test_path_traversal_and_symlinks_rejected(self):
        for p in ('../outside','/absolute','a/../b','.git/config','a\\b','a//b'):
            with self.assertRaises(FactoryError): confined(self.game,p)
        (self.game/'link').symlink_to(self.game/'RULES.md')
        with self.assertRaises(FactoryError): reference(self.game,'link')

    def test_draft_can_remain_open_no_manufactured_design(self):
        self.migrate()
        req=self.request(); req.update(capability='idea',task='exploration',unresolved=['No fitting direction yet.'])
        checkpoint(self.roots,req)
        record,_=latest(self.game,'lantern')
        self.assertIsNone(record['design'])
        self.assertEqual(record['stage'],'DRAFT')

    def test_stage_skipping_unapproved_execution_fails(self):
        self.migrate()
        with self.assertRaisesRegex(FactoryError,'never approved work'):
            checkpoint(self.roots,self.request('PRODUCING'))

    def test_checkpoint_conflicting_writer_is_rejected(self):
        self.migrate()
        checkpoint(self.roots,self.request())
        with self.assertRaisesRegex(FactoryError,'predecessor changed'):
            checkpoint(self.roots,self.request())

    def test_context_contains_complete_active_authorities(self):
        self.design()
        c=context(self.roots,'asset','prop')
        text='\n'.join(r['text'] for r in c['constraints'])
        self.assertIn('Never change the bridge mystery.',text)
        self.assertIn('No hidden character knowledge.',text)
        self.assertFalse(c['authority'])

    def test_review_context_does_not_include_peer_or_work(self):
        d,ref,out,record=self.save_design()
        self.reviews(d,ref,record['dependencies'])
        c=context(self.roots,'asset','prop','intent_experience','lantern')
        self.assertNotIn('work',c)
        self.assertNotIn('reviews',c)
        self.assertNotIn('Synthetic fixture satisfies',json.dumps(c))
        self.assertEqual(c['dependency_fingerprint'],record['dependencies']['fingerprint'])

    def test_blind_context_returns_no_project_information(self):
        self.design()
        with self.assertRaises(FactoryError) as raised:
            context(self.roots,'asset','prop','blind_observer')
        self.assertEqual(raised.exception.code,'BLIND_CONTEXT_REQUIRES_SANITIZED_PROTOCOL')
        self.assertNotIn('bridge',str(raised.exception))

    def test_irrelevant_file_does_not_invalidate_relevant_does(self):
        d,ref,out,record=self.save_design()
        self.write('unrelated.md','unrelated')
        verify_record(self.roots,record)
        self.write('RULES.md','Different knowledge.')
        with self.assertRaises(FactoryError): verify_record(self.roots,record)

    def test_new_nested_agent_rule_invalidates(self):
        d,ref,out,record=self.save_design()
        self.write('texture/AGENTS.md','New alpha requirement.')
        with self.assertRaises(FactoryError): verify_record(self.roots,record)

    def test_unknown_dependency_cannot_be_ignored(self):
        d,ref=self.design()
        d['inputs']=[dict(scope='unknown',path='missing',sha256='0'*64)]
        ref=self.write('design/assets/PACKAGE.json',d)
        with self.assertRaises(FactoryError): checkpoint(self.roots,self.request('DESIGN_COMPLETE',design=ref))

    def test_reviews_same_exact_version_different_contexts(self):
        d,ref,out,record=self.save_design()
        reviews=self.reviews(d,ref,record['dependencies'])
        reviewed=checkpoint(self.roots,self.request('REVIEWED',out['checkpoint']['sha256'],design=ref,reviews=reviews))
        self.assertEqual(reviewed['stage'],'REVIEWED')
        view=context(self.roots,'asset','prop','human','lantern')
        self.assertEqual(view['decisions'],d['decisions'])
        self.assertFalse(view['authority'])

    def test_author_cannot_review_itself(self):
        d,ref,out,record=self.save_design()
        reviews=self.reviews(d,ref,record['dependencies'])
        payload=read_json(self.game/reviews[0]['path']);payload['reviewer_context_id']='author'
        reviews[0]=self.write(reviews[0]['path'],payload)
        with self.assertRaises(FactoryError) as raised:
            checkpoint(self.roots,self.request('REVIEWED',out['checkpoint']['sha256'],design=ref,reviews=reviews))
        self.assertEqual(raised.exception.code,'REVIEW_NOT_INDEPENDENT')

    def test_peer_review_leak_or_wrong_fingerprint_rejected(self):
        for field,value in [('peer_reviews_read',['peer']),('dependency_fingerprint','0'*64)]:
            with self.subTest(field=field):
                d,ref,out,record=self.save_design() if not (self.game/'design/factory/checkpoints').exists() else self._existing_design()
                reviews=self.reviews(d,ref,record['dependencies'])
                payload=read_json(self.game/reviews[0]['path']);payload[field]=value
                reviews[0]=self.write(reviews[0]['path'],payload)
                with self.assertRaises(FactoryError):
                    checkpoint(self.roots,self.request('REVIEWED',out['checkpoint']['sha256'],design=ref,reviews=reviews))

    def _existing_design(self):
        record,h=latest(self.game,'lantern'); ref=record['design']; d=load_design(self.roots,ref)
        return d,ref,dict(checkpoint=dict(sha256=h)),record

    def test_raw_user_ruling_required_not_context_view(self):
        d,ref,out,record=self.save_design()
        reviews=self.reviews(d,ref,record['dependencies'])
        out=checkpoint(self.roots,self.request('REVIEWED',out['checkpoint']['sha256'],design=ref,reviews=reviews))
        source=self.write('design/rulings/RAW.json',dict(role='assistant',content='I approve.'))
        ruling=self.write('design/rulings/RULING.json',dict(schema_version='factory_ruling.v2',owner='USER',decision='APPROVE',design=ref,
            dependency_fingerprint=record['dependencies']['fingerprint'],source=source,quote='I approve.'))
        with self.assertRaises(FactoryError) as raised:
            checkpoint(self.roots,self.request('AUTHORIZED',out['checkpoint']['sha256'],design=ref,reviews=reviews,ruling=ruling))
        self.assertEqual(raised.exception.code,'INVALID_RULING_SOURCE')

    def test_unreviewed_human_view_blocked(self):
        self.save_design()
        with self.assertRaises(FactoryError): context(self.roots,'asset','prop','human','lantern')

    def test_card_excerpt_cannot_invent_new_decision(self):
        d,ref=self.design();d['decisions'][0]['excerpt']='Add a new boss.'
        ref=self.write('design/assets/PACKAGE.json',d)
        with self.assertRaises(FactoryError):load_design(self.roots,ref)

    def test_factory_dependency_set_is_scoped(self):
        refs=factory_dependencies(ROOT,'sound','sfx')
        paths={r['path'] for r in refs}
        self.assertIn('sound/pipeline/trim.py',paths)
        self.assertNotIn('story/core/craft/quoted-dialogue.md',paths)
        self.assertNotIn('README.md',paths)
        self.assertIn('factory_core/catalog.py',paths)

    def test_rule_map_sources_all_exist(self):
        rules=read_json(ROOT/'factory_core/rule_map.json')['rules']
        self.assertEqual(len(rules),len({r['id'] for r in rules}))
        for rule in rules:self.assertTrue((ROOT/rule['source']).is_file(),rule['source'])


if __name__=='__main__': unittest.main()
