"""Admission regressions. Synthetic consistency is never semantic success."""
from __future__ import annotations

import unittest

from factory_core.refs import FactoryError, digest, read_json, reference
from product import judgment, value
from product.tests import test_value as value_tests
from product.tests.judgment_fixtures import JudgmentFixture, reviews


class JudgmentTests(unittest.TestCase):
    setUp = value_tests.ProductTests.setUp
    write = value_tests.ProductTests.write
    assessment = value_tests.ProductTests.assessment
    save = value_tests.ProductTests.save

    def fixture(self, **kwargs):
        count = getattr(self, '_fixture_count', 0) + 1
        self._fixture_count = count
        return JudgmentFixture(self.roots, self.assessment(f'judgment-{count}', **kwargs))

    def rejected(self, code, action, *args, **kwargs):
        with self.assertRaises(FactoryError) as raised:
            action(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    def before_decision(self, fixture):
        return fixture.seal_through('independent_completeness_project')

    def test_packets_keep_raw_sources_and_exclude_report_and_peer_conclusions(self):
        f = self.fixture()
        initial = f.packet('frame')
        self.assertEqual(initial['question'], f.case['question'])
        self.assertIn(f.case['conditions'][0]['source'], initial['inputs'])
        f.seal('frame')
        independent = f.packet('independent_intent_experience')
        self.assertNotIn(f.assessment['report'], independent['inputs'])
        self.assertFalse(any('evidence.json' in r['path'] for r in independent['inputs']))
        f.seal('evidence')
        for stage in judgment.STAGES[2:4]:
            f.seal(stage)
        decision = f.packet('decision')
        first_refs = [reference(self.game, judgment.stage_path(f.identity, s)) for s in judgment.STAGES[2:4]]
        self.assertEqual(decision['independence_receipts'], [digest(r) for r in first_refs])
        self.assertTrue(all(r not in decision['inputs'] for r in first_refs))
        self.assertNotIn(f.assessment['report'], decision['inputs'])
        self.assertIn(reference(self.game, judgment.stage_path(f.identity, 'evidence')), decision['inputs'])

    def test_decision_preflight_requires_both_sealed_first_passes(self):
        f = self.fixture().seal_through('evidence')
        self.rejected('MISSING_REFERENCE', f.packet, 'decision')
        f.seal('independent_intent_experience')
        self.rejected('MISSING_REFERENCE', f.packet, 'decision')
        f.seal('independent_completeness_project')
        self.assertEqual(f.packet('decision')['stage'], 'decision')

    def test_frame_retains_exact_original_whole_purchase_question(self):
        f = self.fixture()
        draft = f.draft('frame')
        draft['findings']['whole_purchase_question'] = 'Could someone enjoy a small part of this experience?'
        self.rejected('CHANGED_JUDGMENT_QUESTION', f.seal, 'frame', draft)

    def test_late_author_condition_cannot_replace_independent_frame(self):
        f = self.before_decision(self.fixture())
        for scope in ('verdict', 'condition'):
            with self.subTest(scope=scope):
                draft = f.draft('decision')
                condition = 'Only for buyers who would already judge the whole purchase worthwhile.'
                draft['findings']['conditionality'] = [condition]
                if scope == 'condition':
                    draft['findings']['conditions'][0].update(disposition='CONDITIONAL', assumptions=[condition])
                self.rejected('CHANGED_JUDGMENT_QUESTION', f.seal, 'decision', draft)
        f = self.fixture().seal_through('frame')
        draft = f.draft('independent_intent_experience')
        draft['findings']['conditions'][0].update(
            disposition='CONDITIONAL', assumptions=['Only for an invented easier buyer.'])
        self.rejected('CHANGED_JUDGMENT_QUESTION', f.seal, 'independent_intent_experience', draft)

    def test_original_quote_and_mandatory_authority_are_checked(self):
        f = self.fixture()
        f.case['conditions'][0].update(text='An invented easier buying requirement.', quote='An invented easier buying requirement.')
        f.write_case()
        self.rejected('INVALID_JUDGMENT_CASE', f.packet, 'frame')
        f = self.fixture()
        f.case['sources'] = [r for r in f.case['sources'] if r['path'] != 'AGENTS.md']
        f.write_case()
        self.rejected('INCOMPLETE_JUDGMENT_SOURCES', f.packet, 'frame')

    def test_case_cannot_relabel_an_original_quote_as_an_easier_condition(self):
        f = self.fixture()
        f.case['conditions'][0]['text'] = 'At least one choice exists.'
        f.write_case()
        self.rejected('CHANGED_JUDGMENT_QUESTION', f.packet, 'frame')

    def test_raw_packet_requires_fixed_build_offer_and_audience_sources(self):
        for omitted in ('build.bin', 'offer.md'):
            with self.subTest(omitted=omitted):
                f = self.fixture()
                f.case['sources'] = [ref for ref in f.case['sources'] if ref['path'] != omitted]
                f.write_case()
                self.rejected('INCOMPLETE_JUDGMENT_SOURCES', f.packet, 'frame')

    def test_completed_outputs_cannot_enter_raw_packet_directly_or_transitively(self):
        for kind in ('report', 'renamed-stage', 'nested-stage', 'nested-review-text'):
            with self.subTest(kind=kind):
                f = self.fixture()
                if kind == 'report':
                    source = f.assessment['report']
                elif kind == 'nested-review-text':
                    source = self.write(f'{f.base}/apparently-raw.txt',
                                        dict(envelope=[dict(payload=dict(schema_version='product_value_review.v2',
                                                                        verdict='AGREE'))]))
                else:
                    source = self.write(f'{f.base}/renamed-source.json',
                                        dict(schema_version='product_judgment_stage.v1', note='Prior judgment conclusions'))
                    if kind == 'nested-stage':
                        source = self.write(f'{f.base}/raw-wrapper.json', dict(upstream=source))
                f.case['sources'].append(source)
                f.write_case()
                self.rejected('CONTAMINATED_JUDGMENT_SOURCES', f.packet, 'frame')

    def test_final_assessment_cannot_add_evidence_unseen_by_prior_owners(self):
        f = self.fixture().seal_through()
        new_source = self.write('new-post-decision-observation.md', 'Synthetic new observation unavailable to the sealed owners.')
        f.assessment['evidence'][0]['reference'] = new_source
        ref = f.bind()
        self.rejected('INCOMPLETE_JUDGMENT_SOURCES', value.prepare, self.roots, ref['path'])

    def test_experiential_obligations_require_distinct_existing_claim_dependencies(self):
        for dependencies in ([], ['missing-claim'], ['complete-sequence', 'complete-sequence']):
            with self.subTest(dependencies=dependencies):
                f = self.fixture().seal_through('frame')
                draft = f.draft('evidence')
                draft['findings']['conditions'][0]['obligations'][0]['claim_ids'] = dependencies
                self.rejected('INVALID_JUDGMENT_STAGE', f.seal, 'evidence', draft)

    def test_supported_obligation_cannot_promote_unresolved_or_contradicted_claims(self):
        for state in ('UNRESOLVED', 'CONTRADICTED'):
            for mapped in (True, False):
                with self.subTest(state=state, mapped=mapped):
                    f = self.fixture().seal_through('frame')
                    draft = f.draft('evidence')
                    condition = draft['findings']['conditions'][0]
                    contrary = dict(condition['claims'][0], id='contrary-premise', status=state)
                    if mapped:
                        contrary['proposition'] = 'A separately worded required causal premise is established.'
                        condition['obligations'][0]['claim_ids'] = ['contrary-premise']
                    condition['claims'].append(contrary)
                    self.rejected('UNRESOLVED_JUDGMENT_CONDITION', f.seal, 'evidence', draft)

    def test_unchanged_original_text_and_all_condition_ids_are_required(self):
        for mutation in (
            lambda draft: draft['findings']['conditions'][0].update(text='There are some real choices.'),
            lambda draft: draft['findings'].update(conditions=[]),
            lambda draft: draft['findings']['conditions'][0].update(id='narrower-question'),
        ):
            f = self.fixture()
            draft = f.draft('frame')
            mutation(draft)
            self.rejected('CHANGED_JUDGMENT_QUESTION', f.seal, 'frame', draft)

    def test_compound_obligations_cannot_be_dropped_reworded_or_retyped(self):
        for stage in ('evidence', 'independent_intent_experience', 'decision'):
            for mutation in (
                lambda units: units.pop(),
                lambda units: units[0].update(proposition='There is at least one real choice.'),
                lambda units: units[1].update(kind='EXPERIENTIAL'),
            ):
                with self.subTest(stage=stage, mutation=mutation):
                    f = self.fixture()
                    if stage == 'decision':
                        self.before_decision(f)
                    else:
                        f.seal('frame')
                    draft = f.draft(stage)
                    mutation(draft['findings']['conditions'][0]['obligations'])
                    self.rejected('CHANGED_JUDGMENT_QUESTION', f.seal, stage, draft)

    def test_independent_frame_challenge_blocks_admission(self):
        f = self.fixture().seal_through('frame')
        draft = f.draft('independent_intent_experience')
        draft['findings']['frame_fidelity']['omitted_or_weakened_obligations'] = [
            'The frame forgot that the full experience must earn the purchase.'
        ]
        self.rejected('JUDGMENT_REOPEN_REQUIRED', f.seal, 'independent_intent_experience', draft)

    def test_contamination_and_reopening_cannot_be_erased_by_sealing(self):
        for field, code in (('extra_exposure', 'CONTAMINATED_JUDGMENT_STAGE'),
                            ('reopen_requests', 'JUDGMENT_REOPEN_REQUIRED')):
            f = self.fixture()
            draft = f.draft('frame')
            draft[field] = ['Prior purchase verdict was supplied; this context cannot be independent.']
            self.rejected(code, f.seal, 'frame', draft)
            self.assertFalse((self.game / judgment.stage_path(f.identity, 'frame')).exists())

    def test_distinct_frame_evidence_review_and_decision_contexts(self):
        f = self.fixture().seal_through('frame')
        draft = f.draft('evidence')
        draft['context_id'] = f.contexts['frame']
        self.rejected('JUDGMENT_NOT_INDEPENDENT', f.seal, 'evidence', draft)
        for reused in ('evidence', 'independent_intent_experience', 'independent_completeness_project'):
            f = self.before_decision(self.fixture())
            draft = f.draft('decision')
            draft['context_id'] = f.contexts[reused]
            self.rejected('JUDGMENT_NOT_INDEPENDENT', f.seal, 'decision', draft)
        f = self.fixture()
        f.contexts['independent_completeness_project'] = f.contexts['independent_intent_experience']
        self.before_decision(f)
        self.rejected('JUDGMENT_NOT_INDEPENDENT', f.seal, 'decision')

    def test_packet_digest_and_raw_dependency_mutations_stale_the_chain(self):
        f = self.fixture()
        draft = f.draft('frame')
        f.case['question'] = 'A changed whole-purchase question'
        f.write_case()
        self.rejected('STALE_JUDGMENT_STAGE', f.seal, 'frame', draft)
        f = self.before_decision(self.fixture())
        self.write('experience.md', 'A different synthetic experience.')
        self.rejected('STALE_DEPENDENCY', f.packet, 'decision')

    def test_changed_sealed_frame_or_first_pass_invalidates_descendants(self):
        for stage, path_field in (('frame', 'meaning'),
                                   ('independent_intent_experience', None)):
            with self.subTest(stage=stage):
                f = self.before_decision(self.fixture())
                decision = f.draft('decision')
                path = judgment.stage_path(f.identity, stage)
                changed = read_json(self.game / path)
                if path_field:
                    changed['findings']['conditions'][0][path_field] += ' Changed after sealing.'
                else:
                    changed['findings']['frame_fidelity']['reason'] += ' Changed after sealing.'
                self.write(path, changed)  # Simulate hostile direct filesystem mutation.
                self.rejected('STALE_JUDGMENT_STAGE', f.seal, 'decision', decision)

    def test_stage_seals_are_idempotent_but_never_replace_outputs(self):
        f = self.fixture()
        draft = f.draft('frame')
        first = f.seal('frame', draft)
        before = (self.game / first['stage']['path']).read_bytes()
        self.assertEqual(f.seal('frame', draft)['stage'], first['stage'])
        draft['findings']['conditions'][0]['meaning'] += ' A changed criterion.'
        self.rejected('IMMUTABLE_JUDGMENT_STAGE', f.seal, 'frame', draft)
        self.assertEqual((self.game / first['stage']['path']).read_bytes(), before)
        self.assertFalse(first['semantic_success_proven'])

    def test_evidence_cannot_resolve_evaluative_obligation_as_fact(self):
        f = self.fixture().seal_through('frame')
        draft = f.draft('evidence')
        draft['findings']['conditions'][0]['obligations'][1]['status'] = 'SUPPORTED'
        self.rejected('INVALID_JUDGMENT_STAGE', f.seal, 'evidence', draft)

    def test_unresolved_or_contradicted_experience_cannot_become_met_or_conditional(self):
        for prior in ('UNRESOLVED', 'CONTRADICTED'):
            for later in ('MET', 'CONDITIONAL'):
                with self.subTest(prior=prior, later=later):
                    f = self.fixture()
                    if later == 'CONDITIONAL':
                        f.set_external_conditions(['Only at the explicit hypothetical offer.'])
                    f.seal('frame')
                    evidence = f.draft('evidence')
                    condition = evidence['findings']['conditions'][0]
                    condition['obligations'][0]['status'] = prior
                    condition['claims'][0]['status'] = prior
                    self.assertEqual(condition['material_unknowns'], [])
                    f.seal('evidence', evidence)
                    for stage in judgment.STAGES[2:4]:
                        f.seal(stage)
                    draft = f.draft('decision')
                    condition = draft['findings']['conditions'][0]
                    condition['obligations'][0]['status'] = later
                    if later == 'CONDITIONAL':
                        condition.update(disposition='CONDITIONAL', assumptions=['Only at the explicit hypothetical offer.'])
                        draft['findings']['conditionality'] = list(condition['assumptions'])
                    error = self.rejected('UNRESOLVED_JUDGMENT_CONDITION', f.seal, 'decision', draft)
                    self.assertIn('unresolved necessary facts', str(error))

    def test_supported_local_fact_does_not_resolve_unknown_whole_scope(self):
        f = self.fixture().seal_through('frame')
        evidence = f.draft('evidence')
        condition = evidence['findings']['conditions'][0]
        condition['claims'][0]['proposition'] = 'A local consequential choice was observed.'
        condition['obligations'][0].update(status='UNRESOLVED', reason='The supported local fact does not establish the required throughout scope.')
        f.seal('evidence', evidence)
        for stage in judgment.STAGES[2:4]:
            f.seal(stage)
        error = self.rejected('UNRESOLVED_JUDGMENT_CONDITION', f.seal, 'decision')
        self.assertIn('experiential premises', str(error))

    def test_evaluative_conclusion_cannot_launder_unresolved_necessary_fact(self):
        for prior in ('UNRESOLVED', 'CONTRADICTED'):
            for disposition in ('MET', 'CONDITIONAL'):
                with self.subTest(prior=prior, disposition=disposition):
                    f = self.fixture()
                    if disposition == 'CONDITIONAL':
                        f.set_external_conditions(['Only at the explicit hypothetical offer.'])
                    f.seal('frame')
                    evidence = f.draft('evidence')
                    condition = evidence['findings']['conditions'][0]
                    premise = dict(condition['claims'][0], id='necessary-payoff',
                                   proposition='The ending preserves the payoff needed for whole-purchase sufficiency.', status=prior)
                    condition['claims'].append(premise)
                    condition['obligations'][1]['claim_ids'] = ['necessary-payoff']
                    self.assertEqual(condition['obligations'][1]['status'], 'EVALUATIVE')
                    f.seal('evidence', evidence)
                    for stage in judgment.STAGES[2:4]:
                        f.seal(stage)
                    error = self.rejected('UNRESOLVED_JUDGMENT_CONDITION', f.seal, 'decision')
                    self.assertIn('unresolved necessary facts', str(error))

    def test_met_requires_every_compound_obligation_to_be_met(self):
        for status in ('UNRESOLVED', 'NOT_MET'):
            f = self.before_decision(self.fixture())
            draft = f.draft('decision')
            draft['findings']['conditions'][0]['obligations'][1]['status'] = status
            error = self.rejected('UNRESOLVED_JUDGMENT_CONDITION', f.seal, 'decision', draft)
            self.assertIn('every original obligation', str(error))

    def test_conditional_taste_cannot_launder_unresolved_whole_purchase(self):
        for status in ('UNRESOLVED', 'NOT_MET', 'CONDITIONAL'):
            with self.subTest(status=status):
                f = self.fixture()
                f.set_external_conditions(['Only for buyers who would find the whole purchase worthwhile.'])
                self.before_decision(f)
                draft = f.draft('decision')
                condition = draft['findings']['conditions'][0]
                condition.update(disposition='CONDITIONAL', assumptions=['Only for buyers who would find the whole purchase worthwhile.'])
                condition['obligations'][1]['status'] = status
                draft['findings']['conditionality'] = list(condition['assumptions'])
                self.rejected('UNRESOLVED_JUDGMENT_CONDITION', f.seal, 'decision', draft)

    def test_material_unknowns_must_reach_condition_and_verdict(self):
        for dropped_at in ('condition', 'verdict'):
            f = self.fixture(judgment='EVIDENCE_INSUFFICIENT')
            f.assessment['material_unknowns'] = [
                'The ending may reward the choices or erase them; observe the exact final sequence to distinguish these outcomes.'
            ]
            self.before_decision(f)
            draft = f.draft('decision')
            if dropped_at == 'condition':
                draft['findings']['conditions'][0]['material_unknowns'] = []
            else:
                draft['findings']['material_unknowns'] = []
            self.rejected('UNRESOLVED_JUDGMENT_CONDITION', f.seal, 'decision', draft)

    def test_essential_scenario_assumption_must_qualify_verdict(self):
        f = self.fixture(offer='SCENARIO')
        f.set_external_conditions(['Only at the explicitly hypothetical 1.99 USD scenario offer.'])
        self.before_decision(f)
        draft = f.draft('decision')
        draft['findings']['conditionality'] = []
        self.rejected('CHANGED_JUDGMENT_QUESTION', f.seal, 'decision', draft)

    def test_met_under_fixed_scenario_may_repeat_only_frame_owned_conditions(self):
        f = self.fixture(offer='SCENARIO')
        external = ['Only at the explicitly stipulated offer and buyer scenario.']
        f.set_external_conditions(external)
        f.seal('frame'); f.seal('evidence')
        for stage in judgment.STAGES[2:]:
            draft = f.draft(stage)
            draft['findings']['conditions'][0]['disposition'] = 'MET'
            self.assertEqual(draft['findings']['conditions'][0]['assumptions'], external)
            self.assertEqual(draft['findings']['conditions'][0]['material_unknowns'], [])
            f.seal(stage, draft)
        f.bind()
        result = value.record(self.roots, value.paths(f.identity)['input'], reviews(self.roots, f.assessment))
        self.assertEqual(result['qualifications'][0], external[0])
        self.assertFalse(result['value_claim_eligible'])
        other = self.fixture().seal_through('frame')
        draft = other.draft('independent_intent_experience')
        draft['findings']['conditions'][0]['assumptions'] = ['A new unframed buyer preference.']
        self.rejected('CHANGED_JUDGMENT_QUESTION', other.seal, 'independent_intent_experience', draft)

    def test_valid_external_scenario_conditionality_is_preserved_and_claim_blocked(self):
        f = self.fixture(offer='SCENARIO')
        f.set_external_conditions(['Only at the explicitly hypothetical 1.99 USD scenario offer.'])
        f.seal_through().bind()
        result = value.record(self.roots, value.paths(f.identity)['input'], reviews(self.roots, f.assessment))
        self.assertEqual(result['judgment'], 'SUPPORTED')
        self.assertEqual(result['qualifications'][0], f.assessment['conditionality'][0])
        self.assertFalse(value.gate(self.roots, result['result']['path'], 'build.bin')['ok'])

    def test_finite_positive_negative_and_unresolved_inference_are_valid_completed_assessments(self):
        for verdict in ('SUPPORTED', 'VALUE_GAP', 'JUDGMENT_UNRESOLVED'):
            with self.subTest(verdict=verdict):
                f = self.fixture(judgment=verdict, amount='19.99')
                f.seal_through().bind()
                result = value.record(self.roots, value.paths(f.identity)['input'], reviews(self.roots, f.assessment))
                checked = value.check(self.roots, result['result']['path'])
                self.assertEqual(checked['judgment'], verdict)
                self.assertEqual(checked['mechanical_status'], 'RECORD_VALID')
                self.assertFalse(result['semantic_success_proven'])
                self.assertFalse(checked['semantic_success_proven'])
                self.assertFalse(checked['user_accepted'])
                self.assertFalse(checked['delivery_eligible'])
                self.assertEqual(value.gate(self.roots, result['result']['path'], 'build.bin')['ok'], verdict == 'SUPPORTED')
                self.assertNotIn('hours', f.assessment)
                self.assertNotIn('replay_count', f.assessment)

    def test_v1_readable_but_cannot_prepare_or_record_new_receipt(self):
        a = self.assessment('historical-v1')
        a['schema_version'] = 'product_value_assessment.v1'
        a.pop('deliberation')
        ref = self.save(a)
        self.assertEqual(value.validate_assessment(self.roots, ref), a)
        self.rejected('PRODUCT_STAGED_JUDGMENT_REQUIRED', value.prepare, self.roots, ref['path'])
        self.rejected('PRODUCT_STAGED_JUDGMENT_REQUIRED', value.record, self.roots, ref['path'], [])
        self.assertFalse((self.game / value.paths(a['assessment_id'])['result']).exists())

    def test_readable_historical_v1_receipt_cannot_authorize_current_value_claim(self):
        # Construct a historical-format sample directly. The public record API
        # remains forbidden from minting it, as the preceding regression proves.
        a = self.assessment('historical-result')
        a['schema_version'] = 'product_value_assessment.v1'
        a.pop('deliberation')
        assessment_ref = self.save(a)
        package = value.prepare(self.roots, assessment_ref['path'], historical=True)
        review_refs = []
        for role in value.ROLES:
            review = dict(
                schema_version='product_value_review.v1', role=role, reviewer_context_id=role,
                fresh=True, peer_reviews_read=[], assessment=assessment_ref,
                dependency_fingerprint=package['dependencies']['fingerprint'], verdict='AGREE',
                findings={key: dict(rationale='Synthetic historical review fixture.', evidence=[a['report']])
                          for key in value.FINDINGS},
                source_coverage=[digest(ref) for ref in package['dependencies']['references'] if ref['scope'] != 'factory'],
            )
            review_refs.append(self.write(f"design/product_value/{a['assessment_id']}/reviews/{role}.json", review))
        historical = value._expected(self.roots, assessment_ref['path'], review_refs, historical=True)
        result_ref = self.write(value.paths(a['assessment_id'])['result'], historical)
        checked = value.check(self.roots, result_ref['path'])
        self.assertEqual(checked['judgment'], 'SUPPORTED')
        self.assertNotIn('judgment_protocol', checked)
        gate = value.gate(self.roots, result_ref['path'], 'build.bin')
        self.assertFalse(gate['ok'])
        self.assertTrue(any('Historical assessment' in reason for reason in gate['qualifications']))

    def test_assessment_author_is_the_sealed_decision_context(self):
        f = self.fixture().seal_through()
        f.assessment['author_context_id'] = 'another-author'
        ref = f.bind()
        self.rejected('JUDGMENT_NOT_INDEPENDENT', value.prepare, self.roots, ref['path'])

    def test_assessment_cannot_change_sealed_verdict_or_fixed_offer(self):
        for mutate in (lambda a: a.update(judgment='VALUE_GAP'),
                       lambda a: a['offer'].update(amount='0.01'),
                       lambda a: a['audience'].update(description='A different more forgiving audience')):
            f = self.fixture().seal_through()
            mutate(f.assessment)
            ref = f.bind()
            self.rejected('CHANGED_JUDGMENT_QUESTION', value.prepare, self.roots, ref['path'])

    def test_review_requires_its_own_exact_first_pass(self):
        f = self.fixture().seal_through()
        f.bind()
        paths = reviews(self.roots, f.assessment)
        review = read_json(self.game / paths[0])
        review['independent_first_pass'] = reference(self.game, judgment.stage_path(f.identity, 'independent_completeness_project'))
        self.write(paths[0], review)
        self.rejected('JUDGMENT_NOT_INDEPENDENT', value.record, self.roots, value.paths(f.identity)['input'], paths)

    def test_final_comparison_blocks_weakened_question_and_unresolved_disagreement(self):
        mutations = (
            (lambda comparison: comparison.update(original_meaning_preserved=False), 'CHANGED_JUDGMENT_QUESTION'),
            (lambda comparison: comparison.update(resolution='UNRESOLVED'), 'UNRESOLVED_JUDGMENT_CONDITION'),
            (lambda comparison: comparison.update(independent_disposition='NOT_MET'), 'INVALID_PRODUCT_REVIEW'),
        )
        for mutate, code in mutations:
            f = self.fixture().seal_through()
            f.bind()
            paths = reviews(self.roots, f.assessment)
            review = read_json(self.game / paths[0])
            mutate(review['condition_comparison'][0])
            self.write(paths[0], review)
            self.rejected(code, value.record, self.roots, value.paths(f.identity)['input'], paths)

    def test_changed_independent_finding_requires_explicit_justified_change(self):
        f = self.fixture().seal_through('evidence')
        draft = f.draft('independent_intent_experience')
        draft['findings']['conditions'][0].update(disposition='NOT_MET')
        draft['findings']['conditions'][0]['obligations'][1]['status'] = 'NOT_MET'
        f.seal('independent_intent_experience', draft)
        f.seal('independent_completeness_project')
        f.seal('decision')
        f.bind()
        paths = reviews(self.roots, f.assessment)
        review = read_json(self.game / paths[0])
        self.assertEqual(review['condition_comparison'][0]['resolution'], 'JUSTIFIED_CHANGE')
        review['condition_comparison'][0]['resolution'] = 'SAME_FINDING'
        self.write(paths[0], review)
        self.rejected('UNRESOLVED_JUDGMENT_CONDITION', value.record, self.roots, value.paths(f.identity)['input'], paths)


if __name__ == '__main__':
    unittest.main()
