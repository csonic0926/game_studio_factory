# Project-owned Gameplay Decision Card standard workflow

This workflow is mandatory before every new or materially revised Gameplay
Decision Card. It applies equally to `STUDIO_WHOLE_GAME` and
`DIRECT_SPECIALIST` routes.

## Ownership boundary

The Factory owns only the portable envelope:

- the blank answer sheet and schemas;
- exact path/version/SHA bindings;
- lifecycle and staleness rules;
- mechanical validation;
- the generic final Studio Card review; and
- fail-closed routing and negative tests.

The game repository owns its gameplay vocabulary, lap/cycle scale,
scene/beat/interaction or equivalent composition, controls, player work,
rhythm, resolution/time/resource boundaries, failure/recovery/replay,
validation methods, and the finite list of decisions that must be visible on
the rendered Card. Project answers in Factory core are defects.

Human/project authority adopts or corrects that standard. A generated,
inferred, `TBD`, blank, machine-local, or Factory-owned file is never active
authority.

## Initialize or migrate the project layer

The Factory ships:

```text
gameplay/templates/PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json
gameplay/templates/PROJECT_GAMEPLAY_COMPOSITION.json
gameplay/templates/GAMEPLAY_DECISION_CARD_PROJECT_REVIEW.json
```

To create only missing blank answer sheets:

```bash
python3 gameplay/init.py seed-card-standard --game-repo <GAME_REPO>
```

This returns `PROJECT_CARD_AUTHORING_STANDARD_REQUIRED`. The seeded standard
is deliberately `DRAFT_NOT_ADOPTED`; it cannot authorize a Card. Fill it from
project authority, record adoption as
`HUMAN_OR_PROJECT_AUTHORITY_ADOPTED`, set it `ACTIVE`, and commit it in:

```text
design/gameplay/adapter/PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json
```

The exact filename may differ, but it must remain directly under the game
repo's `design/gameplay/adapter/`. The game repo's committed root `AGENTS.md`
or equivalent collaboration contract must point to that path. The standard
binds the exact collaboration-contract SHA.

Add this exact block to the canonical Project Gameplay Profile:

```text
## Gameplay Decision Card authoring authority

- Project Card authoring standard path: `<GAME_REPO_RELATIVE_PATH>`
- Project Card authoring standard version: `<EXACT_VERSION>`
- Project Card authoring standard SHA-256: `<EXACT_SHA256>`
- Project Card authoring standard status: `ACTIVE`
```

`init.py start` returns `PROJECT_CARD_AUTHORING_STANDARD_REQUIRED` instead of
ordinary readiness when a complete existing adapter set lacks this active
binding. For a new project with active Product authority, the same state
precedes the first Studio Card. Existing-project reconstruction may propose a
draft from accepted gameplay and rulings, but may not activate inferred rules.

## Formal authority and eligibility

Let `S_t` be the Profile-selected project standard at time `t`, `A_i` the
project-owned composition artifacts for one Card, `I` the Player-Facing
Interaction Contract and passed review, `C` the Card material payload, and
`R_p` the fresh project review.

```text
eligible(C, t) =
  active_and_adopted(S_t)
  and card_standard_ref(C) == exact_ref(S_t)
  and required_composition_kinds(S_t) subset kinds(A)
  and exact_refs(C, A, I)
  and independent_project_review(R_p)
  and inventory(R_p) == requirements(S_t)
  and render_inventory(R_p) == render_only_requirements(S_t)
  and no_blockers(R_p)
```

Changing the selected standard bytes or Profile binding changes `S_t` and
immediately makes an old `PENDING` Card ineligible for render, registration,
verdict recording, or Full-Spec authorization. Never replace a Card's old
standard hash by hand. Regenerate the composition/Card/review chain instead.

Historical approved Cards remain readable evidence. They require migration
only when materially revised or reused to authorize new production.

## Per-Card route

The active standard declares one or more project-specific composition artifact
kinds. At least one kind is mandatory. A Scene/Beat Map is one possible game
answer, not a Factory default. The chosen artifact(s) must freeze the project's
applicable playable span, lap/loop boundaries, ordered composition and
transitions, interactions or bounded repetitions, branches, resolution and
settlement, failure/recovery, persistent return, and validation plan before the
Card is approved.

The route is:

```text
Project Gameplay Profile
  -> active project Card standard
  -> exact project composition artifact(s)
  -> Player-Facing Interaction Contract
  -> fresh Interaction Contract review
  -> Gameplay Decision Card v3
  -> fresh project-standard Card review
  -> route-specific Studio final Card/alignment gates when applicable
  -> human Card verdict
  -> exact-conformance Full Spec
  -> production/runtime
```

`GAMEPLAY_DECISION_CARD.json` v3 binds:

- `project_card_authoring_standard` with exact path, version, and SHA-256;
- `project_composition_artifacts` with kind and author context ids;
- the Interaction Contract and review; and
- `project_card_review`.

The project review inventories every declared standard requirement, including
conditional `NOT_APPLICABLE` findings with rationale. It separately inventories
every finite `render_only_requirement_id` and maps each to exact Card claim ids.
Its reviewer must differ from every composition, Contract, and Card author.
Only:

```text
verdict = PASS_PROJECT_CARD_AUTHORING_STANDARD
blocking_findings = []
```

may continue.

The fresh project reviewer validates the exact chain before handing it to the
route-specific next gate:

```bash
python3 gameplay/design_gate.py validate-project-card-review \
  --game-repo <GAME_REPO> \
  --card design/gameplay/objective_gameplay/<OBJECTIVE_ID>/GAMEPLAY_DECISION_CARD.json
```

The review binds the Card's decision-payload and rendered-surface SHA rather
than the complete Card file. The Card can therefore bind the review's own file
SHA without a circular hash. `project_card_review` itself is excluded from the
human decision payload; the active standard and composition artifacts are
included.

Each validation hypothesis names a `validation_method_id` declared by the
project standard. Mental-state claims require the project's operational
observation or debrief protocol; a keyword or field-presence check never awards
the semantic project verdict.

For Studio work, the later generic
`GAMEPLAY_DECISION_CARD_FACTORY_REVIEW.json` v3 also binds the exact project
standard, composition artifacts, and passed project review. It remains a
different review with a different reviewer. Direct-specialist work has no
Studio final/alignment register gate, but `render-card` and
`record-card-verdict` still require the passed project review.

## Commands and fail-closed surfaces

Normal human rendering always requires the game repo:

```bash
python3 gameplay/design_gate.py render-card \
  --game-repo <GAME_REPO> \
  --card design/gameplay/objective_gameplay/<OBJECTIVE_ID>/GAMEPLAY_DECISION_CARD.json
```

`draft-card-surface` is for review preparation only and is not permission to
show the Card as a normal pending decision. `register-card`, `render-card`,
`record-card-verdict`, and Full-Spec/design-conformance validation reject
missing, blank, stale, blocked, incomplete, or self-reviewed project authority.
Both routing modes are covered.

## Multi-Codex synchronization

The standard lives only in the game repository, never only in Factory checkout,
chat history, a machine-local skill, an ignored pointer, or an absolute path.
Every Card handoff records its version and exact SHA. Separate sessions pull
the game repo independently from the Factory repo and use the same committed
standard bytes. A Factory update does not synchronize project authority, and a
project-authority update does not synchronize Factory software.
