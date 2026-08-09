"""Shared valid Studio gameplay-cycle fixture for contract tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from studio.cycle import READY


def _write_json(repo: Path, relative: str, payload: dict) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _ref(repo: Path, relative: str) -> dict[str, str]:
    return {
        "path": relative,
        "sha256": hashlib.sha256((repo / relative).read_bytes()).hexdigest(),
    }


def write_valid_cycle(
    repo: Path,
    factory_revision: str,
    *,
    project_id: str = "sample-game",
    root: str = "design/studio/gameplay_system/core",
) -> str:
    """Write one cycle-complete system and return its manifest path."""

    product_input_relative = "design/product/idea/PRODUCT_THESIS_INPUT.json"
    _write_json(
        repo,
        product_input_relative,
        {"causal_links": [{"link_id": "choice-reward-return"}]},
    )
    product_input_ref = _ref(repo, product_input_relative)
    product_relative = "design/product/PRODUCT_THESIS.md"
    product = repo / product_relative
    product.parent.mkdir(parents=True, exist_ok=True)
    product.write_text(
        "# Product\n\n## Product causal thesis\n\n"
        "### `choice-reward-return`\n\n"
        "A resolved choice changes a visible opportunity used by the next choice.\n",
        encoding="utf-8",
    )
    constraints_relative = "design/product/FACTORY_CONSTRAINTS.json"
    _write_json(
        repo,
        constraints_relative,
        {
            "schema_version": "factory_constraints.v2",
            "source_input_sha256": product_input_ref["sha256"],
            "constraints": [
                {"constraint_id": "core-must-cycle", "factories": ["all"]}
            ],
            "non_goals": [
                {"non_goal_id": "no-attendance-proxy"}
            ],
        },
    )

    system_relative = f"{root}/STUDIO_GAMEPLAY_SYSTEM.json"
    causal = ["choice-reward-return"]
    constraints = ["core-must-cycle"]
    transitions = [
        {
            "transition_id": "decide", "from_stage_id": "choose",
            "to_stage_id": "committed", "phase": "PLAYER_DECISION",
            "player_action": "Read the current opportunity and choose a risk.",
            "reads_state_ids": ["opportunity-tier"], "writes_state_ids": [],
            "visible_consequence": "The chosen risk becomes the active position.",
            "motivation_effect": "The player commits visible standing.",
            "causal_link_ids": causal, "constraint_ids": constraints,
        },
        {
            "transition_id": "commit", "from_stage_id": "committed",
            "to_stage_id": "committed", "phase": "COMMITMENT",
            "player_action": "Lock the position.",
            "reads_state_ids": ["opportunity-tier"], "writes_state_ids": [],
            "visible_consequence": "The position can no longer be edited.",
            "motivation_effect": "Commitment creates anticipation.",
            "causal_link_ids": causal, "constraint_ids": constraints,
        },
        {
            "transition_id": "resolve", "from_stage_id": "committed",
            "to_stage_id": "resolved", "phase": "RESOLUTION",
            "player_action": "Observe the position resolve.",
            "reads_state_ids": [], "writes_state_ids": [],
            "visible_consequence": "The game reveals success or failure.",
            "motivation_effect": "The result tests the player's judgment.",
            "causal_link_ids": causal, "constraint_ids": constraints,
        },
        {
            "transition_id": "reward", "from_stage_id": "resolved",
            "to_stage_id": "rewarded", "phase": "REWARD",
            "player_action": "Claim the result.",
            "reads_state_ids": [], "writes_state_ids": ["opportunity-tier"],
            "visible_consequence": "The visible opportunity tier changes.",
            "motivation_effect": "A different next opportunity opens.",
            "causal_link_ids": causal, "constraint_ids": constraints,
        },
        {
            "transition_id": "reinvest", "from_stage_id": "rewarded",
            "to_stage_id": "rewarded", "phase": "REINVESTMENT",
            "player_action": "Choose how to use the changed opportunity tier.",
            "reads_state_ids": ["opportunity-tier"],
            "writes_state_ids": ["opportunity-tier"],
            "visible_consequence": "The next risk set changes.",
            "motivation_effect": "Progress creates a new goal, not a replay prompt.",
            "causal_link_ids": causal, "constraint_ids": constraints,
        },
        {
            "transition_id": "return", "from_stage_id": "rewarded",
            "to_stage_id": "choose", "phase": "RETURN",
            "player_action": "Enter the next choice with the changed opportunity.",
            "reads_state_ids": ["opportunity-tier"], "writes_state_ids": [],
            "visible_consequence": "The next decision exposes a different risk set.",
            "motivation_effect": "The player has a concrete reason to decide again.",
            "causal_link_ids": causal, "constraint_ids": constraints,
        },
    ]
    system = {
        "schema_version": "studio_gameplay_system.v2",
        "status": READY,
        "system_id": "core",
        "cycle_id": "choice-reward-cycle",
        "project_id": project_id,
        "factory_revision": factory_revision,
        "product_authority": _ref(repo, product_relative),
        "product_input": product_input_ref,
        "factory_constraints": _ref(repo, constraints_relative),
        "author_context_id": "cycle-author",
        "system_promise": "Choose, resolve, gain a changed opportunity, and choose again.",
        "core_player_verbs": ["read", "choose", "resolve", "reinvest"],
        "stages": [
            {"stage_id": "choose", "player_goal": "Choose a worthwhile risk."},
            {"stage_id": "committed", "player_goal": "Anticipate the result."},
            {"stage_id": "resolved", "player_goal": "Understand the result."},
            {"stage_id": "rewarded", "player_goal": "Use the changed opportunity."},
        ],
        "state_objects": [{
            "state_id": "opportunity-tier", "kind": "PROGRESSION",
            "owner": "PLAYER", "player_visible": True,
            "meaning": "The visible risk and reward set available next.",
        }],
        "transitions": transitions,
        "cycle_path": ["decide", "commit", "resolve", "reward", "reinvest", "return"],
        "feedback_state_ids": ["opportunity-tier"],
        "coupled_systems": [{
            "component_id": "choice-reward-return",
            "role": "Join the decision, reward, and changed next opportunity.",
            "transition_ids": ["decide", "reward", "reinvest", "return"],
            "required_in_first_baseline": True,
        }],
        "causal_link_coverage": [{
            "link_id": "choice-reward-return",
            "transition_ids": ["decide", "reward", "return"],
            "status": "REALIZED_IN_CYCLE",
        }],
        "constraint_coverage": [{
            "constraint_id": "core-must-cycle",
            "transition_ids": ["decide", "reward", "return"],
            "status": "REALIZED_IN_CYCLE",
        }],
        "non_goal_coverage": [{
            "non_goal_id": "no-attendance-proxy",
            "transition_ids": ["reward", "return"],
            "status": "PRESERVED",
            "rationale": "The cycle returns through changed opportunity rather than attendance rewards.",
        }],
        "two_lap_witness": {
            "lap_one": {
                "player_goal": "Prove the first choice.",
                "decision": "Choose the starter risk.",
                "resolution": "The position resolves.",
                "resulting_state": "Opportunity tier increases.",
            },
            "feedback_state_deltas": [{
                "state_id": "opportunity-tier", "before": "Starter risk set.",
                "after": "Advanced risk set.",
                "effect_on_next_decision": "The next decision has a different risk and reward set.",
            }],
            "lap_two": {
                "player_goal": "Use the advanced opportunity.",
                "decision": "Choose an advanced risk unavailable in lap one.",
                "resolution": "The advanced position resolves.",
                "resulting_state": "Another opportunity results.",
            },
            "why_second_lap_is_not_repetition": "Lap one changes the opportunity used by lap two.",
        },
        "forbidden_linearizations": [
            "A result followed only by a replay button is not a gameplay cycle."
        ],
        "authored_at": "2026-08-05T10:00:00Z",
    }
    _write_json(repo, system_relative, system)
    system_ref = _ref(repo, system_relative)
    transition_ids = [item["transition_id"] for item in transitions]
    review_paths: dict[str, str] = {}
    for role, reviewer, suffix in (
        ("PRODUCT_FIDELITY", "cycle-product-reviewer", "PRODUCT"),
        ("CYCLE_CLOSURE", "cycle-closure-reviewer", "CYCLE"),
    ):
        relative = f"{root}/STUDIO_GAMEPLAY_SYSTEM_REVIEW_{suffix}.json"
        _write_json(repo, relative, {
            "schema_version": "studio_gameplay_system_review.v2",
            "review_id": f"core-{suffix.lower()}-review",
            "review_role": role,
            "project_id": project_id,
            "system_id": "core",
            "cycle_id": "choice-reward-cycle",
            "factory_revision": factory_revision,
            "gameplay_system": system_ref,
            "reviewer_context_id": reviewer,
            "reviewer_freshness": "FRESH",
            "causal_link_ids_reviewed": causal if role == "PRODUCT_FIDELITY" else [],
            "constraint_ids_reviewed": constraints if role == "PRODUCT_FIDELITY" else [],
            "non_goal_ids_reviewed": ["no-attendance-proxy"] if role == "PRODUCT_FIDELITY" else [],
            "transition_ids_reviewed": transition_ids,
            "cycle_findings": {
                "closed_graph": "PASS", "reward_changes_next_decision": "PASS",
                "second_lap_materially_differs": "PASS",
                "coupled_systems_preserved": "PASS",
                "product_boundaries_consistent": "PASS",
                "gamification_intent_is_reward_cycle": "PASS",
                "no_proxy_loop": "PASS",
            },
            "blocking_findings": [],
            "verdict": "PASS_SYSTEM_REVIEW",
            "reviewed_at": "2026-08-05T10:10:00Z",
        })
        review_paths[role] = relative

    manifest_relative = f"{root}/STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json"
    _write_json(repo, manifest_relative, {
        "schema_version": "studio_gameplay_system_manifest.v1",
        "status": READY,
        "project_id": project_id,
        "system_id": "core",
        "cycle_id": "choice-reward-cycle",
        "factory_revision": factory_revision,
        "gameplay_system": system_ref,
        "reviews": {
            "product_fidelity": _ref(repo, review_paths["PRODUCT_FIDELITY"]),
            "cycle_closure": _ref(repo, review_paths["CYCLE_CLOSURE"]),
        },
    })
    return manifest_relative
