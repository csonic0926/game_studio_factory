"""Synthetic contract cases. These tests do not measure real player value."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from factory_core.refs import FactoryError, digest, encoded, read_json, reference
from factory_core.state import checkpoint, latest, load_design, requirement_ids, approval_action
from product import value

ROOT = Path(__file__).resolve().parents[2]


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name).resolve() / 'game'
        self.game.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.game)], check=True)
        self.roots = dict(game=self.game, factory=ROOT)
        self.write('AGENTS.md', '# User requirements\nA focused complete experience.\n')
        self.build = self.write('build.bin', 'Exact synthetic runnable artifact.\n')
        self.source = self.write('offer.md', 'Synthetic current $1.99 USD US desktop offer, observed 2026-10-09.\n')
        self.player = self.write('experience.md', 'Synthetic observation: actual action, response and satisfying conclusion.\n')

    def write(self, path, body):
        dest = self.game / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(encoded(body) if isinstance(body, dict) else body.encode())
        return reference(self.game, path)

    def assessment(self, identity='offer-one', judgment='SUPPORTED', offer='CURRENT_OFFER', amount='1.99'):
        owned = value.paths(identity)
        report = self.write(owned['report'], 'Synthetic reasoned case: the small coherent experience fulfills this buyer promise.\n')
        a = dict(schema_version='product_value_assessment.v1', assessment_id=identity, author_context_id='author',
                 subject=dict(title='Synthetic game', build=self.build),
                 offer=dict(status=offer, grounding='GROUNDED', amount=amount, currency='USD', platform='desktop', region='US',
                            as_of='2026-10-09', provenance=[self.source], adoption=None, rationale='Synthetic source establishes this scoped offer.'),
                 audience=dict(grounding='GROUNDED', description='Buyers seeking a concise completed experience',
                               provenance=[self.source], rationale='Synthetic grounded buyer context.'),
                 report=report, evidence=[dict(id='play', kind='EXPERIENCE', reference=self.player, build=self.build,
                                             observation='Synthetic full value-bearing experience observed.', limitations='No sales forecast is proven.')],
                 judgment=judgment, material_unknowns=[], conditionality=[],
                 next_move=dict(action='Preserve the focused experience', owner='Studio', reason='No material value gap in this fixture',
                                what_would_change_judgment='Contrary representative play evidence'))
        if offer == 'ADOPTED_OFFER':
            quote='Set the actual product price to '+amount+' USD for the US desktop offer.'
            source=self.write('adopted-offer.json',dict(role='user',content=quote))
            a['offer'].update(adoption=dict(source=source,quote=quote),provenance=[self.source,source])
        self.write(owned['input'], a)
        return a

    def save(self, a):
        return self.write(value.paths(a['assessment_id'])['input'], a)

    def reviews(self, a):
        p = value.prepare(self.roots, value.paths(a['assessment_id'])['input'])
        result = []
        for role in value.ROLES:
            r = dict(schema_version='product_value_review.v1', role=role, reviewer_context_id=role, fresh=True, peer_reviews_read=[],
                     assessment=p['assessment'], dependency_fingerprint=p['dependencies']['fingerprint'], verdict='AGREE',
                     findings={k:dict(rationale='Synthetic contract finding, not a real value review.', evidence=[a['report']]) for k in value.FINDINGS},
                     source_coverage=[digest(ref) for ref in p['dependencies']['references'] if ref['scope'] != 'factory'])
            path = f"design/product_value/{a['assessment_id']}/reviews/{role}.json"
            self.write(path, r)
            result.append(path)
        return result

    def record(self, a=None):
        a = a or self.assessment()
        out = value.record(self.roots, value.paths(a['assessment_id'])['input'], self.reviews(a))
        return a, out

    def test_standalone_legacy_inspect_is_read_only_no_migration(self):
        before = sorted(str(p) for p in self.game.rglob('*'))
        result = value.inspect(self.roots)
        self.assertEqual(result['authority']['status'], value.NO_ACTIVE)
        self.assertFalse(result['authority']['register_exists'])
        self.assertFalse(result['authority']['claim_blocked'])
        self.assertEqual(before, sorted(str(p) for p in self.game.rglob('*')))
        self.assertFalse((self.game/'design/factory/PROJECT.json').exists())

    def test_short_premium_and_low_price_small_cases_have_no_hours_or_feature_floor(self):
        for identity, amount in [('short-premium','19.99'), ('small-affordable','0.99')]:
            with self.subTest(identity=identity):
                a, out = self.record(self.assessment(identity, amount=amount))
                gate = value.gate(self.roots, out['result']['path'], 'build.bin')
                self.assertTrue(gate['ok'])
                self.assertEqual(gate['claim_scope']['offer']['amount'], amount)
                self.assertFalse(gate['user_accepted'])
                self.assertFalse(gate['delivery_eligible'])

    def test_good_premise_weak_purchase_and_expensive_art_can_record_negative(self):
        for identity, verdict in [('good-premise-poor-value','VALUE_GAP'), ('expensive-art-empty-play','VALUE_GAP'),
                                  ('opening-unseen-ending','EVIDENCE_INSUFFICIENT')]:
            with self.subTest(identity=identity):
                a, out = self.record(self.assessment(identity, verdict))
                self.assertEqual(out['mechanical_status'], 'RECORD_VALID')
                self.assertEqual(value.check(self.roots, out['result']['path'])['judgment'], verdict)
                self.assertFalse(value.gate(self.roots, out['result']['path'], 'build.bin')['ok'])

    def test_unknown_context_is_explicit_and_cannot_support(self):
        a = self.assessment(judgment='CONTEXT_UNRESOLVED')
        a['offer'].update(status='UNKNOWN', grounding='UNKNOWN', amount=None, currency=None, provenance=[])
        a['audience'].update(grounding='UNKNOWN', provenance=[])
        a['evidence'] = []
        a['subject']['build'] = None
        self.save(a)
        _, out = self.record(a)
        self.assertFalse(out['value_claim_eligible'])
        a['judgment'] = 'SUPPORTED'; self.save(a)
        with self.assertRaisesRegex(FactoryError, 'unknown offer/audience'):
            value.prepare(self.roots, value.paths(a['assessment_id'])['input'])

    def test_grounded_user_proposal_and_scenario_never_gate_as_current(self):
        for status in ('PROPOSED_OFFER','SCENARIO'):
            a, out = self.record(self.assessment(status.lower(), offer=status, amount='5'))
            g = value.gate(self.roots, out['result']['path'], 'build.bin')
            self.assertFalse(g['ok'])
            self.assertEqual(g['claim_scope']['offer']['status'], status)
            self.assertEqual(g['claim_scope']['offer']['provenance'], [self.source])
            self.assertEqual(g['claim_scope']['offer']['amount'], '5')

    def test_explicit_adopted_offer_can_gate_but_conditionality_blocks(self):
        _, out = self.record(self.assessment('adopted', offer='ADOPTED_OFFER'))
        self.assertTrue(value.gate(self.roots, out['result']['path'], 'build.bin')['ok'])
        a = self.assessment('conditional', offer='ADOPTED_OFFER'); a['conditionality']=['Only if this buyer scenario is confirmed']; self.save(a)
        _, out = self.record(a)
        self.assertFalse(value.gate(self.roots, out['result']['path'], 'build.bin')['ok'])

    def test_unobserved_central_promise_blocks_support(self):
        a = self.assessment(); a['material_unknowns']=['No experience of the central replay promise']; self.save(a)
        with self.assertRaisesRegex(FactoryError,'untested material promises'):
            value.prepare(self.roots, value.paths(a['assessment_id'])['input'])

    def test_tests_and_screenshots_alone_are_not_experience(self):
        for kind in ('TEST','VISUAL','AUDIO','SOURCE'):
            a = self.assessment(); a['evidence'][0]['kind'] = kind; self.save(a)
            with self.assertRaisesRegex(FactoryError,'actual build-bound experience'):
                value.prepare(self.roots, value.paths(a['assessment_id'])['input'])

    def test_wrong_evidence_build_and_requested_build_block(self):
        another = self.write('other.bin','Different synthetic build')
        a = self.assessment(); a['evidence'][0]['build'] = another; self.save(a)
        with self.assertRaisesRegex(FactoryError,'assessed exact build'):
            value.prepare(self.roots, value.paths(a['assessment_id'])['input'])
        _, out = self.record(self.assessment())
        self.assertFalse(value.gate(self.roots, out['result']['path'], 'other.bin')['ok'])

    def test_changed_external_capture_or_build_stales_result(self):
        for changed in ('offer.md','build.bin','experience.md'):
            with self.subTest(changed=changed):
                a, out = self.record(self.assessment(changed.replace('.','-')))
                original=(self.game/changed).read_bytes(); (self.game/changed).write_text('Changed')
                with self.assertRaises(FactoryError): value.check(self.roots,out['result']['path'])
                (self.game/changed).write_bytes(original)

    def test_new_mandatory_authority_stales_reviews(self):
        a, out = self.record()
        self.write('nested/AGENTS.md', 'New material user boundary')
        with self.assertRaisesRegex(FactoryError,'exact current assessment'):
            value.check(self.roots, out['result']['path'])

    def test_unrelated_file_and_git_commit_do_not_stale_frozen_build(self):
        _, out = self.record()
        self.write('unrelated.txt','Unrelated work')
        subprocess.run(['git','-C',str(self.game),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.game),'-c','user.name=Synthetic','-c','user.email=fixture@localhost','commit','-qm','fixture'],check=True)
        self.assertTrue(value.check(self.roots,out['result']['path'])['value_claim_eligible'])

    def test_self_peer_same_context_missing_coverage_and_rejection_block(self):
        mutations = [lambda r:r.update(reviewer_context_id='author'), lambda r:r.update(peer_reviews_read=['peer']),
                     lambda r:r.update(fresh=False), lambda r:r.update(source_coverage=[]), lambda r:r.update(verdict='REVISE')]
        for mutation in mutations:
            a=self.assessment(); reviews=self.reviews(a); r=read_json(self.game/reviews[0]); mutation(r); self.write(reviews[0],r)
            with self.assertRaises(FactoryError): value.record(self.roots,value.paths(a['assessment_id'])['input'],reviews)
            self.assertFalse((self.game/value.paths(a['assessment_id'])['result']).exists())
        a=self.assessment(); reviews=self.reviews(a); r=read_json(self.game/reviews[1]); r['reviewer_context_id']=value.ROLES[0]; self.write(reviews[1],r)
        with self.assertRaisesRegex(FactoryError,'distinct required roles'): value.record(self.roots,value.paths(a['assessment_id'])['input'],reviews)

    def test_idempotent_and_immutable_result(self):
        a, out = self.record(); before=(self.game/out['result']['path']).read_bytes()
        value.record(self.roots,value.paths(a['assessment_id'])['input'],self.reviews(a))
        self.assertEqual(before,(self.game/out['result']['path']).read_bytes())
        a['judgment']='VALUE_GAP'; self.save(a)
        with self.assertRaisesRegex(FactoryError,'existing result differs'):
            value.record(self.roots,value.paths(a['assessment_id'])['input'],self.reviews(a))
        self.assertEqual(before,(self.game/out['result']['path']).read_bytes())

    def test_symlink_path_escape_and_factory_output_are_rejected(self):
        a=self.assessment(); (self.game/'escape').symlink_to(self.game/'offer.md')
        for path in ('../outside','/etc/passwd','escape'):
            a['offer']['provenance']=[dict(scope='game',path=path,sha256='0'*64)];self.save(a)
            with self.assertRaises(FactoryError): value.prepare(self.roots,value.paths(a['assessment_id'])['input'])

    def test_concurrent_change_prevents_result_publication(self):
        a=self.assessment(); reviews=self.reviews(a); original=value._expected; count=0
        def changed(*args):
            nonlocal count
            count+=1
            out=original(*args)
            if count==1:self.write('offer.md','Concurrent price change')
            return out
        with patch.object(value,'_expected',side_effect=changed):
            with self.assertRaises(FactoryError):value.record(self.roots,value.paths(a['assessment_id'])['input'],reviews)
        self.assertFalse((self.game/value.paths(a['assessment_id'])['result']).exists())

    def test_partial_authority_blocks_claim_without_preventing_diagnostic_record(self):
        self.write('design/product/PRODUCT_THESIS.md','Incomplete old authority')
        _, out=self.record()
        self.assertEqual(out['authority']['status'],value.BLOCKED)
        self.assertFalse(out['value_claim_eligible'])

    def test_cli_and_studio_consumer_preserve_scope(self):
        _, out=self.record(self.assessment(offer='PROPOSED_OFFER'))
        for script, command in [('product/product.py','gate'),('studio/product.py','check-value')]:
            run=subprocess.run(['python3',str(ROOT/script),command,'--game-repo',str(self.game),'--result',out['result']['path'],'--build','build.bin'],capture_output=True,text=True)
            self.assertEqual(run.returncode,2,run.stderr)
            self.assertEqual(json.loads(run.stdout)['claim_scope']['offer']['status'],'PROPOSED_OFFER')

    def test_all_schema_files_are_valid_and_fixture_matches(self):
        import jsonschema
        for path in (ROOT/'product/schemas').glob('*.json'):
            jsonschema.Draft202012Validator.check_schema(read_json(path))
        a,out=self.record()
        jsonschema.validate(a,read_json(ROOT/'product/schemas/assessment.schema.json'))
        jsonschema.validate(read_json(self.game/out['result']['path']),read_json(ROOT/'product/schemas/result.schema.json'))
        for ref in out['reviews']:jsonschema.validate(read_json(self.game/ref['path']),read_json(ROOT/'product/schemas/review.schema.json'))

    def shared(self, workflow=2):
        if workflow==2:
            from factory_core.migration import preview, apply
        else:
            from factory_core.migration_gpt6 import preview, apply
        p=preview(self.game,ROOT,'fixture');apply(self.game,ROOT,'fixture',p['source_digest'])
        a=self.assessment(); owned=value.paths(a['assessment_id'])
        artifact=self.write('design/value-plan.md','Assess this exact buyer offer.\nDo not change the product to pass.\n')
        d=dict(schema_version=f'factory_design.v{workflow}',design_id='value-plan',capability='product',task='assessment',author_context_id='plan-author',intent='Assess the exact whole product',artifacts=[artifact],inputs=[self.build],decisions=[dict(id='scope',source=artifact,excerpt='Assess this exact buyer offer.',consequence='Do not change the product to pass.')],requirements={},production_scope=list(owned.values()),acceptance=['Complete the exact assessment, not product acceptance'],product=dict(assessment_id=a['assessment_id'],subject=a['subject'],offer=a['offer'],audience=a['audience'],result_path=owned['result'],required_output_paths=list(owned.values())))
        if workflow==3:d.update(methods=[],decision_sections=[dict(id='scope',source=artifact,text='Assess this exact buyer offer.\nDo not change the product to pass.\n',decision_ids=['scope'])])
        ref=self.write('design/value-plan.json',d)
        return a,d,ref

    def advance(self,a,d,ref, *, omitted=(), value_reviewer_context=None):
        req=dict(task_id='value-task',previous=None,capability='product',task='assessment',stage='DESIGN_COMPLETE',summary='Synthetic contract case only',unresolved=[],artifacts=[],design=ref)
        out=checkpoint(self.roots,req); rec,_=latest(self.game,'value-task'); binding=rec['dependencies']
        reviews=[]
        for role in value.ROLES:
            r=dict(schema_version='factory_review.v2',role=role,reviewer_context_id='plan-'+role,fresh=True,peer_reviews_read=[],design=ref,dependency_fingerprint=binding['fingerprint'],verdict='PASS',findings={k:dict(status='PASS',evidence=[d['artifacts'][0]],rationale='Synthetic fixture only') for k in requirement_ids(ROOT,d,role)},source_coverage=[r['scope']+':'+r['path'] for r in binding['references'] if r['scope']!='factory'],decision_coverage=['scope'])
            reviews.append(self.write('design/'+role+'.json',r))
        req.update(previous=out['checkpoint']['sha256'],stage='REVIEWED',reviews=reviews);out=checkpoint(self.roots,req)
        action=approval_action(ref,binding);source=self.write('design/synthetic-user.json',dict(role='user',content=action))
        ruling=self.write('design/synthetic-ruling.json',dict(schema_version='factory_ruling.v2',owner='USER',decision='APPROVE',design=ref,dependency_fingerprint=binding['fingerprint'],source=source,quote=action))
        for stage in ('AUTHORIZED','PRODUCING'):
            req.update(previous=out['checkpoint']['sha256'],stage=stage,ruling=ruling);out=checkpoint(self.roots,req)
        value_reviews=self.reviews(a)
        if value_reviewer_context:
            r=read_json(self.game/value_reviews[0]);r['reviewer_context_id']=value_reviewer_context;self.write(value_reviews[0],r)
        result=value.record(self.roots,value.paths(a['assessment_id'])['input'],value_reviews)
        artifacts=[reference(self.game,p) for p in d['product']['required_output_paths']]
        req.update(previous=out['checkpoint']['sha256'],stage='EVIDENCE_READY',artifacts=[r for r in artifacts if r['path'] not in omitted]);out=checkpoint(self.roots,req)
        req.update(previous=out['checkpoint']['sha256'],stage='COMPLETE',artifacts=artifacts,acceptance=result['result'])
        return req,result

    def test_full_v2_product_completion_is_assessment_not_game_acceptance(self):
        a,d,ref=self.shared();req,result=self.advance(a,d,ref)
        self.assertEqual(checkpoint(self.roots,req)['stage'],'COMPLETE')
        self.assertFalse(result['user_accepted'])

    def test_full_v3_negative_product_completion_and_context(self):
        from factory_core.context import context
        a,d,ref=self.shared(3);a['judgment']='VALUE_GAP';self.save(a)
        req,result=self.advance(a,d,ref)
        self.assertEqual(checkpoint(self.roots,req)['stage'],'COMPLETE')
        self.assertFalse(result['value_claim_eligible'])
        self.assertTrue(any('product/schemas' in r['path'] for r in context(self.roots,'product','assessment')['contracts']))

    def test_missing_evidence_ready_output_cannot_be_added_late_at_complete(self):
        a,d,ref=self.shared();req,result=self.advance(a,d,ref,omitted=[value.paths(a['assessment_id'])['report']])
        with self.assertRaisesRegex(FactoryError,'already be in EVIDENCE_READY'):checkpoint(self.roots,req)

    def test_valid_unrelated_result_cannot_substitute_at_complete(self):
        a,d,ref=self.shared();req,result=self.advance(a,d,ref)
        _,other=self.record(self.assessment('other-assessment'))
        req['acceptance']=other['result'];req['artifacts'].append(other['result'])
        with self.assertRaisesRegex(FactoryError,'expected result path'):checkpoint(self.roots,req)

    def test_product_binding_fields_and_scope_checked_by_state(self):
        a,d,ref=self.shared()
        mutations=[lambda d:d.pop('product'), lambda d:d['product'].update(assessment_id='other'),lambda d:d['product'].update(result_path='different.json'),lambda d:d['product'].update(required_output_paths=[]),lambda d:d.update(production_scope=[value.paths(a['assessment_id'])['result']]),lambda d:d['product']['offer'].update(grounding='made-up'),lambda d:d['product']['audience'].update(grounding='made-up'),lambda d:d['product']['subject'].update(extra='forbidden'),lambda d:d.update(capability='asset')]
        for mutation in mutations:
            changed=copy.deepcopy(d);mutation(changed);changed_ref=self.write('design/bad-plan.json',changed)
            with self.subTest(mutation=repr(mutation)):
                with self.assertRaises(FactoryError):load_design(self.roots,changed_ref)

    def test_each_sealed_context_field_rejects_a_different_valid_result(self):
        # Direct adapter cases preserve the actual ledger and then alter the
        # proposed expected binding. Real state.load_design additionally seals
        # this data in reviews/ruling; neither layer silently substitutes context.
        a,d,ref=self.shared();req,result=self.advance(a,d,ref)
        mutations=[lambda b:b.update(assessment_id='another'),lambda b:b['subject'].update(title='Other title'),lambda b:b['subject'].update(build=None),lambda b:b['offer'].update(amount='9.99'),lambda b:b['offer'].update(currency='EUR'),lambda b:b['offer'].update(platform='mobile'),lambda b:b['offer'].update(region='HK'),lambda b:b['audience'].update(description='Different buyers')]
        for mutation in mutations:
            changed=copy.deepcopy(d);mutation(changed['product'])
            with self.assertRaises(FactoryError):value.validate_acceptance(self.roots,req,changed,result['result'])


    def canonical_authority(self, status=None):
        files = {}
        for key,path in [('product_thesis','design/product/PRODUCT_THESIS.md'),('factory_constraints','design/product/FACTORY_CONSTRAINTS.json'),('product_input','design/product/idea/PRODUCT_THESIS_INPUT.json'),('idea_result','design/product/idea/IDEA_FACTORY_RESULT.json')]:
            ref=self.write(path, {'schema_version':'synthetic-authority-fixture','note':'contract test only'} if path.endswith('.json') else 'Synthetic adopted product authority')
            files[key]={k:v for k,v in ref.items() if k!='scope'}
        if status is not None:
            active = dict(authority_id='synthetic', **files, activated_at='2026-10-09') if status==value.ACTIVE else None
            self.write('design/product/PRODUCT_AUTHORITY_REGISTER.json',dict(schema_version='product_authority_register.v1',project_id='fixture',status=status,active_authority=active,transitions=[],updated_at='2026-10-09'))

    def test_legacy_active_and_active_authority_remain_distinct(self):
        self.canonical_authority()
        _,out=self.record(self.assessment('legacy'))
        self.assertEqual(out['authority']['status'],value.LEGACY_ACTIVE)
        self.assertTrue(out['value_claim_eligible'])
        self.canonical_authority(value.ACTIVE)
        _,out=self.record(self.assessment('active'))
        self.assertEqual(out['authority']['status'],value.ACTIVE)
        self.assertTrue(out['value_claim_eligible'])

    def test_archive_blocks_new_claim_and_invalidates_prior_current_result(self):
        self.canonical_authority(value.ACTIVE)
        _,out=self.record(self.assessment('before-archive'))
        self.canonical_authority(value.NO_ACTIVE)
        with self.assertRaises(FactoryError): value.check(self.roots,out['result']['path'])
        _,out=self.record(self.assessment('archived-history'))
        self.assertTrue(out['authority']['claim_blocked'])
        self.assertFalse(value.gate(self.roots,out['result']['path'],'build.bin')['ok'])

    def test_stale_active_authority_refs_fail_closed(self):
        self.canonical_authority(value.ACTIVE)
        self.write('design/product/PRODUCT_THESIS.md','Changed active authority outside lifecycle')
        with self.assertRaises(FactoryError): self.record()

    def test_complete_must_keep_required_evidence_outputs(self):
        a,d,ref=self.shared();req,result=self.advance(a,d,ref)
        req['artifacts']=[result['result']]
        with self.assertRaisesRegex(FactoryError,'already be in EVIDENCE_READY'):checkpoint(self.roots,req)

    def test_result_cannot_first_appear_at_complete(self):
        a,d,ref=self.shared();req,result=self.advance(a,d,ref,omitted=[value.paths(a['assessment_id'])['result']])
        with self.assertRaisesRegex(FactoryError,'already be in EVIDENCE_READY'):checkpoint(self.roots,req)

    def test_output_reviewer_cannot_reuse_plan_author_or_design_reviewer(self):
        a,d,ref=self.shared();req,result=self.advance(a,d,ref,value_reviewer_context='plan-author')
        with self.assertRaisesRegex(FactoryError,'fresh from task author'):checkpoint(self.roots,req)

    def test_adopted_offer_needs_auditable_raw_user_quote(self):
        a=self.assessment();a['offer']['status']='ADOPTED_OFFER';self.save(a)
        with self.assertRaises(FactoryError):value.prepare(self.roots,value.paths(a['assessment_id'])['input'])
        a=self.assessment(offer='ADOPTED_OFFER');a['offer']['adoption']['quote']='An invented adoption';self.save(a)
        with self.assertRaisesRegex(FactoryError,'exact quote'):value.prepare(self.roots,value.paths(a['assessment_id'])['input'])


    def test_legacy_canonical_input_and_result_changes_invalidate_claim(self):
        self.canonical_authority()
        _,out=self.record(self.assessment('legacy-canonical-closure'))
        canonical=('design/product/idea/PRODUCT_THESIS_INPUT.json','design/product/idea/IDEA_FACTORY_RESULT.json')
        bound={ref['path'] for ref in out['dependencies']['references'] if ref['scope']=='game'}
        self.assertTrue(set(canonical).issubset(bound))
        for path in canonical:
            with self.subTest(path=path):
                original=(self.game/path).read_bytes()
                self.write(path,dict(schema_version='synthetic-authority-fixture',note='Changed adopted authority provenance'))
                with self.assertRaises(FactoryError):value.gate(self.roots,out['result']['path'],'build.bin')
                (self.game/path).write_bytes(original)
        self.assertTrue(value.gate(self.roots,out['result']['path'],'build.bin')['ok'])

    def test_legacy_canonical_removal_or_new_presence_invalidates_claim(self):
        canonical=('design/product/idea/PRODUCT_THESIS_INPUT.json','design/product/idea/IDEA_FACTORY_RESULT.json')
        self.canonical_authority()
        for index,path in enumerate(canonical):
            with self.subTest(path=path):
                _,out=self.record(self.assessment('before-remove-'+str(index)))
                old=(self.game/path).read_bytes();(self.game/path).unlink()
                with self.assertRaises(FactoryError):value.gate(self.roots,out['result']['path'],'build.bin')
                _,partial=self.record(self.assessment('partial-'+str(index)))
                self.assertFalse(partial['value_claim_eligible'])
                (self.game/path).write_bytes(old)
                with self.assertRaises(FactoryError):value.gate(self.roots,partial['result']['path'],'build.bin')

    def test_legacy_canonical_input_and_result_symlinks_fail_closed(self):
        self.canonical_authority()
        for path in ('design/product/idea/PRODUCT_THESIS_INPUT.json','design/product/idea/IDEA_FACTORY_RESULT.json'):
            with self.subTest(path=path):
                original=(self.game/path).read_bytes();(self.game/path).unlink();(self.game/path).symlink_to(self.game/'offer.md')
                a=self.assessment()
                with self.assertRaises(FactoryError):value.prepare(self.roots,value.paths(a['assessment_id'])['input'])
                (self.game/path).unlink();(self.game/path).write_bytes(original)

if __name__=='__main__':unittest.main()
