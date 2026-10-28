import os
import sys
import unittest

SOUND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sound")
sys.path.insert(0, SOUND)

from scoring import automation as au  # noqa: E402  (stdlib only)

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


def value_at(points, t):
    """Linear interpolation between automation points (how a DAW reads them)."""
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if t0 <= t <= t1:
            return v0 if t1 == t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return points[-1][1]


class ScenePointsTest(unittest.TestCase):
    def test_values_are_reached_at_scene_time_after_ramp(self):
        scenes = [{"t": 0, "values": {"Pads": -1}}, {"t": 5.0, "values": {"Pads": 1}, "ramp": 2.0}]
        pts = au.scene_points(scenes, ["Pads", "Hall"])
        self.assertEqual(value_at(pts["Pads"], 0.0), -1)
        self.assertEqual(value_at(pts["Pads"], 3.0), -1)       # ramp starts at t - ramp
        self.assertAlmostEqual(value_at(pts["Pads"], 4.0), 0.0)
        self.assertEqual(value_at(pts["Pads"], 5.0), 1)
        self.assertEqual(pts["Hall"], [(0.0, 0.0)])             # missing track = 0 dB, no moves

    def test_unchanged_values_add_no_points(self):
        scenes = [{"t": 0, "values": {"A": 2}}, {"t": 4, "values": {"A": 2}}, {"t": 8, "values": {"A": 2}}]
        self.assertEqual(au.scene_points(scenes, ["A"])["A"], [(0.0, 2.0)])


class DuckPointsTest(unittest.TestCase):
    def test_shallow_dip_under_lines_and_base_between(self):
        pts = au.duck_points([[2, 4], [10, 12]], 20)
        self.assertEqual(value_at(pts, 0.5), -3)                # base before first line
        self.assertEqual(value_at(pts, 3.0), -7)                # base + depth under a line
        self.assertEqual(value_at(pts, 7.0), -3)                # long gap: fully back
        self.assertEqual(value_at(pts, 11.0), -7)
        self.assertEqual(pts[-1], (20.0, -30.0))                # end fade

    def test_short_breath_stays_ducked(self):
        pts = au.duck_points([[0, 3.0], [4.0, 6.0]], 10, end_fade=0)   # 1.0 s gap < hold_gap
        self.assertTrue(all(v <= -7 for t, v in pts if 3.0 <= t <= 4.0))
        self.assertEqual(value_at(pts, 3.5), -7)

    def test_medium_gap_only_comes_back_halfway(self):
        pts = au.duck_points([[0, 3.0], [5.0, 7.0]], 12, end_fade=0)   # 2.0 s gap
        self.assertGreaterEqual(min(v for t, v in pts if 3.0 < t < 5.0), -7)
        self.assertEqual(max(v for t, v in pts if 3.0 < t < 5.0), -5)  # base + depth/2

    def test_extra_db_per_segment(self):
        pts = au.duck_points([[2, 4, -1]], 10, end_fade=0)
        self.assertEqual(value_at(pts, 3.0), -8)

    def test_moves_are_never_faster_than_attack_and_release_allow(self):
        pts = au.duck_points([[2, 4], [10, 12]], 20, end_fade=0)
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t1 > t0 and v1 > v0:                              # coming back up
                self.assertLessEqual((v1 - v0) / (t1 - t0), 4 / 1.8 + 1e-6)


class MergeRideTest(unittest.TestCase):
    def test_ride_points_override_same_time(self):
        merged = au.merge_ride([(0.0, 0.0), (5.0, -1.0)], [[3.0, -6], [5.0, 0]])
        self.assertEqual(merged, [(0.0, 0.0), (3.0, -6.0), (5.0, 0.0)])


@unittest.skipUnless(HAVE_NUMPY, "numpy not installed")
class NoteParsingTest(unittest.TestCase):
    def test_parse_note_and_velocity_from_library_file_names(self):
        from scoring import srender
        self.assertEqual(srender.parse_note("VlnEns_susVib_A2_v1.wav"), 45)
        self.assertEqual(srender.parse_note("KSHarp_D#4_mf.wav"), 63)
        self.assertEqual(srender.parse_note("GPiano_sus_A#-1_v2_rr1_Player.wav"), 10)
        self.assertIsNone(srender.parse_note("susCymb1_cresc_7.5s.wav"))
        self.assertEqual(srender.parse_vel("VlnEns_Spic_A2_v2_rr1.wav"), 2)
        self.assertEqual(srender.parse_vel("glock_loud_C5_01.wav"), 7)

    def test_octave_offset_lookup(self):
        from scoring import srender
        self.assertEqual(srender._offset_for("VCSL/Idiophones/Struck Idiophones/Glockenspiel"), 12)
        self.assertEqual(srender._offset_for("VSCO-2-CE/Strings/Harp"), 0)
        self.assertEqual(srender._offset_for("Some/Unknown/Library"), 0)


if __name__ == "__main__":
    unittest.main()
