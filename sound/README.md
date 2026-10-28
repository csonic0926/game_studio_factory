# Sound Game AI Factory

Game **SFX factory**: text prompt -> generated sound -> **de-silenced + peak-fit**
deliverable. It is the Sound specialist in the Game AI Factories capability
layer under **Game Studio Factory**, and remains directly callable through a
spec JSON + CLI + run artifacts.

It also scores **video** (promo / trailer / cutscene): AI-composed note events → real CC0
instrument samples → picture-driven SoundCraft mix → scored video. Contract and role guidance
(recommended: compose with GPT Astra, mix with Claude Opus): [`docs/SCORING_WORKFLOW.md`](docs/SCORING_WORKFLOW.md).

```bash
python3 score.py analyze --video in.mp4 --out work/analysis     # cuts, VO timing, contact sheet
python3 score.py pitch <sample.wav>                             # verify sample octave naming
python3 score.py mix --config examples/score_mix.example.json   # stems + VO -> mix + scored mp4 + report
```

## Why the trim stage exists

ElevenLabs `sound-generation` returns clips padded with leading/trailing silence
and not peak-normalized — they never "just fit". The factory's **trim stage**
(ffmpeg `silenceremove` + peak-normalize) is what turns a raw generation into a
drop-in game asset. This is the sound factory's analog of the asset factory's
prop-cleanup step.

## Use

```bash
python3 sfx.py run --spec examples/door_open.spec.json          # generate + trim
python3 sfx.py run --spec examples/door_open.spec.json --provider mock   # offline smoke
python3 sfx.py trim --in raw.mp3 --out clean.wav                # trim an existing file
```

Start reading a run at `<output_root>/<run_id>/artifact_status.json`, then
`deliverables/`.

## Layout

```
sfx.py                       CLI (public order contract)
pipeline/
  credentials.py             ElevenLabs key (env or ~/.config/voicein/key)
  elevenlabs_provider.py     POST /v1/sound-generation (stdlib urllib)
  trim.py                    ffmpeg silenceremove + peak-normalize
  run.py                     generate -> trim -> deliverables + artifacts
examples/door_open.spec.json
score.py                     video scoring CLI (analyze / isolate / pitch / mix / check)
scoring/
  automation.py              scene rides + gentle VO duck (stdlib, unit-tested)
  srender.py                 note-named multisample renderer (numpy)
  pitch.py                   YIN + FFT pitch/octave check
  analyze_video.py           contact sheet, luma/motion timeline, change candidates, ASR
  isolate_voice.py           ElevenLabs Voice Isolator
  mix.py                     SoundCraft MCP picture-driven mixer (score_mix_v1 config)
  check_mix.py               swing / VO-over-music / chroma checks
examples/score_mix.example.json
docs/AI_CALLER_LANDING.md     start here if you are an AI caller
docs/SCORING_WORKFLOW.md      video scoring contract
```

## Runtime

- Python 3.9+ (SFX path: stdlib only; video scoring: + numpy, a whisper CLI, `soundcraft-cli`)
- ffmpeg + ffprobe on PATH
- ElevenLabs key via `ELEVENLABS_API_KEY` or `~/.config/voicein/key`

## Providers

- `elevenlabs` (default) — the only real provider today; provider field is
  abstracted so more can be added without changing callers.
- `mock` — offline; synthesizes a silence-padded tone so the trim pipeline can
  be smoke-tested with no credits.
