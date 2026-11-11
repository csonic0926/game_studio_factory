"""Run the existing core and UI regression suites without starting any engine."""
from pathlib import Path
import importlib
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def leaves(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite):
            yield from leaves(case)
        else:
            yield case


if __name__ == "__main__":
    loader = unittest.TestLoader()
    cases = []
    for department in ("factory_core", "ui"):
        for path in sorted((ROOT / department / "tests").glob("test_*.py")):
            module = importlib.import_module(f"{department}.tests.{path.stem}")
            cases.extend(leaves(loader.loadTestsFromModule(module)))
    excluded = {"test_authorized_production_runs_real_godot_ui_state_and_regression",
                "test_native_godot_ui_state_and_repeated_regression", "test_real_render_export_and_seal"}
    selected = [case for case in cases if case.id().split(".")[-1] not in excluded]
    print(f"Running {len(selected)} core/UI tests; intentionally excluding {len(cases)-len(selected)} engine-launch cases", flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
    raise SystemExit(not result.wasSuccessful())
