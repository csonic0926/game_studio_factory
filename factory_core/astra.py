"""Small GPT-6 contract adapter, not a model runner or approval authority."""
from pathlib import Path
import re

from .refs import confined, fail, read_json, reference, resolve_ref

WORKFLOW = 'factory_core/docs/WORKFLOW_GPT6.md'
CATALOG = 'factory_core/knowledge.json'
POINTER = 'design/STUDIO_FACTORY.local.md'


def check_checkout(project, factory):
    path = confined(project, POINTER)
    if not path.is_file():
        fail('FACTORY_SOURCE_REQUIRED', 'v3 needs its explicit local checkout pointer; relink with the selected GPT-6 checkout')
    values = re.findall(r'^STUDIO_ROOT:\s*(.+?)\s*$', path.read_text(), re.M)
    if len(values) != 1 or Path(values[0]).expanduser().resolve() != factory.resolve():
        fail('FACTORY_SOURCE_MISMATCH', 'use the checkout selected by the project; migration/relink must be explicit')


def catalog(factory, capability, task):
    from .catalog import CAPABILITIES, STORY_TASKS
    if capability not in CAPABILITIES:
        fail('UNKNOWN_CAPABILITY', capability)
    task = 'beat-sheet' if task == 'beatsheet' else task
    if capability == 'story' and task not in STORY_TASKS:
        fail('UNKNOWN_TASK', 'Story task must name a supported capability')
    return [m for m in read_json(factory / CATALOG)['methods']
            if capability in m['capabilities'] and ('*' in m['tasks'] or task in m['tasks'])]


def selected_methods(factory, capability, task, ids):
    if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
        fail('UNKNOWN_METHOD', 'method ids must be a unique list')
    available = {m['id']: m for m in catalog(factory, capability, task)}
    if set(ids) - set(available):
        fail('UNKNOWN_METHOD', 'method is unknown or belongs to another capability/task')
    return [reference(factory, available[key]['source'], 'factory') for key in sorted(ids)]


def rule_source(rule):
    """Stable rule ids retain ownership; only the superseded process source moves."""
    source = rule['source']
    if source == 'factory_core/docs/WORKFLOW.md':
        return WORKFLOW
    if source == 'story/docs/WORKFLOW_V2.md':
        return 'story/docs/WORKFLOW_GPT6.md'
    return source


def docs(capability):
    from .catalog import DOCS
    result = list(DOCS[capability])
    if capability in ('studio', 'gameplay', 'story'):
        result[0] = f'{capability}/docs/WORKFLOW_GPT6.md'
    if capability == 'story':
        result = ['story/docs/WORKFLOW_GPT6.md', 'story/core/NARRATIVE_FOUNDATIONS.md']
    if capability == 'idea':
        result.insert(0, 'idea/docs/WORKFLOW_GPT6.md')
    from player_text.workflow import PRODUCERS
    if capability in PRODUCERS:
        result.append('player_text/WORKFLOW.md')
    return result


def validate_sections(roots, design):
    """Exact full sections are projected, not rewritten Card summaries.

    Named sections cover the human decision surface, including composition.
    Reviewers still judge material completeness: strings alone cannot prove it.
    """
    from .state import keys, text
    sections = design.get('decision_sections')
    if not isinstance(sections, list) or not sections:
        fail('INCOMPLETE_DECISION_VIEW', 'v3 requires exact decision sections, not only chosen snippets')
    seen = set()
    for section in sections:
        keys(section, {'id', 'source', 'text', 'decision_ids'})
        identity = text(section['id'])
        if identity in seen:
            fail('INCOMPLETE_DECISION_VIEW', 'duplicate decision section')
        seen.add(identity)
        if section['source'] not in design['artifacts']:
            fail('INCOMPLETE_DECISION_VIEW', 'decision section must come from the sealed authored design')
        if text(section['text']) not in resolve_ref(roots, section['source']).read_text():
            fail('INCOMPLETE_DECISION_VIEW', 'decision section is not an exact original excerpt')
        ids = section['decision_ids']
        decisions = {x['id']: x for x in design['decisions']}
        if not isinstance(ids, list) or not ids or any(i not in decisions for i in ids):
            fail('INCOMPLETE_DECISION_VIEW', 'section needs known material decision ids')
        for identity in ids:
            decision = decisions[identity]
            if (decision['source'] != section['source'] or decision['excerpt'] not in section['text']
                    or decision['consequence'] not in section['text']):
                fail('INCOMPLETE_DECISION_VIEW', 'section must expose its full decision and consequences')
    covered = {i for s in sections for i in s['decision_ids']}
    if covered != {d['id'] for d in design['decisions']}:
        fail('INCOMPLETE_DECISION_VIEW', 'every material decision requires an exact section')
