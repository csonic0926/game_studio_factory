"""Explicit production-only continuation under an unchanged historical contract.

Never rewrites a checkpoint, review, ruling or dependency hash. The old proof is
verified as old proof; a separate USER-selected receipt binds current resolution.
Normal checkpoint and acceptance validators are deliberately not relaxed.
"""
from pathlib import Path
import hashlib

from .refs import (GitFile, confined, digest, exclusive_json, fail, read_json,
                   reference, resolve_ref, sha)
from .state import (check_reviews, check_ruling, dependencies, identifier, latest,
                    load_design, project, project_lock, requirement_ids, text, ensure_current_task)


PLAYER_TEXT_RULE = 'player_text.complete_coverage_and_meaning'
UI_GENRE_RULE = 'ui.genre_expectation_audit'
UI_EXPERIENCE_RULES = frozenset({
    UI_GENRE_RULE, 'ui.presentation_semantics_and_goals',
    'ui.capture_first_and_proportionate_review', 'ui.feedback_disposition_and_retest'})
UI_EXPERIENCE_SOURCES = frozenset({
    'ui/experience.py', 'ui/readiness.py', 'ui/visual.py',
    'ui/schemas/ui_experience.schema.json', 'ui/docs/UI_EXPERIENCE_WORKFLOW.md',
    'ui/godot_engine/capture.gd'})


def _legacy_ui_experience_contract(roots, record, old_rules):
    """Recognize pre-feature Studio/Gameplay history, not reviewed UI NONE.

    The caller first verifies the complete original closure. Only the new genre
    rule shared with Studio/Gameplay can be deferred; UI-owned experience rules
    and every explicit current binding remain outside this narrow exception.
    """
    d = read_json(resolve_ref(roots, record['design']))
    binding = d.get('ui', {})
    if (d.get('schema_version') != 'factory_design.v3'
            or d.get('capability') not in ('studio', 'gameplay')
            or not isinstance(binding, dict) or 'experience' in binding):
        return None
    paths = {r['path'] for r in record['dependencies']['references']
             if r['scope'] == 'factory'}
    if (not {'factory_core/schemas/design_v3.schema.json', 'factory_core/rule_map.json'} <= paths
            or paths & UI_EXPERIENCE_SOURCES
            or any(r['id'] in UI_EXPERIENCE_RULES for r in old_rules['rules'])):
        return None
    schema = read_json(GitFile(roots['factory'], 'factory_core/schemas/design_v3.schema.json',
                               record['factory_revision']))
    ui_schema = schema.get('properties', {}).get('ui', {})
    # An indirect/compound old UI schema is not proof of feature absence.
    if (not isinstance(ui_schema, dict)
            or any(k in ui_schema for k in ('$ref', 'allOf', 'anyOf', 'oneOf'))
            or 'experience' in ui_schema.get('properties', {})):
        return None
    return {'schema_version': 'ui_experience_historical_production_compatibility.v1',
            'historical_applicability': 'UNDECLARED_PRE_FEATURE_NOT_REVIEWED_NONE',
            'deferred_current_review_requirements': [UI_GENRE_RULE],
            'allowed_stage': 'PRODUCING',
            'current_adoption_required_before': ['NEW_DESIGN', 'EVIDENCE_READY', 'COMPLETE',
                                                 'WHOLE_GAME_HANDOFF'],
            'normal_UI_applicability_reviews_and_evidence_not_waived': True,
            'explicit_UI_bindings_validated_normally': True}


def _legacy_player_text_contract(roots, record, old_rules):
    """Identify one pre-feature contract, not a general parser/rule waiver.

    Called only after every historical dependency has been verified. Feature
    support in either old schema, rule membership or closure defeats eligibility.
    The unchanged design remains undeclared, never reclassified as reviewed NONE.
    """
    d = read_json(resolve_ref(roots, record['design']))
    from player_text.workflow import PRODUCERS
    if (d.get('schema_version') != 'factory_design.v3' or d.get('capability') not in PRODUCERS
            or 'player_text' in d):
        return None
    refs = record['dependencies']['references']
    paths = {r['path'] for r in refs if r['scope'] == 'factory'}
    if (not {'factory_core/schemas/design_v3.schema.json', 'factory_core/rule_map.json'} <= paths
            or any(p.startswith('player_text/') for p in paths)):
        return None
    schema = read_json(GitFile(roots['factory'], 'factory_core/schemas/design_v3.schema.json',
                               record['factory_revision']))
    if ('player_text' in schema.get('properties', {})
            or any(r['id'] == PLAYER_TEXT_RULE for r in old_rules['rules'])):
        return None
    return {'schema_version': 'player_text_historical_production_compatibility.v1',
            'historical_applicability': 'UNDECLARED_PRE_FEATURE_NOT_REVIEWED_NONE',
            'deferred_current_review_requirements': [PLAYER_TEXT_RULE],
            'allowed_stage': 'PRODUCING',
            'current_adoption_required_before': ['NEW_DESIGN', 'EVIDENCE_READY', 'COMPLETE',
                                                  'WHOLE_GAME_HANDOFF'],
            'normal_applicability_reviews_and_latest_text_evidence_not_waived': True}


def audit(roots, task_id):
    """Read-only preflight. Output artifacts of the old checkpoint are NOT revived."""
    from .authorship import mode
    if project(roots['game'])['workflow_version'] != 3 or mode(roots) != 'COLLABORATIVE':
        fail('CONTINUATION_NOT_APPLICABLE', 'only an already authorized collaborative v3 task may continue')
    ensure_current_task(roots['game'], task_id)
    register = confined(roots['game'], 'design/product/PRODUCT_AUTHORITY_REGISTER.json')
    if register.exists() and read_json(register).get('status') != 'ACTIVE':
        fail('NO_ACTIVE_PRODUCT_AUTHORITY', 'continuation never revives archived product authority')
    record, predecessor = latest(roots['game'], identifier(task_id))
    if not record or record['stage'] != 'PRODUCING' or record.get('unresolved'):
        fail('CONTINUATION_NOT_APPLICABLE', 'requires the latest unblocked PRODUCING checkpoint')
    old = record['dependencies']
    if old.get('algorithm') != 'sha256-content-closure.v2' or digest(old['references']) != old['fingerprint']:
        fail('INVALID_CHECKPOINT', 'invalid historical dependency fingerprint')
    factory_revision = record['factory_revision']
    # Verify the full historical closure, not merely the review evidence subset.
    for ref in old['references']:
        if ref['scope'] == 'factory':
            raw = GitFile(roots['factory'], ref['path'], factory_revision).read_bytes()
            if hashlib.sha256(raw).hexdigest() != ref['sha256']:
                fail('STALE_DEPENDENCY', 'historical Factory bytes mismatch: ' + ref['path'])
        else:
            resolve_ref(roots, ref)  # Any game/authority/design mutation fails closed.
    old_rules = read_json(GitFile(roots['factory'], 'factory_core/rule_map.json', factory_revision))
    compatibility = _legacy_player_text_contract(roots, record, old_rules)
    ui_compatibility = _legacy_ui_experience_contract(
        roots, {**record, 'factory_revision': factory_revision}, old_rules)
    d = load_design(roots, record['design'], _legacy_player_text=bool(compatibility))
    current = dependencies(roots, record['design'], d)
    from .astra import selected_methods
    for ref in selected_methods(roots['factory'], d['capability'], d['task'], d.get('methods', [])):
        if ref not in old['references']:
            fail('CHANGED_METHOD', 'selected method content changed; design boundary required')
    old_game = [r for r in old['references'] if r['scope'] != 'factory']
    if any(r not in old_game for r in current['references'] if r['scope'] != 'factory'):
        fail('NEW_PROJECT_DEPENDENCY', 'new project authority/input needs its own design boundary')
    # Requirement membership may not silently change. Historical sources remain
    # historical even where current docs have moved or gained explanations.
    for role in ('intent_experience', 'completeness_project'):
        required = {r['id'] for r in old_rules['rules'] if role in r['reviewers'] and
                    ('all' in r['capabilities'] or d['capability'] in r['capabilities']) and
                    3 in r.get('workflow_versions', (2, 3)) and
                    'COLLABORATIVE' in r.get('modes', ['COLLABORATIVE'])} | set(d['requirements'])
        current_required = requirement_ids(roots['factory'], d, role, 'COLLABORATIVE')
        deferred = {PLAYER_TEXT_RULE} if compatibility else set()
        if ui_compatibility:
            deferred.add(UI_GENRE_RULE)
        if (required - current_required or current_required - required != deferred):
            fail('CHANGED_REVIEW_REQUIREMENTS', 'applicable rule membership changed')
    check_reviews(roots, record['design'], d, old, record['reviews'], factory_revision)
    check_ruling(roots, record['ruling'], record['design'], old)
    value = {'schema_version': 'factory_continuation_preview.v1', 'task_id': task_id,
            'checkpoint_sha256': predecessor, 'design': record['design'],
            'historical_factory_revision': factory_revision,
            'historical_dependency_fingerprint': old['fingerprint'],
            'current_dependencies': current, 'production_scope': d['production_scope'],
            'historical_reviews_are_current': False, 'delivery_eligible': False,
            'allowed_stage': 'PRODUCING', 'acceptance_authority_granted': False}
    if compatibility:
        value['compatibility_obligations'] = compatibility
    if ui_compatibility:
        value['ui_compatibility_obligations'] = ui_compatibility
    return value


def preview(roots, task_id):
    value = audit(roots, task_id)
    return {'status': 'CONTINUATION_PREVIEW', 'expected': digest(value), 'preview': value}


def _directory(roots, task_id):
    return confined(roots['game'], 'design/factory/continuations/' + identifier(task_id))


def latest_receipt(roots, task_id):
    paths = sorted(_directory(roots, task_id).glob('*.json'))
    previous = None
    value = None
    for generation, path in enumerate(paths, 1):
        value = read_json(path)
        if (path.name != f'{generation:06d}.json' or value.get('generation') != generation
                or value.get('previous') != previous or value.get('task_id') != task_id
                or value.get('schema_version') != 'factory_continuation.v1'):
            fail('INVALID_CONTINUATION', 'broken append-only continuation chain')
        previous = sha(path)
    return value, previous


def verify(roots, task_id):
    receipt, receipt_hash = latest_receipt(roots, task_id)
    if receipt is None:
        fail('CONTINUATION_REQUIRED', 'no explicit production continuation receipt')
    current = audit(roots, task_id)
    if receipt['preview'] != current or receipt['expected'] != digest(current):
        fail('STALE_CONTINUATION', 'checkpoint, design, authority or Factory closure changed')
    source = read_json(resolve_ref(roots, receipt['source']))
    quote = text(receipt['quote'])
    if source.get('role') != 'user' or source.get('content', '').strip() != quote.strip():
        fail('INVALID_RULING_SOURCE', 'continuation requires the exact raw USER submission')
    for ref in receipt['artifacts']:
        if ref['scope'] != 'game' or ref['path'] not in current['production_scope']:
            fail('OUT_OF_SCOPE', 'invalid continuation output scope')
        resolve_ref(roots, ref)
    value = {'status': 'HISTORICAL_CONTRACT_CONTINUATION', 'receipt_sha256': receipt_hash,
            'task_id': task_id, 'stage': 'PRODUCING', 'summary': receipt['summary'],
            'design': current['design'],
            'historical_dependency_fingerprint': current['historical_dependency_fingerprint'],
            'artifacts': receipt['artifacts'], 'production_scope': current['production_scope'],
            'historical_reviews_are_current': False, 'delivery_eligible': False,
            'acceptance_authority_granted': False}
    if 'compatibility_obligations' in current:
        value['compatibility_obligations'] = current['compatibility_obligations']
    if 'ui_compatibility_obligations' in current:
        value['ui_compatibility_obligations'] = current['ui_compatibility_obligations']
    return value


def apply(roots, task_id, expected, source_path, quote, summary, artifacts=()):
    """Publish only after explicit source-bound selection of this exact preview.

    This USER message selects compatibility treatment, not a new design approval.
    The operator must retain the preceding request as provenance alongside it.
    """
    with project_lock(roots['game']):
        value = audit(roots, task_id)
        if digest(value) != expected:
            fail('CONCURRENT_WRITE', 'continuation preview changed')
        source_ref = reference(roots['game'], source_path)
        source = read_json(resolve_ref(roots, source_ref))
        if source.get('role') != 'user' or source.get('content', '').strip() != text(quote).strip():
            fail('INVALID_RULING_SOURCE', 'exact raw USER compatibility submission required')
        refs = [reference(roots['game'], path) for path in artifacts]
        for ref in refs:
            if ref['path'] not in value['production_scope']:
                fail('OUT_OF_SCOPE', 'continuation artifacts must be approved production outputs')
        prior, prior_hash = latest_receipt(roots, task_id)
        generation = prior['generation'] + 1 if prior else 1
        result = {'schema_version': 'factory_continuation.v1', 'task_id': task_id,
                  'generation': generation, 'previous': prior_hash, 'preview': value,
                  'expected': expected, 'source': source_ref, 'quote': quote,
                  'summary': text(summary), 'artifacts': refs}
        # Recheck all live inputs immediately before append-only publication.
        if audit(roots, task_id) != value or reference(roots['game'], source_path) != source_ref:
            fail('CONCURRENT_WRITE', 'continuation inputs changed before publication')
        for ref in refs:
            resolve_ref(roots, ref)
        relative = f'design/factory/continuations/{task_id}/{generation:06d}.json'
        exclusive_json(confined(roots['game'], relative), result)
        return {'status': 'CONTINUATION_SAVED', 'receipt': reference(roots['game'], relative),
                'historical_reviews_are_current': False, 'delivery_eligible': False}
