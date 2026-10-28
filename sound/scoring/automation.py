"""Pure automation builders for picture-driven music mixes (stdlib only, unit-tested).

Two layers, applied to different aux tracks so they stack:
  * scene rides  — per group (and the reverb return) a small dB offset per picture section;
  * VO duck      — on the outer Music aux, a shallow, slow dip under narration.

Defaults encode a USER-verified lesson (2026-10-28, Fair promo): fast/deep ducking and big scene
moves read as "大細聲落差變化太急" (pumping). Keep moves shallow and slow; hold through short breaths.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

Point = Tuple[float, float]

DUCK_DEFAULTS = {
    "base_db": -3.0,      # music level between lines (relative to fader)
    "depth_db": -4.0,     # extra dip while narration speaks
    "attack": 0.8,        # seconds to reach the dip before a line
    "release": 1.8,       # seconds to come back after a line
    "hold_gap": 1.5,      # gaps shorter than this stay ducked
    "half_gap": 2.5,      # gaps shorter than this only come back halfway
    "end_fade": 1.5,      # final fade length (0 = none)
    "end_fade_db": -30.0,
}


def _clean(points: Iterable[Point]) -> List[Point]:
    """Sort, clamp to t >= 0, round, and drop exact duplicates (last value wins per time)."""
    by_t: Dict[float, float] = {}
    for t, v in sorted(points, key=lambda p: p[0]):
        by_t[round(max(0.0, t), 3)] = round(v, 2)
    return sorted(by_t.items())


def scene_points(scenes: Sequence[dict], tracks: Sequence[str], default_ramp: float = 1.2) -> Dict[str, List[Point]]:
    """scenes: [{"t": end_time, "values": {track: dB}, "ramp": seconds?}, ...] in time order.

    Each scene's values are REACHED at its `t`, ramping from the previous scene's value over `ramp`
    seconds. Missing tracks count as 0 dB. The first scene sets the starting values at t=0.
    """
    out: Dict[str, List[Point]] = {tr: [] for tr in tracks}
    if not scenes:
        return out
    prev = {tr: float(scenes[0].get("values", {}).get(tr, 0.0)) for tr in tracks}
    for tr in tracks:
        out[tr].append((0.0, prev[tr]))
    for sc in scenes[1:]:
        t = float(sc["t"]); ramp = float(sc.get("ramp", default_ramp))
        for tr in tracks:
            v = float(sc.get("values", {}).get(tr, 0.0))
            if v != prev[tr]:
                out[tr] += [(t - ramp, prev[tr]), (t, v)]
            prev[tr] = v
    return {tr: _clean(p) for tr, p in out.items()}


def duck_points(segments: Sequence[Sequence[float]], length: float, **kw) -> List[Point]:
    """segments: [[start, end], [start, end, extra_db], ...] narration spans (seconds).

    Returns Music-aux volume points: base between lines, base+depth(+extra) under lines,
    no release across gaps < hold_gap, half release across gaps < half_gap.
    """
    p = dict(DUCK_DEFAULTS); p.update({k: v for k, v in kw.items() if v is not None})
    base, depth = float(p["base_db"]), float(p["depth_db"])
    segs = sorted((float(s[0]), float(s[1]), float(s[2]) if len(s) > 2 else 0.0) for s in segments)
    if not segs:
        pts = [(0.0, base)]
    else:
        a0, _, e0 = segs[0]
        lvl0 = base + depth + e0
        pts = [(0.0, lvl0)] if a0 <= p["attack"] else [(0.0, base), (a0 - p["attack"], base), (a0 - 0.05, lvl0)]
        for i in range(1, len(segs)):
            a, b, extra = segs[i]
            pa, pb, pe = segs[i - 1]
            lvl, plvl, gap = base + depth + extra, base + depth + pe, a - pb
            if gap < p["hold_gap"]:
                pts += [(a - 0.3, plvl), (a, lvl)]
                continue
            lift = base if gap >= p["half_gap"] else base + depth / 2
            up = min(p["release"], gap * 0.45); down = min(p["attack"], gap * 0.35)
            pts += [(pb + 0.15, plvl), (pb + 0.15 + up, lift), (a - down, lift), (a - 0.05, lvl)]
        lb, le = segs[-1][1], base + depth + segs[-1][2]
        pts += [(lb + 0.15, le), (min(length, lb + 0.15 + p["release"]), base)]
    if p["end_fade"] and p["end_fade"] > 0:
        pts += [(length - p["end_fade"], base), (length, p["end_fade_db"])]
    return _clean(pts)


def merge_ride(base_points: List[Point], ride: Sequence[Sequence[float]]) -> List[Point]:
    """Overlay explicit [t, dB] ride points (e.g. fold an ostinato in under a fade-up)."""
    return _clean(list(base_points) + [(float(t), float(v)) for t, v in ride])
