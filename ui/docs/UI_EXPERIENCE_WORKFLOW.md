# UI experience loop — explicit v3, experience protocol v1

The purpose is fewer player misreads, missed goals and undiscoverable actions at
handoff, including CLOSED_BETA with almost no human feedback. More fields, PASSes
or review rounds are not success. UI does not own gameplay rules, balance, product
commission or art direction. A plain UI that works is acceptable.

## Design: a thin relation layer

New v3 UI boundaries bind `ui.experience` to a game-owned sealed
`ui_experience_contract.v1`. Keep the four existing artifacts; reuse their fact,
step, surface and chain IDs. The complete definitions are in
`../schemas/ui_experience.schema.json` (`$defs.contract`). Each scenario names an
actual decision state, locale and viewport. Each of PAIRING, ZONE, COLOR, PRIMARY,
REDUNDANCY, DENSITY and GOAL has checks or a substantive reviewed not-applicable
reason. Probes name a criterion and falsifier, not an optimal move the observer
must select. Every MUST_KNOW fact needs an internal unprompted probe; beta cannot
assign essential comprehension solely to a future USER playtest.

Checks say what observations can falsify a presentation:

- PAIRING: same-row value/attribute association, or an explicit common group.
- ZONE: the actual global bounds of a control lie in the intended region. The
  reviewers establish ownership semantics; the node parent is not the proof.
- COLOR: an effective draw colour collides with a reserved rule role. A role
  label is not semantic truth. Decorative art is not categorically banned.
- PRIMARY: visible, enabled, within the reviewed flow/viewport anchor tolerance.
  Highest contrast is neither required nor proof that the action is discoverable.
- REDUNDANCY: one canonical visible fact placement, or a concrete reason for
  contextual repetition. XP amount, XP price and level are different facts.
- DENSITY: measured concurrent overlays and crossings. A low count is not
  readability; animation is not an automatic repair.
- GOAL: current progress, next meaningful threshold and next reward are present
  and bound to the right existing facts when deciding. A prominent combo count
  alone does not establish that the player can use the goal. Gameplay-hidden
  information must remain hidden.

The genre profile (`../profiles/auto_battler.v1.json`) is a non-authoritative
expectation inventory. UI AND Gameplay/Studio authors/reviewers audit every item
as PRESENT, NOT_APPLICABLE (reason), GAP or UPSTREAM_REQUIRED. Resolve a gap with
its owner before claiming design completeness. Shop lock changes Gameplay; UI
cannot implement it merely because it appears on this list. Success criteria
come from this product, not a universal Top-N convention. Other genres use NONE
with a reason until an appropriate profile is added.

## Capture first; then inspect the entire design

Before requesting full Factory reviewer context, each of the SAME two independent
reviewers obtains a `review-packet`, inspects every original image/sequence, and
seals `ui_visual_first_pass.v1` under its own context and role. The design locator
is for later binding, not permission to open it before the pass. Record what the
screen communicates, what may be missed/misread, and unknowns. This expert pass
is NOT Studio blind Phase A. It must allow discoveries absent from the contract.

Then obtain full Factory context and review every applicable source and decision,
without reading the peer's first pass. Every blocker explains a concrete player,
implementation or verification consequence. Text precision with no such effect
is NON_BLOCKING (record in the rationale and feedback); a clock/bound change
that changes verification remains blocking. There is no numeric issue quota.
The generic `factory_review.v2` format and two-review independence are unchanged.

At design time use current captures plus clearly labelled DESIGN_PREVIEWs.
Do not require unapproved production to obtain future runtime proof. A bounded
nonshipping prototype follows existing authorization, not an implicit permission
to change game rules. Readiness requires real RUNTIME captures after production.

## Runtime capture and measurements

An isolated authorized runner awaits `../godot_engine/capture.gd`'s `sample()`
after rendering; it supplies ordinary scene state, sample times and the metadata
described there. It never modifies the shipped startup scene. Exporter output is
`ui_capture_export.v1`; `capture` hashes the PNGs and seals
`ui_runtime_capture.v1`. Identify the exact committed game revision, hashed build
artifact (a `ui_capture_build.v1` consumed-source manifest with optional binary
ref), exporter and scene. `capture-build` pins the available game commit/tree,
`project.godot`, actual entrypoint and declared consumed files before launch;
sealing rejects changed live consumed sources. The manifest inventory's
completeness and the runner actually consuming it remain review/harness duties,
not something a file hash or an arbitrary note can prove.
Root-relative paths only. Keep originals and failed evidence. Frame sequences
must include transition/density peaks, not only the clearest frame.

The default Godot exporter observes Controls/Line2Ds, common effective draw colours
and global geometry. It does not reconstruct arbitrary shaders, occlusion,
custom drawing, clipping or perceptual salience. Extend the game-owned exporter
for relied-on custom rendering, and attest `overlays_complete` only after its
inventory is actually complete. Missing observations yield UNVERIFIABLE, never
PASS. Reviewers cross-check telemetry against pixels and gameplay sources.

`evaluate` recomputes every check from all supplied frames. It does not trust a
saved PASS report and does not prove comprehension. `ui_readiness.v1` is the typed
specialist input at EVIDENCE_READY/COMPLETE; it binds the recomputed captures,
exact-build `ui_mechanical_report.v2`, both visual passes and existing Studio runtime
chains. The informed comparer additionally writes `ui_outcome_review.v1`, using
its own context, exact sealed attempts, and the actual scenario surface. Required
probes must be supported; each attempted interaction is explicitly considered for
unplanned UI escapes. Phase A receives NO telemetry, expected answers or probes.
No new question is added to the blind packet.

Each v2 mechanical check references `ui_check_result.v1` with the planned method,
status, revision, build ID and exact raw evidence. A same-revision report for a
different runner/build is not interchangeable. Legacy report v1 stays readable
but does not satisfy new readiness. Each UI comprehension chain binds one
reviewed scenario locale; other locale chains cannot substitute for it.

## Director-owned discovery and disposition

In autonomous modes the orchestrator personally plays the UI and records its own
judgment in the existing Director note: first focus, choices, result, biggest risk,
strongest case against continuing, and what changes next. A reviewer PASS is not
Director play. Prioritize important, uncertain, changed and previously unobserved
states: first entry; copies 0/1/2; before/after a goal threshold; maximum board;
win/loss next action; modal/animation competition; shipped languages and viewports.
Do not repeat the whole matrix for a harmless text repair.

`ui_feedback.v1` preserves source, observation ID, problem, player cost and
severity. Add new revisions; never overwrite the original. At a new design freeze,
bind existing JSON records in `design/ui/<upstream-gameplay-objective-id>/feedback/`
as inputs. Moving a contract cannot change this inventory. Prior feedback may be
pinned in Git (matching canonical path/bytes), avoiding recursive renewal of old
designs when a live design path is replaced. Keep original feedback files intact.
Readiness carries every prior finding forward with an explicit disposition:

- REPAIRED: new retest evidence, including the failure case and an unseen variant.
- NOT_APPLICABLE: supported reason; not an in-place waiver of a hard failure.
- ACCEPT_RESIDUAL: NON_BLOCKING only, concrete cost and revisit trigger. In
  CLOSED_BETA the Director may retain it only with the delegated internal-verdict
  seat; label AI_DIRECTOR, never USER. Include it in the beta weaknesses.
- OPEN: does not complete the disposition loop.

A repair's `ui_retest.v1` binds the current design, finding, original scenario and
at least one distinct variant. Those captures must join current measurements and
independently supported outcomes, not merely resolve as an arbitrary file. Every
blind `lost_or_passive_points[index]` also receives a preserved feedback record
with source=the blind record and observation_id=`lost.<index>`.

Raw USER feedback is a rare calibration input, not the daily discovery engine.
Classify why the problem escaped (execution, bad check, missing evidence,
missing requirement, or new principle) before adding a reusable rule. Extract
the purpose of implementation hints; ask only about material ambiguity outside
delegation. Do not automatically promote a specific fix into universal law.

Hard authority/review/mechanical/comprehension/isolation failures cannot be
waived by the Director. Revise through a new reviewed design if the requirement
itself needs to change; do not downgrade it after observing failure and claim
the same proof passed. USER acceptance of a nonblocking risk uses raw role=user
content `ACCEPT_UI_RISK <finding-id> <source-sha256> <ui-design-sha256>`.

## Readiness and the decision entry

New UI transitions require the experience binding; historical design parsing
does not. Relevant code/schema/rule changes still require ordinary revalidation;
there is no broad stale-ref skip, proof renewal, migration or automatic relink.

EVIDENCE_READY consumes immutable `ui_readiness.v1` and all required evidence.
COMPLETE consumes a separate append-only `ui_acceptance.v1` referencing that
unchanged readiness plus the actual mode-appropriate verdict. Do not overwrite
an EVIDENCE_READY receipt to add a later USER verdict. CLOSED_BETA with the named
INTERNAL_PLAYTEST_VERDICT seat may yield UI_INTERNAL_READY from its checked
Director handoff note. Other cases require the raw exact-build USER action
`ACCEPT_UI <ui-design-sha256> <game-revision> <build-id>`. Neither result is an
Accepted Playable Baseline or whole-game delivery; baseline gates remain intact.

`decision-view` derives a compact visual ENTRY from reviewed exact excerpts and
consequences, risk/unknown text and matched before/after captures. The full checked
human view and exact approval action remain linked/embedded, with the same digest.
It is not an alternate specification or a rewrite. Baseline absence is explicit.
Different states/viewports/locales/time windows cannot masquerade as a comparison.
Optional contact sheets and GIFs preserve and link original pixel-size PNGs.

## Commands

```sh
python3 ui/ui_design.py capture-build --game-repo <GAME> --sources project.godot <complete-consumed-sources> --entrypoint <runner.gd> --output <new-build.json>
python3 ui/ui_design.py capture --game-repo <GAME> --raw <export.json> --output <new-capture.json>
python3 ui/ui_design.py evaluate --game-repo <GAME> --design <design.json> --captures <capture.json> ...
python3 ui/ui_design.py review-packet --game-repo <GAME> --design <design.json> --output <new-packet.json>
python3 ui/ui_design.py decision-view --game-repo <GAME> --design <design.json> --output <new-entry.html> --media-directory <new-media-directory>
# Explicit non-authoritative retrospective audit, without migration/approval:
python3 ui/ui_design.py evaluate --game-repo <GAME> --archive --contract <audit-contract.json> --captures <pinned-capture.json> ...
```

Existing check/report CLI stays compatible. Core checks require only Python's
stdlib. Contact sheets/GIFs alone use optional `../requirements-visual.txt`.
All explicit outputs fail if they exist. Capture sealing does not launch Godot,
run an arbitrary shell command or authorize production. Budget runner/import/
capture allocation under STORAGE_LIFECYCLE before expensive batches.

Archive audits are UI_RETROSPECTIVE_AUDIT with authority=false, even if all
measurements pass; they cannot be consumed as current readiness. Missing old
telemetry remains UNVERIFIABLE. Known c7b9411 cases are regression, not evidence
of predictive validity. Compare residual defects, unprompted failures, transfer,
false positives and cost on isolated unseen cases; do not count findings as wins.
Without human feedback, AI usability and lower constructed escapes do not prove
human experience. The Director must still make a fallible, evidence-based choice.
