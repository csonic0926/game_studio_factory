"""Joint initialization contracts, not evidence of player value or USER acceptance.

Commission/archive fixtures below are explicitly synthetic contract tests. No
test result is a commercial judgment, a real commission, or an approval receipt.
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from factory_core import migration, migration_gpt6
from factory_core.catalog import authority_paths, factory_dependencies
from factory_core.context import context, inspect as factory_inspect
from factory_core.refs import FactoryError, encoded, read_json, reference, resolve_ref
from factory_core.state import checkpoint, latest, project, project_lock, verify_record
from idea import idea
from idea.tests import test_idea as idea_fixture
from product import intent, value
from product.product import main as product_main
from product.tests import test_value as product_fixture


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("initialization_setup", ROOT / "setup.py")
factory_setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(factory_setup)


def tree_snapshot(root):
    """Include directories, symlinks, and .git so dry-run cannot hide a lock write."""
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[relative] = ("symlink", os.readlink(path))
            elif path.is_dir():
                result[relative] = ("directory",)
            else:
                result[relative] = ("file", path.read_bytes())
    return result


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.game = Path(self.temporary.name).resolve() / "game"
        self.game.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.game)], check=True)
        self.roots = {"game": self.game, "factory": ROOT}
        self.game_repo = self.game  # Existing Idea helper convention.

    def write(self, path, body):
        destination = self.game / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(encoded(body) if isinstance(body, dict) else body.encode())
        return reference(self.game, str(path))

    def initialize(self, **kwargs):
        return factory_setup.initialize_game_repo(str(ROOT), str(self.game), **kwargs)

    def payload(self):
        return read_json(self.game / intent.PATH)

    def author_intent(self):
        data = self.payload()
        data.update(
            state="DRAFTED",
            buying_reason="Synthetic hypothesis: a concise strategy toy makes consequences legible.",
            adequacy_case="Synthetic hypothesis: one decision feels meaningful enough to revisit.",
            value_hypotheses=[{
                "id": "readable-consequence",
                "statement": "Synthetic hypothesis: the player wants to try a different team after a loss.",
                "source_refs": copy.deepcopy(data["source_refs"]),
            }],
            material_unknowns=["No player has encountered the proposed interaction."],
            next_move="Build the smallest reversible choice-and-consequence experiment.",
        )
        self.write(intent.PATH, data)
        return data

    def prepare_idea_fixture(self):
        self.write("README.md", "# Early Auto Battler\nA small experimental auto battler.\n")
        self.write("game.gd", "const CURRENT_LOOP = 'draft_then_auto_battle'\n")
        self.initialize()
        self.probe = read_json(self.game / idea.PROBE_RELATIVE)

    _exploration = idea_fixture.IdeaFactoryTests._exploration
    _write_exploration = idea_fixture.IdeaFactoryTests._write_exploration
    _record_emerged_exploration = idea_fixture.IdeaFactoryTests._record_emerged_exploration
    _payload = idea_fixture.IdeaFactoryTests._payload
    _write_input = idea_fixture.IdeaFactoryTests._write_input
    canonical_authority = product_fixture.ProductTests.canonical_authority

    def migrate(self, workflow):
        module = migration_gpt6 if workflow == 3 else migration
        preview = module.preview(self.game, ROOT, "synthetic-initialization")
        return module.apply(self.game, ROOT, "synthetic-initialization", preview["source_digest"])

    def test_fresh_unborn_git_initializes_routing_idea_and_honest_product_intent(self):
        result = self.initialize()
        self.assertIn("status", result)
        self.assertIn("idea", result)
        self.assertIn("routing", result)
        self.assertEqual(result["product"]["status"], "PRODUCT_INTENT_OPEN")
        for name in ("AGENTS.md", "CLAUDE.md", ".gitignore", factory_setup.POINTER_REL_PATH,
                     idea.PROBE_RELATIVE, intent.PATH):
            self.assertTrue((self.game / name).is_file(), name)
        data = self.payload()
        self.assertEqual(data["schema_version"], "product_value_intent.v1")
        self.assertEqual(data["state"], "OPEN")
        self.assertEqual(data["offer"]["status"], "UNKNOWN")
        self.assertEqual(data["offer"]["grounding"], "UNKNOWN")
        self.assertIsNone(data["offer"]["amount"])
        self.assertIsNone(data["offer"]["currency"])
        self.assertEqual(data["audience"]["grounding"], "UNKNOWN")
        self.assertIsNone(data["buying_reason"])
        self.assertIsNone(data["adequacy_case"])
        self.assertEqual(data["current_build_assessment"], "NOT_ASSESSED")
        self.assertIs(data["value_claim_eligible"], False)
        self.assertIs(data["authority_granted"], False)
        self.assertTrue(data["next_move"])
        self.assertEqual(data["source_refs"], [reference(self.game, idea.PROBE_RELATIVE.as_posix())])
        self.assertEqual(read_json(self.game / idea.PROBE_RELATIVE)["repository"]["revision"], "UNBORN_HEAD")
        for ref in data["source_refs"]:
            self.assertEqual(ref["scope"], "game")
            self.assertTrue(resolve_ref(self.roots, ref).is_file())
        for name in ("design/factory/PROJECT.json", "design/product/PRODUCT_AUTHORITY_REGISTER.json",
                     idea.INPUT_RELATIVE, idea.THESIS_RELATIVE, idea.RESULT_RELATIVE):
            self.assertFalse((self.game / name).exists(), name)
        self.assertEqual(factory_inspect(self.roots)["status"], "MIGRATION_REQUIRED")

    def test_rerun_is_byte_identical_including_authored_draft_and_user_routing_prose(self):
        self.write("AGENTS.md", "# User-owned project rules\nKeep this prose exactly.\n")
        self.write("CLAUDE.md", "# User-owned harness instructions\n")
        self.initialize()
        authored = self.author_intent()
        before = tree_snapshot(self.game)
        result = self.initialize()
        self.assertEqual(tree_snapshot(self.game), before)
        self.assertEqual(result["product"]["intent"], authored)
        self.assertEqual(result["product"]["status"], "PRODUCT_INTENT_DRAFTED")
        self.assertEqual(result["product"]["reference"], reference(self.game, intent.PATH))

    def test_resume_after_idea_only_artifact_preserves_original_probe(self):
        idea.start_idea_factory(str(self.game))
        before = (self.game / idea.PROBE_RELATIVE).read_bytes()
        result = self.initialize()
        self.assertEqual((self.game / idea.PROBE_RELATIVE).read_bytes(), before)
        self.assertEqual(result["product"]["status"], "PRODUCT_INTENT_OPEN")
        self.assertTrue((self.game / intent.PATH).is_file())

    def test_interrupted_after_idea_creation_resumes_without_reset(self):
        with patch.object(intent, "seed", side_effect=RuntimeError("synthetic interruption after Idea")):
            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                self.initialize()
        self.assertTrue((self.game / idea.PROBE_RELATIVE).is_file())
        self.assertFalse((self.game / intent.PATH).exists())
        before = (self.game / idea.PROBE_RELATIVE).read_bytes()
        self.initialize()
        self.assertEqual((self.game / idea.PROBE_RELATIVE).read_bytes(), before)
        self.assertEqual(intent.inspect(self.roots)["status"], "PRODUCT_INTENT_OPEN")

    def test_standalone_product_start_adds_to_idea_only_without_link_or_migration(self):
        idea.start_idea_factory(str(self.game))
        before = tree_snapshot(self.game)
        result = intent.start(self.roots)
        self.assertEqual(result["status"], "PRODUCT_INTENT_OPEN")
        after = tree_snapshot(self.game)
        for path, contents in before.items():
            self.assertEqual(after[path], contents)
        self.assertFalse((self.game / "AGENTS.md").exists())
        self.assertFalse((self.game / factory_setup.POINTER_REL_PATH).exists())
        self.assertFalse((self.game / "design/factory/PROJECT.json").exists())
        before = after
        intent.start(self.roots)
        self.assertEqual(tree_snapshot(self.game), before)

    def test_standalone_product_start_preserves_existing_open_idea_binding(self):
        self.write("README.md", "# Early Auto Battler\nA small experimental auto battler.\n")
        self.write("game.gd", "const CURRENT_LOOP = 'draft_then_auto_battle'\n")
        idea.start_idea_factory(str(self.game))
        self.probe = read_json(self.game / idea.PROBE_RELATIVE)
        self._write_exploration(self._exploration(frontier_state="OPEN"))
        result = idea.record_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix())
        self.assertEqual(result.status, idea.IDEA_EXPLORATION_OPEN, result.errors)
        protected = {p: (self.game / p).read_bytes() for p in intent.IDEA_PATHS if (self.game / p).is_file()}
        intent.start(self.roots)
        self.author_intent()
        checked = idea.check_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix())
        self.assertEqual(checked.status, idea.IDEA_EXPLORATION_OPEN, checked.errors)
        for path, contents in protected.items():
            self.assertEqual((self.game / path).read_bytes(), contents)
        self.assertFalse((self.game / "AGENTS.md").exists())

    def test_legacy_link_remains_routing_only(self):
        factory_setup.link_game_repo(str(ROOT), str(self.game))
        self.assertTrue((self.game / "AGENTS.md").exists())
        self.assertFalse((self.game / idea.PROBE_RELATIVE).exists())
        self.assertFalse((self.game / intent.PATH).exists())
        self.assertFalse((self.game / "design/factory/PROJECT.json").exists())

    def test_setup_init_cli_and_project_root_alias(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(factory_setup.main(["init", "--project-root", str(self.game)]), 0)
        self.assertTrue((self.game / intent.PATH).exists())

    def test_product_start_cli_and_project_root_alias(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(product_main(["start", "--project-root", str(self.game)]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PRODUCT_INTENT_OPEN")
        self.assertFalse((self.game / "design/factory/PROJECT.json").exists())

    def test_init_dry_run_writes_no_files_directories_or_git_lock(self):
        before = tree_snapshot(self.game)
        result = self.initialize(dry_run=True)
        self.assertEqual(tree_snapshot(self.game), before)
        self.assertTrue(result.get("dry_run") or result["product"].get("dry_run"))
        self.assertFalse((self.game / ".git/factory-v2.lock").exists())

    def test_product_start_dry_run_writes_no_files_directories_or_git_lock(self):
        before = tree_snapshot(self.game)
        result = intent.start(self.roots, dry_run=True)
        self.assertEqual(tree_snapshot(self.game), before)
        self.assertTrue(result["dry_run"])
        self.assertIn(intent.PATH, result["planned_paths"])

    def test_dry_run_preserves_existing_authored_intent(self):
        self.initialize()
        self.author_intent()
        before = tree_snapshot(self.game)
        self.initialize(dry_run=True)
        intent.start(self.roots, dry_run=True)
        self.assertEqual(tree_snapshot(self.game), before)

    def test_rejects_non_git_subdirectory_and_factory_targets_without_writes(self):
        outside = Path(self.temporary.name) / "not-git"
        outside.mkdir()
        nested = self.game / "nested"
        nested.mkdir()
        for target in (outside, nested, ROOT, ROOT / "product"):
            with self.subTest(target=str(target)):
                before = tree_snapshot(self.game)
                with self.assertRaises((FactoryError, SystemExit)):
                    factory_setup.initialize_game_repo(str(ROOT), str(target))
                self.assertEqual(tree_snapshot(self.game), before)
        self.assertEqual(tree_snapshot(outside), {})

    def test_all_initialization_owned_symlink_targets_fail_without_external_writes(self):
        targets = ("AGENTS.md", "CLAUDE.md", ".gitignore", "design/STUDIO_FACTORY.local.md",
                   idea.PROBE_RELATIVE.as_posix(), intent.PATH,
                   "design/product/PRODUCT_AUTHORITY_REGISTER.json")
        outside = Path(self.temporary.name) / "outside.txt"
        outside.write_text("Synthetic external file.\n")
        for name in targets:
            with self.subTest(path=name):
                target = self.game / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(outside)
                before = tree_snapshot(self.game)
                with self.assertRaises((FactoryError, SystemExit)):
                    self.initialize()
                self.assertEqual(tree_snapshot(self.game), before)
                self.assertEqual(outside.read_text(), "Synthetic external file.\n")
                target.unlink()

    def test_parent_directory_symlink_rejected_even_if_destination_is_inside_game(self):
        internal = self.game / "owned-directory"
        internal.mkdir()
        (self.game / "design").symlink_to(internal, target_is_directory=True)
        before = tree_snapshot(self.game)
        with self.assertRaises((FactoryError, SystemExit)):
            self.initialize()
        self.assertEqual(tree_snapshot(self.game), before)

    def test_regular_file_parent_blocks_init_and_product_start_before_writes(self):
        for name in ("design/product_value", "design/product/idea", "design/product"):
            with self.subTest(parent=name):
                # Earlier subtests may have left empty parent directories only.
                target = self.game / name
                if target.is_dir():
                    target.rmdir()
                self.write(name, "Synthetic file where an initialization directory is required.\n")
                before = tree_snapshot(self.game)
                for dry_run in (True, False):
                    with self.subTest(dry_run=dry_run):
                        with self.assertRaises(FactoryError):
                            self.initialize(dry_run=dry_run)
                        self.assertEqual(tree_snapshot(self.game), before)
                        with self.assertRaises(FactoryError):
                            intent.start(self.roots, dry_run=dry_run)
                        self.assertEqual(tree_snapshot(self.game), before)
                target.unlink()

    def test_malformed_existing_json_blocks_before_any_initializer_write(self):
        for name in (intent.PATH, idea.PROBE_RELATIVE.as_posix(),
                     "design/product/PRODUCT_AUTHORITY_REGISTER.json"):
            with self.subTest(path=name):
                self.write(name, "{ invalid synthetic JSON\n")
                before = tree_snapshot(self.game)
                with self.assertRaises((FactoryError, SystemExit)):
                    self.initialize()
                self.assertEqual(tree_snapshot(self.game), before)
                (self.game / name).unlink()

    def test_valid_json_with_malformed_intent_blocks_without_reset(self):
        self.initialize()
        original = self.payload()
        mutations = (
            lambda d: d.update(authority_granted=True),
            lambda d: d.update(value_claim_eligible=True),
            lambda d: d.update(current_build_assessment="SUPPORTED"),
            lambda d: d.update(state="APPROVED"),
            lambda d: d.update(source_refs=[{"scope": "factory", "path": "AGENTS.md", "sha256": "0" * 64}]),
            lambda d: d.update(source_refs=[{"scope": "game", "path": "../outside", "sha256": "0" * 64}]),
            lambda d: d.update(value_hypotheses=[{"id": "broken", "statement": 7, "source_refs": []}]),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                invalid = copy.deepcopy(original)
                mutate(invalid)
                self.write(intent.PATH, invalid)
                before = tree_snapshot(self.game)
                with self.assertRaises((FactoryError, SystemExit)):
                    self.initialize()
                self.assertEqual(tree_snapshot(self.game), before)
                self.assertEqual(intent.inspect(self.roots)["status"], "INVALID_PRODUCT_INTENT")

    def test_stale_offer_reference_does_not_hide_malformed_audience(self):
        self.initialize()
        data = self.payload()
        source = self.write("synthetic-offer.txt", "Synthetic conditional source, version one.\n")
        data["offer"]["provenance"] = [source]
        data["audience"]["description"] = 23
        self.write(intent.PATH, data)
        self.write("synthetic-offer.txt", "Synthetic conditional source, version two.\n")
        before = tree_snapshot(self.game)
        with self.assertRaises(FactoryError):
            self.initialize()
        self.assertEqual(tree_snapshot(self.game), before)
        self.assertEqual(intent.inspect(self.roots)["status"], "INVALID_PRODUCT_INTENT")

    def test_standalone_start_validates_malformed_intent_before_creating_git_lock(self):
        self.write(intent.PATH, "{ broken synthetic intent\n")
        before = tree_snapshot(self.game)
        with self.assertRaises(FactoryError):
            intent.start(self.roots)
        self.assertEqual(tree_snapshot(self.game), before)

    def test_malformed_routing_markers_block_before_any_initializer_write(self):
        self.write("AGENTS.md", "# User content\n" + factory_setup.BLOCK_BEGIN + "\n")
        before = tree_snapshot(self.game)
        with self.assertRaises(FactoryError):
            self.initialize()
        self.assertEqual(tree_snapshot(self.game), before)

    def test_non_utf8_gitignore_blocks_before_any_initializer_write(self):
        (self.game / ".gitignore").write_bytes(b"# Synthetic invalid UTF-8\n\xff\xfe\n")
        before = tree_snapshot(self.game)
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run):
                with self.assertRaises((FactoryError, UnicodeError)):
                    self.initialize(dry_run=dry_run)
                self.assertEqual(tree_snapshot(self.game), before)

    def test_pending_v2_or_v3_migration_blocks_before_any_write(self):
        for name in (migration.JOURNAL, migration_gpt6.JOURNAL):
            with self.subTest(journal=name):
                self.write(name, {"note": "Synthetic unfinished migration marker"})
                before = tree_snapshot(self.game)
                with self.assertRaises(FactoryError) as raised:
                    self.initialize()
                self.assertEqual(raised.exception.code, "MIGRATION_RECOVERY_REQUIRED")
                self.assertEqual(tree_snapshot(self.game), before)
                (self.game / name).unlink()

    def test_public_product_start_uses_shared_project_lock(self):
        with project_lock(self.game):
            with self.assertRaises(FactoryError) as raised:
                intent.start(self.roots)
        self.assertEqual(raised.exception.code, "CONCURRENT_WRITE")
        self.assertFalse((self.game / intent.PATH).exists())

    def test_initializer_uses_shared_project_lock_without_nested_lock(self):
        with project_lock(self.game):
            with self.assertRaises(FactoryError) as raised:
                self.initialize()
        self.assertEqual(raised.exception.code, "CONCURRENT_WRITE")
        self.assertFalse((self.game / intent.PATH).exists())
        self.initialize()
        self.assertTrue((self.game / intent.PATH).exists())

    def test_changed_missing_and_new_idea_sources_require_deliberate_reconciliation(self):
        self.initialize()
        original = (self.game / intent.PATH).read_bytes()
        probe = self.game / idea.PROBE_RELATIVE
        before_probe = probe.read_bytes()
        changed = read_json(probe)
        changed["interpretation_warning"] += " Synthetic new observation."
        self.write(idea.PROBE_RELATIVE.as_posix(), changed)
        changed_view = intent.inspect(self.roots)
        self.assertEqual(changed_view["status"], "RECONCILIATION_REQUIRED")
        self.assertTrue(changed_view["blockers"])
        self.assertEqual(self.initialize()["product"]["status"], "RECONCILIATION_REQUIRED")
        self.assertEqual((self.game / intent.PATH).read_bytes(), original)
        probe.unlink()
        self.assertEqual(intent.inspect(self.roots)["status"], "RECONCILIATION_REQUIRED")
        probe.write_bytes(before_probe)
        self.assertEqual(intent.inspect(self.roots)["status"], "PRODUCT_INTENT_OPEN")
        self.write(idea.EXPLORATION_MD_RELATIVE.as_posix(), "Synthetic new exploration source.\n")
        view = intent.inspect(self.roots)
        self.assertEqual(view["status"], "RECONCILIATION_REQUIRED")
        self.assertIn(idea.EXPLORATION_MD_RELATIVE.as_posix(), {r["path"] for r in view["current_source_refs"]})
        self.assertNotEqual(view["intent"]["source_refs"], view["current_source_refs"])
        self.assertEqual((self.game / intent.PATH).read_bytes(), original)
        authored = self.payload()
        authored["source_refs"] = view["current_source_refs"]
        authored["material_unknowns"].append("Synthetic new source has been read; still no actual-play evidence.")
        self.write(intent.PATH, authored)
        self.assertEqual(intent.inspect(self.roots)["status"], "PRODUCT_INTENT_OPEN")

    def test_inspect_all_surfaces_are_read_only_and_have_separate_nonbinding_intent(self):
        self.initialize()
        before = tree_snapshot(self.game)
        direct = intent.inspect(self.roots)
        self.assertEqual(value.inspect(self.roots)["product_intent"], direct)
        self.assertEqual(factory_inspect(self.roots)["product_intent"], direct)
        self.assertEqual(tree_snapshot(self.game), before)

    def test_actual_idea_exploration_continues_after_intent_creation_and_authoring(self):
        self.prepare_idea_fixture()
        self.author_intent()
        self._write_exploration(self._exploration(frontier_state="OPEN"))
        result = idea.record_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix())
        self.assertEqual(result.status, idea.IDEA_EXPLORATION_OPEN, result.errors)
        checked = idea.check_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix())
        self.assertEqual(checked.status, idea.IDEA_EXPLORATION_OPEN, checked.errors)
        self.assertEqual(intent.inspect(self.roots)["status"], "RECONCILIATION_REQUIRED")
        self.write("game.gd", "const CURRENT_LOOP = 'genuinely_changed_gameplay'\n")
        stale = idea.check_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix())
        self.assertEqual(stale.status, idea.BLOCKED_BY_IDEA_MATERIAL)
        self.assertTrue(any("repository" in error and "changed" in error for error in stale.errors), stale.errors)

    def test_only_exact_intent_is_excluded_from_idea_probe_candidates_and_binding(self):
        self.prepare_idea_fixture()
        self.author_intent()
        refreshed = idea.start_idea_factory(str(self.game), reopen=True)
        self.assertEqual(refreshed.status, idea.IDEA_EXPLORATION_REQUIRED)
        self.probe = read_json(self.game / idea.PROBE_RELATIVE)
        candidates = {x["path"] for x in self.probe["candidate_product_materials"]}
        self.assertNotIn(intent.PATH, candidates)
        self.assertNotIn(intent.PATH, self.probe["repository"]["dirty_paths"])
        self._write_exploration(self._exploration(frontier_state="OPEN"))
        self.assertEqual(idea.record_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix()).status,
                         idea.IDEA_EXPLORATION_OPEN)
        self.write("design/product_value/OTHER_EVIDENCE.md", "Synthetic material evidence must remain visible.\n")
        stale = idea.check_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix())
        self.assertEqual(stale.status, idea.BLOCKED_BY_IDEA_MATERIAL)

    def test_intent_cannot_be_promoted_to_repo_commitment_in_thesis_provenance(self):
        self.prepare_idea_fixture()
        payload = self._payload(authority="REPO_COMMITMENT")
        alias = idea.WORKSPACE_RELATIVE / "synthetic-intent-alias.json"
        (self.game / alias).symlink_to(self.game / intent.PATH)
        for path in (intent.PATH, "./" + intent.PATH,
                     "design/product_value/../product_value/PRODUCT_VALUE_INTENT.json", alias.as_posix()):
            with self.subTest(path=path):
                payload["decisions"][0]["evidence_refs"] = [{"path": path, "contains": ["product_value_intent.v1"]}]
                self._write_input(payload)
                result = idea.compile_product_thesis(str(self.game), idea.INPUT_RELATIVE.as_posix())
                self.assertEqual(result.status, idea.BLOCKED_BY_IDEA_MATERIAL)
                self.assertTrue(any("intent" in error.lower() for error in result.errors), result.errors)
                self.assertFalse((self.game / idea.THESIS_RELATIVE).exists())

    def test_actual_synthetic_commissioned_idea_is_preserved_without_recompilation(self):
        self.prepare_idea_fixture()
        # Existing helper declares synthetic delegation/commission for this unit test only.
        self._write_input(self._payload())
        compiled = idea.compile_product_thesis(str(self.game), idea.INPUT_RELATIVE.as_posix())
        self.assertEqual(compiled.status, idea.IDEA_FACTORY_READY, compiled.errors)
        before = tree_snapshot(self.game)
        result = self.initialize()
        self.assertEqual(tree_snapshot(self.game), before)
        self.assertEqual(result["product"]["status"], "RECONCILIATION_REQUIRED")
        self.assertFalse(result["product"]["authority_granted"])

    def test_synthetic_partial_authority_is_preserved_and_reported(self):
        self.write(idea.THESIS_RELATIVE.as_posix(), "Synthetic incomplete canonical authority.\n")
        before = (self.game / idea.THESIS_RELATIVE).read_bytes()
        result = self.initialize()
        self.assertEqual((self.game / idea.THESIS_RELATIVE).read_bytes(), before)
        self.assertFalse((self.game / idea.PROBE_RELATIVE).exists())
        self.assertTrue((self.game / intent.PATH).exists())
        self.assertTrue(result["product"]["idea_authority"]["claim_blocked"])
        self.assertFalse(result["product"]["authority_granted"])

    def test_synthetic_archived_authority_and_history_preserved_without_reactivation(self):
        self.canonical_authority(value.NO_ACTIVE)
        historical = self.write("design/studio/synthetic-history.json", {
            "note": "Synthetic archived history; not an actual USER ruling", "status": "USER_REJECTED",
        })
        protected = {p: (self.game / p).read_bytes() for p in intent.IDEA_PATHS if (self.game / p).is_file()}
        protected[historical["path"]] = (self.game / historical["path"]).read_bytes()
        result = self.initialize()
        for name, contents in protected.items():
            self.assertEqual((self.game / name).read_bytes(), contents)
        self.assertEqual(result["product"]["idea_authority"]["status"], value.NO_ACTIVE)
        self.assertTrue(result["product"]["idea_authority"]["claim_blocked"])
        self.assertFalse((self.game / idea.PROBE_RELATIVE).exists())
        self.assertFalse((self.game / "design/factory/PROJECT.json").exists())

    def test_unbuilt_intent_is_never_an_assessment_or_current_offer_gate(self):
        self.initialize()
        self.assertFalse(value.inspect(self.roots)["results"])
        self.assertFalse(intent.inspect(self.roots)["value_claim_eligible"])
        with self.assertRaises(FactoryError):
            value.check(self.roots, intent.PATH)
        with self.assertRaises(FactoryError):
            value.gate(self.roots, intent.PATH, "missing-build.bin")
        self.assertFalse((self.game / "missing-build.bin").exists())

    def test_scenario_priced_early_experiment_needs_no_adoption_or_value_pass(self):
        self.prepare_idea_fixture()
        data = self.author_intent()
        data["offer"].update(status="SCENARIO", grounding="HYPOTHESIS", amount="4.99", currency="USD",
                             rationale="Synthetic conditional experiment price, never an adopted offer.")
        data["audience"].update(grounding="HYPOTHESIS", description="Synthetic strategy-miniature audience")
        self.write(intent.PATH, data)
        view = intent.inspect(self.roots)
        self.assertEqual(view["status"], "PRODUCT_INTENT_DRAFTED")
        self.assertFalse(view["value_claim_eligible"])
        self.assertIsNone(view["intent"]["offer"]["adoption"])
        self._write_exploration(self._exploration(frontier_state="OPEN"))
        explored = idea.record_exploration(str(self.game), idea.EXPLORATION_RELATIVE.as_posix())
        self.assertEqual(explored.status, idea.IDEA_EXPLORATION_OPEN, explored.errors)
        self.assertFalse((self.game / idea.THESIS_RELATIVE).exists())

    def test_v2_selected_routing_and_metadata_stay_v2(self):
        self.migrate(2)
        before = (self.game / "design/factory/PROJECT.json").read_bytes()
        self.initialize()
        self.assertEqual((self.game / "design/factory/PROJECT.json").read_bytes(), before)
        self.assertEqual(project(self.game)["workflow_version"], 2)
        self.assertIn("product", (self.game / "AGENTS.md").read_text().lower())
        self.assertIn(intent.PATH, (self.game / "AGENTS.md").read_text())

    def test_v3_selected_routing_and_metadata_stay_v3(self):
        self.migrate(3)
        before = (self.game / "design/factory/PROJECT.json").read_bytes()
        self.initialize()
        self.assertEqual((self.game / "design/factory/PROJECT.json").read_bytes(), before)
        self.assertEqual(project(self.game)["workflow_version"], 3)
        self.assertEqual(factory_inspect(self.roots)["workflow"], "gpt6")
        self.assertIn("GPT-6", (self.game / "AGENTS.md").read_text())
        self.assertIn(intent.PATH, (self.game / "AGENTS.md").read_text())

    def test_wrong_selected_v3_checkout_rejected_without_any_new_write(self):
        self.migrate(3)
        before = tree_snapshot(self.game)
        with self.assertRaises(FactoryError):
            factory_setup.initialize_game_repo(str(self.game.parent / "other-factory"), str(self.game))
        self.assertEqual(tree_snapshot(self.game), before)

    def check_wrong_selected_pointer_blocks_writes(self, workflow=None, legacy=False):
        if workflow is not None:
            self.migrate(workflow)
        pointer = factory_setup.LEGACY_POINTER_REL_PATH if legacy else factory_setup.POINTER_REL_PATH
        other = Path(self.temporary.name) / "synthetic-other-checkout"
        self.write(pointer, f"STUDIO_ROOT: {other}\nFACTORY_ROOT: {other}\n")
        before = tree_snapshot(self.game)
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run):
                with self.assertRaises(FactoryError) as raised:
                    self.initialize(dry_run=dry_run)
                self.assertEqual(raised.exception.code, "FACTORY_SOURCE_MISMATCH")
                self.assertEqual(tree_snapshot(self.game), before)
                with self.assertRaises(FactoryError) as raised:
                    intent.start(self.roots, dry_run=dry_run)
                self.assertEqual(raised.exception.code, "FACTORY_SOURCE_MISMATCH")
                self.assertEqual(tree_snapshot(self.game), before)

    def test_wrong_selected_v2_pointer_blocks_init_and_product_start_without_relink(self):
        self.check_wrong_selected_pointer_blocks_writes(workflow=2)

    def test_wrong_selected_unversioned_pointer_blocks_init_and_product_start_without_relink(self):
        self.check_wrong_selected_pointer_blocks_writes()

    def test_wrong_selected_legacy_pointer_blocks_init_and_product_start_without_relink(self):
        self.check_wrong_selected_pointer_blocks_writes(legacy=True)

    def test_author_context_v2_and_v3_exposes_intent_separately_from_authority(self):
        for workflow in (2, 3):
            with self.subTest(workflow=workflow):
                self.migrate(workflow)
                self.initialize()
                for capability in ("idea", "product", "studio", "gameplay"):
                    with self.subTest(capability=capability):
                        view = context(self.roots, capability, "assessment" if capability == "product" else "planning")
                        self.assertEqual(view["product_intent"]["reference"], reference(self.game, intent.PATH))
                        self.assertFalse(view["product_intent"]["authority_granted"])
                        self.assertNotIn(intent.PATH, {x["reference"]["path"] for x in view["constraints"]})
                        self.assertNotIn(intent.PATH, authority_paths(self.game, capability))
                self.assertNotIn(intent.PATH, project(self.game)["authority_paths"])

    def test_factory_dependency_sets_include_product_intent_contract_for_each_consumer(self):
        for workflow in (2, 3):
            for capability in ("idea", "product", "studio", "gameplay"):
                with self.subTest(workflow=workflow, capability=capability):
                    paths = {r["path"] for r in factory_dependencies(ROOT, capability, "assessment", workflow)}
                    self.assertIn("product/intent.py", paths)
                    self.assertIn("product/schemas/intent.schema.json", paths)
                    self.assertIn(intent.WORKFLOW, paths)

    def check_intent_input_edit_stales_existing_design(self, workflow):
        self.migrate(workflow)
        self.initialize()
        body = "Synthetic readable lantern.\nKeep it readable in the smallest experiment.\n"
        artifact = self.write("design/assets/DESIGN.md", body)
        data = {
            "schema_version": f"factory_design.v{workflow}", "design_id": "synthetic-lantern", "capability": "asset",
            "task": "prop", "author_context_id": "synthetic-author", "intent": "Test an explicit planning input.",
            "artifacts": [artifact], "inputs": [reference(self.game, intent.PATH)],
            "decisions": [{"id": "light", "source": artifact, "excerpt": "Synthetic readable lantern.",
                           "consequence": "Keep it readable in the smallest experiment."}],
            "requirements": {}, "production_scope": ["texture/lantern.png"], "acceptance": ["Synthetic visual check."],
        }
        if workflow == 3:
            data.update(methods=[], decision_sections=[{
                "id": "appearance", "source": artifact, "text": body, "decision_ids": ["light"],
            }])
        design = self.write("design/assets/PACKAGE.json", data)
        out = checkpoint(self.roots, {"task_id": "synthetic-lantern", "previous": None, "capability": "asset", "task": "prop",
                                     "stage": "DESIGN_COMPLETE", "summary": "Synthetic contract fixture, no USER approval.",
                                     "unresolved": [], "artifacts": [], "design": design})
        record, _ = latest(self.game, "synthetic-lantern")
        before = (self.game / out["checkpoint"]["path"]).read_bytes()
        self.author_intent()
        with self.assertRaises(FactoryError):
            verify_record(self.roots, record)
        self.assertEqual((self.game / out["checkpoint"]["path"]).read_bytes(), before)

    def test_exact_intent_input_edit_stales_v2_design_without_rehashing_history(self):
        self.check_intent_input_edit_stales_existing_design(2)

    def test_exact_intent_input_edit_stales_v3_design_without_rehashing_history(self):
        self.check_intent_input_edit_stales_existing_design(3)

    def test_seed_and_authored_intent_match_schema_and_fixed_false_contract(self):
        import jsonschema
        schema = read_json(ROOT / "product/schemas/intent.schema.json")
        jsonschema.Draft202012Validator.check_schema(schema)
        self.initialize()
        jsonschema.validate(self.payload(), schema)
        drafted = self.author_intent()
        jsonschema.validate(drafted, schema)
        intent.validate(self.roots, drafted)
        for key, bad in (("authority_granted", True), ("value_claim_eligible", True),
                         ("current_build_assessment", "SUPPORTED"), ("state", "APPROVED")):
            with self.subTest(field=key):
                mutated = copy.deepcopy(drafted)
                mutated[key] = bad
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(mutated, schema)
                with self.assertRaises(FactoryError):
                    intent.validate(self.roots, mutated)


if __name__ == "__main__":
    unittest.main()
