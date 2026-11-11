# Workspace storage and safe cleanup

This is operational hygiene for all Factory versions and all execution hosts.
It does not migrate a project, renew historical proof, grant deletion authority,
or change gameplay acceptance. The workspace owner coordinates storage across
workers. A cleanup-policy PR is not permission to clean a live workspace.

## What the inventory showed

A read-only, metadata-only inspection of a development workspace on 2026-11-09
found approximately 59.1 GiB of regular-file allocation, including 7.9 GiB under
Godot import-cache directories. PNG paths accounted for approximately 28.8 GiB,
but included both source assets and irreplaceable runtime evidence. The system
temporary directory was below 1 MiB. Only about 516 MiB remained free at that
snapshot. These are historical measurements, not a current cleanup plan or a
claim that any of those bytes were safe to delete.

Repeated runner copies, import caches, captures, transfer archives and preserved
checkpoints grew together. A current mutable runner lived under an older run's
folder name. Therefore neither an old date nor a name such as `temp`, `final`,
`private`, `failed`, `output` or `backup` determines ownership or disposability.
This document deliberately omits machine paths and project artifacts.

## Classify by purpose, not extension or Git ignore rules

| Class | Examples | Default treatment |
| --- | --- | --- |
| Authority and authored work | Source, design, reviews, USER rulings, dependency manifests, uncommitted changes, pinned Factory checkout | Preserve. Git history protects only the committed bytes actually available in the verified repository. |
| Evidence and recovery | Original screenshots/audio/video, failed-test logs, exact fixtures, saves, reference bindings, accepted and rollback checkpoints | Preserve while referenced, under review, required for reproduction, or subject to a retention hold. Failure is evidence, not garbage. |
| Rebuildable cache | An explicitly verified retired runner's `.godot`, Python bytecode or pytest cache | Eligible for a **review queue** only after retirement, preservation checks, grace period and owner coordination. A directory name alone is insufficient. |
| Transfer or build intermediates | Download fragments, extracted copies, temporary archives, build exports | Separately review exact paths after verifying the retained original/destination, hashes and restore procedure. Not automatically selected by this tool. |
| Unknown or active data | Unregistered runs, paused work, live runner, arbitrary `output/` and scratch folders | Preserve until the owning task explains them. Ignored/untracked does not mean disposable. |

Do not sweep a whole home, `/tmp`, scratch root, game repo, or cache tree by age,
glob, extension, `git clean -fdx`, global cache purge or recursive deletion of a
parent run. Never remove credential/tool state, Git objects, live engine locks,
source `.import`/`.uid` files, saves, or a pinned tool installation as cleanup.
A stale-looking lock needs its own owner/liveness investigation, not deletion.

## Plan allocation before producing it

Before a new runner, engine import, full test matrix, archive or capture batch:

1. Inspect the relevant filesystem and current worker plans. Keep an explicit
   list of active runners, source/checkpoint roots, saves, evidence and pinned
   Factory tools. A reused runner stays active regardless of its directory name.
2. Estimate **peak additional allocation**, not the final artifact size. Include
   source materialization, imported assets, simultaneous workers, evidence,
   archive staging, compression output and upload staging. Compression can need
   both the original and archive at once. Check output filesystems separately.
3. Require `free >= expected_peak_new_bytes + reserve_bytes`. The audit defaults
   to a 2 GiB reserve; an existing project-specific budget may be supplied
   explicitly. Record why a smaller reserve is sufficient. Do not lower it just
   to obtain a passing check. Recheck before each expensive phase, since other
   workers can spend the same space.
4. If the check fails, pause **new bulky writes**, keep read-only diagnosis
   available, and report the exact capacity shortfall. Do not skip required
   tests, overwrite previous evidence, fabricate PASS, or perform emergency
   deletion without the required authorization.

Use one deliberately allocated mutable runner per active execution lane when
possible. Prefer source-controlled changes or a small exact overlay over full
copies for every tiny revision. Do not hardlink mutable sources or caches between
independent runners. If a copy-on-write copy is used, budget later writes too.
Use immutable content-addressed source/assets only when the workflow supports
that identity; runtime evidence is still tied to the exact tested build.
Coordinate engine, GUI and storage use through the project's existing leases.
The storage auditor does not acquire, release, replace or delete those leases.

## Give each run an owner and an end

Keep a small **machine-local** manifest beside the workspace, outside evidence
and published source. Do not publish private paths, raw conversations or secrets.
The manifest is a local declaration, not project authority or acceptance proof.

- `active`: producing or consuming data, including an old runner reused today.
- `paused`: may resume. Keep its caches and all recovery material.
- `closed`: work ended, but preservation/review is not yet complete.
- `retired`: the owner has checked the consumer/dependency list, preserved unique
  work and evidence, and recorded a retirement timestamp and reconstruction
  recipe. Retirement is not approval to delete.

Only the owner/coordinator updates these declarations. An absent worker, expired
heartbeat, directory age, newer revision or passing test does not retire a run.
No worker should retire another worker's paths by inference. Keep registered run
roots disjoint; if part of an older run becomes active again, pin that subtree
with `protected_paths` or `--protect` immediately. Unregistering a run does not
make it disposable. Missing entries remain unknown and preserved.

The default grace period is **seven days after explicit retirement**, not seven
days after file modification. It is a review trigger, not an automatic expiry.
For a genuine storage emergency, the owner may review exact retired cache paths
sooner using an explicitly documented exception and the same preservation and
authorization checks. Do not falsify retirement dates or remove protection to
make the tool nominate a path.

## Read-only inventory and review queue

No migration, install, engine, GUI, service, network access or third-party Python
package is required. The scanner uses no-follow directory descriptors on Linux
and macOS. It refuses unsupported platforms rather than falling back to unsafe
traversal. Other Factory commands are unchanged.

```bash
python3 -B factory.py storage --workspace-root /physical/path/to/workspace \
  --expected-write-bytes 1073741824 --reserve-bytes 2147483648
```

This reads directory/file **metadata**, not contents. Only an explicitly supplied
regular-file manifest is read as JSON (maximum 1 MiB); links, pipes, devices
and changing manifests are rejected. No command, cache recipe or file deletion
is executed. There is no `--apply`, `--delete`, background job or automatic purge.
Use a physical workspace path, not a symlink, filesystem root or home directory.
The opened workspace is checked against the home directory's device/inode
identity before enumeration, so alternate spellings cannot bypass that guard.
An unavailable home identity blocks the scan rather than weakening the guard.
Save the JSON only if useful, to a small task-owned location outside the scanned
root so the report itself does not race the scan. Do not copy the workspace to
make an inventory.

Defaults are 500,000 entries, 30 seconds and depth 64; `--max-entries` and
`--max-seconds` explicitly change the first two. The output lists the 50 largest
top-level entries by logical size and reports how many were omitted. It skips
symlink targets, other filesystems and private tool/credential directories.
An unreadable/changing directory, cross-device mount or exhausted scan budget blocks every
cache nomination. Same-device bind mounts cannot be identified by the device-ID
check and require an operator mount-table review before any separate cleanup.
Expected private exclusions are reported; a cache containing
one is held even if the detailed exclusion list has been truncated.

The audit is not an atomic snapshot. File contents can change without a directory
mtime change. `complete_within_declared_scope` means enumeration finished under
the stated limits, **not** that the files are frozen or deletable. Allocation
figures omit directory metadata and can double-count hardlinked paths; shared
extents, open deleted files and filesystem snapshots also affect actual space
recovered. They are observations, not guaranteed reclaimable bytes.

Without a manifest, the command inventories only and nominates **nothing**. An
example declaration for a synthetic run is below; replace all placeholder
references with the owner's exact retained source/assets/config identities.
Do not copy `retired` onto an existing run without investigating it.

```json
{
  "schema_version": "factory_storage_manifest.v1",
  "protected_paths": ["current-runner", "evidence", "pinned-factory"],
  "runs": [
    {
      "id": "example-retired-run",
      "path": "runs/example-retired-run",
      "owner": "owning-task",
      "state": "retired",
      "retired_at": "2026-10-01T00:00:00Z",
      "caches": [
        {
          "path": "runner/.godot",
          "kind": "godot_import",
          "rebuild_recipe": "Exact engine version and import command, recorded but not executed here",
          "preserved_inputs": ["Exact retained source revision, uncommitted delta, assets, config and plugin references"]
        }
      ]
    }
  ]
}
```

```bash
python3 -B factory.py storage --workspace-root /physical/path/to/workspace \
  --manifest /path/to/local-storage-manifest.json \
  --protect runs/old-name/current-runner --expected-write-bytes 1073741824
```

Supported cache kinds are `godot_import` (`.godot`), `python_bytecode`
(`__pycache__`) and `pytest` (`.pytest_cache`). Paths are relative, exact and
confined, never globs. Cache and run roots must not overlap. Duplicate IDs/keys,
unknown fields/versions, malformed dates and ambiguous paths fail closed.
Protected ancestors **and descendants** hold the whole nominated cache.
Protection and run/cache overlap checks conservatively compare case-folded,
Unicode-normalized path components on every platform, including case-sensitive
volumes. This can hold distinct similarly named paths; it never grants cleanup
authority. Original paths and no-follow traversal remain unchanged. Cache
declarations must match the exact observed entry spelling to be nominated.
Conventional evidence, design, saves, checkpoints, archives, Git and private-state
components, including protected entries found inside a cache, are protected as
an additional guard, with the same alias comparisons. Private directory aliases
such as `.SSH` are excluded without enumeration. Custom evidence locations must
be declared explicitly; the tool cannot discover all semantic dependencies.

`review_candidates` means only that the declarations and conservative metadata
checks allow an **operator review**. `held_candidates` explains why paths were
excluded. Recipes, source preservation, retirement and process inactivity are
not independently verified. A successful exit code does not authorize cleanup.
Exit 2 indicates an invalid input, incomplete/changing scan or capacity blocker;
normal held candidates do not make an otherwise complete audit fail.

## Execute a separate, authorized cleanup safely

The first release deliberately stops at a review queue. A future deletion
implementation needs a separately reviewed transaction/lease design and tests.
Until then, a responsible operator follows this checklist for the exact paths:

1. **Coordinate and bind scope.** Identify the owning task and current workers;
   obtain their acknowledgement that the candidate is retired and not in use.
   Hold the relevant execution/storage lease throughout the operation. Verify
   the current runner and pinned Factory path explicitly. Do not kill an engine
   or steal another worker's lock to make cleanup possible.
2. **Prove preservation.** Review all files in the candidate, not just its name.
   Confirm it is generated and reconstructible; no tracked/uncommitted source,
   manually modified imports, saves, unique logs or evidence may be hidden there.
   Verify retained original inputs, exact source/delta, assets, engine/plugins,
   configuration and rebuild recipe. Preserve failed attempts and their bindings.
   If anything is uncertain, hold the path.
3. **Authorize the exact action.** Present the exact paths, purpose, estimated
   space, reconstruction cost and preservation scope. Follow the user's current
   confirmation rules. A policy, manifest, TTL, disk-pressure warning, PR approval
   or `review_candidates` entry does not supply deletion permission.
4. **Revalidate immediately.** Recheck root/candidate identity, containment,
   symlinks, mounts, hardlinks, worker use and the reviewed file inventory after
   approval and while the lease is held. Compare hashes/metadata of retained
   non-cache files where required. Stop on any change or uncertain partial result.
   Do not turn the earlier report into a wildcard or delete the parent directory.
5. **Remove only the approved scope.** Use the platform's supported recovery
   route when available. Permanent removal needs its applicable confirmation.
   Do not purge unrelated caches, archives or trash. Rebuilding a cache later is
   a new allocation and may require fresh engine work and verification; it does
   not automatically preserve old runtime-proof validity.
6. **Verify and record once.** Record exact paths, timestamp, owner, authorization
   reference, outcome and measured free-space delta in one small local receipt.
   Check protected sources, saves and evidence remain intact. Mark only the
   successfully handled cache entries, preserve partial failures, then release
   the lease. Report actual recovered space rather than the estimate.

Moving evidence to an archive is a separate task, not cache cleanup. Verify the
retained bytes, manifest and restore procedure at the authorized destination
before considering local removal. An uploaded file ID alone is not proof that a
consumer can restore it. Path/hash references in current or historical Factory
contracts must remain resolvable; do not silently rewrite bindings, discard the
only original, or compress evidence in place. No upload, external sharing or
remote archive is authorized by this policy.

## Close the loop without adding a second pile of artifacts

At task closure, keep one source/delta reference, one evidence index and the
small retention/cleanup receipt. Reference existing artifacts instead of copying
the same source tree, screenshots or transcript into every status packet. Record
which run remains active and when retired caches can next be reviewed. Revisit
retired runs at task closure or before a space-heavy phase; no timer or scheduled
purge is installed by this change. Longer-term retention of evidence requires an
explicit project decision, not a universal age-based rule.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest factory_core.tests.test_storage -v
```

The tests use tiny synthetic fixtures and no engine/GUI. They cover active old
runners, protection in both directions, age not granting permission, malformed
manifests, traversal and links, missing reconstruction declarations, private
exclusions, limits/read failures, capacity budgeting and the absence of deletion
or recipe execution. Alias regressions cover protected scopes, overlapping runs
and caches, conventional/private names, and opened-root home identity. Native
case-insensitive fixtures also verify actual filesystem aliases; macOS CI requires
these fixtures to run rather than skip. Run the existing non-engine Factory core regressions before
publication; engine-only cases require their own execution lease. Project engine/gameplay regressions are separate from these storage
checks and must not be represented as tested by this suite.
