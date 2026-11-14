"""Synthetic tiny fixtures only: no engine, repository mutation, or real cleanup."""
from datetime import datetime, timezone
import contextlib
import copy
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
from factory_core.storage import PRIVATE_NAMES, PROTECTED_NAMES, SCHEMA, audit, capacity, load_manifest

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

    def case_alias(self, path):
        alias = path.with_name(path.name.swapcase())
        if not alias.exists() or not path.samefile(alias):
            if os.environ.get("FACTORY_REQUIRE_CASE_INSENSITIVE_TESTS") == "1":
                self.fail("This job requires a case-insensitive fixture filesystem")
            self.skipTest("Fixture filesystem is case-sensitive")
        return alias

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

    def test_protected_scope_case_aliases_hold_cache_and_preserve_exact_paths(self):
        for path in ("Retired/RUNNER", "RETIRED/RUNNER/.GODOT/imported/A.CTEX"):
            for source in ("manifest", "argument"):
                with self.subTest(path=path, source=source):
                    self.manifest["protected_paths"] = [path] if source == "manifest" else []
                    result = self.run_audit(protected=[path] if source == "argument" else [])
                    self.assertFalse(result["review_candidates"])
                    held = result["held_candidates"][0]
                    self.assertIn("protected_path_overlap", held["reasons"])
                    self.assertEqual("retired/runner/.godot", held["path"])
                    self.assertEqual([path], result["protected_paths"])

    def test_canonical_unicode_scope_aliases_hold_cache(self):
        self.write("caf\u00e9/runner/.godot/imported/item", b"cache")
        self.manifest["runs"][0]["path"] = "caf\u00e9"
        result = self.run_audit(protected=["CAFE\u0301/RUNNER"])
        self.assertFalse(result["review_candidates"])
        self.assertIn("protected_path_overlap", result["held_candidates"][0]["reasons"])
        self.assertEqual("caf\u00e9/runner/.godot", result["held_candidates"][0]["path"])

    def test_case_alias_comparisons_preserve_component_boundaries(self):
        result = self.run_audit(protected=["RETIRED/RUNNER-other", "RETIRED-other"])
        self.assertEqual(1, len(result["review_candidates"]))

    def test_case_aliased_active_and_nested_run_roots_are_rejected(self):
        original = copy.deepcopy(self.manifest)
        for path in ("RETIRED", "RETIRED/RUNNER"):
            for reverse in (False, True):
                with self.subTest(path=path, reverse=reverse):
                    manifest = copy.deepcopy(original)
                    manifest["runs"].append({"id": "active", "path": path,
                        "owner": "fixture-owner", "state": "active", "caches": []})
                    if reverse:
                        manifest["runs"].reverse()
                    with self.assertRaisesRegex(FactoryError, "Run roots must not overlap"):
                        self.run_audit(manifest=manifest)

    def test_case_aliased_cache_roots_are_rejected(self):
        cache = self.manifest["runs"][0]["caches"][0]
        for path in ("RUNNER/.godot", "RUNNER/.GODOT/imported/.godot"):
            with self.subTest(path=path):
                manifest = copy.deepcopy(self.manifest)
                manifest["runs"][0]["caches"].append(dict(cache, path=path))
                with self.assertRaisesRegex(FactoryError, "Cache paths must not overlap"):
                    self.run_audit(manifest=manifest)

    def test_conventional_protected_ancestor_case_aliases_hold_cache(self):
        for name in sorted(PROTECTED_NAMES):
            with self.subTest(name=name):
                relative = name.upper() + "/.godot"
                self.write("retired/" + relative + "/original", b"retain")
                self.manifest["runs"][0]["caches"][0]["path"] = relative
                result = self.run_audit()
                self.assertFalse(result["review_candidates"])
                self.assertIn("protected_path_overlap", result["held_candidates"][0]["reasons"])

    def test_conventional_protected_descendant_case_aliases_hold_cache(self):
        for name in sorted(PROTECTED_NAMES):
            with self.subTest(name=name):
                fixture = self.write("retired/runner/.godot/" + name.upper() + "/original", b"retain")
                result = self.run_audit()
                self.assertFalse(result["review_candidates"])
                self.assertIn("protected_descendant", result["held_candidates"][0]["reasons"])
                fixture.unlink()
                fixture.parent.rmdir()
        self.write("retired/runner/.godot/.GIT", b"gitdir: retained source")
        self.assertIn("protected_descendant", self.run_audit()["held_candidates"][0]["reasons"])

    def test_private_directory_case_aliases_are_not_scanned(self):
        paths = ["retired/runner/.godot/" + name.upper() for name in sorted(PRIVATE_NAMES)]
        for path in paths:
            self.write(path + "/private", b"must not be scanned")
        result = self.run_audit()
        self.assertEqual(3, result["totals"]["files"])
        self.assertFalse(result["review_candidates"])
        self.assertEqual(set(paths), {item["path"] for item in result["excluded_private_directories"]})
        self.assertIn("uninspected_private_directory", result["held_candidates"][0]["reasons"])

    def test_cache_observation_still_requires_exact_entry_spelling(self):
        self.manifest["runs"][0]["caches"][0]["path"] = "RUNNER/.godot"
        result = self.run_audit()
        self.assertFalse(result["review_candidates"])
        self.assertIn("cache_directory_not_observed", result["held_candidates"][0]["reasons"])

    def test_native_case_alias_cannot_unprotect_active_runner(self):
        runner = self.root / "retired/runner"
        alias = self.case_alias(self.root / "retired") / "RUNNER"
        self.assertTrue(runner.samefile(alias))
        result = self.run_audit(protected=[str(alias.relative_to(self.root))])
        self.assertFalse(result["review_candidates"])
        self.assertIn("protected_path_overlap", result["held_candidates"][0]["reasons"])

    def test_native_case_alias_cannot_register_active_run_as_disjoint(self):
        alias = self.case_alias(self.root / "retired")
        self.manifest["runs"].append({"id": "active", "path": alias.name,
            "owner": "fixture-owner", "state": "active", "caches": []})
        with self.assertRaisesRegex(FactoryError, "Run roots must not overlap"):
            self.run_audit()

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

    def test_home_identity_is_rejected_before_scan_and_descriptor_is_closed(self):
        from factory_core import storage
        home = Path(self.temp.name) / "synthetic-home-alias"
        home.symlink_to(self.root, target_is_directory=True)
        self.assertTrue(home.samefile(self.root))
        opened = []
        original = storage._open_root
        def record_open(path):
            descriptor = original(path)
            opened.append(descriptor)
            return descriptor
        with patch("factory_core.storage.Path.home", return_value=home), \
                patch("factory_core.storage._open_root", side_effect=record_open), \
                patch("factory_core.storage.os.scandir", wraps=os.scandir) as scan:
            with patch("factory_core.storage.os.supports_fd", os.supports_fd | {scan}):
                with self.assertRaisesRegex(FactoryError, "home directory"):
                    self.run_audit()
            scan.assert_not_called()
        self.assertEqual(1, len(opened))
        with self.assertRaises(OSError):
            os.fstat(opened[0])

    def test_home_guard_checks_opened_root_not_replaced_pathname(self):
        from factory_core import storage
        home = self.root.with_name("synthetic-home")
        original = storage._open_root
        def replace_root(path):
            descriptor = original(path)
            self.root.rename(home)
            self.root.mkdir()
            return descriptor
        with patch("factory_core.storage.Path.home", return_value=home), \
                patch("factory_core.storage._open_root", side_effect=replace_root):
            with self.assertRaisesRegex(FactoryError, "home directory"):
                self.run_audit()

    def test_unavailable_home_identity_fails_closed_before_scan(self):
        with patch("factory_core.storage.Path.home", return_value=self.root / "missing-home"), \
                patch("factory_core.storage.os.scandir", wraps=os.scandir) as scan:
            with patch("factory_core.storage.os.supports_fd", os.supports_fd | {scan}):
                with self.assertRaises(OSError):
                    self.run_audit()
            scan.assert_not_called()

    def test_native_case_alias_cannot_bypass_home_guard(self):
        alias = self.case_alias(self.root)
        with patch("factory_core.storage.Path.home", return_value=self.root), \
                patch("factory_core.storage.os.scandir", wraps=os.scandir) as scan:
            with patch("factory_core.storage.os.supports_fd", os.supports_fd | {scan}):
                with self.assertRaisesRegex(FactoryError, "home directory"):
                    audit(alias, reserve_bytes=0)
            scan.assert_not_called()

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

    def capacity_cli(self, *options):
        import factory
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = factory.main(["storage", "--capacity-only", "--workspace-root", str(self.root), *options])
        return status, json.loads(output.getvalue())

    def test_capacity_does_not_enumerate_or_read_contents(self):
        with patch("factory_core.storage.os.scandir", side_effect=AssertionError("must not scan")), \
                patch("factory_core.storage.os.supports_fd", set()), \
                patch("builtins.open", side_effect=AssertionError("must not read content")), \
                patch("factory_core.storage.os.fdopen", side_effect=AssertionError("must not read manifest")):
            result = capacity(self.root, expected_write_bytes=123)
        self.assertEqual("STORAGE_CAPACITY", result["status"])
        self.assertFalse(result["inventory_performed"])
        self.assertFalse(result["cleanup_authorized"])
        self.assertEqual(0, result["entries_scanned"])
        self.assertEqual([], result["review_candidates"])
        self.assertEqual({"device": self.root.stat().st_dev, "root_inode": self.root.stat().st_ino},
            result["filesystem_identity"])
        self.assertEqual(2 * 1024 ** 3, result["capacity"]["reserve_bytes"])

    def test_capacity_still_requires_no_follow_directory_support(self):
        with patch("factory_core.storage.os.supports_dir_fd", set()):
            status, result = self.capacity_cli("--expected-write-bytes", "0")
        self.assertEqual(2, status)
        self.assertEqual("STORAGE_UNSUPPORTED", result["status"])

    def test_capacity_unavailable_fails_closed_and_closes_descriptor(self):
        opened = []
        def unavailable(fd):
            opened.append(fd)
            raise OSError("capacity unavailable")
        with patch("factory_core.storage.os.fstatvfs", side_effect=unavailable):
            status, result = self.capacity_cli("--expected-write-bytes", "0")
        self.assertEqual(2, status)
        self.assertEqual("INVALID_INPUT", result["status"])
        self.assertIn("capacity unavailable", result["message"])
        with self.assertRaises(OSError):
            os.fstat(opened[0])

    def test_capacity_threshold_uses_available_not_free_blocks(self):
        from types import SimpleNamespace
        disk = SimpleNamespace(f_frsize=4, f_bsize=8, f_blocks=100, f_bavail=10, f_bfree=90)
        with patch("factory_core.storage.os.fstatvfs", return_value=disk):
            equal = capacity(self.root, expected_write_bytes=30, reserve_bytes=10)
            over = capacity(self.root, expected_write_bytes=31, reserve_bytes=10)
            disk.f_frsize = 0
            fallback = capacity(self.root, expected_write_bytes=80, reserve_bytes=0)
        self.assertEqual(40, equal["capacity"]["free_bytes"])
        self.assertTrue(equal["capacity"]["sufficient"])
        self.assertFalse(over["capacity"]["sufficient"])
        self.assertTrue(over["blockers"])
        self.assertEqual(80, fallback["capacity"]["free_bytes"])

    def test_capacity_rejects_invalid_byte_estimates(self):
        for name in ("expected_write_bytes", "reserve_bytes"):
            for value in (-1, True, 1.5, "100", None):
                with self.subTest(name=name, value=value):
                    args = {"expected_write_bytes": 0, name: value}
                    with self.assertRaises(FactoryError):
                        capacity(self.root, **args)

    def test_capacity_rejects_unsafe_or_missing_roots(self):
        alias = self.root.parent / "workspace-link"
        os.symlink(self.root, alias)
        for root in (Path(self.root.anchor), Path.home(), alias, alias / "retired", self.root / "missing"):
            with self.subTest(root=root), self.assertRaises((FactoryError, OSError)):
                capacity(root, expected_write_bytes=0)

    def test_capacity_rejects_home_alias_identity_and_closes_descriptor(self):
        from factory_core import storage
        original = storage._open_root
        opened = []
        def capture(root):
            fd = original(root)
            opened.append(fd)
            return fd
        # A different spelling resolving to the same inode must not bypass home protection.
        with patch("factory_core.storage.Path.home", return_value=self.root / "retired/.."), \
                patch("factory_core.storage._open_root", side_effect=capture):
            with self.assertRaises(FactoryError):
                capacity(self.root, expected_write_bytes=0)
        with self.assertRaises(OSError):
            os.fstat(opened[0])

    def test_capacity_ignores_descendant_churn_without_hiding_audit_failure(self):
        original = os.fstatvfs
        temporary = self.write("retired/runner/transient.json", b"temporary")
        def changing(fd):
            temporary.unlink()
            self.write("retired/runner/new-transient.json", b"new")
            return original(fd)
        with patch("factory_core.storage.os.fstatvfs", side_effect=changing):
            result = capacity(self.root, expected_write_bytes=0, reserve_bytes=0)
        self.assertTrue(result["capacity"]["sufficient"])
        self.assertEqual([], result["blockers"])
        self.assertFalse(result["inventory_performed"])
        # Full inventory keeps its existing fail-closed behavior.
        self.assertTrue(self.run_audit(max_entries=1)["blockers"])

    def test_capacity_cli_requires_estimate_and_rejects_inventory_options_before_reading(self):
        with patch("factory_core.storage.load_manifest", side_effect=AssertionError("must not read")):
            status, result = self.capacity_cli()
            self.assertEqual(2, status)
            self.assertEqual("INVALID_STORAGE_INPUT", result["status"])
            for options in (("--manifest", "missing.json"), ("--protect", "retired"),
                    ("--min-retired-days", "7"), ("--max-entries", "500000"), ("--max-seconds", "30")):
                with self.subTest(options=options):
                    status, result = self.capacity_cli("--expected-write-bytes", "0", *options)
                    self.assertEqual(2, status)
                    self.assertEqual("INVALID_STORAGE_INPUT", result["status"])

    def test_capacity_cli_success_and_insufficient_space(self):
        status, result = self.capacity_cli("--expected-write-bytes", "0", "--reserve-bytes", "0")
        self.assertEqual(0, status)
        self.assertEqual("STORAGE_CAPACITY", result["status"])
        status, result = self.capacity_cli("--expected-write-bytes", str(result["capacity"]["total_bytes"] + 1))
        self.assertEqual(2, status)
        self.assertFalse(result["capacity"]["sufficient"])
        status, result = self.capacity_cli("--expected-write-bytes", "-1")
        self.assertEqual(2, status)
        self.assertEqual("INVALID_STORAGE_INPUT", result["status"])


if __name__ == "__main__":
    unittest.main()
