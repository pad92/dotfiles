#!/usr/bin/env python3
"""Check how run_unit_tests.py splits, orders and sizes the test run."""

import importlib.util
import io
import json
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


class SummarizeTests(unittest.TestCase):
    def test_counts_only_unittest_summaries(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            # A failed play test prints its PLAY RECAP before unittest's summary.
            (logs / "play.log").write_text(
                "AssertionError: 2 != 0 : PLAY RECAP\n"
                "case0 : ok=3    changed=0    unreachable=0    failed=1    "
                "skipped=0    rescued=0    ignored=0   \n"
                "Ran 1 test in 4.2s\n"
                "\n"
                "FAILED (failures=1, skipped=2)\n"
            )
            (logs / "fast.log").write_text("Ran 12 tests in 0.3s\n\nOK (skipped=1)\n")
            (logs / "plain.log").write_text("Ran 3 tests in 0.1s\n\nOK\n")
            self.assertEqual(RUNNER.summarize(logs), (16, 3))


class ShardTests(unittest.TestCase):
    def units(self, estimates):
        return [
            RUNNER.Unit(f"u{i}", [f"t.C.test_{i}"], seconds)
            for i, seconds in enumerate(estimates)
        ]

    def test_shards_partition_the_units_and_balance_the_load(self):
        units = self.units([90, 60, 50, 40, 10, 5, 1])
        shards = [RUNNER.shard_units(units, i, 2) for i in (1, 2)]
        names = [unit.name for shard in shards for unit in shard]
        self.assertCountEqual(names, [unit.name for unit in units])
        loads = [sum(unit.estimate for unit in shard) for shard in shards]
        self.assertLessEqual(abs(loads[0] - loads[1]), 10)

    def test_a_single_shard_keeps_every_unit_in_order(self):
        units = self.units([3, 2, 1])
        self.assertEqual(RUNNER.shard_units(units, 1, 1), units)

    def test_shard_argument_rejects_out_of_range_values(self):
        self.assertEqual(RUNNER.parse_shard("2/3"), (2, 3))
        for value in ("0/2", "3/2", "x/2", "2"):
            with self.subTest(value=value), self.assertRaises(Exception):
                RUNNER.parse_shard(value)


class CombineReportsTests(unittest.TestCase):
    def combine(self, reports, durations=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for number, report in enumerate(reports):
                path = root / f"report{number}.json"
                path.write_text(json.dumps(report))
                paths.append(path)
            history = root / "durations.json"
            history.write_text(json.dumps(durations or {}))
            with (
                mock.patch.object(sys, "stdout", io.StringIO()),
                mock.patch.object(sys, "stderr", io.StringIO()) as stderr,
            ):
                code = RUNNER.combine_reports(paths, history)
            return code, stderr.getvalue(), RUNNER.load_durations(history)

    def report(self, index, ran, measured=None, discovered=("a", "b", "c"), total=2):
        return {
            "shard": [index, total],
            "discovered": list(discovered),
            "ran": ran,
            "measured": measured or {},
        }

    def test_complete_shards_record_their_durations(self):
        code, _, durations = self.combine(
            [
                self.report(1, ["a", "c"], {"a": 1.5}),
                self.report(2, ["b"], {"b": 2.5}),
            ],
            {"a": 9.0, "gone": 4.0},
        )
        self.assertEqual(code, 0)
        self.assertEqual(durations, {"a": 1.5, "b": 2.5})

    def test_a_test_never_run_fails_and_keeps_the_history(self):
        code, error, durations = self.combine(
            [self.report(1, ["a"]), self.report(2, ["b"])], {"a": 9.0}
        )
        self.assertEqual(code, 1)
        self.assertIn("never run: c", error)
        self.assertEqual(durations, {"a": 9.0})

    def test_a_test_run_twice_fails(self):
        code, error, _ = self.combine(
            [self.report(1, ["a", "b"]), self.report(2, ["b", "c"])]
        )
        self.assertEqual(code, 1)
        self.assertIn("run twice: b", error)

    def test_a_missing_shard_fails(self):
        code, error, _ = self.combine([self.report(1, ["a", "b", "c"])])
        self.assertEqual(code, 1)
        self.assertIn("shards found: [1]", error)

    def test_shards_that_discovered_different_tests_fail(self):
        code, error, _ = self.combine(
            [
                self.report(1, ["a", "b"]),
                self.report(2, ["c"], discovered=("a", "b", "c", "d")),
            ]
        )
        self.assertEqual(code, 1)
        self.assertIn("discovered different tests", error)

    def test_no_report_fails(self):
        code, error, _ = self.combine([])
        self.assertEqual(code, 1)
        self.assertIn("no shard report", error)


if __name__ == "__main__":
    unittest.main()
