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
    d = load_design(roots, record['design'])  # Current design parser must also accept it.
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
    old_rules = read_json(GitFile(roots['factory'], 'factory_core/rule_map.json', factory_revision))
    for role in ('intent_experience', 'completeness_project'):
        required = {r['id'] for r in old_rules['rules'] if role in r['reviewers'] and
                    ('all' in r['capabilities'] or d['capability'] in r['capabilities']) and
                    'COLLABORATIVE' in r.get('modes', ['COLLABORATIVE'])} | set(d['requirements'])
        if required != requirement_ids(roots['factory'], d, role, 'COLLABORATIVE'):
            fail('CHANGED_REVIEW_REQUIREMENTS', 'applicable rule membership changed')
    check_reviews(roots, record['design'], d, old, record['reviews'], factory_revision)
    check_ruling(roots, record['ruling'], record['design'], old)
    return {'schema_version': 'factory_continuation_preview.v1', 'task_id': task_id,
            'checkpoint_sha256': predecessor, 'design': record['design'],
            'historical_factory_revision': factory_revision,
            'historical_dependency_fingerprint': old['fingerprint'],
            'current_dependencies': current, 'production_scope': d['production_scope'],
            'historical_reviews_are_current': False, 'delivery_eligible': False,
            'allowed_stage': 'PRODUCING', 'acceptance_authority_granted': False}


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
    return {'status': 'HISTORICAL_CONTRACT_CONTINUATION', 'receipt_sha256': receipt_hash,
            'task_id': task_id, 'stage': 'PRODUCING', 'summary': receipt['summary'],
            'design': current['design'],
            'historical_dependency_fingerprint': current['historical_dependency_fingerprint'],
            'artifacts': receipt['artifacts'], 'production_scope': current['production_scope'],
            'historical_reviews_are_current': False, 'delivery_eligible': False,
            'acceptance_authority_granted': False}


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
