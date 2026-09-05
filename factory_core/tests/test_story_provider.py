import unittest
from unittest.mock import patch
from factory_core.tests import test_regressions as fixture
from factory_core.refs import FactoryError, reference, sha
from factory_core.context import provider_result
from story.v2 import CHECKS,validate_acceptance

class StoryProviderTests(unittest.TestCase):
    setUp=fixture.RegressionTests.setUp
    write=fixture.RegressionTests.write
    profile=fixture.RegressionTests.profile

    def story_report(self):
        self.profile();profile=reference(self.game,'narrative/control/PROJECT_PROFILE.md')
        outputs=[self.write('narrative/en.md','Mara does not know why the envoy vanished.'),self.write('narrative/zh.md','瑪拉不知道使者為何失蹤。')]
        design_ref=self.write('design/package.json',{'example':'complete synthetic design'})
        design={'author_context_id':'author','production_scope':[r['path'] for r in outputs]}
        reviews=[self.write('design/review-'+role+'.json',{'reviewer_context_id':role}) for role in ('intent','complete')]
        record={'design':design_ref,'dependencies':{'fingerprint':'a'*64,'references':[profile]},'reviews':reviews,'artifacts':outputs}
        log=self.write('narrative/check.log','Executed synthetic checker: PASS')
        technical=self.write('narrative/technical.json',{'schema_version':'story_technical_evidence.v2','outputs':outputs,'checks':{name:dict(status='PASS',command='synthetic unit-test check',exit_code=0,log=log) for name in ('style_lint','glossary','routing','locale_integrity')}})
        clean=[]
        for locale,output in zip(('en','zh-TW'),outputs):
            packet=self.write('narrative/packet-'+locale+'.json',dict(schema_version='story_fluency_packet.v2',locale=locale,beats=['An observed absence, no explanation.'],protected_forms=[],banned_forms=[],lines=['The guest is absent.']))
            back=self.write('narrative/back-'+locale+'.json',dict(schema_version='story_canon_backcheck.v2',packet=packet,outputs=[output],reviewer_context_id='back-'+locale,sources=[profile],verdict='PASS',rationale='Synthetic record verifies no invented knowledge.'))
            clean.append(self.write('narrative/clean-'+locale+'.json',dict(schema_version='story_cleanroom_evidence.v2',locale=locale,packet=packet,outputs=[output],worker_context_id='clean-'+locale,fresh=True,sources_read=[packet],verdict='PASS',canon_backcheck=back)))
        report=dict(schema_version='story_output_acceptance.v2',design=design_ref,dependency_fingerprint='a'*64,outputs=outputs,reviewer_context_id='qa',fresh=True,verdict='PASS',checks={name:dict(status='PASS',rationale='Synthetic test evidence, not actual creative quality.',evidence=[profile,*outputs]) for name in CHECKS},technical_evidence=[technical],shipped_locales=['en','zh-TW'],locale_coverage=['en','zh-TW'],cleanroom_evidence=clean)
        return record,design,report

    def test_exact_typed_story_acceptance_and_no_gameplay_claim(self):
        record,design,report=self.story_report();ref=self.write('acceptance.json',report)
        self.assertFalse(validate_acceptance(self.roots,record,design,ref)['gameplay_accepted'])

    def test_relationship_semantic_failure_blocks_despite_technical_passes(self):
        record,design,report=self.story_report()
        report['checks']['all_shipped_locale_semantics'].update(status='FAIL',
            rationale='Synthetic reviewer: the target-language player cannot identify the required familial relationship.')
        # Mechanical checks, clean-room records and an overall PASS assertion
        # cannot overrule an unresolved semantic finding. This test exercises
        # gate enforcement, not an automatic keyword-based language judgment.
        with self.assertRaisesRegex(FactoryError,'unresolved finding'):
            validate_acceptance(self.roots,record,design,self.write('acceptance.json',report))

    def test_self_declared_english_only_does_not_override_profile(self):
        record,design,report=self.story_report();report['shipped_locales']=report['locale_coverage']=['en']
        with self.assertRaises(FactoryError):validate_acceptance(self.roots,record,design,self.write('acceptance.json',report))

    def test_profile_is_not_cleanroom_or_technical_evidence(self):
        record,design,report=self.story_report();report['technical_evidence']=[record['dependencies']['references'][0]]
        with self.assertRaises(FactoryError):validate_acceptance(self.roots,record,design,self.write('acceptance.json',report))

    def test_story_output_mutation_or_missing_planned_output_fails(self):
        record,design,report=self.story_report();self.write('narrative/en.md','Mara knows the envoy culprit.')
        with self.assertRaises(FactoryError):validate_acceptance(self.roots,record,design,self.write('acceptance.json',report))

    def test_no_dialogue_task_does_not_invent_cleanroom_work(self):
        record,design,report=self.story_report()
        scope=self.write('narrative/scope.md','Only the knowledge ledger changes. No new or changed spoken dialogue.')
        design['story']={'spoken_output_paths':[],'scope_evidence':scope}
        report['cleanroom_evidence']=[]
        report['checks']['cleanroom_fluency_backcheck']['evidence'].append(scope)
        result=validate_acceptance(self.roots,record,design,self.write('acceptance.json',report))
        self.assertEqual(result['cleanroom'],'NOT_APPLICABLE_REVIEWED_SCOPE')

    def test_sound_and_asset_existing_results_have_compact_readers(self):
        self.write('audio/bell.wav','mock bytes')
        self.write('audio/sound_result.json',dict(ok=True,stage='done',deliverable='bell.wav'))
        result=provider_result(self.roots,'audio/sound_result.json');self.assertTrue(result['ok']);self.assertIn('NOT_GAMEPLAY',result['acceptance'])
        self.write('art/lantern.png','mock png')
        self.write('art/result.json',dict(variants={'one':dict(validation={'status':'pass'},deliverable={'status':'ok','primary_artifact':'lantern.png'})}))
        self.assertTrue(provider_result(self.roots,'art/result.json')['ok'])
        self.write('art/result.json',dict(variants={'one':dict(validation={'status':'fail'},deliverable={'status':'ok','primary_artifact':'lantern.png'})}))
        self.assertFalse(provider_result(self.roots,'art/result.json')['ok'])

    def test_existing_sound_trim_and_normalize_mock_contract(self):
        from sound.pipeline import trim
        with patch.object(trim,'_trim_silence') as cut,patch.object(trim,'_max_volume_dbfs',return_value=-6),patch.object(trim,'_apply_gain') as gain,patch.object(trim,'_duration_seconds',side_effect=[2,1]):
            report=trim.trim_and_normalize('provider.wav','delivery.ogg')
        self.assertEqual(report['gain_applied_db'],5);cut.assert_called_once();gain.assert_called_once_with('delivery.ogg.trim.wav','delivery.ogg',5)
        self.assertEqual(report['out_duration_s'],1)

if __name__=='__main__':unittest.main()
