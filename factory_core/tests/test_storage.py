"""Synthetic tiny fixtures only: no engine, repository mutation, or real cleanup."""
from datetime import datetime, timezone
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from factory_core.refs import FactoryError
from factory_core.storage import SCHEMA, audit, load_manifest

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "workspace"
        self.root.mkdir()
        self.write("retired/runner/.godot/imported/a.ctex", b"cache")
        self.write("retired/runner/project.godot", b"source")
        self.write("retired/evidence/failure.png", b"original evidence")
        self.manifest = {"schema_version": SCHEMA, "protected_paths": [], "runs": [
            {"id": "synthetic-old-run", "path": "retired", "owner": "fixture-owner",
             "state": "retired", "retired_at": "2026-10-01T00:00:00Z", "caches": [
                 {"path": "runner/.godot", "kind": "godot_import",
                  "rebuild_recipe": "Recorded import command, never executed by the auditor",
                  "preserved_inputs": ["fixture source revision + exact assets/config manifest"]}]}]}

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return path

    def run_audit(self, **kwargs):
        kwargs.setdefault("manifest", self.manifest)
        kwargs.setdefault("reserve_bytes", 0)
        kwargs.setdefault("now", NOW)
        return audit(self.root, **kwargs)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_read_only_and_rebuild_recipe_is_not_executed(self):
        before = self.snapshot()
        with patch("subprocess.run", side_effect=AssertionError("must not execute a recipe")):
            result = self.run_audit()
        self.assertEqual(before, self.snapshot())
        self.assertTrue(result["advisory_only"])
        self.assertEqual(1, len(result["review_candidates"]))
        self.assertEqual("operator_required", result["review_candidates"][0]["reconstruction_verification"])
        self.assertEqual([], result["blockers"])

    def test_inventory_without_manifest_does_not_infer_candidates(self):
        result = self.run_audit(manifest=None)
        self.assertEqual([], result["review_candidates"])
        self.assertEqual(5, result["categories"][".godot"]["logical_bytes"])
        self.assertEqual(3, result["totals"]["files"])

    def test_old_folder_name_does_not_retire_active_paused_or_closed_runner(self):
        for state in ("active", "paused", "closed"):
            with self.subTest(state=state):
                self.manifest["runs"][0]["state"] = state
                result = self.run_audit()
                self.assertFalse(result["review_candidates"])
                self.assertIn("run_not_retired", result["held_candidates"][0]["reasons"])

    def test_current_runner_override_wins_over_retired_declaration(self):
        result = self.run_audit(protected=["retired/runner"])
        self.assertFalse(result["review_candidates"])
        self.assertIn("protected_path_overlap", result["held_candidates"][0]["reasons"])

    def test_protected_descendant_blocks_whole_cache_and_root_pin_blocks_all(self):
        for path in ("retired/runner/.godot/imported/a.ctex", "."):
            self.manifest["protected_paths"] = [path]
            self.assertFalse(self.run_audit()["review_candidates"])

    def test_component_boundaries_not_string_prefixes(self):
        self.manifest["protected_paths"] = ["retired/runner-other"]
        self.assertEqual(1, len(self.run_audit()["review_candidates"]))

    def test_evidence_cache_is_protected_even_if_declared_retired(self):
        self.write("retired/evidence/.godot/item", b"original evidence")
        self.manifest["runs"][0]["caches"][0]["path"] = "evidence/.godot"
        self.assertIn("protected_path_overlap", self.run_audit()["held_candidates"][0]["reasons"])

    def test_future_or_recent_retirement_is_held(self):
        for stamp in ("2026-11-10T00:00:00Z", "2026-11-08T00:00:00Z"):
            self.manifest["runs"][0]["retired_at"] = stamp
            self.assertIn("retirement_grace_not_met", self.run_audit()["held_candidates"][0]["reasons"])

    def test_missing_retirement_and_naive_time_rejected(self):
        run = self.manifest["runs"][0]
        del run["retired_at"]
        with self.assertRaises(FactoryError):
            self.run_audit()
        run["retired_at"] = "2026-10-01T00:00:00"
        with self.assertRaises(FactoryError):
            self.run_audit()

    def test_path_traversal_absolute_and_ambiguous_paths_rejected(self):
        for path in ("../escape/.godot", "/outside/.godot", "runner//.godot", "runner/./.godot", "C:/.godot", "runner\\.godot"):
            self.manifest["runs"][0]["caches"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(FactoryError):
                self.run_audit()

    def test_unknown_cache_names_and_missing_reconstruction_rejected(self):
        cache = self.manifest["runs"][0]["caches"][0]
        cache["path"] = "evidence"
        with self.assertRaises(FactoryError):
            self.run_audit()
        cache["path"] = "runner/.godot"
        cache["preserved_inputs"] = []
        with self.assertRaises(FactoryError):
            self.run_audit()

    def test_unknown_version_and_typo_rejected(self):
        self.manifest["schema_version"] = "future"
        with self.assertRaises(FactoryError):
            self.run_audit()
        self.manifest["schema_version"] = SCHEMA
        self.manifest["protected_path"] = []
        with self.assertRaises(FactoryError):
            self.run_audit()

    def test_overlapping_runs_and_duplicate_cache_rejected(self):
        run = self.manifest["runs"][0]
        second = dict(run, id="other", path="retired/runner", caches=[])
        self.manifest["runs"].append(second)
        with self.assertRaises(FactoryError):
            self.run_audit()
        self.manifest["runs"].pop()
        run["caches"].append(dict(run["caches"][0]))
        with self.assertRaises(FactoryError):
            self.run_audit()

    def test_no_symlink_traversal_or_cache_nomination(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "private").write_bytes(b"not scanned")
        os.symlink(outside, self.root / "retired/runner/.godot/alias")
        result = self.run_audit()
        self.assertEqual(3, result["totals"]["files"])
        self.assertFalse(result["review_candidates"])
        self.assertEqual(1, result["totals"]["symlinks"])

    def test_symlink_in_workspace_ancestor_is_rejected(self):
        alias = Path(self.temp.name) / "alias"
        os.symlink(self.root.parent, alias)
        with self.assertRaises(OSError):
            audit(alias / "workspace", reserve_bytes=0)

    def test_missing_or_file_instead_of_cache_is_held(self):
        cache = self.manifest["runs"][0]["caches"][0]
        cache["path"] = "missing/.godot"
        self.assertFalse(self.run_audit()["review_candidates"])
        self.write("retired/missing/.godot", b"not a directory")
        self.assertIn("cache_directory_not_observed", self.run_audit()["held_candidates"][0]["reasons"])

    def test_hardlinks_and_special_files_are_held(self):
        os.link(self.root / "retired/runner/project.godot", self.root / "retired/runner/.godot/hardlink")
        result = self.run_audit()
        self.assertFalse(result["review_candidates"])
        self.assertEqual(2, result["totals"]["hardlinked_files"])
        os.mkfifo(self.root / "retired/runner/.godot/fifo")
        self.assertEqual(1, self.run_audit()["totals"]["special_files"])

    def test_private_directories_are_not_scanned(self):
        self.write("retired/runner/.godot/.codex/private", b"not read")
        result = self.run_audit()
        self.assertEqual(3, result["totals"]["files"])
        self.assertFalse(result["review_candidates"])
        self.assertEqual(1, len(result["excluded_private_directories"]))

    def test_entry_limit_fails_closed(self):
        result = self.run_audit(max_entries=2)
        self.assertFalse(result["complete_within_declared_scope"])
        self.assertFalse(result["review_candidates"])
        self.assertTrue(result["blockers"])
        self.assertEqual(2, result["entries_scanned"])

    def test_time_limit_fails_closed(self):
        with patch("factory_core.storage.time.monotonic", side_effect=[0, 2]):
            result = self.run_audit(max_seconds=1)
        self.assertTrue(result["issues"])
        self.assertFalse(result["review_candidates"])

    def test_unreadable_directory_fails_closed(self):
        original = os.scandir
        calls = 0
        def guarded(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise PermissionError("fixture")
            return original(fd)
        with patch("factory_core.storage.os.scandir", side_effect=guarded) as mocked:
            # Capability check normally uses identity of the stdlib function.
            with patch("factory_core.storage.os.supports_fd", os.supports_fd | {mocked}):
                result = self.run_audit()
        self.assertTrue(result["issues"])
        self.assertFalse(result["review_candidates"])

    def test_budget_reserves_peak_writes_plus_margin(self):
        result = self.run_audit(expected_write_bytes=10 ** 30, reserve_bytes=10)
        self.assertFalse(result["capacity"]["sufficient"])
        self.assertEqual(10 ** 30 + 10, result["capacity"]["required_free_bytes"])
        self.assertTrue(result["blockers"])

    def test_invalid_limits_and_broad_root_rejected(self):
        for args in ({"max_entries": 0}, {"max_seconds": -1}, {"reserve_bytes": -1}, {"min_retired_days": True}):
            with self.subTest(args=args), self.assertRaises(FactoryError):
                self.run_audit(**args)
        with self.assertRaises(FactoryError):
            audit("/")
        with self.assertRaises(FactoryError):
            audit(Path.home())

    def test_manifest_loader_rejects_duplicate_keys_and_oversize(self):
        path = self.write("manifest.json", b'{"runs": [], "runs": []}')
        with self.assertRaises(FactoryError):
            load_manifest(path)
        path.write_bytes(b" " * (1024 * 1024 + 1))
        with self.assertRaises(FactoryError):
            load_manifest(path)

    def test_conventional_protected_descendants_hold_the_cache(self):
        for name in ("evidence", "saves", "checkpoints", ".git"):
            with self.subTest(name=name):
                self.assertTrue(self.run_audit()["review_candidates"])
                fixture = self.write("retired/runner/.godot/" + name + "/original", b"retain")
                result = self.run_audit()
                self.assertFalse(result["review_candidates"])
                self.assertIn("protected_descendant", result["held_candidates"][0]["reasons"])
                fixture.unlink()
                fixture.parent.rmdir()
        self.assertTrue(self.run_audit()["review_candidates"])
        self.write("retired/runner/.godot/.git", b"gitdir: retained source")
        self.assertIn("protected_descendant", self.run_audit()["held_candidates"][0]["reasons"])

    def test_manifest_mutation_during_read_is_rejected(self):
        path = self.write("changing.json", b'{}')
        original = os.fdopen
        @contextlib.contextmanager
        def changing(descriptor, *args, **kwargs):
            with original(descriptor, *args, **kwargs) as handle:
                class ChangingReader:
                    def fileno(self):
                        return handle.fileno()
                    def read(self, amount):
                        raw = handle.read(amount)
                        path.write_bytes(b'{"changed": true}')
                        return raw
                yield ChangingReader()
        with patch("factory_core.storage.os.fdopen", side_effect=changing):
            with self.assertRaisesRegex(FactoryError, "Manifest changed"):
                load_manifest(path)

    def test_manifest_fifo_directory_and_symlink_are_rejected(self):
        fifo = self.root / "manifest-pipe"
        os.mkfifo(fifo)
        with self.assertRaises(FactoryError):
            load_manifest(fifo)
        with self.assertRaises((FactoryError, OSError)):
            load_manifest(self.root)
        regular = self.write("regular.json", b'{}')
        alias = self.root / "manifest-link.json"
        os.symlink(regular, alias)
        with self.assertRaises(OSError):
            load_manifest(alias)

    def test_directory_replaced_by_symlink_between_stat_and_open_is_not_followed(self):
        original = os.open
        cache = self.root / "retired/runner/.godot"
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "private").write_bytes(b"not scanned")
        replaced = False
        def racing(path, *args, **kwargs):
            nonlocal replaced
            if path == ".godot" and not replaced:
                replaced = True
                cache.rename(cache.with_name("preserved-cache"))
                os.symlink(outside, cache)
            return original(path, *args, **kwargs)
        with patch("factory_core.storage.os.open", side_effect=racing) as mocked:
            with patch("factory_core.storage.os.supports_dir_fd", os.supports_dir_fd | {mocked}):
                result = self.run_audit()
        self.assertTrue(replaced)
        self.assertFalse(result["review_candidates"])
        self.assertTrue(any(x["reason"] == "directory_open_failed_or_changed" for x in result["issues"]))
        self.assertEqual(b"not scanned", (outside / "private").read_bytes())

    def test_directory_mutation_during_enumeration_is_reported(self):
        from factory_core import storage
        original = storage._record
        changed = False
        def mutate(metric, info):
            nonlocal changed
            if not changed:
                changed = True
                before = self.root.stat()
                os.utime(self.root, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000000))
            return original(metric, info)
        with patch("factory_core.storage._record", side_effect=mutate):
            result = self.run_audit()
        self.assertFalse(result["review_candidates"])
        self.assertTrue(any(x["reason"] == "directory_changed_during_scan" for x in result["issues"]))

    def test_cross_device_directories_are_excluded(self):
        from types import SimpleNamespace
        original = os.fstat
        def other_device(fd):
            info = original(fd)
            fields = {key: getattr(info, key) for key in dir(info) if key.startswith("st_")}
            fields["st_dev"] += 1
            return SimpleNamespace(**fields)
        with patch("factory_core.storage.os.fstat", side_effect=other_device):
            result = self.run_audit()
        self.assertFalse(result["review_candidates"])
        self.assertTrue(any(x["reason"] == "different_filesystem_not_scanned" for x in result["issues"]))

    def test_depth_limit_fails_closed(self):
        path = "retired/runner/.godot/" + "/".join(["d"] * 66) + "/last"
        self.write(path, b"fixture")
        result = self.run_audit()
        self.assertFalse(result["review_candidates"])
        self.assertTrue(any(x["reason"] == "depth_limit" for x in result["issues"]))

    def test_truncated_private_exclusion_list_still_holds_candidate(self):
        for index in range(105):
            self.write(f"retired/runner/.godot/{index}/.codex/private", b"not scanned")
        result = self.run_audit()
        self.assertEqual(100, len(result["excluded_private_directories"]))
        self.assertEqual(105, result["held_candidates"][0]["observed"]["excluded_directories"])
        self.assertIn("uninspected_private_directory", result["held_candidates"][0]["reasons"])

    def test_top_level_report_is_bounded(self):
        for index in range(60):
            self.write(f"file-{index}", b"fixture")
        result = self.run_audit()
        self.assertEqual(50, len(result["top_level"]))
        self.assertEqual(11, result["top_level_omitted"])

    def test_unsupported_no_follow_platform_fails_closed(self):
        with patch("factory_core.storage.os.supports_fd", set()):
            with self.assertRaises(FactoryError) as raised:
                self.run_audit()
        self.assertEqual("STORAGE_UNSUPPORTED", raised.exception.code)

    def test_cli_works_outside_game_repo_without_migration(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "factory.py"), "storage",
            "--workspace-root", str(self.root), "--reserve-bytes", "0"],
            text=True, capture_output=True, cwd=self.root)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("STORAGE_AUDIT", json.loads(result.stdout)["status"])

    def test_cli_has_no_apply_or_delete_and_storage_errors_are_structured(self):
        import factory
        for option in ("--apply", "--delete"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                factory.parser().parse_args(["storage", "--workspace-root", str(self.root), option])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = factory.main(["storage", "--workspace-root", str(self.root), "--max-entries", "0"])
        self.assertEqual(2, status)
        self.assertEqual("INVALID_STORAGE_INPUT", json.loads(output.getvalue())["status"])


if __name__ == "__main__":
    unittest.main()
