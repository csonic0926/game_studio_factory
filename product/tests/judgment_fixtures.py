"""Synthetic protocol fixtures, not genuine model calls or semantic evidence.

All stage receipts are produced through packet/seal. Assessments stay unsealed
until a test has finished legitimate fixture setup; sealed stages are never
refreshed after a mutation to make stale work pass.
"""
from __future__ import annotations

import copy

from factory_core.refs import digest, encoded, read_json, reference, unique_refs
from product import judgment, value

CONDITION = (
    'For the declared buyer and offer, the finite experience must deliver '
    'consequential choices throughout and a rewarding whole purchase.'
)
OBLIGATIONS = [
    dict(id='consequential-throughout', kind='EXPERIENTIAL',
         proposition='The finite experience delivers consequential choices throughout.'),
    dict(id='whole-purchase', kind='EVALUATIVE',
         proposition='The complete experienced benefit justifies the full cost for this buyer.'),
]


def write(roots, path, body):
    target = roots['game'] / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encoded(body) if isinstance(body, dict) else body.encode())
    return reference(roots['game'], path)


class JudgmentFixture:
    """Build one explicit synthetic chain, with inspectable editable drafts."""

    def __init__(self, roots, assessment, *, reviewer_contexts=None):
        self.roots = roots
        self.assessment = assessment
        self.identity = assessment['assessment_id']
        self.base = f'design/product_value/{self.identity}/judgment'
        self.case_path = f'{self.base}/CASE.json'
        self.contexts = {
            'frame': 'synthetic-frame', 'evidence': 'synthetic-evidence',
            'decision': assessment['author_context_id'],
            **{'independent_' + role: role for role in value.ROLES},
        }
        for role, context in (reviewer_contexts or {}).items():
            self.contexts['independent_' + role] = context
        original = write(roots, f'{self.base}/original-task.md', CONDITION + '\n')
        sources = [original, *value._mandatory(roots),
                   *assessment['offer']['provenance'], *assessment['audience']['provenance']]
        if assessment['subject']['build'] is not None:
            sources.append(assessment['subject']['build'])
        sources.extend(e['reference'] for e in assessment['evidence'])
        self.case = dict(
            schema_version='product_judgment_case.v1', assessment_id=self.identity,
            question='Does this complete finite experience earn this declared whole offer?',
            subject=copy.deepcopy(assessment['subject']), offer=copy.deepcopy(assessment['offer']),
            audience=copy.deepcopy(assessment['audience']), mode='retrospective',
            exposure_note='Synthetic contract fixture; no real independent calls or observed taste are asserted.',
            sources=unique_refs(sources),
            conditions=[dict(id='whole-offer', text=CONDITION, source=original, quote=CONDITION)],
        )
        self.external_source = original
        if assessment['conditionality']:
            self.set_external_conditions(assessment['conditionality'])
        else:
            self.write_case()

    def set_external_conditions(self, conditions):
        if (self.roots['game'] / judgment.stage_path(self.identity, 'frame')).exists():
            raise ValueError('Declare synthetic external conditions before sealing the frame.')
        self.assessment['conditionality'] = list(conditions)
        self.external_source = write(self.roots, f'{self.base}/external-scenario.md',
                                     'Synthetic explicit external scenario conditions:\n' + '\n'.join(conditions) + '\n')
        retained = [ref for ref in self.case['sources'] if ref['path'] != self.external_source['path']]
        self.case['sources'] = unique_refs([*retained, self.external_source])
        self.write_case()
        return self

    def write_case(self):
        return write(self.roots, self.case_path, self.case)

    def packet(self, stage):
        return judgment.packet(self.roots, self.case_path, stage)

    def draft(self, stage):
        a = self.assessment
        status = a['judgment']
        assumptions = list(a['conditionality'])
        unknowns = list(a['material_unknowns'])
        disposition = ('CONDITIONAL' if assumptions else 'MET') if status == 'SUPPORTED' else (
            'NOT_MET' if status == 'VALUE_GAP' else 'UNRESOLVED')
        raw = [e['reference'] for e in a['evidence']]
        if not raw:
            raw = [self.case['conditions'][0]['source']]
        conditions = []
        for source_condition in self.case['conditions']:
            item = {k: source_condition[k] for k in ('id', 'text')}
            units = copy.deepcopy(OBLIGATIONS)
            if stage == 'frame':
                item.update(
                    meaning='Both sustained consequential experience and whole-offer sufficiency must hold.',
                    benefit='A complete finite sequence connects decisions to a satisfying conclusion.',
                    buyer_cost='The full price, attention, repetition and deliberate limits of this experience.',
                    sufficiency='The experienced whole must give this buyer a reason to choose the purchase.',
                    falsifier='Administrative repetition or an unrewarding whole defeats the compound case.',
                    basis='Preserve the literal raw task as synthetic authority; the bar is a value criterion.',
                    scope='This exact build, full finite experience, declared offer and same buyer.',
                    obligations=units,
                )
            elif stage == 'evidence':
                experiential = 'UNRESOLVED' if status in ('EVIDENCE_INSUFFICIENT', 'CONTEXT_UNRESOLVED') else 'SUPPORTED'
                for unit in units:
                    unit.update(claim_ids=['complete-sequence'] if unit['kind'] == 'EXPERIENTIAL' else [],
                                status='EVALUATIVE' if unit['kind'] == 'EVALUATIVE' else experiential,
                                reason='Observed scope supports the factual unit; whole-offer sufficiency remains an evaluation.'
                                if experiential == 'SUPPORTED' else 'The required experiential scope is not established.')
                item.update(
                    claims=[dict(id='complete-sequence', proposition=OBLIGATIONS[0]['proposition'],
                                 status=experiential, scope='The declared exact build and its finite complete sequence.',
                                 evidence=raw if experiential == 'SUPPORTED' else [],
                                 support_relation='The synthetic trace records choices and consequences through the ending.'
                                 if experiential == 'SUPPORTED' else 'The source does not resolve the missing experience.')],
                    benefits='Consequences connect the finite choices and conclusion where observed.',
                    costs='The buyer pays the full offer and encounters the same finite limits and repetition.',
                    shared_evidence='Both a positive and a negative value judgment may acknowledge these local choices.',
                    discriminators='Whole-sequence consequences establish scope; they do not mechanically settle worth.',
                    material_unknowns=unknowns, obligations=units,
                )
            else:
                for unit in units:
                    unit_status = 'MET' if disposition == 'CONDITIONAL' else disposition
                    if unit['kind'] == 'EXPERIENTIAL' and status in ('VALUE_GAP', 'JUDGMENT_UNRESOLVED'):
                        unit_status = 'MET'
                    unit.update(status=unit_status, reason=(
                        'The whole offer is not justified despite real choices and a complete finite structure.'
                        if status == 'VALUE_GAP' and unit['kind'] == 'EVALUATIVE' else
                        'The exact scoped unit has the declared synthetic finding, subject to retained assumptions and unknowns.'))
                item.update(
                    disposition=disposition,
                    positive_case='Connected choices and a finite conclusion provide a concrete local benefit.',
                    strongest_objection='The full price and repetition may outweigh that benefit for this same buyer.',
                    sufficiency_reason=(
                        'Despite genuine local choices, the experienced whole does not justify this buyer cost.'
                        if status == 'VALUE_GAP' else
                        'The connected full sequence earns this offer for this buyer under the explicit external scenario assumption.'
                        if disposition == 'CONDITIONAL' else
                        'The connected full sequence and payoff justify this finite purchase despite its limits.'
                        if disposition == 'MET' else
                        'The named unresolved experience or inference prevents a whole-offer conclusion.'),
                    assumptions=assumptions, material_unknowns=unknowns, evidence=raw, obligations=units,
                )
            conditions.append(item)
        findings = dict(conditions=conditions)
        if stage == 'frame':
            findings['whole_purchase_question'] = self.case['question']
            findings['external_conditions'] = [dict(condition=condition, source=self.external_source,
                                                    basis='The raw synthetic scenario declares this external condition before judgment.')
                                               for condition in assumptions]
        elif stage == 'evidence':
            findings['experience_scope'] = 'Synthetic exact-build finite sequence; no population or market outcome is claimed.'
        elif stage.startswith('independent_'):
            findings['frame_fidelity'] = dict(omitted_or_weakened_obligations=[],
                                             reason='Both original compound obligations and their whole-offer scope remain explicit.')
        elif stage == 'decision':
            findings.update(judgment=status, whole_purchase_reason=conditions[0]['sufficiency_reason'],
                            material_unknowns=unknowns, conditionality=assumptions,
                            next_move=a['next_move']['action'])
        return dict(schema_version='product_judgment_stage.v1', stage=stage,
                    context_id=self.contexts[stage], packet_digest=self.packet(stage)['packet_digest'],
                    extra_exposure=[], reopen_requests=[], findings=findings)

    def seal(self, stage, draft=None):
        draft = draft if draft is not None else self.draft(stage)
        path = f'{self.base}/draft-{stage}.json'
        write(self.roots, path, draft)
        return judgment.seal(self.roots, self.case_path, stage, path)

    def seal_through(self, final='decision'):
        for stage in judgment.STAGES:
            self.seal(stage)
            if stage == final:
                break
        return self

    def bind(self):
        self.assessment['deliberation'] = {
            'case': reference(self.roots['game'], self.case_path),
            **{stage: reference(self.roots['game'], judgment.stage_path(self.identity, stage))
               for stage in ('frame', 'evidence', 'decision')},
        }
        return write(self.roots, value.paths(self.identity)['input'], self.assessment)


def seal_assessment(roots, assessment, *, reviewer_contexts=None):
    if assessment.get('deliberation'):
        # Deliberately no rehash/reseal path. Mutations to admitted dependencies
        # must fail in the real validator, not become a newly passing fixture.
        return assessment
    fixture = JudgmentFixture(roots, assessment, reviewer_contexts=reviewer_contexts)
    fixture.seal_through().bind()
    return assessment


def reviews(roots, assessment):
    package = value.prepare(roots, value.paths(assessment['assessment_id'])['input'])
    result = []
    decision = read_json(roots['game'] / assessment['deliberation']['decision']['path'])
    for role in value.ROLES:
        first_ref = reference(roots['game'], judgment.stage_path(assessment['assessment_id'], 'independent_' + role))
        first = read_json(roots['game'] / first_ref['path'])
        comparisons = []
        for before, after in zip(first['findings']['conditions'], decision['findings']['conditions']):
            comparisons.append(dict(
                id=before['id'], text=before['text'], original_meaning_preserved=True,
                independent_disposition=before['disposition'], decision_disposition=after['disposition'],
                resolution='SAME_FINDING' if before['disposition'] == after['disposition'] else 'JUSTIFIED_CHANGE',
                reason='Synthetic comparison retains every original obligation and its exact scope.',
            ))
        review = dict(
            schema_version='product_value_review.v2', role=role, reviewer_context_id=first['context_id'],
            fresh=True, peer_reviews_read=[], assessment=package['assessment'],
            dependency_fingerprint=package['dependencies']['fingerprint'], verdict='AGREE',
            findings={key: dict(rationale='Synthetic contract finding, not a real value review.',
                                evidence=[assessment['report']]) for key in value.FINDINGS},
            source_coverage=[digest(ref) for ref in package['dependencies']['references'] if ref['scope'] != 'factory'],
            independent_first_pass=first_ref, condition_comparison=comparisons,
        )
        path = f"design/product_value/{assessment['assessment_id']}/reviews/{role}.json"
        write(roots, path, review)
        result.append(path)
    return result
