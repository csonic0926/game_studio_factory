"""Resolve Story's adopted adapter before choosing sovereignty or locale inputs.

V2 requires game-owned adapters. Factory-local legacy profiles remain readable
by v1, but are not silently relocated or reinterpreted by this resolver.
"""
from pathlib import Path
import re
from .refs import confined, fail, read_json, reference


def field(body, name):
    values = []
    for line in body.splitlines():
        match = re.match(r'^\s*-\s*`?<'+name+r'>`?\s*:\s*(.+)$', line)
        if match:
            values.append(match.group(1).split(' #',1)[0].strip().strip('`'))
        elif line.lstrip().startswith('|'):
            cells = [c.strip().strip('`') for c in line.strip().strip('|').split('|')]
            if len(cells) >= 2 and cells[0] == '<'+name+'>':
                values.append(cells[1].split(' #',1)[0].strip().strip('`'))
    if len(values) != 1 or not values[0]:
        fail('BLOCKED_BY_PROFILE', f'profile must resolve exactly one {name}')
    return values[0]


def resolve(game, extra=(), factory=None):
    game=game.resolve()
    factory=factory or Path(__file__).resolve().parents[1]
    explicit=[p for p in extra if Path(p).name=='PROJECT_PROFILE.md']
    if len(explicit)>1:
        fail('BLOCKED_BY_PROFILE','multiple explicit Story profiles')
    if explicit:
        profile=confined(game,explicit[0])
    else:
        metadata=confined(game,'design/factory/PROJECT.json')
        pid=read_json(metadata)['project_id'] if metadata.exists() else None
        registered=[]
        registry=factory/'story/adapters/registry.md'
        if pid and registry.exists():
            for line in registry.read_text().splitlines():
                match=re.match(r'^-\s+([^ ]+)\s+→\s+(.+?)\s*$',line)
                if match and match[1]==pid: registered.append(Path(match[2])/'PROJECT_PROFILE.md')
        if len(registered)>1: fail('BLOCKED_BY_PROFILE','ambiguous Story registry')
        profile=registered[0] if registered else game/'design/story/adapter/PROJECT_PROFILE.md'
    if not profile.is_relative_to(game):
        fail('MIGRATION_REQUIRED','v2 needs a game-owned adopted Story profile; explicitly declare its relative path at migration')
    profile=confined(game,profile.relative_to(game).as_posix())
    if not profile.is_file(): fail('BLOCKED_BY_PROFILE','missing adopted Story profile')
    body=profile.read_text()
    root_value=field(body,'STORY_ROOT').replace('<GAME_REPO>',str(game)).strip('`')
    story_root=Path(root_value)
    if not story_root.is_absolute(): story_root=game/story_root
    if not story_root.is_relative_to(game): fail('BLOCKED_BY_PROFILE','Story root must be inside this game')
    story_root=confined(game,story_root.relative_to(game).as_posix())
    primary=field(body,'PRIMARY_LOCALE')
    locales=[s.strip().strip('`') for s in field(body,'SHIPPED_LOCALES').split(',')]
    if (not locales or len(set(locales))!=len(locales) or primary not in locales
            or any(not re.fullmatch(r'[a-zA-Z]{2,3}(?:[-_][a-zA-Z0-9]{2,8})*',s) for s in locales)):
        fail('BLOCKED_BY_PROFILE','unresolved or inconsistent shipped locales')
    paths=[p.relative_to(game).as_posix() for p in profile.parent.rglob('*') if p.is_file()]
    sovereignty=[story_root/'state'/name for name in ('WORLD_RULES.md','NARRATIVE_DELIVERY.md','WORKFLOW_CORE_VARIABLES.md')]
    if not any(p.is_file() for p in sovereignty):
        fail('BLOCKED_BY_PROFILE','Story sovereignty is missing; never infer it from runtime')
    paths.extend(p.relative_to(game).as_posix() for p in sovereignty if p.is_file())
    return dict(profile=reference(game,profile.relative_to(game).as_posix()),story_root=story_root,
                authority_paths=sorted(set(paths)),shipped_locales=locales,primary_locale=primary)
