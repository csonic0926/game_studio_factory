"""Analyse a video for scoring: contact sheet, luma/motion timeline, change candidates, narration.

    python3 score.py analyze --video in.mp4 --out work/analysis [--whisper-model small] [--no-asr]

Writes: contact_sheet.png (look at it), timeline.csv (t, luma, diff at 8 fps), candidates.json
(ranked visual changes — fades included, which ffmpeg's scene filter misses), audio.wav (16 kHz mono),
asr.json (word timestamps, if a `whisper` CLI is on PATH), report.json (summary).
A change candidate is a hint, not a cut: confirm on the contact sheet.
"""
from __future__ import annotations

import csv, json, math, pathlib, shutil, subprocess

import numpy as np


def _run(args, **kw):
    return subprocess.run(args, check=True, capture_output=True, **kw)


def analyze(video: str, out: str, whisper_model: str = "small", asr: bool = True, fps: int = 8) -> dict:
    out_p = pathlib.Path(out); out_p.mkdir(parents=True, exist_ok=True)
    probe = json.loads(_run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", video]).stdout)
    dur = float(probe["format"]["duration"])
    has_audio = any(s.get("codec_type") == "audio" for s in probe["streams"])

    # contact sheet: ~24 tiles
    step = max(0.5, dur / 24); cols = 6; rows = math.ceil(dur / step / cols)
    _run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps=1/{step:.3f},scale=320:-1,tile={cols}x{rows}",
          "-frames:v", "1", str(out_p / "contact_sheet.png")])

    # luma + frame-difference timeline
    raw = _run(["ffmpeg", "-v", "error", "-i", video, "-an", "-vf", f"fps={fps},scale=64:36,format=gray",
                "-f", "rawvideo", "-"]).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.float32)
    lum = f.mean((1, 2)); diff = np.zeros(len(f)); diff[1:] = np.abs(np.diff(f, axis=0)).mean((1, 2))
    with open(out_p / "timeline.csv", "w", newline="") as h:
        w = csv.writer(h); w.writerow(["t", "luma", "diff"])
        for i in range(len(f)): w.writerow([round(i / fps, 3), round(float(lum[i]), 2), round(float(diff[i]), 2)])
    cands, taken = [], []
    for i in np.argsort(diff)[::-1]:
        if diff[i] < max(3.0, float(np.percentile(diff, 90))): break
        if all(abs(i - j) / fps >= 0.6 for j in taken):
            taken.append(int(i)); cands.append({"t": round(i / fps, 2), "diff": round(float(diff[i]), 1),
                                                "luma_before": round(float(lum[max(0, i - 2)]), 1), "luma_after": round(float(lum[min(len(lum) - 1, i + 2)]), 1)})
        if len(cands) >= 24: break
    cands.sort(key=lambda c: c["t"])
    (out_p / "candidates.json").write_text(json.dumps(cands, indent=1))

    report = {"video": video, "duration_s": round(dur, 3), "has_audio": has_audio, "change_candidates": len(cands)}
    if has_audio:
        _run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", str(out_p / "audio.wav")])
        lufs = subprocess.run(["ffmpeg", "-nostats", "-i", video, "-vn", "-af", "ebur128", "-f", "null", "-"],
                              capture_output=True, text=True).stderr
        report["original_integrated_lufs"] = next((l.split("I:")[1].strip() for l in reversed(lufs.splitlines()) if "I:" in l), None)
        wh = shutil.which("whisper")
        if asr and wh:
            subprocess.run([wh, str(out_p / "audio.wav"), "--model", whisper_model, "--word_timestamps", "True",
                            "--output_format", "json", "--output_dir", str(out_p), "--fp16", "False"],
                           capture_output=True)
            j = out_p / "audio.json"
            if j.exists():
                d = json.loads(j.read_text()); j.rename(out_p / "asr.json")
                segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip(),
                         "no_speech_prob": round(s.get("no_speech_prob", 0), 2)} for s in d.get("segments", [])]
                report["asr_segments"] = segs
                report["narration_likely"] = sum(1 for s in segs if s["no_speech_prob"] < 0.5 and len(s["text"].split()) >= 3) >= 2
        elif asr:
            report["asr"] = "skipped: no `whisper` CLI on PATH — install one or transcribe another way"
    (out_p / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    return report
