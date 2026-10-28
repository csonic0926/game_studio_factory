# AI caller landing — Sound Game AI Factory

First stop for an AI agent that needs a game SFX asset. Mirrors the calling
model of `game_asset_factory` (spec JSON + CLI + run artifacts) so the same
inspection habits apply.

## Decide the path

| Caller need | Do this |
| --- | --- |
| Generate a game SFX (text prompt -> trimmed, peak-fit clip) | `python3 sfx.py run --spec <spec.json>` |
| Only trim/normalize an existing audio file | `python3 sfx.py trim --in a.mp3 --out a.wav` |
| Offline smoke (no ElevenLabs credits) | add `--provider mock` to `run` |
| Score a video (music under picture, with or without narration) | read [`SCORING_WORKFLOW.md`](SCORING_WORKFLOW.md), then `python3 score.py analyze / mix` |
| Mix a composer's printed stems to picture | `python3 score.py mix --config <score_mix_v1.json>` |
| Verify a sample's real pitch/octave | `python3 score.py pitch <wav>` |

## Calling contract

Resolve `$STUDIO_ROOT` from the linked game repo's
`design/STUDIO_FACTORY.local.md` (legacy `design/AI_FACTORY.local.md` remains a
fallback), then run:

```bash
cd "$STUDIO_ROOT/sound"
python3 sfx.py run --spec examples/door_open.spec.json
```

- Provider: **ElevenLabs only** for now (`/v1/sound-generation`). Key resolves
  from `ELEVENLABS_API_KEY` or `~/.config/voicein/key`.
- ElevenLabs returns silence-padded, non-peak-fit mp3. The factory's **trim
  stage** (ffmpeg `silenceremove` + peak-normalize) makes the deliverable
  tight and consistent — this is the sound factory's counterpart to the asset
  factory's prop-cleanup stage.

## Spec

```json
{
  "schema_version": "sound_factory_v1",
  "run_id": "door_open",
  "output_root": "/abs/output/sound_runs",
  "provider": { "name": "elevenlabs", "model": null },
  "prompt": "a heavy wooden door creaking open then a soft thud, dry, no music",
  "duration_seconds": 2.0,
  "prompt_influence": 0.4,
  "loop": false,
  "trim": { "threshold_db": -50, "min_silence_ms": 60, "peak_dbfs": -1.0 },
  "output_format": "wav"
}
```

Prompt tips for game SFX: describe the source + material + action, add "dry",
"close-mic", "no music", "no reverb" to keep it drop-in. Use `loop: true` for
ambiences. `duration_seconds` null lets the model choose.

## What to inspect in a run

Under `<output_root>/<run_id>/`:

- `artifact_status.json` — read first (`ok`, `stage`, `deliverable`)
- `deliverables/<run_id>.<fmt>` — the final asset
- `deliverables/validation_summary.json` — silence trimmed, duration, peak
- `step_1_raw/` — raw provider output (before trim)

Copy only `deliverables/` into the game repo (e.g. a Godot `sound/` dir or the
Vinci World cutscene `sfx` beat asset path).

## Video scoring roles

Recommended split: **compose with GPT Astra, mix with Claude Opus**. The composer delivers the
score source, section clips and printed stems; the mixer works only from those and reports musical
problems back rather than re-timing stems. Details and evidence are in `SCORING_WORKFLOW.md`.

## Not enough?

Adding a provider (beyond ElevenLabs) or a new stage is a factory-side change —
extend `pipeline/` and this landing doc.
