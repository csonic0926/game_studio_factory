"""Root-confined references and content fingerprints (Git is provenance only)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any


class FactoryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str):
    raise FactoryError(code, message)


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def sha(path: Path) -> str:
    if not path.is_file():
        fail("MISSING_REFERENCE", str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confined(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        fail("UNSAFE_PATH", repr(relative))
    rel = PurePosixPath(relative)
    if rel.is_absolute() or any(p in ("", ".", "..", ".git") for p in relative.split("/")):
        fail("UNSAFE_PATH", relative)
    root = root.resolve()
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            fail("UNSAFE_PATH", f"symlink component: {relative}")
    if not current.resolve().is_relative_to(root):
        fail("UNSAFE_PATH", relative)
    return current


def game_root(value: str | Path, factory: Path) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir() or root.is_relative_to(factory.resolve()):
        fail("INVALID_PROJECT", "target must be an existing game root outside Factory")
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                            text=True, capture_output=True, timeout=10)
    if result.returncode or Path(result.stdout.strip()).resolve() != root:
        fail("INVALID_PROJECT", "pass the exact game Git root")
    return root


def revision(root: Path) -> str:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            text=True, capture_output=True, timeout=10)
    return result.stdout.strip() if result.returncode == 0 else "UNCOMMITTED"


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail("INVALID_JSON", f"{path}: {exc}")
    if not isinstance(value, dict):
        fail("INVALID_JSON", f"{path}: expected object")
    return value


def reference(root: Path, path: str, scope: str = "game") -> dict:
    return {"scope": scope, "path": path, "sha256": sha(confined(root, path))}


def resolve_ref(roots: dict[str, Path], ref: dict) -> Path:
    if isinstance(ref, dict) and ref.get("scope") == "game_git":
        if set(ref) != {"scope", "path", "sha256", "revision"}:
            fail("INVALID_REFERENCE", "Git reference requires scope, path, sha256, revision")
        path = GitFile(roots["game"], ref["path"], ref["revision"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != ref["sha256"]:
            fail("STALE_DEPENDENCY", "wrong historical Git object digest")
        return path
    if not isinstance(ref, dict) or set(ref) != {"scope", "path", "sha256"}:
        fail("INVALID_REFERENCE", "reference requires exactly scope, path, sha256")
    if ref["scope"] not in roots:
        fail("INVALID_REFERENCE", f"unknown scope: {ref['scope']}")
    path = confined(roots[ref["scope"]], ref["path"])
    if sha(path) != ref["sha256"]:
        fail("STALE_DEPENDENCY", f"changed reference: {ref['scope']}:{ref['path']}")
    return path


def unique_refs(refs: list[dict]) -> list[dict]:
    seen = {}
    for ref in refs:
        key = (ref["scope"], ref["path"], ref.get("revision", ""))
        if key in seen and seen[key] != ref:
            fail("CONFLICTING_REFERENCE", ":".join(key))
        seen[key] = ref
    return [seen[key] for key in sorted(seen)]


def exclusive_json(path: Path, payload: dict):
    """Publish one new immutable object; never truncate an existing artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = encoded(payload)
    # Publish via link so readers never see half-written JSON. This is staging a
    # new output, not making a backup. Remove it on success or any exception.
    import tempfile
    fd, temporary = tempfile.mkstemp(prefix=".factory-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            fail("CONCURRENT_WRITE", f"already exists: {path}")
    finally:
        os.unlink(temporary)


def expand_references(roots: dict[str, Path], refs: list[dict]) -> list[dict]:
    """Transitive JSON file refs in current sources, never archived ledger entries.

    Legacy {path,sha256,...} refs are expanded as game-owned. Non-file schema
    $refs are not filesystem dependencies. Empty optional references are absent;
    partial references and missing/stale nonempty sources fail closed.
    """
    queue = list(refs)
    found = {}
    while queue:
        ref = queue.pop()
        key = (ref["scope"], ref["path"], ref.get("revision", ""))
        if key in found:
            if found[key] != ref:
                fail("CONFLICTING_REFERENCE", ":".join(key))
            continue
        path = resolve_ref(roots, ref)
        found[key] = ref
        if ref["scope"] != "game" or path.suffix != ".json" or ref["path"] == "design/factory/PROJECT.json":
            continue
        value = read_json(path)
        if value.get("schema_version") == "product_authority_register.v1":
            value = value.get("active_authority") if value.get("status") == "ACTIVE" else {}
        elif "register" in str(value.get("schema_version", "")):
            # Pending/rejected history is not imported as active design. Explicit
            # selected dependencies must be in the current task package itself.
            continue
        def walk(node):
            if isinstance(node, dict):
                if "scope" in node and "path" in node and "sha256" not in node:
                    fail("INVALID_REFERENCE", "typed transitive reference is missing sha256")
                if "path" in node and "sha256" in node:
                    if not node["path"] and not node["sha256"]:
                        return
                    child = {"scope": node.get("scope", "game"), "path": node["path"], "sha256": node["sha256"]}
                    if child["scope"] == "game_git":
                        child["revision"] = node.get("revision")
                    if child["scope"] == "game" and child["path"] == "AGENTS.md":
                        from .migration import routing_reference_valid
                        if routing_reference_valid(roots["game"], child["path"], child["sha256"]):
                            child = reference(roots["game"], child["path"])
                    queue.append(child)
                else:
                    for child in node.values(): walk(child)
            elif isinstance(node, list):
                for child in node: walk(child)
        walk(value)
    return [found[key] for key in sorted(found)]


class GitFile:
    """Read an immutable planning input directly from normal Git history.

    No working-tree snapshot, duplicate file, alternate branch or worktree.
    """
    def __init__(self, root: Path, path: str, revision: str):
        import re
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40,64}", revision):
            fail("INVALID_REFERENCE", "historical input requires a full Git object revision")
        confined(root, path)
        self.root, self.path, self.revision = root, path, revision
        self.suffix = Path(path).suffix

    def read_bytes(self):
        result = subprocess.run(["git", "-C", str(self.root), "show", f"{self.revision}:{self.path}"],
                                capture_output=True, timeout=10)
        if result.returncode:
            fail("MISSING_REFERENCE", f"Git input {self.revision}:{self.path} unavailable")
        return result.stdout

    def read_text(self, encoding="utf-8"):
        return self.read_bytes().decode(encoding)

    def __str__(self):
        return f"git:{self.revision}:{self.path}"


def reference_at_revision(game: Path, path: str, revision: str) -> dict:
    blob = GitFile(game, path, revision)
    return {"scope": "game_git", "path": path, "revision": revision,
            "sha256": hashlib.sha256(blob.read_bytes()).hexdigest()}
