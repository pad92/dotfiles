#!/usr/bin/env python3
"""Check how run_unit_tests.py splits, orders and sizes the test run."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).with_name("run_unit_tests.py")
SPEC = importlib.util.spec_from_file_location("run_unit_tests", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT_PATH}")
RUNNER = importlib.util.module_from_spec(SPEC)
# Dataclasses look their module up in sys.modules while it executes.
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)

MIB = 1024 * 1024


class PlanUnitsTests(unittest.TestCase):
    def plan(self, ids, durations):
        return [(unit.name, unit.tests) for unit in RUNNER.plan_units(ids, durations)]

    def test_slow_tests_run_alone_longest_first_and_fast_ones_share_a_process(self):
        durations = {
            "test_a.A.test_fast": 0.1,
            "test_a.A.test_slow": 30.0,
            "test_a.B.test_fast": 0.2,
            "test_b.C.test_slower": 90.0,
            "test_b.C.test_fast": 0.1,
        }
        self.assertEqual(
            self.plan(sorted(durations), durations),
            [
                ("test_b.C.test_slower", ["test_b.C.test_slower"]),
                ("test_a.A.test_slow", ["test_a.A.test_slow"]),
                ("test_a", ["test_a.A.test_fast", "test_a.B.test_fast"]),
                ("test_b", ["test_b.C.test_fast"]),
            ],
        )

    def test_unknown_tests_run_first_one_process_per_class(self):
        durations = {"test_a.A.test_slow": 300.0}
        ids = ["test_a.A.test_slow", "test_b.New.test_one", "test_b.New.test_two"]
        self.assertEqual(
            self.plan(ids, durations),
            [
                ("test_b.New", ["test_b.New.test_one", "test_b.New.test_two"]),
                ("test_a.A.test_slow", ["test_a.A.test_slow"]),
            ],
        )

    def test_every_test_is_planned_exactly_once(self):
        ids = [f"test_m{i % 3}.C{i % 2}.test_{i}" for i in range(20)]
        durations = {test: float(i % 5) for i, test in enumerate(ids[:15])}
        planned = [
            test for unit in RUNNER.plan_units(ids, durations) for test in unit.tests
        ]
        self.assertCountEqual(planned, ids)


class DefaultJobsTests(unittest.TestCase):
    def jobs(self, cpus, limits):
        with (
            mock.patch.object(RUNNER.os, "process_cpu_count", return_value=cpus),
            mock.patch.object(RUNNER, "cgroup_values", side_effect=limits.get),
        ):
            return RUNNER.default_jobs()

    def test_uses_every_cpu_without_container_limits(self):
        self.assertEqual(self.jobs(16, {}), 16)

    def test_memory_limit_caps_the_workers(self):
        self.assertEqual(self.jobs(32, {"memory.max": [4096 * MIB]}), 13)

    def test_cpu_quota_caps_the_workers(self):
        self.assertEqual(self.jobs(32, {"cpu.max": [400000, 100000]}), 4)

    def test_tiny_limits_still_leave_one_worker(self):
        limits = {"cpu.max": [50000, 100000], "memory.max": [100 * MIB]}
        self.assertEqual(self.jobs(8, limits), 1)


class DurationsFileTests(unittest.TestCase):
    def test_missing_or_corrupt_history_is_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary, "durations.json")
            self.assertEqual(RUNNER.load_durations(path), {})
            path.write_text("{not json")
            with mock.patch.object(sys, "stderr"):
                self.assertEqual(RUNNER.load_durations(path), {})

    def test_history_round_trips(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary, "cache/durations.json")
            RUNNER.save_durations(path, {"test_b.T.test": 2.5, "test_a.T.test": 0})
            self.assertEqual(
                RUNNER.load_durations(path),
                {"test_a.T.test": 0.0, "test_b.T.test": 2.5},
            )


if __name__ == "__main__":
    unittest.main()
