# Game Studio Factory — caller index

For new-game initialization, use `init-game-studio-factory` and
`python3 setup.py init --game-repo <GAME_REPO>`; then continue into bounded Idea
exploration and Product intent authoring. Read
[the initialization workflow](product/docs/PROJECT_INITIALIZATION_WORKFLOW.md).

For ongoing work, start with `python3 factory.py inspect --game-repo <GAME_REPO>`.
It is read-only: version, history, current checkpoints, blockers and legal action.
Read the separately exposed nonbinding Product intent before material planning.
`MIGRATION_REQUIRED` never means silently apply new approval rules or require a
migration just to continue standalone Idea exploration/Product intent.

| Responsibility | Entry | Capability rules |
|---|---|---|
| whole playable game | game-studio-factory | studio/docs/WORKFLOW_V2.md |
| early whole-value intent / experienced value judgment | product-factory | [initialization](product/docs/PROJECT_INITIALIZATION_WORKFLOW.md) / [assessment](product/docs/VALUE_ASSESSMENT_WORKFLOW.md) |
| product exploration/commission | idea-factory | idea/docs/PRODUCT_DEFINITION_WORKFLOW.md |
| gameplay/progression/repair | gameplay-factory | gameplay/docs/WORKFLOW_V2.md |
| world/character/cast/chapter/branch and narrative tools | game-story-factory | story/docs/WORKFLOW_V2.md |
| visual asset generation/cleanup/validation | asset/itf.py | asset/docs/AI_CALLER_LANDING.md |
| sound generation/trim/normalization | sound/sfx.py | sound/docs/AI_CALLER_LANDING.md |
| initialize Idea + Product + routing | init-game-studio-factory | setup.py init |
| routing-only link/relink | init-game-studio-factory | setup.py link |

Open-ended whole-game intent routes to Studio; deliberately bounded specialist
intent goes directly to its owner. A runnable interactive demo is not Studio
delivery. Only an accepted playable baseline with new gameplay acceptance,
predecessor regression, exact-build human verdict and no blockers is delivery.

Version 3 is explicit GPT-6 opt-in, not an automatic replacement for v2. Its
process source is [WORKFLOW_GPT6](factory_core/docs/WORKFLOW_GPT6.md).
`migrate --workflow gpt6 --check` previews the full opt-in; apply requires the
exact authorized digest. The original checkout/global skills stay on main.
Use `inspect` to select the version and follow the selected checkout's skill.
`--project-root` aliases `--game-repo`; `context --method <id>` expands an
optional v3 technique. No comparative/token-savings gate applies to v3.

The one v2 process source is [factory_core/docs/WORKFLOW.md](factory_core/docs/WORKFLOW.md).
`context` loads relevant authority/work and method references; `checkpoint`
validates work transitions; `migrate` previews explicit version changes (default
check); `benchmark` measures complete fixed task cost plus quality gates.

Install: `python3 setup.py install`. Initialize: `python3 setup.py init --game-repo
<GAME_REPO>`. Explicit routing-only relink: `python3 setup.py link --game-repo
<GAME_REPO>`. Existing specialist CLI arguments, skill names, legacy local pointers
and historical formats remain readable. New formats are never inferred from old
approval hashes. Initialization preserves existing Idea work and adds only missing
planning artifacts; an empty seed is not completed value analysis. Unknowns and
explicit scenarios need no extra USER gate. Intent is not commission, actual-play
evidence or acceptance. Bind it as an exact explicit input when a material design
uses it; reconcile stale sources rather than refreshing old proof. Whole-product
stopping/value claims retain the applicable experience/review/claim gates; a
meaningful build alone adds no commercial gate. Game artifacts always land in the
game repo, never in this checkout.
