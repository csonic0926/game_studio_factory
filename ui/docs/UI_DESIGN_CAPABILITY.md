# UI Design capability

Status: APPROVED by the USER on 2026-10-14 ("1. approve 2. okay", after asking for a
UI factory whose core is to make UI "對" — correct — not pretty, as an independent
capability that follows the Idea and Gameplay results: "一定是先有 solid 的 game
system, game rules ，才有可能知道什麼是「對」的 UI"). Implemented in
`ui/ui_design.py` with schemas in `ui/schemas/ui_*.schema.json`.

## 1. Purpose

UI Factory makes UI **correct**, not pretty. Correct UI lets the player play the
gameplay that was designed:

- the player can see every fact the gameplay needs them to know, at the moment
  they need it, and never a fact the gameplay hides;
- every rule that acts is visible when it acts;
- motion and emphasis lead the eye to what matters now, long enough to read it,
  without hiding anything else that matters;
- every input gets a visible response, and every preview equals what will happen;
- after an outcome, the player can trace it back to a choice they can change.

Beauty, art direction and brand belong to other owners (Asset, the visual grammar
the USER already ruled). UI Factory may refuse a pretty UI that hides gameplay; it
never refuses a plain UI that plays correctly.

## 2. Position in the Factory

UI design starts only from solid gameplay. "Correct" is defined by the rules and
the system, so it cannot be judged before they exist.

```text
Idea  ->  Gameplay (rules, system, interaction contract)  ->  UI design  ->  UI Production Adapter  ->  production  ->  evidence
          AUTHORIZED, rules model checked                      this doc       existing ui/ui.py          plans          mechanical + blind + USER
```

Entry gate (mechanical, blocks otherwise):

1. a gameplay or studio design for the same objective is AUTHORIZED;
2. its executable rules model passed `gameplay/rules_check.py` (when the game has one);
3. its player-facing interaction contract exists (beats, steps, player entry knowledge);
4. no OPEN gameplay question touches a fact the UI must show or hide.

UI design binds those gameplay artifacts as inputs. A later gameplay change
invalidates the UI design closure (new UI draft). A UI failure (a readability
hypothesis rejected) revises only the UI design, unless the repair needs a rule
change, which returns to Gameplay.

The UI Production Adapter stays the construction layer ("how this repo builds UI").
UI design says what to show, when and with what priority; the adapter says how to
build it in this repo's style. Production plans bind both.

## 3. The UI design: three authored artifacts and one verification plan

Written in the game repo under `design/ui/<objective_id>/`, frozen as one design in
the normal v3 design package (`factory_design.v3`, capability `ui`).

### 3.1 Player Information Model — what the player must, may and must not know

Derived from the gameplay authority, not invented. One entry per **fact**:

| Field | Meaning |
| --- | --- |
| `fact_id`, `statement` | e.g. `fact.first-target`: "whom each unit strikes first" |
| `source` | the rule, system transition or contract step it comes from (exact ref) |
| `need` | `MUST_KNOW` · `ON_DEMAND` · `MAY_KNOW` · `FORBIDDEN` (e.g. the winner before the fight) |
| `serves` | the player decision or understanding it serves (contract beat/step) |
| `when` | the moment(s): before a decision, during resolution, after an outcome |
| `channel` | `PERSISTENT` (always on screen) · `DISCLOSED` (tap / hold / hover) · `TRANSIENT_CUE` (an event cue) · `EXPLANATION` (after the fact) |
| `canonical_wording` | one term and one number source used on every surface |

Mechanical completeness (validator): every rule of the rules model and every
player-visible system transition maps to at least one fact; every decision step
of the contract lists the facts it needs and each is reachable at that step; every
`FORBIDDEN` fact names its guard (what in the UI could leak it and why it does not);
every fact has exactly one canonical wording.

### 3.2 Attention and Motion Plan — what draws the eye, when, for how long

One entry per **event** the player must notice (from the rules model's log / system
transitions):

- the cue (word, mark, motion, sound, haptic) and the fact it carries;
- timing budget: maximum latency after the event, minimum readable time, whether
  it is real time or follows the speed setting, and Skip behaviour;
- concurrency: at most N cues per object; priority and merge rule when cues collide
  (which wins, which waits, how long, what is dropped);
- the first thing the eye should land on in each beat, and what must stay calm
  until then;
- an occlusion list: what this cue may never cover (numbers, rule words, the cue
  of another rule).

Mechanical checks: every rule that acts during resolution has a cue; every
priority/merge rule is bounded (a replay can prove the worst-case delay); no cue's
area overlaps a protected element on the same layer band.

### 3.3 Screen Contracts — where each fact lives and how input answers

Per surface:

- information placement: which facts appear, in which channel, at what size class;
- the layer stack by name (e.g. art < lines < number plates < marks < badges < overlays)
  and which facts each layer protects;
- a default density ceiling (e.g. how many persistent lines/marks before disclosure
  is required) and the disclosure control for the rest;
- an input -> response table: every input lists its visible response and its
  persistent change; every preview names the committed state it must equal;
- the terminology table used on this surface (from canonical wording).

Mechanical checks: every input has a response; every preview has an equality test;
every surface uses only canonical wording; text fit and minimum sizes across all
shipped locales (the adapter's typography rules).

### 3.4 Verification plan — three layers, never merged

1. **Mechanical** (every build): coverage (fact -> surface, rule -> cue, input ->
   response), preview equality, layer/occlusion, timing bounds, text fit, canonical
   wording. Generated from the three artifacts; failing checks block evidence.
2. **Blind comprehension** (the existing Studio runtime chain, unchanged
   procedure): a blind observer sees only frames; the sealed record is compared
   afterwards. The UI design lists, per chain, the `MUST_KNOW` facts the observer's
   own attempt fields must show they understood, and the readability hypotheses
   with falsifiers. No question is added to Phase A.
3. **USER playtest**: signals only a human gives (feel, number of tries, session
   pace), named in advance.

## 4. Lifecycle

Same v3 stages: DRAFT -> DESIGN_COMPLETE -> REVIEWED -> AUTHORIZED -> PRODUCING ->
EVIDENCE_READY -> COMPLETE, with checkpoints, two fresh reviewers and the verbatim
USER approval action.

- **Intent/experience reviewer**: walks each beat as the player; can the player do
  the gameplay's work (read, decide, commit, understand the result) with exactly
  the facts shown; does attention go where the beat needs it; is anything forbidden
  leaked.
- **Completeness/project reviewer**: every fact/rule/input covered; wording
  consistent with gameplay authority; layers and timing bounded; feasible with the
  UI Production Adapter and the USER's visual grammar rulings.

Production plans bind the UI design checkpoint and the adapter. Evidence = the
mechanical report on the exact build + the runtime blind chain + its informed
comparison (judged against this UI design's fact list and hypotheses) + the USER
playtest. A rejected readability hypothesis returns to a new UI draft.

## 5. Seed rules, from the Simplest Auto Battler (v4) evidence

Each became a mechanical check or a review question above.

| Rule | What happened |
| --- | --- |
| Every acting rule has its own visible cue | Shield guarding read as "a bug / hit the wrong unit" until a shield mark sat on the guarded line |
| Default calm; disclose density on demand | Always-on target lines were called "line spaghetti" at 15 units |
| Disclosure must be geometrically legible | Tap-a-unit lines from one column ran through the cards in front, so their sources could not be told apart |
| Protected information is never covered | Lines over card numbers; a later damage badge over the "Guard" word |
| Cues have minimum readable time and maximum latency | An unbounded badge queue delayed cues up to 9.2 s; the fix bounded it to 0.5 s |
| Outcomes point back to a changeable choice | Players "could not attribute the win to my swap"; a loss explained only by who fell gave no signal about one's own choices |
| Previews equal outcomes | The drag preview hid the unit a swap would move |
| Every input answers visibly | Buy XP without level-up feedback; a silent swap on drop |
| One term, one number | "Red 2 bonus" in the result next to "Red 3" on the counter |
| The UI must not leak what gameplay hides | Lines may show first targets, never the predicted winner |
| Verification layers stay separate | Typography scans caught overflow no reviewer saw; only blind observation caught comprehension; only the USER can count drags |

## 6. Out of scope

Rules and balance (Gameplay), product fit (Idea/Product), art and brand (Asset and
the USER's visual grammar rulings), how the repo builds UI (UI Production Adapter),
copywriting voice beyond canonical wording (Story where present).

## 7. Implementation (done unless noted)

How to run it:

```text
python3 factory.py context --game-repo <GAME> --capability ui --task ui_design --task-id <id>
python3 ui/ui_design.py check  --game-repo <GAME> --design design/ui/<objective>/FACTORY_DESIGN.json
python3 ui/ui_design.py report --game-repo <GAME> --design <same> --report <mechanical report json>
```

A ui design is an ordinary `factory_design.v3` with `capability: "ui"` and a `ui`
binding: `gameplay_checkpoint` (a design input), `information_model`,
`attention_plan`, `screen_contracts`, `verification_plan` (design artifacts) and,
only when the gameplay design binds no rules check, `rules_model_absent_reason`.
The interaction contract named by the information model is a design input too.
Its review requirements are the `ui.*` rules of `factory_core/rule_map.json`.
Production plans touching UI of a gameplay that has an authorized ui design cite
it in `ui_impact.ui_design_checkpoint`. The Studio comparison of a blind chain
judges the chain's MUST_KNOW facts in `ui_fact_observations`.

Steps:

1. `ui` becomes a design capability in `factory_core/catalog.py` (`UI_DESIGN` task),
   with this document and the adapter workflow as its docs.
2. Schemas and templates for the three artifacts and the verification plan.
3. `ui/ui_design.py`: entry gate, mechanical completeness checks (3.1–3.3), and the
   mechanical-report check bound to an exact build.
4. Production plan binding: UI plans cite the UI design checkpoint as well as the adapter.
5. Studio comparison: the informed comparison reads the UI design's fact list and
   readability hypotheses.
6. Tests for the gate, the validators and the plan binding.
7. Pilot: Simplest Auto Battler revision 18 authored as the first UI design.
