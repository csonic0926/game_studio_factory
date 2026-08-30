"""Crash-recoverable immutable evidence transactions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from studio.alignment import current_factory_revision

from .common import (
    ADAPTER_ROOT,
    AUTOMATION_VERSION,
    EVIDENCE_ROOT,
    OPERATION_STATUSES,
    EngineInfo,
    GodotAutomationError,
    OperationResult,
    atomic_write_json,
    directory_digest,
    ensure_operation_id,
    load_json,
    redact,
    repo_relative,
    repository_binding,
    resolve_game_repo,
    sha256_file,
    utc_now,
)


EVIDENCE_FILE = "GODOT_AUTOMATION_EVIDENCE.json"
PENDING_FILE = "OPERATION_PENDING.json"


def artifact_record(game_repo: Path, path: Path, role: str) -> dict[str, Any]:
    if not path.exists():
        raise GodotAutomationError(f"cannot record missing artifact: {path}")
    if path.is_dir():
        digest, size = directory_digest(path)
        kind = "DIRECTORY"
    elif path.is_file():
        digest, size, kind = sha256_file(path), path.stat().st_size, "FILE"
    else:
        raise GodotAutomationError(f"unsupported artifact kind: {path}")
    return {
        "role": role,
        "kind": kind,
        "path": repo_relative(game_repo, path),
        "sha256": digest,
        "size_bytes": size,
    }


class EvidenceTransaction:
    """One append-only operation directory with one terminal evidence record."""

    def __init__(
        self,
        game_repo: str | Path,
        *,
        operation_id: str,
        operation_type: str,
        project_dir: Path,
        engine: EngineInfo | None,
        automation_manifest: dict[str, Any],
        source_mutation_allowed: bool = False,
        secrets: tuple[str, ...] = (),
    ) -> None:
        self.game_repo = resolve_game_repo(game_repo)
        self.operation_id = ensure_operation_id(operation_id)
        self.operation_type = operation_type
        self.project_dir = project_dir.resolve()
        self.engine = engine
        self.source_mutation_allowed = source_mutation_allowed
        self.secrets = secrets
        self.operation_dir = self.game_repo / EVIDENCE_ROOT / self.operation_id
        try:
            self.operation_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as error:
            raise GodotAutomationError(
                f"operation id is immutable and cannot be reused: {self.operation_id}"
            ) from error
        self.started_at = utc_now()
        self.before = repository_binding(self.game_repo)
        self._registered: list[tuple[Path, str]] = []
        self.automation_manifest = redact(automation_manifest, secrets=secrets)
        pending = {
            "schema_version": "godot_operation_pending.v1",
            "adapter_version": AUTOMATION_VERSION,
            "operation_id": self.operation_id,
            "operation_type": operation_type,
            "factory_revision": current_factory_revision(),
            "started_at": self.started_at,
            "project_dir": repo_relative(self.game_repo, self.project_dir),
            "source_repository_before": self.before,
            "source_mutation_allowed": source_mutation_allowed,
            "automation_manifest": self.automation_manifest,
            "acceptance_authority": "EVIDENCE_ONLY",
            "gameplay_verdict": "NOT_ISSUED",
        }
        atomic_write_json(self.operation_dir / PENDING_FILE, pending)

    def path(self, name: str) -> Path:
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise GodotAutomationError("raw artifact name must be one file name")
        if name in {PENDING_FILE, EVIDENCE_FILE}:
            raise GodotAutomationError(f"reserved evidence file name: {name}")
        return self.operation_dir / name

    def write_text(self, name: str, text: str, role: str) -> Path:
        path = self.path(name)
        path.write_text(self.scrub_text(text), encoding="utf-8")
        self.register(path, role)
        return path

    def scrub_text(self, text: str) -> str:
        rendered = str(redact(text, secrets=self.secrets))
        rendered = rendered.replace(str(self.game_repo), "<GAME_REPO>")
        rendered = rendered.replace(str(self.game_repo.resolve()), "<GAME_REPO>")
        # macOS exposes /var as a /private/var symlink.  Redact both spellings
        # so process output cannot leak whichever alias a child process chose.
        resolved_text = str(self.game_repo.resolve())
        if resolved_text.startswith("/private/"):
            rendered = rendered.replace(resolved_text[len("/private"):], "<GAME_REPO>")
        rendered = rendered.replace(str(Path.home()), "<HOME>")
        return rendered

    def scrub_text_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return
        try:
            if path.suffix == ".json":
                text = json.dumps(
                    redact(json.loads(text), secrets=self.secrets),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ) + "\n"
            elif path.suffix == ".jsonl":
                records = [
                    redact(json.loads(line), secrets=self.secrets)
                    for line in text.splitlines()
                    if line.strip()
                ]
                text = "".join(
                    json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                    for record in records
                )
        except json.JSONDecodeError:
            # Preserve malformed crash evidence as text while still scrubbing
            # explicit session secrets and repository/home paths.
            pass
        path.write_text(self.scrub_text(text), encoding="utf-8")

    def write_json(self, name: str, payload: Any, role: str) -> Path:
        path = self.path(name)
        atomic_write_json(path, redact(payload, secrets=self.secrets))
        self.register(path, role)
        return path

    def register(self, path: Path, role: str) -> None:
        resolved = path.resolve()
        repo_relative(self.game_repo, resolved)
        pair = (resolved, role)
        if pair not in self._registered:
            self._registered.append(pair)

    def finalize(
        self,
        *,
        status: str,
        invocation: dict[str, Any],
        result: dict[str, Any],
        assertions: list[dict[str, Any]] | None = None,
        replay: dict[str, Any] | None = None,
        project_gameplay_evidence_refs: list[dict[str, str]] | None = None,
        limitations: list[str] | None = None,
    ) -> OperationResult:
        if status not in OPERATION_STATUSES:
            raise GodotAutomationError(f"unknown operation status: {status}")
        evidence_path = self.operation_dir / EVIDENCE_FILE
        if evidence_path.exists():
            raise GodotAutomationError("operation already has terminal evidence")
        after = repository_binding(self.game_repo)
        source_mutated = self.before != after
        if source_mutated and not self.source_mutation_allowed and status == "PASS":
            status = "FAIL"
            result = {**result, "source_mutation_violation": True}
        artifacts = [artifact_record(self.game_repo, path, role) for path, role in self._registered if path.exists()]
        payload = {
            "schema_version": "godot_automation_evidence.v1",
            "adapter_version": AUTOMATION_VERSION,
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "status": status,
            "factory_revision": current_factory_revision(),
            "started_at": self.started_at,
            "finished_at": utc_now(),
            "project": {
                "project_dir": repo_relative(self.game_repo, self.project_dir),
                "source_repository_before": self.before,
                "source_repository_after": after,
                "source_mutated": source_mutated,
                "source_mutation_allowed": self.source_mutation_allowed,
            },
            "engine": self.engine.public() if self.engine else None,
            "automation_manifest": self.automation_manifest,
            "invocation": redact(invocation, secrets=self.secrets),
            "result": redact(result, secrets=self.secrets),
            "assertions": assertions or [],
            "replay": replay,
            "artifacts": artifacts,
            "project_gameplay_evidence_refs": project_gameplay_evidence_refs or [],
            "acceptance_authority": "EVIDENCE_ONLY",
            "gameplay_verdict": "NOT_ISSUED",
            "limitations": limitations or [
                "This bundle records technical evidence only.",
                "It cannot replace gameplay acceptance, a human playtest, or baseline promotion.",
            ],
        }
        atomic_write_json(evidence_path, payload)
        return OperationResult(status, repo_relative(self.game_repo, evidence_path), sha256_file(evidence_path))


def _verify_artifacts(game_repo: Path, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for item in payload.get("artifacts", []):
        try:
            path = game_repo / item["path"]
            if item.get("kind") == "DIRECTORY":
                actual, size = directory_digest(path)
            else:
                actual, size = sha256_file(path), path.stat().st_size
            if actual != item["sha256"] or size != item["size_bytes"]:
                failures.append(item["path"])
        except (KeyError, OSError, ValueError):
            failures.append(str(item.get("path", "<invalid>")))
    return failures


def verify_evidence(game_repo_text: str | Path, evidence_text: str | Path) -> OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    evidence_path = (game_repo / evidence_text).resolve() if not Path(evidence_text).is_absolute() else Path(evidence_text).resolve()
    repo_relative(game_repo, evidence_path)
    payload = load_json(evidence_path)
    if not isinstance(payload, dict) or payload.get("schema_version") not in {
        "godot_engine_evidence.v1", "godot_automation_evidence.v1"
    }:
        raise GodotAutomationError("unsupported Godot evidence schema")
    failures = _verify_artifacts(game_repo, payload)
    status = "PASS" if not failures else "FAIL"
    report = {"status": status, "evidence": repo_relative(game_repo, evidence_path), "invalid_artifacts": failures}
    verification_root = game_repo / ADAPTER_ROOT / "verifications"
    verification_root.mkdir(parents=True, exist_ok=True)
    report_path = verification_root / f"{sha256_file(evidence_path)}.json"
    if report_path.exists():
        existing = load_json(report_path)
        if existing != report:
            raise GodotAutomationError("immutable verification id collision")
        return OperationResult(status, repo_relative(game_repo, report_path), sha256_file(report_path))
    atomic_write_json(report_path, report)
    return OperationResult(status, repo_relative(game_repo, report_path), sha256_file(report_path))


def recover_evidence(game_repo_text: str | Path, operation_id: str) -> OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    operation_dir = game_repo / EVIDENCE_ROOT / ensure_operation_id(operation_id)
    pending_path = operation_dir / PENDING_FILE
    evidence_path = operation_dir / EVIDENCE_FILE
    if evidence_path.exists():
        raise GodotAutomationError("completed evidence cannot be recovered or rewritten")
    pending = load_json(pending_path)
    project_dir = game_repo / pending["project_dir"]
    registered: list[dict[str, Any]] = []
    for path in sorted(operation_dir.iterdir()):
        if path.name in {PENDING_FILE, EVIDENCE_FILE}:
            continue
        registered.append(artifact_record(game_repo, path, "RECOVERED_RAW_ARTIFACT"))
    after = repository_binding(game_repo)
    payload = {
        "schema_version": "godot_automation_evidence.v1",
        "adapter_version": AUTOMATION_VERSION,
        "operation_id": pending["operation_id"],
        "operation_type": pending["operation_type"],
        "status": "ABORTED",
        "factory_revision": pending["factory_revision"],
        "started_at": pending["started_at"],
        "finished_at": utc_now(),
        "project": {
            "project_dir": repo_relative(game_repo, project_dir),
            "source_repository_before": pending["source_repository_before"],
            "source_repository_after": after,
            "source_mutated": pending["source_repository_before"] != after,
            "source_mutation_allowed": pending["source_mutation_allowed"],
        },
        "engine": None,
        "automation_manifest": pending["automation_manifest"],
        "invocation": {},
        "result": {"recovered_after_hard_interruption": True},
        "assertions": [],
        "replay": None,
        "artifacts": registered,
        "project_gameplay_evidence_refs": [],
        "acceptance_authority": "EVIDENCE_ONLY",
        "gameplay_verdict": "NOT_ISSUED",
        "limitations": ["Recovered evidence is ABORTED and cannot establish a passing operation."],
    }
    atomic_write_json(evidence_path, payload)
    return OperationResult("ABORTED", repo_relative(game_repo, evidence_path), sha256_file(evidence_path))
