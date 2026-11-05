"""The native design reaches existing production/runtime/admission consumers."""
import json
import unittest

from factory_core.tests import test_gameplay_v2 as legacy_tests
from factory_core import migration_gpt6 as migration
from factory_core.refs import FactoryError, read_json, reference
from factory_core.state import load_design
from gameplay.native import REQUIRED_SECTIONS, production_units


class NativeGameplayTests(unittest.TestCase):
    write = legacy_tests.GameplayV2Tests.write
    req = legacy_tests.GameplayV2Tests.req
    authorize = legacy_tests.GameplayV2Tests.authorize

    def setUp(self):
        legacy_tests.GameplayV2Tests.setUp(self)
        p=migration.preview(self.game,legacy_tests.ROOT,'sample-game')
        migration.apply(self.game,legacy_tests.ROOT,'sample-game',p['source_digest'])
        sections={name:f'{name}: unit-one preserves the source project obligations; this is a synthetic native consumer fixture.' for name in sorted(REQUIRED_SECTIONS)}
        body='\n\n'.join(sections.values())+'\n'
        old=self.objective;self.objective=self.write(old['path'],body)
        self.design['artifacts']=[self.objective if r==old else r for r in self.design['artifacts']]
        self.design['schema_version']='factory_design.v3';self.design['methods']=[]
        # This synthetic fixture exercises unchanged pre-existing UI copy, not a language verdict.
        self.design['player_text']=dict(scope='NONE',scope_evidence=self.objective,receipt_path=None)
        self.design['gameplay']['objective']=self.objective
        self.design['decisions']=[dict(id=name,source=self.objective,excerpt=text,consequence=text) for name,text in sections.items()]
        self.design['decision_sections']=[dict(id=name,source=self.objective,text=text,decision_ids=[name]) for name,text in sections.items()]
        self.design['gameplay']['material_coverage']={name:[name] for name in sections}
        self.design_ref=self.write(self.design_ref['path'],self.design)

    test_native_authorized_production = legacy_tests.GameplayV2Tests.test_two_reviews_and_same_primary_author_authorize_production
    test_native_runtime_through_complete_baseline_and_missing_human_rejected = legacy_tests.GameplayV2Tests.test_full_v2_runtime_chain_is_consumed_without_legacy_review_fabrication
    test_native_godot_ui_state_and_repeated_regression = legacy_tests.GameplayV2Tests.test_authorized_production_runs_real_godot_ui_state_and_regression
    test_superseded_native_authorization_rejected = legacy_tests.GameplayV2Tests.test_superseded_authorization_cannot_execute

    def test_missing_scene_and_time_human_sections_rejected(self):
        self.design['decision_sections']=[s for s in self.design['decision_sections'] if s['id']!='scene-map']
        self.design['decisions']=[d for d in self.design['decisions'] if d['id']!='scene-map']
        self.design['gameplay']['material_coverage'].pop('scene-map')
        with self.assertRaisesRegex(FactoryError,'scene-map'):
            load_design(self.roots,self.write(self.design_ref['path'],self.design))

    def test_native_plan_rows_derive_from_beats_without_markdown_table(self):
        out,_,_=self.authorize()
        from gameplay.plan import validate_production_plan
        from gameplay.v2 import legacy
        rows=[r['row'] for r in production_units(self.roots,self.design)]
        template=self.template
        manifest=read_json(template.game_repo/template.manifest_relative)
        relative='design/gameplay/objective_gameplay/unit-one/PRODUCTION_PLAN_MANIFEST.json'
        plan_path='design/gameplay/objective_gameplay/unit-one/production_plans/P01_gate.md'
        manifest.update(project_id='sample-game',objective_id='unit-one',objective_gameplay_path=self.objective['path'],
            objective_gameplay_sha256=self.objective['sha256'],design_verdict=legacy(out['checkpoint']))
        manifest['plans'][0].update(path=plan_path,objective_rows=rows,planned_paths=['scripts/unit_one.gd'])
        manifest['plans'][0]['existing_repo_refs']=['evidence/runtime-one.json']
        manifest['row_coverage']=[dict(objective_row=row,disposition='IMPLEMENT',plan_ids=['P01'],rationale='Cover the sealed actual-work beat.') for row in rows]
        body=template._plan_text().replace(template.objective_relative,self.objective['path']).replace(template.objective_sha256,self.objective['sha256'])
        body=body.replace('- Objective rows: `1`','- Objective rows: `'+', '.join(map(str,rows))+'`')
        self.write(plan_path,body);self.write(relative,manifest)
        result=validate_production_plan(str(self.game),relative)
        self.assertFalse(result.errors,result.errors)
        manifest['plans'][0]['planned_paths']=['scripts/not-authorized.gd']
        self.write(relative,manifest)
        result=validate_production_plan(str(self.game),relative)
        self.assertTrue(any('approved production scope' in e for e in result.errors),result.errors)


if __name__=='__main__':unittest.main()
