"""Bounded, read-only workspace inventory and non-authorizing cache review queue."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time
import unicodedata

from factory_core.refs import FactoryError

GIB = 1024 ** 3
SCHEMA = "factory_storage_manifest.v1"
CACHE_NAMES = {"godot_import": ".godot", "python_bytecode": "__pycache__", "pytest": ".pytest_cache"}
PRIVATE_NAMES = {".codex", ".aws", ".ssh", ".gnupg"}
PROTECTED_NAMES = PRIVATE_NAMES | {".git", "design", "evidence", "saves", "save", "checkpoints", "archives"}
STATES = {"active", "paused", "closed", "retired"}


def _invalid(message):
    raise FactoryError("INVALID_STORAGE_INPUT", message)


def _relative(value, allow_root=False):
    if allow_root and value == ".":
        return value
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or PurePosixPath(value).is_absolute()
            or any(p in ("", ".", "..") for p in value.split("/"))):
        _invalid(f"Expected a confined relative path: {value!r}")
    return value


def _name_key(value):
    # Compare conservatively on every platform: macOS volumes can alias case
    # and canonically equivalent Unicode. Never use this key for filesystem I/O.
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", value).casefold())


def _scope_parts(value):
    return tuple(_name_key(part) for part in value.split("/"))


def _overlap(left, right):
    if left == "." or right == ".":
        return True
    left, right = _scope_parts(left), _scope_parts(right)
    return left[:len(right)] == right or right[:len(left)] == left


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _invalid(f"{field} must be a nonempty string")
    return value


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        _invalid(f"Expected keys {sorted(required)}, optional {sorted(optional)}")


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(_text(value, "retired_at").replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        _invalid(f"retired_at must be an ISO 8601 timestamp with timezone: {exc}")


def load_manifest(path):
    """Only this explicit, bounded manifest is read; inventory reads no file bytes."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _invalid(f"Duplicate manifest key: {key}")
            result[key] = value
        return result
    path = Path(os.path.abspath(Path(path).expanduser()))
    parent = _open_root(path.parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            _invalid("Manifest must be a regular file, not a pipe, device or stream")
        if before.st_size > 1024 * 1024:
            _invalid("Manifest exceeds 1 MiB")
        raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            _invalid("Manifest exceeds 1 MiB")
        if _identity(before) != _identity(os.fstat(handle.fileno())):
            _invalid("Manifest changed while being read")
    return json.loads(raw, object_pairs_hook=unique)


def _manifest(value, extra_protected):
    if value is None:
        value = {"schema_version": SCHEMA, "protected_paths": [], "runs": []}
    _keys(value, {"schema_version", "protected_paths", "runs"})
    if value["schema_version"] != SCHEMA:
        _invalid("Unsupported storage manifest version")
    if not isinstance(value["protected_paths"], list) or not isinstance(value["runs"], list):
        _invalid("protected_paths and runs must be lists")
    protected = [_relative(p, allow_root=True) for p in value["protected_paths"] + list(extra_protected)]
    if len(protected) > 1000 or len(value["runs"]) > 1000:
        _invalid("At most 1000 protected paths and runs are supported")
    candidates, ids, roots = {}, set(), []
    for run in value["runs"]:
        _keys(run, {"id", "path", "owner", "state", "caches"}, {"retired_at"})
        run_id = _text(run["id"], "id")
        if run_id in ids:
            _invalid("Duplicate run id")
        ids.add(run_id)
        root = _relative(run["path"])
        if any(_overlap(root, old) for old in roots):
            _invalid("Run roots must not overlap; use protected_paths for a reused active runner")
        roots.append(root)
        _text(run["owner"], "owner")
        if run["state"] not in STATES:
            _invalid("Unknown run state; never infer retirement from a name or date")
        retired = _timestamp(run["retired_at"]) if "retired_at" in run else None
        if run["state"] == "retired" and retired is None:
            _invalid("Retired runs require retired_at")
        if not isinstance(run["caches"], list):
            _invalid("caches must be a list")
        for cache in run["caches"]:
            _keys(cache, {"path", "kind", "rebuild_recipe", "preserved_inputs"})
            relative = _relative(cache["path"])
            if cache["kind"] not in CACHE_NAMES or PurePosixPath(relative).name != CACHE_NAMES[cache["kind"]]:
                _invalid("Only explicitly declared .godot, __pycache__, and .pytest_cache directories are supported")
            _text(cache["rebuild_recipe"], "rebuild_recipe")
            if not isinstance(cache["preserved_inputs"], list) or not cache["preserved_inputs"]:
                _invalid("preserved_inputs must list the exact retained source/asset/config references")
            for ref in cache["preserved_inputs"]:
                _text(ref, "preserved_inputs entry")
            path = root + "/" + relative
            if any(_overlap(path, old) for old in candidates):
                _invalid("Cache paths must not overlap")
            candidates[path] = {"path": path, "run_id": run_id, "owner": run["owner"],
                "state": run["state"], "retired_at": retired, "kind": cache["kind"],
                "rebuild_recipe": cache["rebuild_recipe"], "preserved_inputs": cache["preserved_inputs"]}
            if len(candidates) > 1000:
                _invalid("At most 1000 cache declarations are supported")
    return value, protected, candidates


def _metric():
    return dict(files=0, directories=0, logical_bytes=0, allocated_path_bytes=0,
                hardlinked_files=0, symlinks=0, special_files=0, excluded_directories=0, protected_entries=0)


def _record(metric, info):
    if stat.S_ISREG(info.st_mode):
        metric["files"] += 1
        metric["logical_bytes"] += info.st_size
        if hasattr(info, "st_blocks") and metric["allocated_path_bytes"] is not None:
            metric["allocated_path_bytes"] += info.st_blocks * 512
        else:
            metric["allocated_path_bytes"] = None
        metric["hardlinked_files"] += int(info.st_nlink > 1)
    elif stat.S_ISDIR(info.st_mode):
        metric["directories"] += 1
    elif stat.S_ISLNK(info.st_mode):
        metric["symlinks"] += 1
    else:
        metric["special_files"] += 1


def _identity(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _open_root(root):
    # Descriptor-relative no-follow traversal also rejects symlinks in ancestors.
    if (not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY")
            or os.open not in os.supports_dir_fd or os.scandir not in os.supports_fd):
        raise FactoryError("STORAGE_UNSUPPORTED", "No-follow directory descriptors are required (Linux/macOS)")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(root.anchor, flags)
    try:
        for component in root.parts[1:]:
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


class _Limit(Exception):
    pass


def audit(workspace_root, *, manifest=None, protected=(), expected_write_bytes=0,
          reserve_bytes=2 * GIB, min_retired_days=7, max_entries=500000, max_seconds=30, now=None):
    """Inventory metadata only. A review candidate is NEVER permission to delete."""
    for name, value, minimum in (("expected_write_bytes", expected_write_bytes, 0),
            ("reserve_bytes", reserve_bytes, 0), ("min_retired_days", min_retired_days, 0),
            ("max_entries", max_entries, 1), ("max_seconds", max_seconds, 1)):
        if type(value) is not int or value < minimum:
            _invalid(f"{name} must be an integer >= {minimum}")
    root = Path(os.path.abspath(Path(workspace_root).expanduser()))
    home = Path.home()
    if root == Path(root.anchor) or root == home:
        _invalid("Pass a specific workspace, not the filesystem root or home directory")
    value, protected, declared = _manifest(manifest, protected)
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        _invalid("now must have a timezone")
    totals, top, categories = _metric(), {}, {}
    measurements = {path: _metric() for path in declared}
    identities, issues, exclusions = {}, [], []
    entries = 0
    started = time.monotonic()

    def issue(path, reason):
        # Bound JSON output even when many unreadable directories are present.
        if len(issues) < 100:
            issues.append({"path": path, "reason": reason})

    def visit(directory, prefix="", depth=0):
        nonlocal entries
        before = os.fstat(directory)
        if depth > 64:
            issue(prefix, "depth_limit")
            return
        try:
            with os.scandir(directory) as stream:
                for item in stream:
                    if entries >= max_entries or time.monotonic() - started >= max_seconds:
                        issue(prefix or ".", "entry_or_time_limit")
                        raise _Limit()
                    entries += 1
                    rel = prefix + "/" + item.name if prefix else item.name
                    try:
                        info = item.stat(follow_symlinks=False)
                    except OSError:
                        issue(rel, "stat_failed")
                        continue
                    parts = rel.split("/")
                    scope_parts = _scope_parts(rel)
                    category = next((part for part in scope_parts if part in {".git", ".godot", "__pycache__", ".pytest_cache", "node_modules"}), "other")
                    metrics = [totals, top.setdefault(parts[0], _metric()), categories.setdefault(category, _metric())]
                    # Cache observations stay exact. Normalized aliases only
                    # add protection; they must never nominate another entry.
                    for length in range(1, len(parts) + 1):
                        ancestor = "/".join(parts[:length])
                        if ancestor in measurements:
                            metrics.append(measurements[ancestor])
                    for metric in metrics:
                        _record(metric, info)
                        if scope_parts[-1] in PROTECTED_NAMES:
                            metric["protected_entries"] += 1
                    if rel in declared:
                        identities[rel] = _identity(info)
                    if not stat.S_ISDIR(info.st_mode):
                        continue
                    if scope_parts[-1] in PRIVATE_NAMES:
                        for metric in metrics:
                            metric["excluded_directories"] += 1
                        if len(exclusions) < 100:
                            exclusions.append({"path": rel, "reason": "private_tool_or_credential_directory"})
                        continue
                    if info.st_dev != root_stat.st_dev:
                        issue(rel, "different_filesystem_not_scanned")
                        continue
                    try:
                        child = os.open(item.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    except OSError:
                        issue(rel, "directory_open_failed_or_changed")
                        continue
                    try:
                        if (info.st_dev, info.st_ino) != (os.fstat(child).st_dev, os.fstat(child).st_ino):
                            issue(rel, "directory_changed")
                        else:
                            visit(child, rel, depth + 1)
                    finally:
                        os.close(child)
        except OSError:
            issue(prefix or ".", "directory_scan_failed")
        if _identity(before) != _identity(os.fstat(directory)):
            issue(prefix or ".", "directory_changed_during_scan")

    fd = _open_root(root)
    try:
        root_stat = os.fstat(fd)
        # Stat only home metadata, never enumerate it. Compare with the opened
        # root so case aliases and pathname replacement cannot bypass the guard.
        # An unavailable home identity fails closed, and the descriptor closes.
        home_stat = home.stat()
        if (root_stat.st_dev, root_stat.st_ino) == (home_stat.st_dev, home_stat.st_ino):
            _invalid("Pass a specific workspace, not the filesystem root or home directory")
        try:
            visit(fd)
        except _Limit:
            pass
        # Use the open root descriptor, even if its pathname changes during the scan.
        filesystem = os.fstatvfs(fd)
        fragment = filesystem.f_frsize or filesystem.f_bsize
        disk = {"total": filesystem.f_blocks * fragment, "free": filesystem.f_bavail * fragment}
    finally:
        os.close(fd)
    review, held = [], []
    for path, declaration in sorted(declared.items()):
        metric = measurements[path]
        reasons = []
        if declaration["state"] != "retired":
            reasons.append("run_not_retired")
        retired = declaration["retired_at"]
        if retired is None or (now - retired).total_seconds() < min_retired_days * 86400:
            reasons.append("retirement_grace_not_met")
        if any(p in PROTECTED_NAMES for p in _scope_parts(path)) or any(_overlap(path, p) for p in protected):
            reasons.append("protected_path_overlap")
        if metric["protected_entries"]:
            reasons.append("protected_descendant")
        identity = identities.get(path)
        if not identity or not stat.S_ISDIR(identity[2]):
            reasons.append("cache_directory_not_observed")
        if issues:
            reasons.append("inventory_incomplete_or_changed")
        if metric["symlinks"] or metric["hardlinked_files"] or metric["special_files"]:
            reasons.append("links_or_special_files_require_manual_investigation")
        if metric["excluded_directories"]:
            reasons.append("uninspected_private_directory")
        entry = {k: v for k, v in declaration.items() if k != "retired_at"}
        entry.update(retired_at=retired.isoformat() if retired else None, observed=metric,
            root_identity=identity, reasons=reasons, reconstruction_verification="operator_required")
        (held if reasons else review).append(entry)
    required = expected_write_bytes + reserve_bytes
    blockers = []
    if issues:
        blockers.append("Inventory is incomplete or changed; do not derive cleanup decisions from it")
    if disk["free"] < required:
        blockers.append("Free space is below expected writes plus reserve; pause new bulky work")
    return {"schema_version": "factory_storage_audit.v1", "status": "STORAGE_AUDIT",
        "advisory_only": True, "generated_at": now.isoformat(), "workspace_root": str(root),
        "complete_within_declared_scope": not issues, "entries_scanned": entries,
        "manifest_sha256": hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest(),
        "protected_paths": protected, "totals": totals,
        "top_level": [{"path": path, **metric} for path, metric in sorted(top.items(), key=lambda pair: (-pair[1]["logical_bytes"], pair[0]))[:50]],
        "top_level_omitted": max(0, len(top) - 50),
        "categories": categories, "issues": issues, "excluded_private_directories": exclusions,
        "capacity": {"total_bytes": disk["total"], "free_bytes": disk["free"],
            "expected_write_bytes": expected_write_bytes, "reserve_bytes": reserve_bytes,
            "required_free_bytes": required, "sufficient": disk["free"] >= required},
        "review_candidates": review, "held_candidates": held, "blockers": blockers,
        "limits": {"max_entries": max_entries, "max_seconds": max_seconds, "min_retired_days": min_retired_days},
        "notes": ["No file contents were inspected except an explicitly supplied manifest; no files were changed or deleted",
            "Allocated path bytes omit directory blocks and may double-count hardlinks; they are not guaranteed reclaimable space",
            "Private tool/credential directories, symlink targets and other filesystems are not scanned",
            "Run state, retirement, preserved inputs and recipes are operator declarations, not verified liveness or reconstruction proof",
            "Review candidates require exact-scope authorization, worker coordination, preservation proof and a fresh no-follow recheck before any separate cleanup"]}
