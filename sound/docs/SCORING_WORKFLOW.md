# Video scoring workflow — Sound Game AI Factory

Original music for promo videos, trailers and cutscenes, with **reasonable AI generation**:

- an AI composer writes the arrangement as note events against the picture timeline;
- real recorded instrument samples render it;
- a DAW mixes it to the picture;
- the mix is laid under the video.

Never use one-prompt text-to-music as the deliverable. CLI: `python3 score.py …`
(`scoring/`). This file is the contract; follow it whatever model or machine runs it.

## Roles (recommendation)

| Role | Owns | Recommended model |
| --- | --- | --- |
| **Composer** | phrases, harmony, voicing, orchestration, rhythmic design, where hits land against picture/VO | **GPT Astra** |
| **Mixer** | balance, space, picture-driven automation, narration clarity, loudness, final lay-back | **Claude Opus** |

Evidence: on 2026-10-28 the USER compared both models doing the whole job on one 30 s promo.
Astra wrote the stronger phrases; its own mix was weak. Opus's mix workflow was the stronger half.

This is a recommendation, not a lock. Any capable model may take either role. Keep the roles
separate even when one model does both: the composer delivers files (below) and the mixer works
only from those files.

Boundary: hit placement and phrase entries are compositional decisions. If the mixer finds a
musical problem, it reports it back to the composer with timestamps and measurements. Examples:
an ostinato entering from silence, a pad gap at a chord change, a hit 0.3 s off a cut. The mixer
does not re-time printed stems; sliding one stem breaks ensemble sync. The mixer may soften such a
problem with automation and must say that it did.

## Composer → mixer delivery (three layers)

| Layer | Content | Why |
| --- | --- | --- |
| 1. Score source (unprinted) | one `.mid` per instrument, aligned to video start, tempo map inside; `note_events.json`; `score_plan.json` (sections, chords, roles, VO map) | re-arrange, re-voice, or hand to human composers/players — the editable truth |
| 2. Section clips + session | per picture section, per instrument group: audio clips with pre-roll and ≥ 2 s tails, placed in a DAW session | lets an editor re-time/delete/stagger phrases in a DAW when picture changes |
| 3. Printed stems | one full-length WAV per instrument (or group), all from 0 s, same rate/bit depth; narration (`voice/`) separately | the mixer's input; standard film/TV hand-off |

Layer 3 is what `score.py mix` consumes. Layers 1–2 must be kept even if nobody asks for them yet.
Note: composers normally hand their own DAW sessions (clips) to collaborators; full-length printed
stems are the mixing-stage format — expected here, unfamiliar to people who only receive sessions.

## Step 0 — environment (every machine)

1. Check OS/arch, package manager, Python + numpy, ffmpeg/ffprobe, git, a whisper CLI, free disk.
   Report what is missing and how you will fill it. Ask before installs > 500 MB or any paid API call.
2. One persistent shared library root, `$SAMPLE_LIBRARY_ROOT` (default `~/Music/SampleLibraries`),
   with a `MANIFEST.md`: what was downloaded, licence, source URL, tool paths. Read it first; never
   re-download what is there. Record its location in your memory system.
3. DAW: SoundCraft (open source, macOS/Windows/Linux; github.com/storytold/soundcraft). Install the
   release `soundcraft-cli` for your OS; set `SOUNDCRAFT_CLI` or put it on PATH. Optional MCP:
   `claude mcp add -s user soundcraft -- <cli> mcp` (`-s user`, or it only applies to one folder).
   If it cannot run, fall back to ffmpeg filters and say so.
4. ElevenLabs key: `ELEVENLABS_API_KEY` (or `~/.config/voicein/key`). Typical account limit: 4
   concurrent requests.

## Step 1 — instrument samples (licence first)

Use only sources that allow commercial use in ads/games:

- **Preferred (CC0):** VSCO-2-CE (`github.com/sgossner/VSCO-2-CE`) and VCSL (`github.com/sgossner/VCSL`).
  - Both are large (2–4 GB). Fetch only what you need:
    `git clone --depth 1 --filter=blob:none --sparse … && git sparse-checkout set --no-cone "/<folder>/"`.
  - Check folder sizes first with `gh api "repos/<repo>/git/trees/HEAD?recursive=1"`.
- **A bright cinematic palette is about 1.5 GB:**
  - VSCO: violin, viola and cello sections, harp, flute, F horn
  - VCSL: Kawai grand, vibraphone, hand chimes, glockenspiel, suspended cymbal (it includes a 7.5 s crescendo), timpani, bass drum, Mark Trees
- **Also vetted:**
  - Karoryfer Swirly Drums (CC0)
  - jRhodes3d (music made with it is CC0; never ship the raw samples)
  - Salamander Grand (CC-BY; credit needed)
- **Avoid:**
  - jRhodes3c and Rickenbacker 4001 (NC-SA)
  - Sonatina SSO (Sampling Plus excludes advertising)
  - Salamander Drumkit (CC-BY-SA)
  - "Freemium" kits

**Octave trap.** Most VSCO/VCSL folders name middle C "C3", so they sound an octave above their
file names. `scoring/srender.py` carries a measured offset table, but treat it as a starting point
only. Verify every instrument on every machine with `python3 score.py pitch <wav>`:

- For sustained tones, YIN is reliable.
- For bells (glockenspiel, chimes), trust the FFT's lowest strong peak. YIN locked an octave low on
  glockenspiel once, and the error shipped.
- VSCO's Percussion/Glock is too inharmonic to map.
- Exclude piano release samples (`_rel_`); srender does this by default.

**Rendering.** These libraries are raw WAVs with the note in the file name; no SFZ mapping ships
with them. `scoring/srender.py` handles them:

- picks the nearest sampled note and resamples it to the target pitch;
- picks the velocity layer and round-robin;
- applies attack/release envelopes;
- writes one stereo WAV per instrument.

sfizz or fluidsynth are fine where they are available.

**ElevenLabs is good for:**
- textures and foley (room tone, card/paper/foil, risers);
- single pitched notes: the model ignores the requested note but holds pitch, so measure the pitch
  and set root + fine-tune;
- Voice Isolator (`score.py isolate`) to pull narration off a finished mix. This is a paid call;
  prefer the original VO file.

**ElevenLabs is bad for:**
- kick/snare one-shots, which come back near-silent;
- vinyl crackle, which comes back spiky and sounds "broken" if pushed. Limit it, low-pass it, and keep it very low.

## Step 2 — per video

1. **Analyse.** `python3 score.py analyze --video in.mp4 --out work/analysis`, then look at
   `contact_sheet.png` yourself.
   - `candidates.json` ranks visual changes, fades included. ffmpeg's scene filter misses fades.
   - `asr.json` gives narration word timestamps.
   - Narration mixed into the original audio means isolation (with approval) or the original VO.
2. **Plan (composer), and show it to the user before writing notes.**
   - Map picture events, VO lines and VO gaps. Musical features belong in the gaps.
   - Choose a tempo so that main cuts land on bar lines (e.g. 96 BPM gives 2.5 s bars). A rubato
     opening is fine.
   - Set key, chords, palette and the emotional arc per section.
   - Stagger entries rather than switching a whole texture on from silence.
   - Overlap pads across chord changes.
3. **Compose and print (composer).** A re-runnable score script in seconds → layers 1–3 above.
4. **Mix (mixer).** Write a `score_mix_v1` config (`examples/score_mix.example.json`), then run
   `python3 score.py mix --config mix.json`. It builds the whole session from scratch:
   - **Groups** (Pads / Pulse / Lead / Sparkle / Perc / Bass presets, or explicit inserts) feed
     aux tracks.
   - **Hall reverb** is fed by sends and returns into the Music bus, so dry and wet duck together.
   - **Music aux:**
     - ~2.8 kHz carve when there is VO;
     - a **slow leveler** (comp −27 dB, 2.5:1, 80/600 ms);
     - the VO duck.
   - **Narration chain:** EQ, de-ess, comp, small hall send.
   - **Master:** glue comp + maximizer, ceiling −1.5 dBFS so AAC overshoot stays under −1.
   - **Scene rides** (`scenes`): per section, small group/hall offsets reached at `t` over `ramp`.
   - **Extra rides** (`rides`): e.g. fold an entry in under an image fade-up.
5. **Gentle-mix rules** (USER-verified 2026-10-28: fast/deep moves read as "pumping, too abrupt"):
   - **VO duck:** music sits at −3 dB between lines and dips only −4 dB more under them; ~0.8 s down
     and ~1.8 s up.
   - **Short breaths:** gaps under 1.5 s stay ducked; gaps under 2.5 s come back only halfway.
   - **Scene rides:** keep them to ≤ 1.5 dB, with ramps of ≥ 1.2 s (longer under fades).
   - **Clarity:** comes from the carve and the VO chain, not from a deep duck.
6. **Verify — report numbers; you cannot hear.** `mix` writes `report.json` with:
   - integrated LUFS (match the original, typically −14) and true peak (≤ −1 dBTP after AAC);
   - automation point counts;
   - `swing` on the music-only bounce: p95–p5 ≤ 8 dB, and no change > 4 dB per 0.5 s except
     the `designed_hits` and fades;
   - `vo_over_music`: 8–10 dB per line.

   Also check:
   - **Harmony:** `check_mix.chroma` on the pitched stems per section. The top-4 pitch classes must
     match the plan. A mismatch usually means a long ring-over or an octave/name parse error.
   - **Intelligibility:** whisper on the mix must match the VO-only transcript word for word.
7. **Deliver.** Put `scored/<video>/` next to the video:
   - the scored mp4 and mix wav;
   - `source/`: score script/plan, `.mid`, mix config, stems, the DAW session with its Audio
     Files, and the VO;
   - `check/`.

   Tell the user how the music follows the picture, give the numbers, and list the caveats (e.g.
   no legato transitions, VO isolated from a mix). Finish one video and get the user's ear on it
   before batch-scoring the rest.

## SoundCraft notes

- **Positions:** `{"seconds": x}` is seconds. A bare number is samples.
- **`track.new` kind master:** the requested name is ignored, so use the returned id.
- **MCP tool arguments:** some tools take an argument called `name`. Don't name a client wrapper
  parameter `name`.
- **`mix.mute`** takes `value`.
- **Built-in Sampler:** loads one file per track.
- **`import_midi`:** creates an instrument track.
- **Parameter docs:** `soundcraft-cli describe <id>` lists any command's parameters.
- **GUI app:** running it with `--help` launches the app. For a live view, start it with
  `--control <port>` and use `mcp --connect <port>`.
- **Portable sessions:** use `session.save_copy`, then reopen the copy to verify the audio paths
  resolve.
