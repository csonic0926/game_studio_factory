"""v2 author/review/production bridge with existing semantic fixtures.

These are synthetic contract tests, not fresh gameplay/human acceptance.
"""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from factory_core.refs import FactoryError, encoded, read_json, reference
from factory_core.migration import preview, apply
from factory_core.state import checkpoint, latest, load_design, requirement_ids
from gameplay.v2 import authorized_objective, legacy
from studio.tests import test_baseline as bf
from gameplay.tests import test_plan as pf
from studio.v2 import validate_acceptance_input

ROOT=Path(__file__).resolve().parents[2]


class GameplayV2Tests(unittest.TestCase):
    def setUp(self):
        self.fixture=bf.BaselineAdmissionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.game=self.fixture.repo.resolve()
        self.roots=dict(game=self.game,factory=ROOT)
        self.template=pf.ProductionPlanValidationTests();self.template.setUp();self.addCleanup(self.template.tearDown)
        manifest=read_json(self.game/self.fixture.cycle_relative)
        graph=read_json(self.game/manifest['gameplay_system']['path'])
        self.author=graph['author_context_id']
        self.system=dict(scope='game',**manifest['gameplay_system'])
        card=read_json(self.game/self.fixture.player_surface_design['unit-one']['card_ref']['path'])
        contract_path=card['player_facing_interaction_contract']['path']
        contract=read_json(self.game/contract_path)
        contract['studio_gameplay_system']=legacy(self.system)
        contract['author_context_id']=self.author
        self.contract=self.write(contract_path,contract)
        self.objective=self.write('design/gameplay/objective_gameplay/unit-one/OBJECTIVE_GAMEPLAY.md',
            self.template.objective_text.replace('mission.next','unit-one').replace('full-spec-author',self.author))
        standard_ref=card['project_card_authoring_standard']
        standard=read_json(self.game/standard_ref['path'])
        self.standard=reference(self.game,standard_ref['path'])
        from gameplay.design_gate import _extract_material_spec
        errors=[];material,_=_extract_material_spec((self.game/self.objective['path']).read_text(),errors)
        self.assertFalse(errors)
        decisions=[];coverage={}
        for index,(key,value) in enumerate(material.items()):
            id=f'decision-{index}'
            decisions.append(dict(id=id,source=self.objective,excerpt=value,consequence=value))
            coverage[key]=[id]
        inputs=[self.standard]+[reference(self.game,c['path']) for c in card['project_composition_artifacts']]
        self.design=dict(schema_version='factory_design.v2',design_id='unit-one',capability='studio',task='objective',
            author_context_id=self.author,intent='Preserve a complete two-lap causal game.',artifacts=[self.objective,self.system,self.contract],inputs=inputs,
            decisions=decisions,requirements={r['requirement_id']:dict(source=self.standard,obligation=r['rule'])
                for r in standard['requirements']},production_scope=['scripts/unit_one.gd'],acceptance=['Exact-build human acceptance plus predecessor regression.'],
            gameplay=dict(objective_id='unit-one',objective=self.objective,system=self.system,interaction_contract=self.contract,
                project_standard=standard_ref,composition_artifacts=card['project_composition_artifacts'],routing='STUDIO_WHOLE_GAME',
                hypothesis_ids=['hypothesis.player-understands'],material_coverage=coverage))
        p=preview(self.game,ROOT,'sample-game');apply(self.game,ROOT,'sample-game',p['source_digest'])
        self.design_ref=self.write('design/gameplay/objective_gameplay/unit-one/FACTORY_DESIGN.json',self.design)

    def write(self,name,body):
        path=self.game/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(encoded(body) if isinstance(body,dict) else body.encode())
        return reference(self.game,name)

    def req(self,stage,previous=None,**kw):
        return dict(task_id='unit-one',previous=previous,capability='studio',task='objective',stage=stage,
            summary='Synthetic contract test only.',unresolved=[],artifacts=[],design=self.design_ref,**kw)

    def authorize(self):
        out=checkpoint(self.roots,self.req('DESIGN_COMPLETE'))
        record,_=latest(self.game,'unit-one');binding=record['dependencies'];refs=[]
        for role in ('intent_experience','completeness_project'):
            refs.append(self.write(f'design/reviews/{role}.json',dict(schema_version='factory_review.v2',role=role,
                reviewer_context_id=role,fresh=True,peer_reviews_read=[],design=self.design_ref,dependency_fingerprint=binding['fingerprint'],verdict='PASS',
                findings={id:dict(status='PASS',evidence=[self.objective],rationale='Synthetic requirement fixture.') for id in requirement_ids(ROOT,self.design,role)},
                source_coverage=[r['scope']+':'+r['path'] for r in binding['references'] if r['scope']!='factory'],
                decision_coverage=[d['id'] for d in self.design['decisions']])) )
        out=checkpoint(self.roots,self.req('REVIEWED',out['checkpoint']['sha256'],reviews=refs))
        from factory_core.state import approval_action
        action=approval_action(self.design_ref,binding)
        raw=self.write('design/rulings/RAW.json',dict(role='user',content=action))
        ruling=self.write('design/rulings/APPROVAL.json',dict(schema_version='factory_ruling.v2',owner='USER',decision='APPROVE',
            design=self.design_ref,dependency_fingerprint=binding['fingerprint'],source=raw,quote=action))
        out=checkpoint(self.roots,self.req('AUTHORIZED',out['checkpoint']['sha256'],reviews=refs,ruling=ruling))
        return out,refs,ruling

    def test_two_reviews_and_same_primary_author_authorize_production(self):
        out,refs,ruling=self.authorize()
        record,d=authorized_objective(self.roots,out['checkpoint'],self.objective['path'],self.objective['sha256'])
        self.assertEqual(record['stage'],'AUTHORIZED')
        self.assertEqual(d['author_context_id'],self.author)

    def test_unrelated_factory_revision_is_only_provenance(self):
        out,refs,ruling=self.authorize()
        with patch('gameplay.design_gate.current_factory_revision',return_value='f'*40):
            from gameplay.design_gate import validate_objective_design_gate
            errors=[]
            result=validate_objective_design_gate(factory_root=ROOT,game_repo=self.game,project_id='sample-game',objective_id='unit-one',
                objective_path_text=self.objective['path'],objective_path=self.game/self.objective['path'],objective_sha256=self.objective['sha256'],
                objective_text=(self.game/self.objective['path']).read_text(),manifest_factory_revision='e'*40,
                raw_verdict_ref=legacy(out['checkpoint']),errors=errors)
        self.assertFalse(errors)
        self.assertEqual(result.human_verdict,'USER_APPROVED')

    def test_missing_project_requirement_fails(self):
        self.design['requirements']={}
        ref=self.write(self.design_ref['path'],self.design)
        with self.assertRaisesRegex(FactoryError,'omits adopted project requirements'):load_design(self.roots,ref)

    def test_missing_human_surface_coverage_fails(self):
        self.design['gameplay']['material_coverage']={}
        ref=self.write(self.design_ref['path'],self.design)
        with self.assertRaisesRegex(FactoryError,'every material'):load_design(self.roots,ref)

    def test_linear_reward_proxy_fails_same_domain_validator(self):
        system=read_json(self.game/self.system['path']);system['feedback_state_ids']=[]
        new=self.write(self.system['path'],system)
        self.design['artifacts']=[new if r==self.system else r for r in self.design['artifacts']]
        self.design['gameplay']['system']=new
        ref=self.write(self.design_ref['path'],self.design)
        with self.assertRaises(FactoryError):load_design(self.roots,ref)

    def test_superseded_authorization_cannot_execute(self):
        out,refs,ruling=self.authorize()
        req=self.req('DRAFT',out['checkpoint']['sha256']);req.pop('design')
        checkpoint(self.roots,req)
        with self.assertRaisesRegex(FactoryError,'current authorized checkpoint'):
            authorized_objective(self.roots,out['checkpoint'],self.objective['path'],self.objective['sha256'])

    def test_full_v2_runtime_chain_is_consumed_without_legacy_review_fabrication(self):
        out,refs,ruling=self.authorize()
        out=checkpoint(self.roots,self.req('PRODUCING',out['checkpoint']['sha256'],reviews=refs,ruling=ruling))
        self.fixture.revision_one=bf._commit(self.game,'V2 authorized synthetic fixture')
        from studio.tests.player_surface_fixture import write_runtime_chain
        chain=write_runtime_chain(self.game,self.game/'design/studio/admissions/v2-test',
            project_id='sample-game',unit_id='unit-one',game_revision=self.fixture.revision_one,build_id='build-one',
            factory_revision=self.fixture.factory_revision,contract_ref=legacy(self.contract),contract_review_ref=legacy(refs[0]),
            card_ref=legacy(self.design_ref),system_ref=legacy(self.system),
            beat_ids=self.fixture.player_surface_design['unit-one']['beat_ids'],hypothesis_ids=['hypothesis.player-understands'])
        req=self.req('EVIDENCE_READY',out['checkpoint']['sha256'],reviews=refs,ruling=ruling)
        req['artifacts']=[dict(scope='game',**r) for r in chain.values()]
        out=checkpoint(self.roots,req)
        cycle=dict(first_lap=dict(decision='Choose starter risk.',resolution='Position resolves.',reward='Opportunity tier rises.'),
            feedback_state_changes=[dict(state_id='opportunity-tier',before='Starter',after='Advanced',effect_on_next_decision='New risk available.')],
            second_lap=dict(changed_goal='Use advanced opportunity.',changed_decision='Choose advanced risk.',reentry_action='Return to choice.'),
            why_player_has_new_motive='Earned tier changes available choice.')
        payload=dict(schema_version='factory_gameplay_acceptance_input.v2',project_id='sample-game',unit_id='unit-one',
            game_revision=self.fixture.revision_one,build_id='build-one',factory_revision=self.fixture.factory_revision,
            checkpoint=out['checkpoint'],experience_authority=legacy(self.objective),studio_gameplay_system=legacy(self.system),cycle_id='choice-reward-cycle',
            cycle_acceptance=cycle,player_facing_evidence=chain,playtest_questions=['Understand?'],non_claims=['Synthetic contract test, not real acceptance.'])
        errors=[]
        result=validate_acceptance_input(self.game,payload,project_id='sample-game',unit_id='unit-one',game_revision=self.fixture.revision_one,
            build_id='build-one',factory_revision=self.fixture.factory_revision,authority_ref=legacy(self.objective),
            product_authority_ref=legacy(reference(self.game,'design/product/PRODUCT_THESIS.md')),production_context_ids={self.author},
            acceptance_reviewer_context_id='runtime-reviewer',errors=errors)
        self.assertFalse(errors,errors)
        self.assertEqual(result['cycle_id'],'choice-reward-cycle')
        # Outer acceptance consumer still requires an exact USER playtest token.
        acceptance_ref=self.fixture._acceptance_review(admission_id='v2-outer',unit_id='unit-one',revision=self.fixture.revision_one,
            build_id='build-one',reviewer='runtime-reviewer',authority=self.objective['path'],evidence='evidence/runtime-one.json')
        review=read_json(self.game/acceptance_ref['path'])
        input_ref=self.write('design/studio/admissions/v2-outer/GAMEPLAY_ACCEPTANCE_INPUT_unit-one.json',payload)
        review['acceptance_input']=legacy(input_ref);review['player_facing_evidence']=chain
        review['evidence_paths']=[legacy(reference(self.game,'evidence/runtime-one.json')),*chain.values()]
        token=bf.human_playtest_payload_sha256(project_id='sample-game',unit_id='unit-one',game_revision=self.fixture.revision_one,
            build_id='build-one',factory_revision=self.fixture.factory_revision,experience_authority=legacy(self.objective),
            acceptance_input=legacy(input_ref),studio_gameplay_system=legacy(self.system),cycle_id='choice-reward-cycle')
        review['human_playtest']['verdict_payload_sha256']=token
        review['human_playtest']['verdict_source']='HUMAN_PLAYTEST_ACCEPTED '+token
        review_ref=self.write(acceptance_ref['path'],review)
        errors=[]
        bf._validate_acceptance_review(self.game,legacy(review_ref),project_id='sample-game',unit_id='unit-one',
            game_revision=self.fixture.revision_one,build_id='build-one',factory_revision='f'*40,
            authority_ref=legacy(self.objective),product_authority_ref=legacy(reference(self.game,'design/product/PRODUCT_THESIS.md')),
            production_context_ids={self.author},allow_legacy_historical=False,errors=errors)
        self.assertFalse(errors,errors)
        # Exercise the complete admission compiler/checker and terminal core
        # checkpoint, not only the inner acceptance-input dispatch.
        admission_path,admission=self.fixture._reconstruction_input('v2-complete')
        admission['admitted_units'][0]['authority']=legacy(self.objective)
        admission['admitted_units'][0]['acceptance_review']=legacy(review_ref)
        inventory_ref=admission['reconstruction']['inventory']
        inventory=read_json(self.game/inventory_ref['path'])
        inventory['source_paths']=[legacy(self.objective)]
        inventory_ref=self.write(inventory_ref['path'],inventory)
        admission['reconstruction']['inventory']=legacy(inventory_ref)
        admission_ref=self.write(admission_path,admission)
        result=bf.compile_baseline_admission(str(self.game),admission_path)
        self.assertEqual(result.status,bf.BASELINE_ADMITTED,result.errors)
        self.assertEqual(bf.check_baseline_admission(str(self.game),admission_path).status,bf.BASELINE_ADMISSION_VALID)
        finish=self.req('COMPLETE',out['checkpoint']['sha256'],reviews=refs,ruling=ruling,acceptance=admission_ref)
        finish['artifacts']=req['artifacts']
        completed=checkpoint(self.roots,finish)
        self.assertEqual(completed['stage'],'COMPLETE')
        from factory_core.state import verify_record
        verify_record(self.roots,latest(self.game,'unit-one')[0])
        review['human_playtest']['verdict_source']='AI says okay'
        review_ref=self.write(acceptance_ref['path'],review);errors=[]
        bf._validate_acceptance_review(self.game,legacy(review_ref),project_id='sample-game',unit_id='unit-one',
            game_revision=self.fixture.revision_one,build_id='build-one',factory_revision='f'*40,
            authority_ref=legacy(self.objective),product_authority_ref=legacy(reference(self.game,'design/product/PRODUCT_THESIS.md')),
            production_context_ids={self.author},allow_legacy_historical=False,errors=errors)
        self.assertTrue(any('exact accepted payload token' in e for e in errors))

    def test_authorized_production_runs_real_godot_ui_state_and_regression(self):
        import shutil,subprocess
        binary=shutil.which('godot') or shutil.which('godot4')
        if not binary:self.skipTest('Godot is unavailable')
        self.write('project.godot','config_version=5\n[application]\nconfig/name="V2 isolated scope test"\n')
        out,refs,ruling=self.authorize()
        out=checkpoint(self.roots,self.req('PRODUCING',out['checkpoint']['sha256'],reviews=refs,ruling=ruling))
        record,d=authorized_objective(self.roots,out['checkpoint'],self.objective['path'],self.objective['sha256'])
        self.assertIn('scripts/unit_one.gd',d['production_scope'])
        script="""extends SceneTree
func _initialize():
    var label = Label.new()
    root.add_child(label)
    var opportunity = 0
    var first_decision = ["safe", "risky"]
    label.text = "Starter opportunity"
    assert(label.text == "Starter opportunity")
    opportunity += 1
    var second_decision = first_decision + ["advanced"] if opportunity > 0 else first_decision
    label.text = "Advanced opportunity"
    assert(second_decision.size() > first_decision.size())
    assert(label.text == "Advanced opportunity")
    print("V2_UI_STATE_REGRESSION_PASS")
    quit(0)
"""
        artifact=self.write('scripts/unit_one.gd',script)
        logs=[]
        for lap in range(2):
            result=subprocess.run([binary,'--headless','--path',str(self.game),'--script','res://scripts/unit_one.gd'],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('V2_UI_STATE_REGRESSION_PASS',result.stdout)
            self.assertNotIn('SCRIPT ERROR',result.stderr)
            logs.append(self.write(f'evidence/godot-{lap}.log',result.stdout+result.stderr))
        request=self.req('EVIDENCE_READY',out['checkpoint']['sha256'],reviews=refs,ruling=ruling)
        request['artifacts']=[artifact,*logs]
        result=checkpoint(self.roots,request)
        self.assertFalse(result['delivery_eligible'])
        self.assertEqual(result['stage'],'EVIDENCE_READY')

    def test_v2_acceptance_does_not_allow_headless_or_missing_blind_chain(self):
        out,refs,ruling=self.authorize()
        out=checkpoint(self.roots,self.req('PRODUCING',out['checkpoint']['sha256'],reviews=refs,ruling=ruling))
        evidence=self.write('evidence/machine.json',dict(status='PASS',claim='not gameplay acceptance'))
        request=self.req('EVIDENCE_READY',out['checkpoint']['sha256'],reviews=refs,ruling=ruling);request['artifacts']=[evidence]
        out=checkpoint(self.roots,request)
        errors=[]
        payload=dict(schema_version='factory_gameplay_acceptance_input.v2',project_id='sample-game',unit_id='unit-one',
            game_revision=self.fixture.revision_one,build_id='build-one',factory_revision=self.fixture.factory_revision,
            checkpoint=out['checkpoint'],experience_authority=legacy(self.objective),studio_gameplay_system=legacy(self.system),cycle_id='choice-reward-cycle',
            cycle_acceptance={},player_facing_evidence={},playtest_questions=['Understand?'],non_claims=['Not a gameplay verdict.'])
        validate_acceptance_input(self.game,payload,project_id='sample-game',unit_id='unit-one',game_revision=self.fixture.revision_one,
            build_id='build-one',factory_revision=self.fixture.factory_revision,authority_ref=legacy(self.objective),
            product_authority_ref=legacy(reference(self.game,'design/product/PRODUCT_THESIS.md')),production_context_ids={self.author},
            acceptance_reviewer_context_id='runtime-reviewer',errors=errors)
        self.assertTrue(errors)


if __name__=='__main__':unittest.main()
