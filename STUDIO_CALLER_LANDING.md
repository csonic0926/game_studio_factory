# Game Studio Factory — caller index

Start with `python3 factory.py inspect --game-repo <GAME_REPO>`.
It is read-only: version, history, current checkpoints, blockers and legal action.
`MIGRATION_REQUIRED` never means silently apply new approval rules.

| Responsibility | Entry | Capability rules |
|---|---|---|
| whole playable game | game-studio-factory | studio/docs/WORKFLOW_V2.md |
| product exploration/commission | idea-factory | idea/docs/PRODUCT_DEFINITION_WORKFLOW.md |
| gameplay/progression/repair | gameplay-factory | gameplay/docs/WORKFLOW_V2.md |
| world/character/cast/chapter/branch and narrative tools | game-story-factory | story/docs/WORKFLOW_V2.md |
| visual asset generation/cleanup/validation | asset/itf.py | asset/docs/AI_CALLER_LANDING.md |
| sound generation/trim/normalization | sound/sfx.py | sound/docs/AI_CALLER_LANDING.md |
| initialize or relink | init-game-studio-factory | setup.py link |

Open-ended whole-game intent routes to Studio; deliberately bounded specialist
intent goes directly to its owner. A runnable interactive demo is not Studio
delivery. Only an accepted playable baseline with new gameplay acceptance,
predecessor regression, exact-build human verdict and no blockers is delivery.

The one v2 process source is [factory_core/docs/WORKFLOW.md](factory_core/docs/WORKFLOW.md).
`context` loads relevant authority/work and method references; `checkpoint`
validates work transitions; `migrate` previews explicit version changes (default
check); `benchmark` measures complete fixed task cost plus quality gates.

Install: `python3 setup.py install`. Link: `python3 setup.py link --game-repo
<GAME_REPO>`. Existing specialist CLI arguments, skill names, legacy local
pointers and historical formats remain readable. New formats are never inferred
from old approval hashes. Setup/link does not commission a product or approve a
design. Game artifacts always land in the game repo, never in this checkout.
