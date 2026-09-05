# Story v2 capability

Process source: `factory_core/docs/WORKFLOW.md`. One primary author continues
world, character, cast, chapter/branch and production. The existing 68 step files
are methods/checklists, not mandatory worker boundaries. Read only those needed
for the current object/phase, while preserving every applicable requirement.
Full finished prose is the deliverable; references replace repeated handoff
restrictions, not story text or meaningful constraints. Plain language, no
invented shorthand; meaning fidelity outranks label/schema completeness.

## Resolve before writing

Use `PROJECT_PROFILE_CONTRACT.md`: explicit adapter -> registry -> game-owned
`design/story/adapter` -> legacy project adapter. Honor PROJECT_ID, WORLD_NAME,
STORY_ROOT, PRIMARY_LOCALE, all SHIPPED_LOCALES and runtime shape; never infer
canon names from directory names. Read project STYLE_GUIDE for all artifacts.
WORLD_RULES / NARRATIVE_DELIVERY (or unsplit WORKFLOW_CORE_VARIABLES) remain USER
sovereignty, not author output. Only rules-editor with explicit exact USER
approval may change them. GLOSSARY.csv is the sole proprietary-term authority;
no reverse-engineered second list. New forms are pending nominations, not canon.

## Capability and phase index

| Task | Methods | Required preservation |
|---|---|---|
| world | core/steps/world | ontology, geography, institutions, movement, consistency, twin package |
| character | core/steps/character; CHARACTER_SCHEMA | cast requests, world position, behavior/voice, knowledge/relations, full package |
| cast | core/steps/cast | stage scope, overlap/missing seats, relationship pressure, explicit action requests |
| chapter | core/steps/chapter | preflight, commissioned beat intent, spine/source/graph, full draft, staging, landing, latest-output QA, outcomes |
| branch | chapter + BRANCH_IMPLEMENTATION_OVERLAY | legitimate branch memory/knowledge, routing, consequences; no unauthorized trunk rewrite |
| craft | core/craft/README | target-scoped technique, protected information/voice/terms; no full pipeline merely to fix a line |
| beat-sheet | modules/beat-sheet-dialogue | open exploration and USER cuts; headless cannot invent ruled beats |
| delivery | modules/delivery-planner | exact beat-sheet version binding; rough channel intent, not final staging authority |
| twin | modules/twin-db; scripts/twin_db.py | query/CRUD ownership, post-landing deltas and optional SYNC_SPEC |
| rules | modules/world-rules-editor | interactive USER sovereignty; never silent split or mutation |

A beat sheet present means assignment mode; zero USER-ruled beats block rather
than silently reverting to discovery. Missing/stale beat-sheet binding invalidates
its delivery plan. No beat sheet may use the existing discovery method. Inspect
DELIVERY_CHANNELS, VISUAL_GRAMMAR, LANDING_SPEC and actual runtime capabilities
before committing staging: engineering gaps are explicit, not discovered only
at landing. Missing grammar blocks staging, not medium-independent drafting;
missing landing spec blocks runtime translation, not authoring.

## Complete-design boundary and exact-output acceptance

The package contains full draft, character voice and knowledge ledgers, branch
memory, emotional beat holds/releases, term/locale sources, concrete staging and
runtime dependencies. Two independent whole-package reviews replace fixed .5
handoffs: intent/experience checks causality/emotion/voice/knowledge; completeness/
project checks canon, stage obligations, structure, style, feasibility and all
locale delivery. Neither can approve USER-owned story direction on the user's
behalf. Required script/staging approvals in the adapter still block auto mode.

Spoken-fluency remains a **bounded separate clean-room technique**, not another
chapter owner: fresh language context, no design documents, mechanically
extracted canon-protected/banned forms, frozen beat/pragmatic function/voice.
Use `core/craft/spoken-fluency.md`; canon-aware back-check and glossary/style
checks follow. Repaired language returns to the primary author. This preserves
design-register isolation without a fresh worker for every small step.

After production (including authorized repairs), run STEP_9_STORY_AND_PROSE_QA
criteria against the exact latest landed output: runtime knowledge order,
button/choice/route meaning, all-channel holds/releases, voice, native spoken
fluency, and semantic equivalence in every shipped locale. Bind the output hashes
and raw check results in the evidence. A changed output invalidates that QA.
Mechanical glossary/style checks alone cannot replace this independent semantic
acceptance. Final Chinese narrative text retains STEP_7_RUNTIME_LANDING's strong
adverb restraint; functional/help/accessibility/safety copy is excluded. Later
spoken/dialogue passes must not reintroduce avoidable annotation prose.

Do not rewrite repeated constraint paragraphs across handoffs; cite the original
and preserve its full meaning in context. Do not shorten a scene/voice/emotional
curve to claim lower tokens. Human creative-quality judgments remain USER-owned.

### Machine-checked latest-output records

`story/v2.py` checks `story_output_acceptance.v2` against the actual resolved
profile's `SHIPPED_LOCALES`, not a reviewer-invented locale list. Every planned
output must be present. Explicit profile paths are adopted with `migrate
--authority <relative-path>/PROJECT_PROFILE.md`; otherwise the registry and
canonical adapter resolve in contract order. An unresolved/external legacy
profile blocks v2 rather than dropping its rules; v1 historical readers remain.

Technical evidence uses `story_technical_evidence.v2`: exact outputs and named
style_lint/glossary/routing/locale_integrity checks with command, exit_code and
log reference. A checker can document a profile-declared unavailable capability;
it cannot pretend a command ran. Clean-room evidence uses
`story_cleanroom_evidence.v2`, one per shipped locale: fresh worker, only the
sanitized `story_fluency_packet.v2` in sources_read, exact latest output hashes,
and a separate `story_canon_backcheck.v2` PASS citing the adopted profile.
The packet has only locale, frozen beats, protected/banned forms and spoken
lines—not design files or peer conclusions. Final semantic QA is a third,
distinct execution from both design reviewers and these language contexts.

No-dialogue work must not invent dialogue to fill a gate. A reviewed design can
bind `story.spoken_output_paths: []` plus `scope_evidence` pointing to its full
change-scope artifact. Latest-output QA must cite that scope and actual outputs
when marking clean-room NOT_APPLICABLE. Without that reviewed scope exclusion,
the normal language gate remains required. Technical and semantic checks still
apply to world/cast/knowledge-only work; unavailable runtime capabilities need
explicit evidence rather than invented landing work.
