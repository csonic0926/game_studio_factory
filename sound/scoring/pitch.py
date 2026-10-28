"""Pitch check for sample files: YIN (sustained tones) + FFT peaks (bells, glock, chimes).

Use it to (a) verify a sample library's octave naming before rendering, and (b) root/fine-tune
ElevenLabs single-note generations (the model often ignores the requested note but holds pitch well).

    python3 score.py pitch file.wav [...]          # YIN + FFT, flags disagreement
Output: one JSON object per file.
"""
from __future__ import annotations

import json, re, subprocess
import numpy as np

SR = 44100
NAMES = "C C# D D# E F F# G G# A A# B".split()
_NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
         "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def load(path: str) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def name(midi: float) -> str:
    n = int(round(midi)); return f"{NAMES[n % 12]}{n // 12 - 1}"


def hz_to_midi(hz: float) -> float:
    return 69 + 12 * np.log2(hz / 440)


def yin(frame: np.ndarray, fmin=35, fmax=2200, thr=0.15):
    n = len(frame); tmax = min(SR // fmin, n // 2); tmin = SR // fmax
    d = np.array([np.sum((frame[:n - tmax] - frame[t:t + n - tmax]) ** 2) for t in range(tmax)])
    cm = np.ones_like(d); cs = np.cumsum(d[1:]); cm[1:] = d[1:] * np.arange(1, tmax) / np.maximum(cs, 1e-12)
    for t in range(tmin, tmax - 1):
        if cm[t] < thr and cm[t] <= cm[t + 1]:
            a, b, c = cm[t - 1], cm[t], cm[t + 1]; den = a - 2 * b + c
            return SR / (t + (0.5 * (a - c) / den if den else 0))
    return None


def yin_track(x: np.ndarray):
    rms = np.sqrt(np.convolve(x ** 2, np.ones(1024) / 1024, "same")); peak = rms.max()
    f0s = []
    for i in range(0, len(x) - 4096, int(0.05 * SR)):
        if rms[i + 2048] < peak * 0.1: continue
        f = yin(x[i:i + 4096])
        if f: f0s.append(f)
    if not f0s: return None
    m = hz_to_midi(np.array(f0s)); med = float(np.median(m))
    return {"midi": int(round(med)), "note": name(med), "cents": round((med - round(med)) * 100),
            "spread_cents": round(float(np.percentile(m, 90) - np.percentile(m, 10)) * 100)}


def fft_peaks(x: np.ndarray, k: int = 3, fmin: float = 60):
    """Strongest distinct spectral peaks just after the attack. For bells, the lowest strong peak is
    usually the perceived pitch; YIN can lock an octave below it."""
    i = int(np.argmax(np.abs(x))); seg = x[i + int(0.05 * SR): i + int(0.05 * SR) + 32768]
    if len(seg) < 4096: seg = x[-32768:]
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1 / SR)
    m = fr > fmin; order = fr[m][np.argsort(sp[m])[::-1]]
    peaks: list = []
    for f in order:
        if all(abs(f - q) > max(20, q * 0.03) for q in peaks): peaks.append(float(f))
        if len(peaks) == k: break
    low = min(peaks) if peaks else None
    return {"peaks_hz": [round(f, 1) for f in peaks],
            "lowest_strong": None if low is None else {"hz": round(low, 1), "note": name(hz_to_midi(low)),
                                                       "midi": int(round(hz_to_midi(low)))}}


def named_note(filename: str):
    m = re.search(r"(?:^|[_\-\s])([A-G][#b]?)(-?\d)(?=[_\-.\s])", filename)
    return None if not m else 12 * (int(m.group(2)) + 1) + _NOTE[m.group(1)]


def check(path: str) -> dict:
    x = load(path); y = yin_track(x); f = fft_peaks(x)
    out = {"file": path.split("/")[-1], "yin": y, "fft": f}
    nn = named_note(out["file"])
    if nn is not None:
        out["named"] = name(nn)
        if y: out["offset_yin"] = y["midi"] - nn
        if f["lowest_strong"]: out["offset_fft"] = f["lowest_strong"]["midi"] - nn
    if y and f["lowest_strong"] and abs(y["midi"] - f["lowest_strong"]["midi"]) >= 11:
        out["warning"] = "YIN and FFT disagree by an octave — bell-like timbre? trust FFT's lowest strong peak, confirm by ear"
    return out


def main(paths) -> int:
    for p in paths: print(json.dumps(check(p), ensure_ascii=False))
    return 0
