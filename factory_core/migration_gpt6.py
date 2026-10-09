"""Explicit v1/v2 -> v3 opt-in transaction. No history rewriting or auto approval."""
from pathlib import Path
import difflib
import hashlib

from .astra import POINTER, WORKFLOW
from .migration import BEGIN, END, inventory, source_set, split_routing, replace_checked
from .refs import confined, digest, encoded, exclusive_json, fail, read_json, reference, revision, sha
from .state import PROJECT_PATH, identifier, project_lock, keys

JOURNAL = 'design/factory/.migration-gpt6.json'
RECEIPT = 'design/factory/ROUTING_RECEIPT.json'


def routing_block():
    return f'''{BEGIN}
## Game Studio Factory routing (managed; explicit GPT-6 workflow)

Resolve STUDIO_ROOT from design/STUDIO_FACTORY.local.md (legacy
 design/AI_FACTORY.local.md is a v1/v2 fallback only). Use that checkout's
factory.py inspect --project-root . first. Version 3 explicitly selects GPT-6;
MIGRATION_REQUIRED, MIGRATION_RECOVERY_REQUIRED and FACTORY_SOURCE_MISMATCH
block new work. Never silently downgrade or reinterpret historical rulings.

Read $STUDIO_ROOT/{WORKFLOW}, then the owning skill from that same root:
whole game: studio/skills/game-studio-factory/SKILL.md;
idea: idea/skills/idea-factory/SKILL.md;
gameplay: gameplay/skills/gameplay-factory/SKILL.md;
independent story: story/skills/game-story-factory/SKILL.md;
asset/sound: the respective docs/AI_CALLER_LANDING.md and existing CLI.
Globally installed skills are entry aliases, not a competing workflow source.

The continuing primary author designs and produces; context supplies complete
applicable authority and optional methods. This v3 process supersedes old
Factory-generated fixed workers, handoff formats, generic per-turn reviews and
whole-HEAD freshness, including those clauses in project authoring/sync docs.
It does not remove any project quality, semantic, product or human boundary.
One complete design receives two fresh independent reviews of the same version.
The human decision view projects that design, not another author/spec.
Continue fixing FAILs within authority; material changes return for USER ruling.


Game initialization uses setup.py init, establishing both Idea and Product intent.
Read design/product_value/PRODUCT_VALUE_INTENT.json as nonbinding planning context;
product-factory owns this early value target and later whole-product assessment.
Reconcile changed Idea sources and bind used intent as an explicit design input.
It never replaces commission, production approval or actual-build value evidence.

Product adoption, material design approval and gameplay acceptance remain USER
owned. Blind runtime observation and informed comparison remain isolated.
Technical success is not gameplay acceptance. Only new gameplay acceptance,
exact-build human playtest, applicable predecessor regression and no blockers
permit Accepted Playable Baseline promotion. Missing history is not a PASS.
Story can be independent of a game; engine landing is a separate adapter.
All project outputs stay in this project, never in the Factory checkout.
{END}
'''


def routed(body):
    split_routing(body)
    if BEGIN in body:
        start, end = body.index(BEGIN), body.index(END) + len(END)
        return body[:start] + routing_block().rstrip('\n') + body[end:]
    return body + ('\n' if body and not body.endswith('\n') else '') + routing_block()


def sources(game, authority):
    result = source_set(game, authority)
    for name in (PROJECT_PATH, RECEIPT, POINTER, '.gitignore', 'CLAUDE.md'):
        p = confined(game, name)
        result[name] = sha(p) if p.exists() else None
    # Checkpoint history is read-only but must not change under a pending opt-in.
    for path in (game / 'design/factory/checkpoints').glob('*/*.json'):
        result[path.relative_to(game).as_posix()] = sha(path)
    return result


def materialize(game, factory, metadata, receipt):
    from setup import render_pointer_file
    agents = confined(game, 'AGENTS.md')
    ignore = confined(game, '.gitignore')
    ignore_text = ignore.read_text() if ignore.exists() else ''
    if POINTER not in ignore_text.splitlines():
        ignore_text += ('\n' if ignore_text and not ignore_text.endswith('\n') else '') + POINTER + '\n'
    return {'AGENTS.md': routed(agents.read_text() if agents.exists() else '').encode(),
            POINTER: render_pointer_file(str(factory.resolve())).encode(),
            '.gitignore': ignore_text.encode(), RECEIPT: encoded(receipt), PROJECT_PATH: encoded(metadata)}


def preview(game, factory, project_id, authority_paths=()):
    identifier(project_id)
    if confined(game, 'design/factory/.migration.json').exists():
        fail('MIGRATION_RECOVERY_REQUIRED', 'finish the v2 transaction with its original workflow first')
    authority = sorted(set(authority_paths))
    pending = confined(game, JOURNAL)
    if pending.exists():
        j = read_json(pending)
        if (j['project_id'], j['authority_paths'], j['factory_root']) != (project_id, authority, str(factory.resolve())):
            fail('MIGRATION_CONFLICT', 'recovery must use the same target identity, authorities and checkout')
        return {'status': 'MIGRATION_RECOVERY_REQUIRED', 'source_digest': j['source_digest'], 'changes': list(j['targets'])}
    p = confined(game, PROJECT_PATH)
    old = read_json(p) if p.exists() else None
    if old:
        keys(old, {'schema_version', 'workflow_version', 'project_id', 'factory_revision', 'authority_paths', 'historical_inventory', 'migration_source_digest'})
        if (old['schema_version'], old['workflow_version']) not in (('factory_project.v2', 2), ('factory_project.v3', 3)):
            fail('MIGRATION_REQUIRED', 'unknown source contract, no guessed migration')
        if old['project_id'] != project_id or not set(old['authority_paths']).issubset(authority):
            fail('MIGRATION_CONFLICT', 'preserve project identity and all already adopted authorities')
    for name in authority:
        sha(confined(game, name))
    before = sources(game, authority)
    agents = confined(game, 'AGENTS.md')
    body = agents.read_text() if agents.exists() else ''
    new = routed(body)
    from setup import render_pointer_file
    expected_pointer = hashlib.sha256(render_pointer_file(str(factory.resolve())).encode()).hexdigest()
    if (old and old['workflow_version'] == 3 and old['authority_paths'] == authority
            and before[POINTER] == expected_pointer and new == body):
        return {'status': 'ALREADY_MIGRATED', 'source_digest': old['migration_source_digest'], 'changes': []}
    source_digest = digest({'sources': before, 'project_id': project_id, 'authority_paths': authority,
                            'factory_root': str(factory.resolve()), 'routing': routing_block(), 'workflow_version': 3})
    return {'status': 'MIGRATION_AVAILABLE', 'source_digest': source_digest,
            'changes': ['AGENTS.md', POINTER, '.gitignore', RECEIPT, PROJECT_PATH],
            'routing_diff': ''.join(difflib.unified_diff(body.splitlines(True), new.splitlines(True),
                                  fromfile='AGENTS.md (current)', tofile='AGENTS.md (GPT-6)')),
            'pointer_target': str(factory.resolve()), 'from_workflow': old['workflow_version'] if old else None,
            'to_workflow': 3, 'authority_paths': authority, 'history': inventory(game),
            'historical_rulings_reissued': False, 'game_content_changes': False, 'untracked_cleanup': False}


def apply(game, factory, project_id, expected, authority_paths=()):
    with project_lock(game):
        check = preview(game, factory, project_id, authority_paths)
        if check['status'] == 'ALREADY_MIGRATED':
            if expected != check['source_digest']:
                fail('CONCURRENT_WRITE', 'wrong migration receipt digest')
            return check
        if check['source_digest'] != expected:
            fail('CONCURRENT_WRITE', 'preview/source digest changed; inspect a new migration diff')
        pending = confined(game, JOURNAL)
        if pending.exists():
            journal = read_json(pending)
        else:
            before = sources(game, authority_paths)
            old = read_json(game / PROJECT_PATH) if before[PROJECT_PATH] else None
            body = (game / 'AGENTS.md').read_text() if before['AGENTS.md'] else ''
            metadata = {'schema_version': 'factory_project.v3', 'workflow_version': 3,
                        'project_id': project_id, 'factory_revision': revision(factory),
                        'authority_paths': sorted(set(authority_paths)),
                        'historical_inventory': inventory(game), 'migration_source_digest': expected}
            receipt = {'schema_version': 'factory_routing_receipt.v3', 'before_sha256': before['AGENTS.md'],
                       'after_sha256': hashlib.sha256(routed(body).encode()).hexdigest(),
                       'outside_routing_sha256': hashlib.sha256(split_routing(body).encode()).hexdigest(),
                       'source_digest': expected, 'predecessor_project_sha256': before[PROJECT_PATH],
                       'predecessor_receipt_sha256': before[RECEIPT], 'from_workflow': old['workflow_version'] if old else None}
            prior = read_json(game / RECEIPT) if before[RECEIPT] else {}
            receipt['predecessors'] = prior.get('predecessors', []) + ([{
                k: prior[k] for k in ('before_sha256', 'after_sha256', 'outside_routing_sha256')
            }] if prior else [])
            receipt['historical_tasks'] = (sorted({Path(n).parent.name for n in before if n.startswith('design/factory/checkpoints/')})
                if old and old['workflow_version'] == 2 else prior.get('historical_tasks', []))
            outputs = materialize(game, factory, metadata, receipt)
            journal = {'project_id': project_id, 'authority_paths': sorted(set(authority_paths)),
                       'factory_root': str(factory.resolve()), 'routing_digest': digest(routing_block()),
                       'source_digest': expected, 'sources': before, 'metadata': metadata, 'receipt': receipt,
                       'targets': {name: hashlib.sha256(data).hexdigest() for name, data in outputs.items()}}
            if preview(game, factory, project_id, authority_paths)['source_digest'] != expected:
                fail('CONCURRENT_WRITE', 'sources changed during complete preflight')
            exclusive_json(pending, journal)
        if journal['routing_digest'] != digest(routing_block()):
            fail('MIGRATION_IMPLEMENTATION_CHANGED', 'recover using the exact prepared routing implementation')
        check_sources(game, authority_paths, journal)
        outputs = materialize(game, factory, journal['metadata'], journal['receipt'])
        for name, data in outputs.items():
            if hashlib.sha256(data).hexdigest() != journal['targets'][name]:
                fail('MIGRATION_IMPLEMENTATION_CHANGED', f'prepared output changed: {name}')
        # Metadata activation is deliberately last; no success on partial output.
        for name, data in outputs.items():
            if name == PROJECT_PATH:
                check_sources(game, authority_paths, journal)
            path = confined(game, name)
            actual = sha(path) if path.exists() else None
            if actual != journal['targets'][name]:
                replace_checked(path, journal['sources'].get(name), data)
        for name, wanted in journal['targets'].items():
            if sha(confined(game, name)) != wanted:
                fail('CONCURRENT_WRITE', 'migration output changed before completion')
        check_sources(game, authority_paths, journal)
        pending.unlink()
        return {'status': 'MIGRATED', 'workflow_version': 3, 'source_digest': expected,
                'changes': list(outputs), 'historical_rulings_reissued': False, 'game_content_changes': False}


def check_sources(game, authority_paths, journal):
    current = sources(game, authority_paths)
    for name in set(current) | set(journal['sources']):
        if current.get(name) != journal['sources'].get(name) and current.get(name) != journal['targets'].get(name, 'NO_TARGET'):
            fail('CONCURRENT_WRITE', f'pending migration source changed: {name}')
