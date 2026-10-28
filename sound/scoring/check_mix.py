"""Objective checks for a scored mix (numpy + ffmpeg). The mixer cannot listen; these numbers can.

swing(music_only.wav)           — felt level movement of the music bed (1 s sliding RMS every 0.25 s)
vo_ratio(music, vo, segments)   — narration level over the music, speech-active frames only
chroma(wavs, sections)          — top pitch classes per section vs the intended chord

Targets that a USER verified on 2026-10-28 (see docs/SCORING_WORKFLOW.md):
  swing p95-p5 <= 8 dB; no change > 4 dB per 0.5 s except designed hits/fades; VO over music 8-10 dB.
"""
from __future__ import annotations

import subprocess
from typing import Sequence

import numpy as np

SR = 48000
NAMES = "C C# D D# E F F# G G# A A# B".split()


def load(path: str, highpass: float | None = None, sr: int = SR) -> np.ndarray:
    af = ["-af", f"highpass=f={highpass}"] if highpass else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), *af, "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def _db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9))


def swing(music_wav: str, designed: Sequence[float] = (), tolerance: float = 0.75) -> dict:
    x = load(music_wav)
    ts = np.arange(0, max(0.0, len(x) / SR - 1.0), 0.25)
    e = np.array([_db(x[int(t * SR): int((t + 1) * SR)]) for t in ts])
    if len(e) < 3:
        return {"error": "too short"}
    ch = [(float(ts[i]), float(e[i + 2] - e[i])) for i in range(len(e) - 2)]
    big = [(t, round(d, 1)) for t, d in ch if abs(d) > 4]
    undesigned = [(t, d) for t, d in big if not any(abs(t + 0.5 - h) <= tolerance + 0.5 for h in designed)]
    return {"range_p95_p5_db": round(float(np.percentile(e, 95) - np.percentile(e, 5)), 1),
            "max_rise_db_per_0p5s": round(max(d for _, d in ch), 1),
            "max_fall_db_per_0p5s": round(min(d for _, d in ch), 1),
            "changes_over_4db": big, "undesigned_changes_over_4db": undesigned}


def vo_ratio(music_wav: str, vo_wav: str, segments: Sequence[Sequence[float]]) -> list:
    m = load(music_wav, highpass=60); v = load(vo_wav, highpass=60); ref = _db(v)
    w = int(0.05 * SR); out = []
    for s in segments:
        a, b = float(s[0]), float(s[1])
        frames = [v[i:i + w] for i in range(int(a * SR), int(b * SR) - w, w)]
        speech = [f for f in frames if _db(f) > ref - 12]
        if not speech: continue
        out.append({"start": a, "end": b, "vo_over_music_db": round(_db(np.concatenate(speech)) - _db(m[int(a * SR):int(b * SR)]), 1)})
    return out


def chroma(wavs: Sequence[str], sections: Sequence[dict], sr: int = 22050) -> list:
    """sections: [{"label", "start", "end", "chord": ["D","F#","A"]}]. Stems are RMS-equalised first so
    one loud part does not decide the answer. Pass pitched stems only."""
    x = None
    for p in wavs:
        y = load(p, sr=sr); y = y / (np.sqrt(np.mean(y ** 2)) + 1e-9)
        x = y if x is None else x[:len(y)] + y[:len(x)]
    res = []
    for s in sections:
        seg = x[int(s["start"] * sr): int(s["end"] * sr)]; n = 8192; c = np.zeros(12)
        for i in range(0, max(0, len(seg) - n), n // 4):
            f = np.abs(np.fft.rfft(seg[i:i + n] * np.hanning(n))); fr = np.fft.rfftfreq(n, 1 / sr); k = (fr > 60) & (fr < 2000)
            np.add.at(c, np.round(69 + 12 * np.log2(fr[k] / 440)).astype(int) % 12, f[k] ** 2)
        top = [NAMES[i] for i in np.argsort(c)[::-1][:4]]
        res.append({"label": s.get("label"), "chord": s["chord"], "top4": top, "in_chord": sum(t in s["chord"] for t in top)})
    return res
