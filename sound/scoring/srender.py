"""srender — tiny multisample renderer for note-named raw-WAV sample libraries.

Library root: $SAMPLE_LIBRARY_ROOT, default ~/Music/SampleLibraries (keep a MANIFEST.md there;
see ../docs/SCORING_WORKFLOW.md). Needs numpy + ffmpeg.

The VSCO-2-CE / VCSL repos ship WAVs with the note in the file name (KSHarp_D4_mf.wav,
VlnEns_susVib_A2_v1.wav) and no SFZ, so this maps them itself:
  nearest sampled pitch → resample to the target pitch, velocity → layer, random round-robin.

Library use:
    from srender import Instrument, render_part, write_wav
    harp = Instrument("VSCO-2-CE/Strings/Harp", oneshot=True)
    audio = render_part(harp, [(t_sec, dur_sec, midi, vel), ...], length_sec)
    write_wav("harp.wav", audio)
"""
from __future__ import annotations

import os, pathlib, random, re, subprocess
import numpy as np

ROOT = pathlib.Path(os.environ.get("SAMPLE_LIBRARY_ROOT", "~/Music/SampleLibraries")).expanduser()
SR = 44100
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
        "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
NOTE_RE = re.compile(r"(?:^|[_\-\s])([A-G][#b]?)(-?\d)(?=[_\-.\s])")
WORD_VEL = {"ppp": 1, "pp": 2, "p": 3, "soft": 3, "quiet": 3, "mp": 4, "medium": 5, "mf": 5, "med": 5,
            "f": 6, "loud": 7, "ff": 7, "fff": 8}
_cache: dict[str, np.ndarray] = {}


def load(path: pathlib.Path) -> np.ndarray:
    key = str(path)
    if key not in _cache:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", key, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        _cache[key] = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
    return _cache[key]


def parse_note(name: str) -> int | None:
    m = NOTE_RE.search(name)
    if not m: return None
    return 12 * (int(m.group(2)) + 1) + NOTE[m.group(1)]


def parse_vel(name: str) -> int:
    m = re.search(r"_(?:v|vl|dyn)(\d)(?=[_.])", name)
    if m: return int(m.group(1))
    for tok in re.split(r"[_\-.\s]", name.lower()):
        if tok in WORD_VEL: return WORD_VEL[tok]
    return 5


# Octave offset between the note written in the file name and the sounding pitch.
# Measured 2026-10-28 on VSCO-2-CE / VCSL with scoring/pitch.py (YIN for sustained tones, FFT peaks
# for bells) — most folders name middle C "C3". STARTING POINT ONLY: re-verify on every machine /
# library revision (`python3 score.py pitch --fft <wav>`) before trusting a render. Pass
# Instrument(..., offset=N) to override.
OCTAVE_OFFSET = {
    "VSCO-2-CE/Strings/Violin Section": 12, "VSCO-2-CE/Strings/Viola Section": 12,
    "VSCO-2-CE/Strings/Cello Section": 12, "VSCO-2-CE/Brass/F Horn": 12, "VSCO-2-CE/Woodwinds/Flute": 12,
    "VCSL/Chordophones/Zithers/Grand Piano, Kawai": 12, "VCSL/Idiophones/Struck Idiophones/Vibraphone": 12,
    "VCSL/Idiophones/Struck Idiophones/Hand Chimes": 12,
    "VCSL/Idiophones/Struck Idiophones/Glockenspiel": 12,  # FFT fundamental, 2026-10-28 (YIN locked an octave low)
    "VSCO-2-CE/Strings/Harp": 0,
}  # VSCO-2-CE/Percussion/Glock: pitch detection unreliable (inharmonic) — not mapped, avoid
# Bells/glock: verify with FFT peaks, not YIN alone.


def _offset_for(folder: str) -> int:
    for k, v in OCTAVE_OFFSET.items():
        if folder.startswith(k): return v
    return 0


class Instrument:
    """A folder of note-named WAVs (recursive). `include`/`exclude`: substrings of the file name.
    Release-noise samples (`_rel_`, e.g. Kawai Releases/) are excluded by default — they are not pitched notes."""

    def __init__(self, folder: str, include: str | None = None, exclude: tuple[str, ...] = ("_rel_",),
                 oneshot: bool = False, attack: float = 0.005, release: float = 0.25,
                 max_len: float = 12.0, gain_db: float = 0.0, vel_curve: float = 1.6,
                 pitch: int | None = None, start: float = 0.0, offset: int | None = None):
        self.samples: list[tuple[int, int, pathlib.Path]] = []
        for p in sorted((ROOT / folder).rglob("*.wav")):
            n = p.name
            if include and include.lower() not in n.lower(): continue
            if any(x.lower() in n.lower() for x in exclude): continue
            note = pitch if pitch is not None else parse_note(n)
            if note is None: continue
            if pitch is None: note += offset if offset is not None else _offset_for(folder)
            self.samples.append((note, parse_vel(n), p))
        if not self.samples:
            raise ValueError(f"no samples in {folder} (include={include})")
        self.oneshot, self.attack, self.release, self.max_len = oneshot, attack, release, max_len
        self.gain = 10 ** (gain_db / 20); self.vel_curve = vel_curve; self.start = start
        self.notes = sorted({s[0] for s in self.samples})

    def pick(self, midi: int, vel: int) -> tuple[pathlib.Path, int]:
        near = min(self.notes, key=lambda n: (abs(n - midi), n > midi))  # tie → sample below (resample up)
        cands = [s for s in self.samples if s[0] == near]
        layers = sorted({s[1] for s in cands})
        layer = layers[min(len(layers) - 1, int(vel / 128 * len(layers)))]
        return random.choice([s[2] for s in cands if s[1] == layer]), near

    def voice(self, midi: int, dur: float, vel: int) -> np.ndarray:
        path, root = self.pick(midi, vel)
        x = load(path)
        x = x[int(self.start * SR):]
        ratio = 2 ** ((midi - root) / 12)
        need = int(SR * min(self.max_len, (dur + self.release) if not self.oneshot else self.max_len) * ratio) + 2
        x = x[:need]
        if ratio != 1.0:
            src = np.arange(len(x)); dst = np.arange(0, len(x) - 1, ratio)
            x = np.stack([np.interp(dst, src, x[:, c]) for c in (0, 1)], axis=1)
        n = len(x)
        env = np.ones(n, dtype=np.float32)
        a = min(n, int(self.attack * SR)); env[:a] = np.linspace(0, 1, a, endpoint=False) if a else env[:a]
        if not self.oneshot:
            off = int(dur * SR); r = int(self.release * SR)
            if off < n:
                tail = env[off:off + r]; env[off:off + r] = tail * np.linspace(1, 0, len(tail))
                env[off + r:] = 0
        fade = min(n, int(0.02 * SR)); env[n - fade:] *= np.linspace(1, 0, fade)
        amp = self.gain * (vel / 127) ** self.vel_curve
        return (x * env[:, None] * amp).astype(np.float32)


def render_part(inst: Instrument, events, length: float, seed: int = 1) -> np.ndarray:
    """events: iterable of (start_sec, dur_sec, midi, vel)."""
    random.seed(seed)
    out = np.zeros((int(length * SR) + SR, 2), dtype=np.float32)
    for t, d, m, v in events:
        y = inst.voice(int(m), float(d), int(v))
        i = int(t * SR)
        if i >= len(out): continue
        j = min(len(out), i + len(y)); out[i:j] += y[:j - i]
    return out[:int(length * SR)]


def write_wav(path, audio: np.ndarray):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(path)], input=audio.astype(np.float32).tobytes(), check=True)
