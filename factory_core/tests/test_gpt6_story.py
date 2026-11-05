"""Standalone Story acceptance and branch-memory mechanics, not creative self-grading."""
import copy
import json
import subprocess
import unittest
from unittest.mock import patch

from factory_core.tests import test_core as core
from factory_core import migration_gpt6 as migration
from factory_core.refs import FactoryError, digest, read_json, reference, sha
from factory_core.state import checkpoint, latest, approval_action, requirement_ids, verify_record
from factory_core.context import context
from factory_core.story_profile import resolve
from story.v2 import CHECKS, validate_acceptance
from story.world_state import empty_state, replay_event, npc_view, read_branch, append

ROOT = core.ROOT


class NativeStoryTests(unittest.TestCase):
    setUp = core.CoreTests.setUp
    write = core.CoreTests.write

    def prepare(self):
        self.profile = self.write('design/story/adapter/PROJECT_PROFILE.md',
            '- <PROJECT_ID>: fixture\n- <WORLD_NAME>: Harbour\n- <STORY_ROOT>: narrative\n'
            '- <PRIMARY_LOCALE>: zh-Hant\n- <SHIPPED_LOCALES>: zh-Hant\n- <MEDIUM>: standalone\n')
        self.write('narrative/state/WORLD_RULES.md', 'No telepathy. Knowledge requires observation or communication.\n')
        self.write('narrative/state/NARRATIVE_DELIVERY.md', 'Independent daily-life prose; no runtime engine.\n')
        self.write('design/product/PRODUCT_AUTHORITY_REGISTER.json', {'status': 'NO_ACTIVE_PRODUCT_AUTHORITY'})
        p = migration.preview(self.game, ROOT, 'fixture')
        migration.apply(self.game, ROOT, 'fixture', p['source_digest'])
        body = 'Harbour news travels by witnessed events and conversation. No game runtime or dialogue is produced in this memory-only fixture.'
        source = self.write('narrative/design.md', body)
        self.design = dict(schema_version='factory_design.v3', design_id='harbour', capability='story', task='world', author_context_id='author',
            intent='Branch-scoped memory; synthetic contract test.', artifacts=[source], inputs=[], methods=[],
            decisions=[dict(id='memory', source=source, excerpt=body, consequence=body)],
            decision_sections=[dict(id='memory', source=source, text=body, decision_ids=['memory'])],
            requirements={}, production_scope=['narrative/output.json'], acceptance=['Exact-output knowledge/semantic QA.'],
            story=dict(spoken_output_paths=[], runtime_output_paths=[], scope_evidence=source),
            player_text=dict(scope='NONE', scope_evidence=source, receipt_path=None))
        self.design_ref = self.write('narrative/package.json', self.design)

    def req(self, stage, previous=None, **kw):
        return dict(task_id='harbour', previous=previous, capability='story', task='world', stage=stage,
                    summary='Synthetic no-engine Story test.', unresolved=[], artifacts=[], design=self.design_ref, **kw)

    def authorize(self):
        out = checkpoint(self.roots, self.req('DESIGN_COMPLETE'))
        record, _ = latest(self.game, 'harbour'); binding = record['dependencies']; reviews=[]
        for role in ('intent_experience', 'completeness_project'):
            reviews.append(self.write(f'narrative/{role}.json', dict(schema_version='factory_review.v2', role=role,
                reviewer_context_id=role, fresh=True, peer_reviews_read=[], design=self.design_ref,
                dependency_fingerprint=binding['fingerprint'], verdict='PASS',
                findings={key: dict(status='PASS', evidence=[self.design['artifacts'][0]], rationale='Synthetic fixture; not a human/creative verdict.') for key in requirement_ids(ROOT, self.design, role)},
                source_coverage=[r['scope']+':'+r['path'] for r in binding['references'] if r['scope']!='factory'], decision_coverage=['memory'])))
        out = checkpoint(self.roots, self.req('REVIEWED', out['checkpoint']['sha256'], reviews=reviews))
        action = approval_action(self.design_ref, binding)
        raw = self.write('narrative/synthetic-user.json', dict(role='user', content=action))
        ruling = self.write('narrative/synthetic-ruling.json', dict(schema_version='factory_ruling.v2', owner='USER', decision='APPROVE',
            design=self.design_ref, dependency_fingerprint=binding['fingerprint'], source=raw, quote=action))
        out = checkpoint(self.roots, self.req('AUTHORIZED', out['checkpoint']['sha256'], reviews=reviews, ruling=ruling))
        out = checkpoint(self.roots, self.req('PRODUCING', out['checkpoint']['sha256'], reviews=reviews, ruling=ruling))
        return out, reviews, ruling

    def acceptance(self, record):
        output = record['artifacts'][0]
        scope = self.design['story']['scope_evidence']
        log = self.write('narrative/technical.log', 'Synthetic fixture checker; no engine exists or is claimed.')
        technical = self.write('narrative/technical.json', dict(schema_version='story_technical_evidence.v3', outputs=[output], checks={
            **{name: dict(status='PASS', command='synthetic checker', exit_code=0, log=log) for name in ('style_lint','glossary','locale_integrity')},
            'routing': dict(status='NOT_APPLICABLE', command=None, exit_code=None, log=log, rationale='Reviewed standalone memory-only output.', evidence=[self.profile, scope])}))
        checks = {name:dict(status='PASS', rationale='Synthetic mechanic/coverage test, not creative judgment.', evidence=[self.profile, scope, output]) for name in CHECKS}
        checks['staging_landing_fidelity']['status']='NOT_APPLICABLE'
        return dict(schema_version='story_output_acceptance.v3', design=self.design_ref, dependency_fingerprint=record['dependencies']['fingerprint'],
            outputs=[output], reviewer_context_id='final-semantic', fresh=True, verdict='PASS', checks=checks,
            technical_evidence=[technical], shipped_locales=['zh-Hant'], locale_coverage=['zh-Hant'], cleanroom_evidence=[])

    def test_standalone_full_checkpoint_closure_with_inactive_game_product(self):
        self.prepare()
        profile = resolve(self.game)
        self.assertEqual(profile['medium'], 'standalone')
        c = context(self.roots, 'story', 'world', design=self.design_ref)
        self.assertFalse(any('/core/steps/' in m['source'] for m in c['methods']))
        out, reviews, ruling = self.authorize()
        output = self.write('narrative/output.json', {'memory':'An observed absence, no inferred culprit.'})
        req=self.req('EVIDENCE_READY',out['checkpoint']['sha256'],reviews=reviews,ruling=ruling);req['artifacts']=[output]
        out=checkpoint(self.roots,req);record,_=latest(self.game,'harbour')
        report=self.acceptance(record);ref=self.write('narrative/acceptance.json',report)
        req.update(stage='COMPLETE',previous=out['checkpoint']['sha256'],acceptance=ref)
        result=checkpoint(self.roots,req)
        self.assertEqual(result['stage'],'COMPLETE');self.assertFalse(result['delivery_eligible'])
        self.assertFalse((self.game/'project.godot').exists())

    def test_standalone_profile_can_use_project_root(self):
        self.prepare()
        self.write('state/WORLD_RULES.md', 'No telepathy.')
        self.write('state/NARRATIVE_DELIVERY.md', 'Prose only.')
        body=(self.game / self.profile['path']).read_text().replace('<STORY_ROOT>: narrative', '<STORY_ROOT>: <PROJECT_ROOT>')
        self.write(self.profile['path'], body)
        self.assertEqual(resolve(self.game)['story_root'], self.game)
        from factory_core.context import inspect
        self.assertEqual(inspect(self.roots)['status'], 'INDEPENDENT_STORY_READY')

    def test_semantic_failure_not_excluded_with_runtime(self):
        self.prepare();out,reviews,ruling=self.authorize()
        output=self.write('narrative/output.json',{'wrong':'Sibling meaning omitted.'})
        req=self.req('EVIDENCE_READY',out['checkpoint']['sha256'],reviews=reviews,ruling=ruling);req['artifacts']=[output]
        checkpoint(self.roots,req);record,_=latest(self.game,'harbour')
        report=self.acceptance(record);report['checks']['all_shipped_locale_semantics']['status']='NOT_APPLICABLE'
        with self.assertRaisesRegex(FactoryError,'unresolved finding'):
            validate_acceptance(self.roots,record,self.design,self.write('narrative/acceptance.json',report))

    def test_standalone_cannot_claim_engine_outputs(self):
        self.prepare();self.design['story']['runtime_output_paths']=['narrative/output.json']
        self.design_ref=self.write('narrative/package.json',self.design)
        with self.assertRaisesRegex(FactoryError,'cannot claim engine output'):
            checkpoint(self.roots,self.req('DESIGN_COMPLETE'))

    def entities(self):
        self.write('narrative/story_world/seed_entities.json',{'entities':[{'id':f'npc-{i}','name':f'Person {i}','type':'person'} for i in range(6)]})
        subprocess.run(['git','-C',str(self.game),'add','narrative/story_world/seed_entities.json'],check=True)
        subprocess.run(['git','-C',str(self.game),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Synthetic canonical entity fixture'],check=True)
        revision=subprocess.check_output(['git','-C',str(self.game),'rev-parse','HEAD'],text=True).strip()
        return {**reference(self.game,'narrative/story_world/seed_entities.json','game_git'),'revision':revision}

    def delta(self, entity_ref, id='bell', tick=8, branch='main'):
        return dict(schema_version='story_event_delta.v1',event_id=id,branch=branch,tick=tick,entities=entity_ref,
            facts=[dict(id='bell-missing',statement='The harbour bell is absent.')],
            knowledge=[dict(npc_id='npc-0',fact_id='bell-missing',kind='observed',from_npc=None)],relations=[],base=None)

    def test_multi_day_propagation_restart_and_unrelated_npcs(self):
        self.prepare();entities=self.entities();before=empty_state()
        day1=replay_event(self.roots,before,self.delta(entities))
        self.assertEqual(before,empty_state())
        self.assertEqual(npc_view(day1,'npc-1')['known_facts'],[])
        day2=self.delta(entities,'news',32);day2['facts']=[];day2['knowledge']=[dict(npc_id='npc-1',fact_id='bell-missing',kind='told',from_npc='npc-0')]
        state=replay_event(self.roots,json.loads(json.dumps(day1)),day2)
        self.assertEqual(len(npc_view(state,'npc-1')['known_facts']),1)
        self.assertEqual(npc_view(state,'npc-5')['known_facts'],[])
        self.assertEqual(state['knowledge']['npc-0'],day1['knowledge']['npc-0'])
        with self.assertRaisesRegex(FactoryError,'already occurred'):
            replay_event(self.roots,state,day2)
        self.assertEqual(replay_event(self.roots,day1,day2),state)

    def test_omniscience_unknown_source_clock_and_mutable_canon_rejected(self):
        self.prepare();entities=self.entities();delta=self.delta(entities)
        delta['knowledge'][0].update(kind='told',from_npc='npc-5')
        with self.assertRaisesRegex(FactoryError,'speaker has not acquired'):
            replay_event(self.roots,empty_state(),delta)
        delta=self.delta(entities);delta['entities']=reference(self.game,'narrative/story_world/seed_entities.json')
        with self.assertRaisesRegex(FactoryError,'pinned Git history'):
            replay_event(self.roots,empty_state(),delta)
        state=replay_event(self.roots,empty_state(),self.delta(entities))
        with self.assertRaisesRegex(FactoryError,'backwards'):
            replay_event(self.roots,state,self.delta(entities,'too-early',7))

    def test_branch_isolation_and_unaccepted_publication(self):
        self.prepare();entities=self.entities();root=replay_event(self.roots,empty_state(),self.delta(entities))
        alt=self.delta(entities,'found',32,'alt');alt['facts']=[dict(id='bell-found',statement='The bell lies in the shed.')]
        alt['knowledge']=[dict(npc_id='npc-1',fact_id='bell-found',kind='observed',from_npc=None)]
        changed=replay_event(self.roots,root,alt)
        self.assertNotIn('bell-found',root['facts']);self.assertEqual(npc_view(changed,'npc-0')['known_facts'],npc_view(root,'npc-0')['known_facts'])
        draft=checkpoint(self.roots,self.req('DRAFT'))
        delta_ref=self.write('narrative/output.json',self.delta(entities))
        with self.assertRaisesRegex(FactoryError,'COMPLETE Story'):
            append(self.roots,delta_ref,draft['checkpoint'],None)
        self.assertFalse((self.game/'narrative/story_world/events/main').exists())

    def test_private_relation_requires_acquired_fact_not_merely_involvement(self):
        self.prepare(); entities=self.entities(); delta=self.delta(entities)
        delta['facts']=[dict(id='betrayal-intent', statement='Person 0 secretly plans to betray Person 1.')]
        delta['knowledge']=[dict(npc_id='npc-0',fact_id='betrayal-intent',kind='observed',from_npc=None)]
        delta['relations']=[dict(from_npc='npc-0',to_npc='npc-1',kind='private-attitude',change='Plans betrayal.',fact_id='betrayal-intent')]
        state=replay_event(self.roots,empty_state(),delta)
        self.assertEqual(npc_view(state,'npc-1')['relations'],{})
        self.assertEqual(npc_view(state,'npc-1')['known_facts'],[])
        self.assertEqual(len(npc_view(state,'npc-0')['relations']),1)
        news=self.delta(entities,'confession',32); news['facts']=[]; news['relations']=[]
        news['knowledge']=[dict(npc_id='npc-1',fact_id='betrayal-intent',kind='told',from_npc='npc-0')]
        state=replay_event(self.roots,state,news)
        self.assertEqual(len(npc_view(state,'npc-1')['relations']),1)

    def test_pinned_branch_ancestry_does_not_include_later_parent_events(self):
        self.prepare(); entities=self.entities()
        # Synthetic sealed historical records exercise replay only. append's
        # full current acceptance gate is exercised by the next test.
        def historical(delta, generation, previous=None):
            name=delta['branch']+'-'+delta['event_id']
            ref=self.write('narrative/history/'+name+'.json',delta)
            design=self.write('narrative/history/design-'+name+'.json',{'fixture':'synthetic historical design'})
            report=self.write('narrative/history/qa-'+name+'.json',dict(schema_version='story_output_acceptance.v3',verdict='PASS',outputs=[ref],design=design,dependency_fingerprint='synthetic'))
            accepted=self.write('narrative/history/accepted-'+name+'.json',dict(schema_version='factory_checkpoint.v2',stage='COMPLETE',capability='story',artifacts=[ref],acceptance=report,design=design,dependencies={'fingerprint':'synthetic'}))
            return self.write(f"narrative/story_world/events/{delta['branch']}/{generation:06d}.json",dict(schema_version='story_accepted_event.v1',previous=previous,delta=ref,accepted_checkpoint=accepted))
        base=historical(self.delta(entities),1)
        later=self.delta(entities,'later',50);later['facts']=[dict(id='future',statement='Future parent-only event.')];later['knowledge']=[]
        historical(later,2,base['sha256'])
        child=self.delta(entities,'branch-news',32,'alt');child['facts']=[];child['knowledge']=[dict(npc_id='npc-1',fact_id='bell-missing',kind='told',from_npc='npc-0')]
        child['base']={'branch':'main','event':base};historical(child,1)
        branch,_=read_branch(self.roots,'alt');parent,_=read_branch(self.roots,'main')
        self.assertNotIn('future',branch['facts']);self.assertIn('future',parent['facts'])
        self.assertEqual(npc_view(parent,'npc-1')['known_facts'],[])
        self.assertEqual(len(npc_view(branch,'npc-1')['known_facts']),1)

    def test_accepted_event_append_replay_and_idempotence(self):
        self.prepare();entities=self.entities();out,reviews,ruling=self.authorize()
        output=self.write('narrative/output.json',self.delta(entities))
        req=self.req('EVIDENCE_READY',out['checkpoint']['sha256'],reviews=reviews,ruling=ruling);req['artifacts']=[output]
        out=checkpoint(self.roots,req);record,_=latest(self.game,'harbour')
        ref=self.write('narrative/acceptance.json',self.acceptance(record));req.update(stage='COMPLETE',previous=out['checkpoint']['sha256'],acceptance=ref)
        done=checkpoint(self.roots,req)
        result=append(self.roots,output,done['checkpoint'],None)
        state,head=read_branch(self.roots,'main')
        self.assertEqual(head,result['event']['sha256']);self.assertEqual(len(npc_view(state,'npc-0')['known_facts']),1)
        self.assertEqual(append(self.roots,output,done['checkpoint'],None)['status'],'ALREADY_APPLIED')
        verify_record(self.roots,latest(self.game,'harbour')[0])


if __name__=='__main__':unittest.main()
