"""Capability-owned knowledge index. Methods load on demand; rules do not vanish."""
from __future__ import annotations

from pathlib import Path
from .refs import confined, fail, reference, unique_refs

CAPABILITIES = ("idea", "product", "studio", "gameplay", "story", "asset", "sound")
STORY_TASKS = ("world", "character", "cast", "chapter", "branch", "craft", "beat-sheet", "delivery", "twin", "rules")
DOCS = {
    "product": ["product/docs/VALUE_ASSESSMENT_WORKFLOW.md"],
    "idea": ["idea/docs/PRODUCT_DEFINITION_WORKFLOW.md"],
    "studio": ["studio/docs/WORKFLOW_V2.md", "studio/docs/PLAYER_FACING_GAMEPLAY_EVIDENCE_GATE.md",
               "studio/docs/BASELINE_ADMISSION_WORKFLOW.md", "studio/docs/PRODUCT_AUTHORITY_LIFECYCLE.md"],
    "gameplay": ["gameplay/docs/WORKFLOW_V2.md", "gameplay/docs/PROJECT_CARD_AUTHORING_STANDARD_WORKFLOW.md",
                 "gameplay/docs/UI_PRODUCTION_WORKFLOW.md", "gameplay/docs/RUNTIME_OBSERVATION_AND_ACCEPTANCE_CONTRACT.md"],
    "story": ["story/docs/WORKFLOW_V2.md", "story/docs/PROJECT_PROFILE_CONTRACT.md", "story/core/NARRATIVE_FOUNDATIONS.md"],
    "asset": ["asset/docs/AI_CALLER_LANDING.md"],
    "sound": ["sound/docs/AI_CALLER_LANDING.md"],
}
METHODS = {
    "world": ["story/core/steps/world"], "character": ["story/core/steps/character"],
    "cast": ["story/core/steps/cast"], "chapter": ["story/core/steps/chapter"],
    "branch": ["story/core/steps/chapter"], "craft": ["story/core/craft"],
    "beat-sheet": ["story/modules/beat-sheet-dialogue"],
    "delivery": ["story/modules/delivery-planner"], "twin": ["story/modules/twin-db"],
    "rules": ["story/modules/world-rules-editor"],
}


def departments(capability: str) -> list[str]:
    if capability not in CAPABILITIES:
        fail("UNKNOWN_CAPABILITY", capability)
    return ["studio", "gameplay", "idea"] if capability in ("studio", "gameplay") else [capability]


def method_paths(factory: Path, capability: str, task: str) -> list[str]:
    if capability == "story":
        task = "beat-sheet" if task == "beatsheet" else task
        if task not in STORY_TASKS:
            fail("UNKNOWN_TASK", "Story task must name a supported capability")
        prefixes = METHODS[task]
    else:
        prefixes = []
    return sorted({p.relative_to(factory).as_posix() for prefix in prefixes
                   for p in confined(factory, prefix).rglob("*.md")})


def factory_dependencies(factory: Path, capability: str, task: str, workflow_version=2, methods=()) -> list[dict]:
    """Closed conservative code/schema sets; unrelated docs/tests are not inputs.

    Directory membership participates: a newly added validator changes the set.
    Specialist domain rules remain references, not paraphrased replacements.
    """
    native = workflow_version == 3
    if native:
        from .astra import WORKFLOW, CATALOG, docs, rule_source, selected_methods
    paths = {"factory.py", WORKFLOW if native else "factory_core/docs/WORKFLOW.md", "factory_core/rule_map.json"}
    if native:
        paths.add(CATALOG)
    paths.update(p.relative_to(factory).as_posix() for p in (factory / "factory_core").glob("*.py"))
    if native:
        paths = {p for p in paths if not Path(p).name.startswith('benchmark')}
    paths.update(p.relative_to(factory).as_posix() for p in (factory / "factory_core/schemas").glob("*.json"))
    for dept in departments(capability):
        paths.update(docs(dept) if native else DOCS[dept])
        paths.add(f"{dept}/AGENTS.md") if (factory / dept / "AGENTS.md").exists() else None
        paths.update(p.relative_to(factory).as_posix() for p in (factory / dept).glob("*.py"))
        paths.update(p.relative_to(factory).as_posix() for p in (factory / dept / "schemas").rglob("*.json"))
        for subdir in ("pipeline", "scripts", "godot_engine", "blender"):
            paths.update(p.relative_to(factory).as_posix() for p in (factory / dept / subdir).rglob("*")
                         if p.is_file() and p.suffix in (".py", ".gd", ".json", ".gdshader") and "__pycache__" not in p.parts)
    if capability in ("idea", "studio", "gameplay", "product"):
        paths.update(("product/intent.py", "product/value.py", "product/schemas/intent.schema.json",
                      "product/templates/PRODUCT_VALUE_INTENT.json",
                      "product/docs/PROJECT_INITIALIZATION_WORKFLOW.md"))
    if capability == "product":
        paths.update(("studio/product.py", "studio/alignment.py",
                      "product/docs/JUDGMENT_PIPELINE.md", "product/skills/product-value-reviewer/SKILL.md"))
    # Domain sources in the mapped rule registry are part of validity, even
    # when a specialist method loads them only at the relevant boundary.
    from .refs import read_json
    for rule in read_json(factory / "factory_core/rule_map.json")["rules"]:
        if "all" in rule["capabilities"] or capability in rule["capabilities"]:
            if rule["disposition"] != "on_demand_method_and_exact_output_acceptance":
                paths.add(rule_source(rule) if native else rule["source"])
    if native:
        paths.update(r['path'] for r in selected_methods(factory, capability, task, list(methods)))
    else:
        paths.update(method_paths(factory, capability, task))
    if capability == "story":
        paths.add("story/adapters/registry.md")
        # Craft obligations include glossary, native dialogue and final-language
        # quality even when the current step method doesn't mention a craft.
        if not native:
            paths.update(p.relative_to(factory).as_posix() for p in (factory / "story/core/craft").glob("*.md"))
        else:
            paths.add('story/core/craft/spoken-fluency.md')
        paths.update(p.relative_to(factory).as_posix() for p in (factory / "story/core/schemas").rglob("*" ) if p.is_file())
    if not native:
        paths -= {'factory_core/astra.py', 'factory_core/migration_gpt6.py', 'gameplay/native.py', 'story/world_state.py'}
        paths = {p for p in paths if not p.endswith('_v3.schema.json')}
    return [reference(factory, p, "factory") for p in sorted(paths)]


def authority_paths(game: Path, capability: str, extra: list[str] = ()) -> list[str]:
    """All root/product rules plus domain authorities, never inferred approvals.

    Custom authority paths are declared at migration or in a task package.
    Nested AGENTS are mandatory. This is intentionally conservative when
    project rule ownership has not been narrowed by an adopted adapter.
    """
    paths = set(extra)
    for path in ("AGENTS.md", "CLAUDE.md", "design/product/PRODUCT_AUTHORITY_REGISTER.json",
                 "design/product/PRODUCT_THESIS.md", "design/product/FACTORY_CONSTRAINTS.json"):
        if confined(game, path).is_file():
            paths.add(path)
    # git ls-files avoids traversing engine caches and preserves untracked rule
    # files; no sibling discovery or arbitrary filesystem search.
    import subprocess
    out = subprocess.run(["git", "-C", str(game), "ls-files", "-co", "--exclude-standard", "-z"],
                         capture_output=True, check=True).stdout
    for item in out.decode().split("\0"):
        if item and Path(item).name == "AGENTS.md":
            paths.add(item)
    for dept in departments(capability):
        for p in (game / "design" / dept / "adapter").rglob("*"):
            if p.is_file():
                paths.add(p.relative_to(game).as_posix())
    if capability == "story":
        from .story_profile import resolve
        paths.update(resolve(game,extra)["authority_paths"])
    return sorted(paths)


def authority_refs(game: Path, capability: str, extra: list[str] = ()) -> list[dict]:
    return unique_refs([reference(game, p) for p in authority_paths(game, capability, extra)])
