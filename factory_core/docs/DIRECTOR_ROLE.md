# The Director role and full delegation to closed beta

Status: APPROVED by the USER on 2026-10-14 ("approved, go ahead"), after the USER's
ruling that a role judging 好不好玩 "可以錯，但不能不存在", that it is the
orchestrating session ("你就是那個 orchestrator") rather than a subagent, and the request
for a fully autonomous mode delivering a closed beta before the USER plays.
Implemented in `factory_core/director.py`, `factory_core/authorship.py` (CLOSED_BETA),
`factory_core/state.py` (checkpoint gate, AI_DIRECTOR rulings) and
`factory_core/schemas/director_note.schema.json`.

## 1. The problem

The Factory governs compliance well: nothing is forged, nothing exceeds its authority,
nothing approves itself. That stays as it is.

What AUTONOMOUS mode lost is a role, not a gate. In COLLABORATIVE mode the USER manages the
Factory: plays, says "the numbers don't fit the rules, luck dominates, there is no room for
strategy", and the direction changes. AUTONOMOUS mode handed authorship to the AI but not
that management. Every AI role was scoped to an artifact (author, reviewer, observer,
comparer); none owned "is this fun, is it worth continuing". The standing instruction that
an LLM never judges fun, right while the USER is present, guaranteed that seat stayed empty.

Simplest Auto Battler v4 shows the cost: seventeen compliant revisions, every gate green, while
the operator's own data said a single drag improved only 44 of 600 positions. One USER fight
found what the whole chain missed.

**The role may be wrong. It may not be absent.**

## 2. Who holds it

The orchestrating session holds it, as the Director (producer and game director). It is not
a subagent and not a reviewer: only the orchestrator has the whole picture, the continuity
and the authority to turn a judgment into the next action. A subagent "playing the USER" would
be one more scoped reviewer whose advice the orchestrator may ignore.

The Director judges quality and direction; the Factory keeps judging compliance. The Factory
checks that a Director judgment exists, cites play evidence and decides; it never checks
whether the judgment is right.

## 3. What the Director does

1. **Plays before judging.** The Director plays from the player's seat with what the project
   offers: the rules model or simulation driven one decision at a time by the Director itself,
   the runnable build, captured frames. For each decision it records whether it cared and what
   the choice changed. Reading the design is not playing it.
2. **States a judgment at every major boundary** in a Director note (section 5): is it fun,
   what is the biggest risk to fun now, is the current work attacking that risk, and a
   decision: CONTINUE, REDIRECT, STOP or KILL. "The USER will judge in the playtest" is not a
   judgment.
3. **Puts direction above the pipeline.** When a note says the core is weak, polish, UI and
   evidence work on that core stops until the core is redirected.
4. **Writes the strongest case against continuing** in every note, because it is also the
   author and grades its own work.
5. **Calibrates against the USER.** When the USER plays, every difference between the USER's
   reaction and the notes is recorded as a calibration entry (what the Director missed or
   overrated) and carried into the project memory and the operator's memory, so taste
   persists across sessions and context compaction.

## 4. Three modes

| Mode | USER present | Design approval | First USER play | Director |
| --- | --- | --- | --- | --- |
| COLLABORATIVE | throughout | USER | any time | optional notes; the USER is the director |
| AUTONOMOUS | at design approvals | USER (exact APPROVE action) | after production | mandatory notes at major boundaries |
| CLOSED_BETA (new) | at closed beta only | Director ruling, recorded as AI_DIRECTOR | the closed-beta build | mandatory; holds every USER seat until beta |

CLOSED_BETA is selected only by a raw USER message (like the existing mode switch), names the
product it covers and may be revoked by the USER at any time. The USER keeps product
commission (what the product is) unless the delegation says otherwise.

## 5. Director notes

`design/factory/director/<task_id>/<NNNNNN>.json` (`factory_director_note.v1`), written by the
orchestrator itself:

- `boundary`: which major boundary (below), `checkpoint` it accompanies;
- `played`: what was played and how (simulation decisions, build session, frames), with
  evidence refs;
- `fun_judgment`: plain words, including what felt like a decision and what felt like luck;
- `biggest_risk`: the largest remaining risk to fun or value, and whether current work
  addresses it;
- `case_against`: the strongest reason to stop or change course;
- `decision`: CONTINUE | REDIRECT | STOP | KILL, with what changes next;
- `calibration`: earlier USER verdicts this judgment was checked against (may be empty).

Major boundaries (not every checkpoint, so notes stay judgments, not ritual):
1. before a design is frozen for review (DESIGN_COMPLETE);
2. before production starts (PRODUCING);
3. before anything is handed to the USER (a playtest build, closed beta);
4. whenever measured evidence contradicts the design's intent (a falsified hypothesis, a
   balance or leverage number far from intent).

Factory check: a checkpoint at a major boundary in AUTONOMOUS or CLOSED_BETA mode is refused
without a current note that cites at least one play evidence ref and decides. A STOP or KILL
note blocks further production checkpoints on that task until a REDIRECT note or the USER
overrides it.

## 6. CLOSED_BETA in detail

- **Delegation record.** `design/factory/AUTHORSHIP_MODE.json` mode CLOSED_BETA, bound to the raw
  USER message and quote, naming the product and the delegated seats (design approval,
  internal playtest verdicts).
- **Director rulings.** Where the workflow needs a USER ruling before beta, the Director writes
  `factory_ruling.v2` with `owner: "AI_DIRECTOR"`, bound to its note. It authorizes production
  exactly like a USER approval inside this mode, is never presented as a USER ruling, and is
  invalid in any other mode.
- **Milestones**, each closed by a Director note with play evidence:
  1. core prototype: the core decision loop playable or simulable; leverage and luck measured;
  2. vertical slice: one full round loop with real UI;
  3. content complete: every mode, screen and language;
  4. closed beta: an exact build the USER can install.
- **Kill and pivot.** If the core prototype note cannot say the core has meaningful decisions,
  the Director must REDIRECT or KILL before building further; it reports a KILL to the USER
  instead of shipping a beta it does not believe in.
- **Closed-beta package for the USER:** the installable build, the Director's own verdict, the
  known weaknesses it chose to ship with, and three to five questions only the USER can
  answer. The USER's verdict then binds as today, and starts calibration.

## 7. Changes to standing instructions

- "The LLM never judges fun" holds only while the USER is present (COLLABORATIVE). In
  AUTONOMOUS and CLOSED_BETA the orchestrator must judge, may be wrong, and must not defer the
  judgment to a later USER playtest.
- Operator skills and the workflow name the orchestrator as Director in those modes.

## 8. Implementation (done; item 6 is the first use)

1. `factory_director_note.v1` schema and `factory_core/director.py` (existence, evidence and
   decision checks; STOP/KILL blocking).
2. CLOSED_BETA in `factory_core/authorship.py`, AI_DIRECTOR rulings in `state.check_ruling`,
   valid only in that mode.
3. Checkpoint gate for notes at major boundaries.
4. WORKFLOW_GPT6.md, the studio/idea operator skills and this document.
5. Tests: missing note refused, note without play evidence refused, STOP blocks, AI_DIRECTOR
   ruling only in CLOSED_BETA, revocation.
6. First use: Simplest Auto Battler — a Director note on the current core (numbers dominate,
   luck heavy, little strategy), then a REDIRECT of the core before any more UI work.
