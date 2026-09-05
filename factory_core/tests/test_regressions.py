"""Adversarial examples found by the two independent boundary reviews."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from factory_core.tests import test_core as fixture
from factory_core.refs import FactoryError, digest, encoded, expand_references, read_json, reference, sha
from factory_core.state import checkpoint, latest, verify_record, check_ruling, approval_action, load_design
from factory_core.migration import preview, apply
from factory_core.catalog import factory_dependencies, authority_refs

ROOT=fixture.ROOT
class RegressionTests(unittest.TestCase):
    setUp=fixture.CoreTests.setUp
    write=fixture.CoreTests.write
    migrate=fixture.CoreTests.migrate
    design=fixture.CoreTests.design
    request=fixture.CoreTests.request
    save_design=fixture.CoreTests.save_design
    reviews=fixture.CoreTests.reviews

    def test_draft_to_complete_and_changed_design_restart(self):
        d,ref=self.design()
        out=checkpoint(self.roots,self.request())
        out=checkpoint(self.roots,self.request('DESIGN_COMPLETE',out['checkpoint']['sha256'],design=ref))
        d['intent']='Updated intent within the same task.'
        ref=self.write('design/assets/PACKAGE2.json',d)
        out=checkpoint(self.roots,self.request('DRAFT',out['checkpoint']['sha256'],design=ref))
        out=checkpoint(self.roots,self.request('DESIGN_COMPLETE',out['checkpoint']['sha256'],design=ref))
        self.assertEqual(out['stage'],'DESIGN_COMPLETE')

    def test_draft_artifact_cannot_silently_change(self):
        self.migrate();artifact=self.write('work.md','draft')
        req=self.request();req['artifacts']=[artifact]
        checkpoint(self.roots,req);record,_=latest(self.game,'lantern')
        self.write('work.md','changed')
        with self.assertRaises(FactoryError):verify_record(self.roots,record)

    def test_rejection_cannot_become_approval(self):
        d,ref,out,record=self.save_design();binding=record['dependencies']
        for wording in ('No, do not implement this design.', 'Do not '+approval_action(ref,binding)):
            source=self.write('raw.json',dict(role='user',content=wording))
            ruling=self.write('ruling.json',dict(schema_version='factory_ruling.v2',owner='USER',decision='APPROVE',
                       design=ref,dependency_fingerprint=binding['fingerprint'],source=source,quote=wording))
            with self.assertRaisesRegex(FactoryError,'exact approval action'):check_ruling(self.roots,ruling,ref,binding)
        wording=approval_action(ref,binding)
        source=self.write('raw.json',dict(role='user',content=wording))
        ruling=self.write('ruling.json',dict(schema_version='factory_ruling.v2',owner='USER',decision='APPROVE',
                       design=ref,dependency_fingerprint=binding['fingerprint'],source=source,quote=wording))
        check_ruling(self.roots,ruling,ref,binding)

    def test_explicit_authority_race_before_migration(self):
        plan=preview(self.game,ROOT,'fixture',['RULES.md']);self.write('RULES.md','concurrent')
        before=sha(self.game/'AGENTS.md')
        with self.assertRaises(FactoryError):apply(self.game,ROOT,'fixture',plan['source_digest'],['RULES.md'])
        self.assertEqual(before,sha(self.game/'AGENTS.md'))

    def test_all_targets_preflight_before_routing_mutation(self):
        plan=preview(self.game,ROOT,'fixture',['RULES.md'])
        self.write('design/factory/ROUTING_RECEIPT.json',{'concurrent':'user'})
        before=sha(self.game/'AGENTS.md')
        with self.assertRaises(FactoryError):apply(self.game,ROOT,'fixture',plan['source_digest'],['RULES.md'])
        self.assertEqual(before,sha(self.game/'AGENTS.md'))
        self.assertFalse((self.game/'design/factory/.migration.json').exists())

    def test_recovery_rejects_changed_routing_implementation(self):
        from factory_core import migration
        plan=preview(self.game,ROOT,'fixture')
        original=migration.exclusive_json
        def crash(path,payload):
            result=original(path,payload)
            if path.name=='.migration.json':raise RuntimeError('crash after intent')
            return result
        with patch.object(migration,'exclusive_json',side_effect=crash):
            with self.assertRaises(RuntimeError):apply(self.game,ROOT,'fixture',plan['source_digest'])
        before=sha(self.game/'AGENTS.md')
        with patch.object(migration,'routing_block',return_value='changed output'):
            with self.assertRaises(FactoryError):apply(self.game,ROOT,'fixture',plan['source_digest'])
        self.assertEqual(before,sha(self.game/'AGENTS.md'))
        self.assertFalse((self.game/'design/factory/PROJECT.json').exists())
        self.assertEqual(apply(self.game,ROOT,'fixture',plan['source_digest'])['status'],'MIGRATED')

    def test_partial_reference_and_execution_dependency(self):
        ref=self.write('input.json',{'nested':{'scope':'game','path':'missing.json'}})
        with self.assertRaises(FactoryError):expand_references(self.roots,[ref])
        paths={r['path'] for r in factory_dependencies(ROOT,'asset','prop')}
        self.assertIn('asset/blender/scripts/render_tiles.py',paths)
        self.assertIn('asset/blender/scripts/validate_scene.py',paths)

    def test_generic_production_cannot_own_specialist_state(self):
        d,ref=self.design()
        for path in ('design/studio/STUDIO_RUN_STATE.json','design/studio/STUDIO_DECISION_CARD_REGISTER.json',
                     'design/studio/baselines/one.json','design/gameplay/GAMEPLAY_REPAIR_STATE.json'):
            d['production_scope']=[path];ref=self.write('design/assets/PACKAGE.json',d)
            with self.assertRaises(FactoryError):load_design(self.roots,ref)

    def profile(self):
        self.write('narrative/control/PROJECT_PROFILE.md','- `<STORY_ROOT>`: `<GAME_REPO>/narrative`\n- `<PRIMARY_LOCALE>`: en\n- `<SHIPPED_LOCALES>`: en, zh-TW\n')
        self.write('narrative/state/WORLD_RULES.md','No invented mystery resolution.')
        self.write('narrative/control/STYLE_GUIDE.md','Household voice.')
        extra=['narrative/control/PROJECT_PROFILE.md'];plan=preview(self.game,ROOT,'fixture',extra)
        apply(self.game,ROOT,'fixture',plan['source_digest'],extra)
        return extra

    def test_story_custom_root_resolves_mandatory_authorities(self):
        extra=self.profile()
        paths={r['path'] for r in authority_refs(self.game,'story',extra)}
        self.assertIn('narrative/state/WORLD_RULES.md',paths)
        self.assertIn('narrative/control/STYLE_GUIDE.md',paths)
        from factory_core.story_profile import resolve
        self.assertEqual(resolve(self.game,extra)['shipped_locales'],['en','zh-TW'])

    def test_visual_input_is_required_reference_not_utf8_or_dropped(self):
        from factory_core.context import context
        d,ref=self.design()
        path=self.game/'reference.png';path.write_bytes(b'\x89PNG\r\n\x1a\n')
        visual=reference(self.game,'reference.png');d['inputs']=[visual]
        ref=self.write('design/assets/PACKAGE.json',d)
        view=context(self.roots,'asset','prop',design=ref)
        binary=next(item for item in view['design_artifacts'] if item['reference']==visual)
        self.assertEqual(binary['kind'],'binary_source');self.assertIn('Inspect',binary['required_action'])
        self.assertIn(visual,view['source_references'])

    def test_story_unknown_profile_blocks_instead_of_omitting_rules(self):
        self.migrate()
        with self.assertRaises(FactoryError):authority_refs(self.game,'story',['RULES.md'])

if __name__=='__main__':unittest.main()
