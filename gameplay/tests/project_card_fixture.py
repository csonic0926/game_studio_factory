from __future__ import annotations

import hashlib
import json
from pathlib import Path

from gameplay.design_gate import decision_payload_sha256, render_decision_card
from gameplay.project_card_standard import PROJECT_REVIEW_NAME


STANDARD_RELATIVE = Path(
    "design/gameplay/adapter/PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json"
)


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def ref(repo: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.resolve().relative_to(repo.resolve()).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def install_project_standard(
    repo: Path,
    *,
    project_id: str,
    profile_kind: str = "spatial",
) -> dict[str, str]:
    """Install one of two deliberately different valid project profiles."""

    collaboration = repo / "AGENTS.md"
    collaboration.write_text(
        "# Test project collaboration\n\n"
        f"Use `{STANDARD_RELATIVE.as_posix()}` for every Gameplay Decision Card.\n",
        encoding="utf-8",
    )
    if profile_kind == "turn":
        vocabulary = [
            {"term_id": "turn", "term": "Turn", "definition": "One submitted command and its complete opponent response."},
            {"term_id": "round", "term": "Round", "definition": "A bounded set of turns ending at initiative reset."},
        ]
        lap = ["One lap is one round that settles initiative and returns a changed board."]
        work = ["Selecting a command is player work only when target and timing affect the board response."]
        granularity = ["The Card names every turn class, round boundary, and branch that changes legal commands."]
    else:
        vocabulary = [
            {"term_id": "scene", "term": "Scene", "definition": "A continuous place and control mode with an explicit transition."},
            {"term_id": "beat", "term": "Beat", "definition": "One input, judgment, visible response, and returned affordance."},
        ]
        lap = ["One lap resolves one situated action and returns the player to a changed nearby opportunity."]
        work = ["Navigation or dialogue is player work only when judgment changes cost, response, or persistence."]
        granularity = ["The Card names ordered scenes, beats, interaction bounds, branches, and lap boundaries."]
    standard = {
        "schema_version": "project_gameplay_decision_card_standard.v1",
        "standard_id": f"{project_id}.card-standard.v1",
        "project_id": project_id,
        "version": "v1",
        "status": "ACTIVE",
        "applicable_routings": ["STUDIO_WHOLE_GAME", "DIRECT_SPECIALIST"],
        "adoption": {
            "status": "HUMAN_OR_PROJECT_AUTHORITY_ADOPTED",
            "owner": "test project authority",
            "authority_ref": "committed test ruling",
            "adopted_at": "2026-09-04T10:00:00Z",
        },
        "collaboration_contract": ref(repo, collaboration),
        "vocabulary": vocabulary,
        "repeatable_lap": lap,
        "player_work_boundary": work,
        "granularity_rules": granularity,
        "interaction_requirements": ["Each unit states input, judgment, response, persistent change, and next affordance."],
        "resolution_boundaries": ["Each lap names its irreversible state or resource settlement."],
        "failure_recovery_replay": ["Every failure or partial success states a continuing recovery route."],
        "validation_methods": [
            {
                "method_id": "runtime_behavior",
                "use": "Observe action and visible response in the exact build.",
                "observable_evidence": "Input trace plus before, response, and returned-state capture.",
                "falsification_rule": "Reject when the promised response or returned affordance is absent.",
            },
            {
                "method_id": "post_play_debrief",
                "use": "Test a claim about the player's interpretation after play.",
                "observable_evidence": "The exact question and recorded answer.",
                "falsification_rule": "Reject when the answer lacks the promised causal distinction.",
            },
        ],
        "independence_rules": ["The project reviewer differs from composition, Contract, and Card authors."],
        "synchronization_rules": ["Commit the standard in the game repo and bind its exact version and SHA in every handoff."],
        "composition_artifact_kinds": [
            {
                "kind_id": "sequence_map",
                "name": "Project sequence map",
                "purpose": "Freeze the project-defined playable order and settlement before Card approval.",
                "required": True,
            }
        ],
        "requirements": [
            {
                "requirement_id": "project.sequence",
                "rule": "The composition fixes the complete playable order before Card review.",
                "applicability": "Always.",
                "evidence_surface": "MULTIPLE",
            },
            {
                "requirement_id": "project.rendered-completeness",
                "rule": "The rendered Card alone exposes every material decision.",
                "applicability": "Always.",
                "evidence_surface": "CARD",
            },
        ],
        "render_only_requirement_ids": ["project.rendered-completeness"],
    }
    standard_path = write_json(repo / STANDARD_RELATIVE, standard)
    standard_ref = ref(repo, standard_path)
    standard_ref["version"] = standard["version"]
    profile = repo / "design/gameplay/adapter/PROJECT_GAMEPLAY_PROFILE.md"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(
        f"# Project Gameplay Profile — `{project_id}`\n\n"
        "## Gameplay Decision Card authoring authority\n\n"
        f"- Project Card authoring standard path: `{standard_ref['path']}`\n"
        "- Project Card authoring standard version: `v1`\n"
        f"- Project Card authoring standard SHA-256: `{standard_ref['sha256']}`\n"
        "- Project Card authoring standard status: `ACTIVE`\n",
        encoding="utf-8",
    )
    return standard_ref


def attach_project_review(
    repo: Path,
    objective_dir: Path,
    card: dict,
    *,
    interaction_contract_ref: dict[str, str],
    interaction_contract_review_ref: dict[str, str],
    interaction_contract_author: str = "surface-contract-author",
    composition_author: str = "project-composition-author",
    project_reviewer: str = "project-card-reviewer",
    profile_kind: str = "spatial",
) -> tuple[dict[str, str], list[dict], dict[str, str]]:
    """Attach active project authority and its non-circular fresh review."""

    standard_ref = install_project_standard(
        repo, project_id=card["project_id"], profile_kind=profile_kind
    )
    composition_path = objective_dir / "PROJECT_GAMEPLAY_COMPOSITION.json"
    write_json(
        composition_path,
        {
            "project_id": card["project_id"],
            "objective_id": card["objective_id"],
            "ordered_play": ["enter", "judge", "commit", "respond", "return"],
            "resolution": "The visible state settles before the changed next affordance.",
        },
    )
    composition = {
        "artifact_id": f"{card['objective_id']}.sequence-map.v1",
        "kind_id": "sequence_map",
        "path": composition_path.relative_to(repo).as_posix(),
        "sha256": hashlib.sha256(composition_path.read_bytes()).hexdigest(),
        "author_context_id": composition_author,
    }
    review_path = objective_dir / PROJECT_REVIEW_NAME
    card["schema_version"] = "gameplay_decision_card.v3"
    card["project_card_authoring_standard"] = standard_ref
    card["project_composition_artifacts"] = [composition]
    card["project_card_review"] = {
        "path": review_path.relative_to(repo).as_posix(),
        "sha256": "0" * 64,
    }
    for hypothesis in card.get("validation_hypotheses", []):
        hypothesis.setdefault("validation_method_id", "post_play_debrief")
    card["decision_payload_sha256"] = decision_payload_sha256(card)
    if card.get("human_verdict", {}).get("status") != "PENDING":
        card["human_verdict"]["source_text"] = (
            f"{card['human_verdict']['status']} {card['decision_payload_sha256']}"
        )
    card_path = objective_dir / "GAMEPLAY_DECISION_CARD.json"
    write_json(card_path, card)
    claim_ids = [card["player_promise"]["claim_id"]]
    for field in (
        "core_cycle",
        "material_commitments",
        "red_lines",
        "validation_hypotheses",
    ):
        claim_ids.extend(item["claim_id"] for item in card.get(field, []))
    review = {
        "schema_version": "gameplay_decision_card_project_review.v1",
        "review_id": f"{card['objective_id']}.project-card-review.v1",
        "review_role": "PROJECT_CARD_AUTHORING_STANDARD_REVIEW",
        "project_id": card["project_id"],
        "objective_id": card["objective_id"],
        "factory_revision": card["factory_revision"],
        "project_card_authoring_standard": standard_ref,
        "project_composition_artifacts": [composition],
        "player_facing_interaction_contract": interaction_contract_ref,
        "player_facing_interaction_contract_review": interaction_contract_review_ref,
        "decision_card": {
            "path": card_path.relative_to(repo).as_posix(),
            "decision_payload_sha256": card["decision_payload_sha256"],
            "rendered_surface_sha256": hashlib.sha256(
                render_decision_card(card).encode("utf-8")
            ).hexdigest(),
        },
        "author_context_ids": {
            "composition_artifact_authors": [composition_author],
            "interaction_contract_author": interaction_contract_author,
            "decision_card_author": card["author_context_id"],
        },
        "reviewer_context_id": project_reviewer,
        "reviewer_freshness": "FRESH",
        "requirement_findings": [
            {
                "requirement_id": "project.sequence",
                "applicability": "APPLICABLE",
                "verdict": "PASS",
                "evidence_refs": [
                    {"surface": "COMPOSITION_ARTIFACT", "ref": composition["artifact_id"]},
                    {"surface": "INTERACTION_CONTRACT", "ref": "playable_beats"},
                ],
                "rationale": "The exact composition and Contract freeze the playable order.",
            },
            {
                "requirement_id": "project.rendered-completeness",
                "applicability": "APPLICABLE",
                "verdict": "PASS",
                "evidence_refs": [
                    {"surface": "CARD_CLAIM", "ref": claim_ids[0]},
                ],
                "rationale": "The rendered claims expose the project's material decision surface.",
            },
        ],
        "render_only_findings": [
            {
                "requirement_id": "project.rendered-completeness",
                "evidence_claim_ids": claim_ids,
                "verdict": "PASS",
                "rationale": "The complete rendered claim set answers the finite project checklist.",
            }
        ],
        "blocking_findings": [],
        "verdict": "PASS_PROJECT_CARD_AUTHORING_STANDARD",
        "reviewed_at": "2026-09-04T10:10:00Z",
    }
    write_json(review_path, review)
    card["project_card_review"] = ref(repo, review_path)
    write_json(card_path, card)
    return standard_ref, [composition], ref(repo, review_path)
