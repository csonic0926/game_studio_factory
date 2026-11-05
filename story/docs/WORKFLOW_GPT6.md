# Story — independent creative work and persistent world life

Process: factory_core/docs/WORKFLOW_GPT6.md. The primary author creates full world,
character, cast, chapter or branch outputs jointly. Methods are optional aids,
not fixed workers, paragraph lengths or prerequisite handoff files. No generic
story model runner or automatic population scheduler is introduced.

## Medium-independent profile

A project-owned PROJECT_PROFILE.md, selected by explicit migration authority,
registry or design/story/adapter, declares PROJECT_ID, WORLD_NAME, STORY_ROOT,
PRIMARY_LOCALE, SHIPPED_LOCALES and MEDIUM (standalone or game). Field syntax is
`- <NAME>: value`. STORY_ROOT accepts a project-relative path or <PROJECT_ROOT>.
The same Git root/path confinement applies to game and standalone projects.
WORLD_RULES.md and NARRATIVE_DELIVERY.md under STORY_ROOT/state are explicit USER
sovereignty for standalone work; game adapters retain legacy combined-rule reads.
Profile and adapter files are authorities; they are not outputs of generic
production. GLOSSARY.csv remains the sole proprietary-term authority. New forms
are nominations until explicitly adopted; do not invent a parallel canon list.

Standalone work requires no engine path, game commission, product adoption or
playable baseline, even if a colocated game's product is inactive. A game-medium
profile retains actual LANDING_SPEC, DELIVERY_CHANNELS and VISUAL_GRAMMAR for
engine work. Missing runtime support blocks staging/landing, not pure drafting.
Never fabricate a channel or use film language absent from the declared grammar.

## Mandatory content quality — independent of method selection

World: concrete premise; ordinary daily life and exceptional conditions; rules,
constraints, consequences and bounded exceptions; connected geography/settlements,
institutions/factions, pressures, objects, services, travel and transfer points.
Package canonical entities/facts/relations once in the existing story_world twin;
merge accepted chapter additions, never blind-overwrite them with older seeds.

Character: concrete original premise, social reading, daily pressure, visible
contradiction and functional distinctness. Role, routine, movement/obligations,
observable habits, pressure reactions, speaking pattern, avoidances, relationships
and knowledge allowed/forbidden must fit each other and drive scenes. Unsupported
traits/history stay questions or explicitly bounded assumptions, not new canon.
Use CHARACTER_SCHEMA.md for the final indexed character package; consumers read
that package rather than requiring CHARACTER_CONCEPT/WORLD_ROLE/BEHAVIOR handoffs.

Cast: story purpose, scale/scope, covered functions, current members, missing and
overlapping functions, priority, relation/pressure gaps and explicit add/revise/
retain actions. Do not fill seats only to hit a population count. The next action
and effect on existing characters must be clear from the complete cast output.

Chapter: legitimate upstream knowledge/time/world grounding; justified timeframe,
normal track and bending point, distinct segments and coherent throughline; full
scene prose and usable causal/route topology, not recap or labels. Assignment mode
is selected when a beat sheet exists: zero USER-ruled beats blocks; every ruled
beat and cannot remains covered in order with its HOLD/RELEASE curve. Bind delivery
plans to that exact sheet; stale channel intent cannot override original beats.
Discovery without a sheet can explore freely, never inventing USER rulings.
INTRO/non-player setup is not playable choice. Dialogue should sound spoken in
that person's world/pressure, not explanations of the design. Glossary, voice,
knowledge, full prose and emotional pacing survive packaging and localization.

Branch: bind accepted trunk/branch-point ids, inherited memory/pressure, time and
first divergence. Ground the forcing choice in current people/place/objects/
routines. Alternatives differ in action, witnesses and later consequence, not
wording alone. Preserve at least two writing-side axis changes, or a strong axis
plus strong applicable runtime projection, and a delayed hook. No-runtime stories
use writing-side changes, not invented engine tags. Shared nodes cannot leak
branch-only knowledge. Restage changed playable moments; do not clone trunk
staging for altered knowledge/choice/access/emotion. Outcomes preserve branch
identity and later transition consequences without rewriting accepted trunk.

Delivery: concrete pacing holds/releases in all used channels; visual-grammar
primitives, player-operation versus cutscene bindings, cannot collisions and
engineering dependencies checked before landing. Final output checks include
route/button semantics, locale/key/orphan integrity where applicable, knowledge
order, shared-node neutrality, graph/output correspondence, naming, emotion,
native voice and twin/SYNC_SPEC deltas. Chinese narrative retains strong adverb
restraint without damaging necessary contrast, time, degree or voice; functional,
help, accessibility and safety copy are excluded. Do not shorten full prose or
flatten emotional duration to obtain technical PASS.

Meaning is what the native-language reader understands, not dictionary overlap.
Preserve kinship, identity, obligations and other required facts. Unsettled facts
needed by natural localization are design dependencies; resolve only within
creative delegation or with USER. The scoped real-sibling ruling requires real
sibling meaning, without universally banning a word or inventing birth order.

## Acceptance and persistence

All player-facing prose, not only quoted speech, also follows the shared
[player-text clarity workflow](../../player_text/WORKFLOW.md). Declare the v3
`player_text` scope and bind latest-output receipt evidence. Keep the existing
dialogue clean-room production separate; its repaired text is reused, not
compulsorily rewritten again. The independent final semantic-QA execution may
perform the informed text backcheck, but not the fresh first reading. Internal
world records or standalone non-player work can use reviewed NONE, never an
automatic no-dialogue exemption.

Two exact complete-design reviews remain required. Newly authored/revised quoted
speech keeps fresh clean-room fluency packets, canon-aware backcheck and distinct
latest-output semantic QA. No peer/design documents leak into the clean-room.
Every shipped locale is checked against the actual profile. A later output change
invalidates output QA. A technical status cannot overrule a semantic FAIL.

For v3, the story design declares spoken_output_paths, runtime_output_paths and
scope_evidence. Exact-output report is story_output_acceptance.v3. Existing v2
clean-room packets/records remain. Only standalone with an explicitly reviewed
empty runtime scope may mark routing and staging_landing_fidelity NOT_APPLICABLE;
its technical record must cite profile + scope, state the reason and show no
command was run. Route/choice *meaning*, knowledge and all other semantic checks
remain applicable. No-dialogue clean-room exclusion retains reviewed scope rules.

The existing twin owns canonical entities and stable baseline facts. world_state.py
adds branch-scoped accepted-event history beside it, not another editable canon.
Its read-only query gives an NPC only acquired facts with observation/communication
provenance. Relationship changes name a fact_id; involvement alone does not reveal
a private relationship change without acquisition of that fact. Publication consumes an exact COMPLETE Story checkpoint and an event
delta among its accepted outputs, checks predecessor CAS and appends once. Event
ids are idempotent, time never goes backwards, messages require prior knowledge,
and branch inheritance is pinned to an exact ancestor event, not the live future.
Candidate-event replay is explicitly a preview, never canon or acceptance.
No world-state query rewrites unrelated NPCs. Voice remains in the indexed
character package; factual memory does not replace prose craft.
