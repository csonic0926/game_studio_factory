#!/usr/bin/env python3
"""game_sound_factory — video scoring CLI (music for promo / trailer / cutscene video).

Workflow and role guidance: docs/SCORING_WORKFLOW.md. Needs numpy + ffmpeg; `mix` needs soundcraft-cli.

Commands:
  analyze   contact sheet, luma/motion timeline, change candidates, narration ASR
  isolate   pull narration off a finished mix (ElevenLabs Voice Isolator — paid, ask first)
  pitch     verify sample pitch / octave naming (YIN + FFT)
  mix       picture-driven SoundCraft mix of printed stems + narration → mix wav + scored video + report
  check     re-run swing / VO-ratio checks on existing bounces

Examples:
  python3 score.py analyze --video in.mp4 --out work/analysis
  python3 score.py pitch ~/Music/SampleLibraries/VCSL/.../glock_medium_C5_01.wav
  python3 score.py mix --config examples/score_mix.example.json
"""
from __future__ import annotations

import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser(prog="score.py", description="game_sound_factory video scoring")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("--video", required=True); a.add_argument("--out", required=True)
    a.add_argument("--whisper-model", default="small"); a.add_argument("--no-asr", action="store_true")
    i = sub.add_parser("isolate"); i.add_argument("--in", dest="inp", required=True); i.add_argument("--out", required=True)
    p = sub.add_parser("pitch"); p.add_argument("files", nargs="+")
    m = sub.add_parser("mix"); m.add_argument("--config", required=True)
    c = sub.add_parser("check"); c.add_argument("--music", required=True); c.add_argument("--vo")
    c.add_argument("--segments", help='JSON list, e.g. "[[0,3.4],[9.06,11.84]]"'); c.add_argument("--designed", default="[]")
    args = ap.parse_args()

    if args.cmd == "analyze":
        from scoring import analyze_video
        print(json.dumps(analyze_video.analyze(args.video, args.out, args.whisper_model, not args.no_asr), indent=1, ensure_ascii=False))
    elif args.cmd == "isolate":
        from scoring import isolate_voice
        print(f"wrote {args.out} ({isolate_voice.isolate(args.inp, args.out)} bytes)")
    elif args.cmd == "pitch":
        from scoring import pitch
        return pitch.main(args.files)
    elif args.cmd == "mix":
        from scoring import mix
        print(json.dumps(mix.mix(args.config), indent=1, ensure_ascii=False))
    elif args.cmd == "check":
        from scoring import check_mix
        r = {"swing": check_mix.swing(args.music, designed=json.loads(args.designed))}
        if args.vo and args.segments: r["vo_over_music"] = check_mix.vo_ratio(args.music, args.vo, json.loads(args.segments))
        print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
