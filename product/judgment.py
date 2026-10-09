"""Separated judgment packets and declared-call admission, never a taste oracle.

The host/operator launches real fresh contexts. This module cannot authenticate
model calls or prevent extra filesystem reads; declarations are auditable inputs.
"""
from __future__ import annotations

import json
from pathlib import PurePosixPath

from factory_core.refs import (confined, digest, exclusive_json, fail, read_json,
                               reference, resolve_ref, unique_refs, expand_references)
from factory_core.state import identifier, keys, project_lock, text, texts

STAGES = ('frame', 'evidence', 'independent_intent_experience',
          'independent_completeness_project', 'decision')
DISPOSITIONS = ('MET', 'NOT_MET', 'UNRESOLVED', 'CONDITIONAL')
JUDGMENTS = ('SUPPORTED', 'VALUE_GAP', 'EVIDENCE_INSUFFICIENT',
             'JUDGMENT_UNRESOLVED', 'CONTEXT_UNRESOLVED')
INSTRUCTIONS = {
    'frame': 'Preserve the exact original question and every original condition. Decompose the buyer reason, experienced mechanism, whole-experience sufficiency and full buyer cost. Distinguish source fact, authority, hypothesis and evaluator criterion. Declare any external offer/buyer scenario conditions with raw-source basis before a verdict; never condition the answer on the buyer finding it worthwhile or on the original condition being true. Explain scope/quantifiers, support and falsification without choosing a purchase verdict. A finite form does not itself establish a sufficient purchase. Request upstream reopening for omissions or an unfair frame; do not quietly replace it.',
    'evidence': 'For each unchanged condition, determine what the raw experience supports, contradicts or leaves unresolved. Keep entity, build, time and population scope. Separate proposition truth from whether this evidence establishes it. Preserve local benefits AND the full contrary experience, shared evidence and actual discriminators. Identify material missing observations with opposing outcomes. Do not decide worth buying or turn absent proof of failure into affirmative sufficiency.',
    'independent': 'Before seeing the final report or evidence-stage interpretation, independently judge every original condition against all raw sources. Independently challenge the frame and its external conditions against the original raw task: circular taste assumptions cannot resolve the original sufficiency question; identify omitted or weakened obligations, not only the conditions the frame chose. Preserve exact scope and quantifiers. Explain the whole experience, strongest cost and positive sufficiency bridge, not merely whether a plausible preference exists. MET, NOT_MET, UNRESOLVED and CONDITIONAL are all legitimate. Do not impose replay, time/feature quotas or human willingness-to-pay proof. Seal this first pass before reading the completed assessment; no peer conclusions.',
    'decision': 'Use the frozen frame and evidence without changing their propositions, scope or unresolved states. Answer each original condition and the integrated purchase question for the same buyer/offer. Explain the experienced whole benefit, full strongest cost, and why the balance meets or defeats the original condition. Nonzero pleasures, finite structure and not proven bad do not establish sufficiency. A subjective judgment is legitimate if concretely grounded. Conditions may concern independently specified external context such as a scenario offer; a circular preference such as if this buyer finds these runs worth the price cannot establish the original sufficiency question. An ungrounded evaluative preference or unexplained whole-purchase inference stays UNRESOLVED, never CONDITIONAL support. New facts, weakened conditions or downgraded unknowns require reopening their owning upstream stage. Never close whole-product work merely because a narrower activity is worth retaining.',
}


def _contains_completed_output(value):
    if isinstance(value, dict):
        schema = value.get('schema_version', '')
        if isinstance(schema, str) and schema.startswith(('product_judgment_', 'product_value_assessment.', 'product_value_result.', 'product_value_review.')):
            return True
        return any(_contains_completed_output(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_completed_output(child) for child in value)
    return False


def stage_path(identity, stage):
    identifier(identity)
    if stage not in STAGES:
        fail('INVALID_JUDGMENT_STAGE', stage)
    return f'design/product_value/{identity}/judgment/{stage}.json'


def case(roots, case_path):
    from product.value import _refs, validate_context, _mandatory
    ref = reference(roots['game'], case_path)
    c = read_json(resolve_ref(roots, ref))
    keys(c, {'schema_version', 'assessment_id', 'question', 'subject', 'offer', 'audience',
             'mode', 'exposure_note', 'sources', 'conditions'})
    if c['schema_version'] != 'product_judgment_case.v1':
        fail('INVALID_JUDGMENT_CASE', 'explicit judgment case required')
    identifier(c['assessment_id']); text(c['question']); text(c['exposure_note'])
    if case_path != f"design/product_value/{c['assessment_id']}/judgment/CASE.json":
        fail('INVALID_JUDGMENT_CASE', 'case must use its assessment-owned path')
    if c['mode'] not in ('retrospective', 'prospective_new_observation'):
        fail('INVALID_JUDGMENT_CASE', 'declare prior exposure accurately')
    keys(c['subject'], {'title', 'build'}); text(c['subject']['title'])
    if c['subject']['build'] is not None:
        _refs(roots, [c['subject']['build']])
    validate_context(roots, c['offer'], c['audience'])
    _refs(roots, c['sources'])
    closure = expand_references(roots, c['sources'])
    context_sources = [*c['offer']['provenance'], *c['audience']['provenance']]
    if c['subject']['build'] is not None: context_sources.append(c['subject']['build'])
    if any(ref not in closure for ref in context_sources):
        fail('INCOMPLETE_JUDGMENT_SOURCES', 'include fixed build, offer and audience sources in the raw packet')
    for source in closure:
        path = PurePosixPath(source['path'])
        if path.name in ('PRODUCT_VALUE_ASSESSMENT.json', 'PRODUCT_VALUE_REPORT.md', 'PRODUCT_VALUE_RESULT.json') or ('design/product_value/' in source['path'] and 'reviews' in path.parts):
            fail('CONTAMINATED_JUDGMENT_SOURCES', 'raw inputs cannot contain completed assessment/report/review outputs')
        try:
            payload = json.loads(resolve_ref(roots, source).read_text(encoding='utf-8'))
        except (ValueError, UnicodeError):
            continue
        if _contains_completed_output(payload):
            fail('CONTAMINATED_JUDGMENT_SOURCES', 'raw inputs cannot contain labeled judgment or completed assessment outputs, regardless of suffix or transitive nesting')
    if any(r not in closure for r in _mandatory(roots)):
        fail('INCOMPLETE_JUDGMENT_SOURCES', 'include every mandatory authority in the raw packet')
    if not isinstance(c['conditions'], list) or not c['conditions']:
        fail('INVALID_JUDGMENT_CASE', 'preserve the original material conditions')
    seen = set()
    for item in c['conditions']:
        keys(item, {'id', 'text', 'source', 'quote'})
        identifier(item['id']); text(item['text']); text(item['quote'])
        if item['text'] != item['quote']:
            fail('CHANGED_JUDGMENT_QUESTION', 'canonical condition text must be the exact original source quote; interpret only in frame')
        if item['id'] in seen:
            fail('INVALID_JUDGMENT_CASE', 'duplicate condition')
        seen.add(item['id'])
        if item['source'] not in closure:
            fail('INVALID_JUDGMENT_CASE', 'original condition source must be in the packet')
        if item['quote'] not in resolve_ref(roots, item['source']).read_text(encoding='utf-8'):
            fail('INVALID_JUDGMENT_CASE', 'original condition quote is not in its exact source')
    return c, ref, closure


def _read(roots, c, stage):
    path = stage_path(c['assessment_id'], stage)
    ref = reference(roots['game'], path)
    record = read_json(resolve_ref(roots, ref))
    validate_stage(roots, f"design/product_value/{c['assessment_id']}/judgment/CASE.json", stage, record)
    return record, ref


def packet(roots, case_path, stage):
    c, case_ref, sources = case(roots, case_path)
    if stage not in STAGES:
        fail('INVALID_JUDGMENT_STAGE', stage)
    inputs = [case_ref, *sources]
    hidden_receipts = []
    if stage != 'frame':
        _, ref = _read(roots, c, 'frame'); inputs.append(ref)
    if stage == 'decision':
        _, ref = _read(roots, c, 'evidence'); inputs.append(ref)
        for role in STAGES[2:4]:
            _, first_ref = _read(roots, c, role)
            # Hashes attest dependency, not peer conclusions. Never expose the
            # first-pass files through the decision/review source closure.
            hidden_receipts.append(digest(first_ref))
    inputs = unique_refs(inputs)
    instruction = INSTRUCTIONS['independent' if stage.startswith('independent_') else stage]
    body = {'schema_version': 'product_judgment_packet.v1', 'stage': stage,
            'assessment_id': c['assessment_id'], 'question': c['question'],
            'instructions': instruction, 'inputs': inputs,
            'independence_receipts': hidden_receipts,
            'output_contract': reference(roots['factory'], 'product/docs/JUDGMENT_PIPELINE.md', 'factory'),
            'isolation': 'Fresh context; read only these complete inputs and this role instruction. No earlier answer, peer conclusions, sibling files or extra sources. Report extra exposure or request a packet revision instead of silently reading more. Operator-enforced, not sandbox-attested.'}
    return {**body, 'packet_digest': digest(body), 'mechanical_only': True}


def _conditions(c, values):
    if not isinstance(values, list):
        fail('INVALID_JUDGMENT_STAGE', 'conditions must be a list')
    expected = {x['id']: x['text'] for x in c['conditions']}
    if len(values) != len(expected) or {x.get('id'): x.get('text') for x in values} != expected:
        fail('CHANGED_JUDGMENT_QUESTION', 'retain every original condition id and exact text')


def _citations(roots, refs, sources):
    from product.value import _refs
    _refs(roots, refs, allow_empty=True)
    if any(ref not in sources for ref in refs):
        fail('INVALID_JUDGMENT_STAGE', 'cite raw packet sources, not outside evidence')


def validate_stage(roots, case_path, stage, record):
    c, _, sources = case(roots, case_path)
    expected = packet(roots, case_path, stage)
    keys(record, {'schema_version', 'stage', 'context_id', 'packet_digest', 'extra_exposure', 'reopen_requests', 'findings'})
    if record['schema_version'] != 'product_judgment_stage.v1' or record['stage'] != stage:
        fail('INVALID_JUDGMENT_STAGE', 'wrong stage contract')
    text(record['context_id'])
    if record['packet_digest'] != expected['packet_digest']:
        fail('STALE_JUDGMENT_STAGE', 'stage must consume the exact current packet')
    if record['extra_exposure'] != []:
        fail('CONTAMINATED_JUDGMENT_STAGE', 'preserve attempt and use a fresh unexposed context')
    if record['reopen_requests'] != []:
        fail('JUDGMENT_REOPEN_REQUIRED', 'repair earliest owning stage and rerun affected descendants before admission')
    f = record['findings']
    required = {'conditions'}
    if stage == 'frame': required |= {'whole_purchase_question', 'external_conditions'}
    if stage == 'evidence': required |= {'experience_scope'}
    if stage.startswith('independent_'): required |= {'frame_fidelity'}
    if stage == 'decision': required |= {'judgment', 'whole_purchase_reason', 'material_unknowns', 'conditionality', 'next_move'}
    keys(f, required); _conditions(c, f['conditions'])
    for item in f['conditions']:
        if stage == 'frame':
            fields = {'meaning', 'benefit', 'buyer_cost', 'sufficiency', 'falsifier', 'basis', 'scope', 'obligations'}
        elif stage == 'evidence':
            fields = {'claims', 'benefits', 'costs', 'shared_evidence', 'discriminators', 'material_unknowns', 'obligations'}
        else:
            fields = {'disposition', 'positive_case', 'strongest_objection', 'sufficiency_reason', 'assumptions', 'material_unknowns', 'evidence', 'obligations'}
        keys(item, {'id', 'text', *fields})
        if stage == 'frame':
            for field in fields - {'obligations'}: text(item[field])
            if not isinstance(item['obligations'], list) or not item['obligations']:
                fail('INVALID_JUDGMENT_STAGE', 'decompose the original causal and whole-experience obligations')
            seen = set()
            for obligation in item['obligations']:
                keys(obligation, {'id', 'proposition', 'kind'})
                identifier(obligation['id']); text(obligation['proposition'])
                if obligation['id'] in seen or obligation['kind'] not in ('EXPERIENTIAL', 'EVALUATIVE'):
                    fail('INVALID_JUDGMENT_STAGE', 'distinct explicit obligation units required')
                seen.add(obligation['id'])
        elif stage == 'evidence':
            for field in ('benefits', 'costs', 'shared_evidence', 'discriminators'): text(item[field])
            if not isinstance(item['claims'], list) or not item['claims']:
                fail('INVALID_JUDGMENT_STAGE', 'state the experiential propositions, including unresolved ones')
            ids = set()
            for claim in item['claims']:
                keys(claim, {'id', 'proposition', 'status', 'scope', 'evidence', 'support_relation'})
                identifier(claim['id'])
                if claim['id'] in ids or claim['status'] not in ('SUPPORTED', 'CONTRADICTED', 'UNRESOLVED'):
                    fail('INVALID_JUDGMENT_STAGE', 'distinct claim IDs and epistemic states required')
                ids.add(claim['id'])
                for field in ('proposition', 'scope', 'support_relation'): text(claim[field])
                _citations(roots, claim['evidence'], sources)
                if claim['status'] != 'UNRESOLVED' and not claim['evidence']:
                    fail('INVALID_JUDGMENT_STAGE', 'resolved factual claims need raw evidence')
            texts(item['material_unknowns'])
        else:
            if item['disposition'] not in DISPOSITIONS:
                fail('INVALID_JUDGMENT_STAGE', 'invalid condition disposition')
            for field in ('positive_case', 'strongest_objection', 'sufficiency_reason'): text(item[field])
            texts(item['assumptions']); texts(item['material_unknowns'])
            _citations(roots, item['evidence'], sources)
            if item['disposition'] == 'MET' and item['material_unknowns']:
                fail('UNRESOLVED_JUDGMENT_CONDITION', 'MET cannot hide material unknowns')
            if item['disposition'] == 'CONDITIONAL' and not item['assumptions']:
                fail('INVALID_JUDGMENT_STAGE', 'CONDITIONAL needs its actual truth condition')
    if stage.startswith('independent_'):
        keys(f['frame_fidelity'], {'omitted_or_weakened_obligations', 'reason'})
        text(f['frame_fidelity']['reason'])
        if f['frame_fidelity']['omitted_or_weakened_obligations'] != []:
            fail('JUDGMENT_REOPEN_REQUIRED', 'independent frame challenge requires upstream repair')
    if stage == 'frame':
        text(f['whole_purchase_question'])
        if f['whole_purchase_question'] != c['question']:
            fail('CHANGED_JUDGMENT_QUESTION', 'frame must retain the exact original whole-purchase question')
        if not isinstance(f['external_conditions'], list):
            fail('INVALID_JUDGMENT_STAGE', 'external conditions must be explicit before the verdict')
        seen = set()
        for condition in f['external_conditions']:
            keys(condition, {'condition', 'source', 'basis'})
            text(condition['condition']); text(condition['basis'])
            _citations(roots, [condition['source']], sources)
            if condition['condition'] in seen:
                fail('INVALID_JUDGMENT_STAGE', 'duplicate external condition')
            seen.add(condition['condition'])
    if stage == 'evidence': text(f['experience_scope'])
    if stage != 'frame':
        frame, _ = _read(roots, c, 'frame')
        external = [x['condition'] for x in frame['findings']['external_conditions']]
        originals = {x['id']: x for x in frame['findings']['conditions']}
        for item in f['conditions']:
            if stage != 'evidence' and not set(item['assumptions']).issubset(external):
                fail('CHANGED_JUDGMENT_QUESTION', 'decision/reviewer cannot invent new conditional buyer preferences; reopen frame')
            obligations = item['obligations']
            expected_units = {o['id']: (o['proposition'], o['kind']) for o in originals[item['id']]['obligations']}
            if not isinstance(obligations, list) or len(obligations) != len(expected_units) or {o.get('id'): (o.get('proposition'), o.get('kind')) for o in obligations} != expected_units:
                fail('CHANGED_JUDGMENT_QUESTION', 'preserve each compound-condition obligation, including quantified and whole-experience parts')
            for obligation in obligations:
                fields = {'id', 'proposition', 'kind', 'status', 'reason'}
                if stage == 'evidence': fields.add('claim_ids')
                keys(obligation, fields)
                text(obligation['reason'])
                if stage == 'evidence':
                    claim_ids = texts(obligation['claim_ids'])
                    claims = {claim['id']: claim for claim in item['claims']}
                    if len(set(claim_ids)) != len(claim_ids) or any(i not in claims for i in claim_ids):
                        fail('INVALID_JUDGMENT_STAGE', 'obligation dependencies must name distinct existing factual claims')
                    if obligation['kind'] == 'EXPERIENTIAL' and not claim_ids:
                        fail('INVALID_JUDGMENT_STAGE', 'experiential obligations need explicit factual-premise dependencies')
                    matching = [claim for claim in item['claims'] if claim['proposition'] == obligation['proposition']]
                    if obligation['status'] == 'SUPPORTED' and (any(claims[i]['status'] != 'SUPPORTED' for i in claim_ids) or any(claim['status'] != 'SUPPORTED' for claim in matching)):
                        fail('UNRESOLVED_JUDGMENT_CONDITION', 'an obligation cannot promote its unresolved or contradicted factual premises')
                allowed = ('SUPPORTED', 'CONTRADICTED', 'UNRESOLVED', 'EVALUATIVE') if stage == 'evidence' else DISPOSITIONS
                if stage != 'evidence' and obligation['kind'] == 'EVALUATIVE' and obligation['status'] == 'CONDITIONAL':
                    fail('UNRESOLVED_JUDGMENT_CONDITION', 'a conditional evaluative preference cannot establish whole-purchase sufficiency')
                if obligation['status'] not in allowed or (stage == 'evidence' and (obligation['status'] == 'EVALUATIVE') != (obligation['kind'] == 'EVALUATIVE')):
                    fail('INVALID_JUDGMENT_STAGE', 'evidence cannot settle a value obligation as fact')
            if stage != 'evidence' and item['disposition'] == 'MET' and any(o['status'] != 'MET' for o in obligations):
                fail('UNRESOLVED_JUDGMENT_CONDITION', 'MET must resolve every original obligation')
            if stage != 'evidence' and item['disposition'] == 'CONDITIONAL' and any(o['status'] in ('UNRESOLVED', 'NOT_MET') for o in obligations):
                fail('UNRESOLVED_JUDGMENT_CONDITION', 'conditional taste cannot launder unresolved experience or inference')
        if record['context_id'] == frame['context_id']:
            fail('JUDGMENT_NOT_INDEPENDENT', 'frame and downstream judgment require distinct actual contexts')
    if stage == 'decision':
        evidence, _ = _read(roots, c, 'evidence')
        first = [_read(roots, c, s)[0] for s in STAGES[2:4]]
        contexts = [record['context_id'], frame['context_id'], evidence['context_id'], *[r['context_id'] for r in first]]
        if len(set(contexts)) != 5:
            fail('JUDGMENT_NOT_INDEPENDENT', 'five distinct frame/evidence/decision/reviewer contexts required')
        if f['judgment'] not in JUDGMENTS: fail('INVALID_JUDGMENT_STAGE', 'invalid judgment')
        text(f['whole_purchase_reason']); text(f['next_move'])
        if f['conditionality'] != external:
            fail('CHANGED_JUDGMENT_QUESTION', 'preserve exactly the independently framed external conditions; no final-author conditionality escape')
        texts(f['material_unknowns']); texts(f['conditionality'])
        for observed, decided in zip(sorted(evidence['findings']['conditions'], key=lambda x:x['id']), sorted(f['conditions'], key=lambda x:x['id'])):
            premise_states = {o['id']: o for o in observed['obligations']}
            factual_states = {claim['id']: claim['status'] for claim in observed['claims']}
            for unit in decided['obligations']:
                prior = premise_states[unit['id']]
                if unit['status'] in ('MET', 'CONDITIONAL') and any(factual_states[i] != 'SUPPORTED' for i in prior['claim_ids']):
                    fail('UNRESOLVED_JUDGMENT_CONDITION', 'neither experiential nor evaluative conclusions may upgrade unresolved necessary facts')
                if prior['kind'] == 'EXPERIENTIAL' and prior['status'] != 'SUPPORTED' and unit['status'] in ('MET', 'CONDITIONAL'):
                    fail('UNRESOLVED_JUDGMENT_CONDITION', 'decision cannot upgrade unresolved or contradicted experiential premises; reopen evidence')
            if not set(observed['material_unknowns']).issubset(decided['material_unknowns']):
                fail('UNRESOLVED_JUDGMENT_CONDITION', 'decision cannot downgrade upstream material unknowns; reopen evidence')
            if not set(decided['material_unknowns']).issubset(f['material_unknowns']):
                fail('UNRESOLVED_JUDGMENT_CONDITION', 'carry every material unknown into the verdict')
            if not set(decided['assumptions']).issubset(f['conditionality']):
                fail('UNRESOLVED_JUDGMENT_CONDITION', 'essential assumptions must qualify the verdict')
        if f['judgment'] == 'SUPPORTED' and (f['material_unknowns'] or any(x['disposition'] not in ('MET', 'CONDITIONAL') for x in f['conditions'])):
            fail('UNRESOLVED_JUDGMENT_CONDITION', 'SUPPORTED cannot close an unmet or unresolved original condition')
    return record


def seal(roots, case_path, stage, input_path):
    with project_lock(roots['game']):
        c, _, _ = case(roots, case_path)
        record = read_json(confined(roots['game'], input_path))
        validate_stage(roots, case_path, stage, record)
        path = stage_path(c['assessment_id'], stage)
        target = confined(roots['game'], path)
        if target.exists():
            if read_json(target) != record:
                fail('IMMUTABLE_JUDGMENT_STAGE', 'preserve first outputs; reopen with a new assessment ID')
        else:
            exclusive_json(target, record)
        return {'status': 'JUDGMENT_STAGE_SEALED', 'stage': reference(roots['game'], path),
                'mechanical_only': True, 'semantic_success_proven': False}


def validate_assessment(roots, assessment):
    refs = assessment['deliberation']
    keys(refs, {'case', 'frame', 'evidence', 'decision'})
    from product.value import _refs
    _refs(roots, list(refs.values()))
    c, case_ref, sources = case(roots, refs['case']['path'])
    if any(e['reference'] not in sources for e in assessment['evidence']):
        fail('INCOMPLETE_JUDGMENT_SOURCES', 'new assessment evidence requires upstream reopening; every source must reach prior owners')
    if case_ref != refs['case'] or c['assessment_id'] != assessment['assessment_id']:
        fail('INVALID_JUDGMENT_CASE', 'assessment and case identity must match')
    for field in ('subject', 'offer', 'audience'):
        if c[field] != assessment[field]: fail('CHANGED_JUDGMENT_QUESTION', 'assessment cannot change fixed build/buyer/offer')
    records = {}
    for stage in ('frame', 'evidence', 'decision'):
        records[stage], ref = _read(roots, c, stage)
        if ref != refs[stage]: fail('STALE_JUDGMENT_STAGE', 'assessment must bind current exact stage')
    decision = records['decision']
    if decision['context_id'] != assessment['author_context_id']:
        fail('JUDGMENT_NOT_INDEPENDENT', 'assessment author must be the actual decision context')
    for field in ('judgment', 'material_unknowns', 'conditionality'):
        if decision['findings'][field] != assessment[field]:
            fail('CHANGED_JUDGMENT_QUESTION', 'report cannot silently change the sealed decision')
    return c


def validate_review(roots, a, review):
    c = validate_assessment(roots, a)
    stage = 'independent_' + review['role']
    first, ref = _read(roots, c, stage)
    if review['independent_first_pass'] != ref or review['reviewer_context_id'] != first['context_id']:
        fail('JUDGMENT_NOT_INDEPENDENT', 'final reviewer must bind its own previously sealed independent first pass')
    comparisons = review['condition_comparison']
    _conditions(c, comparisons)
    decision, _ = _read(roots, c, 'decision')
    before = {x['id']: x for x in first['findings']['conditions']}
    after = {x['id']: x for x in decision['findings']['conditions']}
    for item in comparisons:
        keys(item, {'id', 'text', 'original_meaning_preserved', 'independent_disposition', 'decision_disposition', 'resolution', 'reason'})
        if item['original_meaning_preserved'] is not True:
            fail('CHANGED_JUDGMENT_QUESTION', 'original scope/quantifier weakening requires revision')
        if item['independent_disposition'] != before[item['id']]['disposition'] or item['decision_disposition'] != after[item['id']]['disposition']:
            fail('INVALID_PRODUCT_REVIEW', 'compare actual independent and final dispositions')
        if item['resolution'] not in ('SAME_FINDING', 'JUSTIFIED_CHANGE'):
            fail('UNRESOLVED_JUDGMENT_CONDITION', 'unresolved semantic disagreement cannot receive AGREE')
        if item['independent_disposition'] != item['decision_disposition'] and item['resolution'] != 'JUSTIFIED_CHANGE':
            fail('UNRESOLVED_JUDGMENT_CONDITION', 'changed findings require an explicit grounded semantic reason')
        text(item['reason'])
