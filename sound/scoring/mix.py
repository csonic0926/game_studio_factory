"""Picture-driven mix of full-length printed stems + narration in SoundCraft (headless MCP), then lay it under the video.

    python3 score.py mix --config mix.json

Signal flow (built from scratch every run):
    stems ─▶ <Group>Bus ─▶ aux <Group> (EQ/comp, scene rides) ─┐
    stems ─▶ sends ─▶ HallBus ─▶ aux Hall (reverb, scene rides) ┼▶ MusicBus ─▶ aux Music (VO carve, slow leveler, VO duck) ─▶ main
    narration (EQ, de-ess, comp, small hall send) ─────────────────────────────────────────────────────────────────────────▶ main ─▶ master (glue + maximizer)

Config: see ../examples/score_mix.example.json (schema "score_mix_v1"). Writes into out_dir:
    <name>_mix.wav, <name>_scored.mp4 (video copied, audio replaced), <name>.scraft (+ Audio Files/),
    check/music_only.wav, check/vo_only.wav, report.json (loudness, automation counts, swing, VO ratio).
"""
from __future__ import annotations

import json, os, pathlib, shutil, subprocess

from . import automation as au

GROUP_FX_DEFAULTS = {   # applied when a group names a preset instead of explicit inserts
    "pads":    [("eq_7band", {"hpf_on": 1, "hpf_freq": 45, "low_mid_freq": 300, "low_mid_gain": -2, "high_shelf_freq": 9000, "high_shelf_gain": 1.5}),
                ("compressor", {"threshold": -20, "ratio": 2, "attack": 40, "release": 300})],
    "pulse":   [("eq_7band", {"hpf_on": 1, "hpf_freq": 70, "mid_freq": 2500, "mid_gain": -1.5, "mid_q": 1.0}),
                ("compressor", {"threshold": -18, "ratio": 2.5, "attack": 8, "release": 120})],
    "lead":    [("eq_7band", {"hpf_on": 1, "hpf_freq": 250, "high_mid_freq": 5000, "high_mid_gain": 1.5})],
    "sparkle": [("eq_7band", {"hpf_on": 1, "hpf_freq": 600})],
    "perc":    [("eq_7band", {"hpf_on": 1, "hpf_freq": 30})],
    "bass":    [("eq_7band", {"hpf_on": 1, "hpf_freq": 30, "low_mid_freq": 250, "low_mid_gain": -2}),
                ("compressor", {"threshold": -20, "ratio": 3, "attack": 20, "release": 150})],
    "none":    [],
}
HALL_DEFAULT = {"mix": 100, "pre_delay": 28, "decay": 3.2, "size": 90, "damping": 6500, "diffusion": 88, "width": 100, "low_cut": 200}
VO_CHAIN_DEFAULT = [
    ("eq_7band", {"hpf_on": 1, "hpf_freq": 85, "low_mid_freq": 250, "low_mid_gain": -2, "high_mid_freq": 4000, "high_mid_gain": 2, "high_shelf_freq": 11000, "high_shelf_gain": 1}),
    ("de_esser", {"threshold": -28}),
    ("compressor", {"threshold": -24, "ratio": 3.5, "attack": 6, "release": 110, "makeup": 5}),
]


def find_cli() -> str:
    for c in (os.environ.get("SOUNDCRAFT_CLI"), shutil.which("soundcraft-cli"), os.path.expanduser("~/.local/bin/soundcraft-cli")):
        if c and os.path.exists(c): return c
    raise SystemExit("soundcraft-cli not found: set SOUNDCRAFT_CLI or put it on PATH (github.com/storytold/soundcraft releases)")


class SoundCraft:
    """Minimal MCP stdio client for `soundcraft-cli mcp`, confined to the given read/write roots."""

    def __init__(self, read_roots, write_root):
        args = [find_cli(), "mcp"] + sum([["--automation-read-root", str(r)] for r in sorted(set(map(str, read_roots)))], []) \
            + ["--automation-write-root", str(write_root)]
        self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                                  env={"SOUNDCRAFT_NO_PREFS": "1", "PATH": "/usr/bin:/bin"})
        self._id = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "sound-factory-score", "version": "1"}})
        self._rpc("notifications/initialized", notify=True)

    def _rpc(self, method, params=None, notify=False):
        m = {"jsonrpc": "2.0", "method": method}
        if params is not None: m["params"] = params
        if not notify: self._id += 1; m["id"] = self._id
        self.p.stdin.write(json.dumps(m) + "\n"); self.p.stdin.flush()
        if notify: return None
        while True:
            r = json.loads(self.p.stdout.readline())
            if r.get("id") == self._id: return r

    def tool(self, _tool, **a):   # `_tool`, not `name`: several tools take a `name` argument
        r = self._rpc("tools/call", {"name": _tool, "arguments": a}); res = r.get("result", {})
        text = "".join(c.get("text", "") for c in res.get("content", []))
        if res.get("isError") or "error" in r:
            raise RuntimeError(f"SoundCraft {_tool} {a.get('command', '')} {json.dumps(a.get('params', a))[:240]} → {text or r.get('error')}")
        try: return json.loads(text)
        except ValueError: return text

    def ex(self, command, **params): return self.tool("execute", command=command, params=params)

    def close(self):
        try: self.p.stdin.close(); self.p.wait(timeout=10)
        except Exception: self.p.kill()


def sec(t: float) -> dict:
    return {"seconds": round(max(0.0, float(t)), 3)}   # NB: a bare number is SAMPLES in SoundCraft


def mix(cfg_path: str) -> dict:
    C = json.loads(pathlib.Path(cfg_path).read_text())
    if C.get("schema_version") != "score_mix_v1":
        raise SystemExit("config schema_version must be score_mix_v1")
    out = pathlib.Path(C["out_dir"]).expanduser(); out.mkdir(parents=True, exist_ok=True)
    stems = pathlib.Path(C["stems_dir"]).expanduser(); L = float(C["length"])
    vo = C.get("vo") or {}; vo_path = pathlib.Path(vo["path"]).expanduser() if vo.get("path") else None
    groups: dict = C["groups"]; tracks_cfg: dict = C.get("tracks", {})
    roots = [stems] + ([vo_path.parent] if vo_path else [])
    sc = SoundCraft(roots, out)
    try:
        sc.tool("new_session", name=C["name"], sample_rate=int(C.get("sample_rate", 48000)), template="blank")
        if C.get("bpm"): sc.ex("event.tempo", bpm=C["bpm"])
        members = [m for g in groups.values() for m in g["members"]]
        missing = [m for m in members if not (stems / f"{m}.wav").exists()]
        if missing: raise SystemExit(f"stems missing in {stems}: {missing}")
        for m in members: sc.tool("import_audio", path=str(stems / f"{m}.wav"), at=sec(0))

        sc.ex("mix.new_bus", name="MusicBus"); sc.ex("mix.new_bus", name="HallBus")
        sc.ex("track.new", kind="aux", name="Music", format="stereo"); sc.ex("track.input", tracks=["Music"], input="MusicBus")
        sc.ex("track.new", kind="aux", name="Hall", format="stereo"); sc.ex("track.input", tracks=["Hall"], input="HallBus")
        sc.ex("track.output", tracks=["Hall"], output="MusicBus")
        sc.ex("mix.insert", track="Hall", slot=0, plugin="eq_7band", params={"hpf_on": 1, "hpf_freq": 220, "high_shelf_freq": 8000, "high_shelf_gain": -3})
        sc.ex("mix.insert", track="Hall", slot=1, plugin=C.get("hall", {}).get("plugin", "room_reverb"),
              params={**HALL_DEFAULT, **C.get("hall", {}).get("params", {})})
        for g, gc in groups.items():
            sc.ex("mix.new_bus", name=f"{g}Bus")
            sc.ex("track.new", kind="aux", name=g, format="stereo"); sc.ex("track.input", tracks=[g], input=f"{g}Bus")
            sc.ex("track.output", tracks=[g], output="MusicBus"); sc.ex("track.output", tracks=gc["members"], output=f"{g}Bus")
            inserts = gc.get("inserts") or GROUP_FX_DEFAULTS[gc.get("preset", "none")]
            for slot, (plug, params) in enumerate([tuple(i) if isinstance(i, (list, tuple)) else (i["plugin"], i.get("params", {})) for i in inserts]):
                sc.ex("mix.insert", track=g, slot=slot, plugin=plug, params=params)
            for m in gc["members"]:
                t = tracks_cfg.get(m, {})
                sc.ex("mix.volume", tracks=[m], db=t.get("trim", 0))
                if "pan" in t: sc.ex("mix.pan", tracks=[m], pan=t["pan"])
                if "hall_send" in t: sc.ex("mix.send", track=m, slot=0, bus="HallBus", level_db=t["hall_send"])
        carve = C.get("music_carve_db", -2.5 if vo_path else 0)
        sc.ex("mix.insert", track="Music", slot=0, plugin="eq_7band", params={"hpf_on": 1, "hpf_freq": 30, "mid_freq": 2800, "mid_gain": carve, "mid_q": 0.8})
        sc.ex("mix.insert", track="Music", slot=1, plugin="compressor",   # slow leveler: evens phrase-level swells, keeps attacks
              params={"threshold": -27, "ratio": 2.5, "attack": 80, "release": 600, "knee": 10, "makeup": 3, **C.get("leveler", {})})

        vo_track = None
        if vo_path:
            sc.tool("import_audio", path=str(vo_path), at=sec(0)); vo_track = vo_path.stem
            for slot, (plug, params) in enumerate(VO_CHAIN_DEFAULT if not vo.get("chain") else [(i["plugin"], i.get("params", {})) for i in vo["chain"]]):
                sc.ex("mix.insert", track=vo_track, slot=slot, plugin=plug, params=params)
            if vo.get("hall_send") is not None: sc.ex("mix.send", track=vo_track, slot=0, bus="HallBus", level_db=vo["hall_send"])
            sc.ex("mix.volume", tracks=[vo_track], db=vo.get("db", 0))

        # automation: scene rides on group auxes + Hall, extra rides, then the VO duck on Music
        auto_tracks = list(groups) + ["Hall"]
        pts = au.scene_points(C.get("scenes", []), auto_tracks, C.get("scene_ramp", 1.2))
        for r in C.get("rides", []):
            pts[r["track"]] = au.merge_ride(pts.get(r["track"], []), r["points"])
        pts["Music"] = au.duck_points(vo.get("segments", []) if vo_path else [], L, **C.get("duck", {}))
        n_points = {}
        for tr, ps in pts.items():
            if len(ps) <= 1 and (not ps or ps[0][1] == 0): continue
            for t, v in ps: sc.ex("automation.set_point", track=tr, param="volume", at=sec(t), value=v)
            n_points[tr] = len(ps)

        M = sc.ex("track.new", kind="master", name="Master", format="stereo")["tracks"][0]   # requested name may be ignored
        ms = C.get("master", {})
        sc.ex("mix.insert", track=M, slot=0, plugin="compressor", params={"threshold": -14, "ratio": 1.5, "attack": 30, "release": 200})
        sc.ex("mix.insert", track=M, slot=1, plugin="maximizer",
              params={"threshold": ms.get("maximizer_threshold", -8), "ceiling": ms.get("ceiling", -1.5), "release": 120})

        wav = out / f"{C['name']}_mix.wav"
        r = sc.tool("bounce_mix", path=str(wav), format="wav", bit_depth="24", start=sec(0), end=sec(L))
        sc.tool("save_session", path=str(out / f"{C['name']}.scraft"), replace=True)
        report = {"name": C["name"], "lufs": round(r["lufs"], 2), "true_peak_db": round(r["true_peak_db"], 2), "automation_points": n_points}
        if vo_track and C.get("checks", True):
            (out / "check").mkdir(exist_ok=True)
            sc.ex("mix.mute", tracks=[vo_track], value=True)
            sc.tool("bounce_mix", path=str(out / "check" / "music_only.wav"), format="wav", bit_depth="24", start=sec(0), end=sec(L))
            sc.ex("mix.mute", tracks=[vo_track], value=False); sc.ex("mix.mute", tracks=["Music"], value=True)
            sc.tool("bounce_mix", path=str(out / "check" / "vo_only.wav"), format="wav", bit_depth="24", start=sec(0), end=sec(L))
            sc.ex("mix.mute", tracks=["Music"], value=False)
    finally:
        sc.close()

    if C.get("video"):
        mp4 = out / f"{C['name']}_scored.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pathlib.Path(C["video"]).expanduser()), "-i", str(wav),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(mp4)], check=True)
        report["video"] = str(mp4)
    if vo_track and C.get("checks", True):
        from . import check_mix
        report["swing"] = check_mix.swing(str(out / "check" / "music_only.wav"), designed=C.get("designed_hits", []))
        report["vo_over_music"] = check_mix.vo_ratio(str(out / "check" / "music_only.wav"), str(out / "check" / "vo_only.wav"), vo["segments"])
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    return report
