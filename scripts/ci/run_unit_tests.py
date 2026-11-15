#!/usr/bin/env python3
"""Run the Python unit tests in parallel, longest first.

Most tests drive ansible-playbook, so a few of them take minutes while most
take milliseconds. Running one process per file made the slowest file the
floor of the whole run, whatever the CPU count. This runner:

* discovers every test of tests/test_*.py;
* reads the durations recorded by the previous run (DURATIONS, kept in the
  GitLab cache), runs each slow test in its own process and packs the fast
  ones of a module into one process, so process start-up stays cheap;
* starts the longest units first (LPT scheduling) on JOBS workers, so a long
  test never starts last;
* records the new durations for the next run.

Tests without a recorded duration run one process per class.

Usage: run_unit_tests.py [--coverage] [--shard INDEX/TOTAL] [--report FILE]
       run_unit_tests.py --combine REPORT...
  --coverage  record with `coverage run -p` and combine the data files; the
              caller then runs `coverage report`. Set COVERAGE_FILE to keep
              the data of each shard apart.
  --shard     run only the INDEX-th (1-based) of TOTAL slices of the plan. The
              slices are balanced from the recorded durations and are the same
              in every shard that reads the same durations file.
  --report    write what this run discovered, ran and measured to FILE.
  --combine   check that the reports of all shards together ran every
              discovered test exactly once, then record their durations in
              DURATIONS for the next pipeline. Shards only read DURATIONS, so a
              cache refreshed mid-pipeline cannot split them differently.

Environment: JOBS (default: usable CPUs, capped by the cgroup memory limit),
DURATIONS (default: .cache/unit-tests/durations.json).

Each unit logs to its own file so outputs do not interleave; the logs of
failing units are printed in full.
"""

from __future__ import annotations

import argparse
import json
import re
import os
import subprocess
import sys
import tempfile
import time
import unittest
from collections import defaultdict
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
DEFAULT_DURATIONS = ROOT / ".cache/unit-tests/durations.json"
# A test at least this long gets its own process; below, start-up (~0.25 s
# with coverage) would cost more than the parallelism gains.
SLOW_TEST_SECONDS = 2.0
# Peak memory of one worker: unittest process, ansible-playbook and a module.
WORKER_MEMORY_BYTES = 300 * 1024 * 1024
SLOWEST_SHOWN = 10


@dataclass
class Unit:
    """Tests run by one process, with their expected duration."""

    name: str
    tests: list[str]
    estimate: float
    known: bool = True
    seconds: float = 0.0
    failed: bool = False
    log: Path = field(default_factory=Path)


def iter_test_ids(suite: unittest.TestSuite) -> Iterator[str]:
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from iter_test_ids(test)
        else:
            yield test.id()


def discover() -> list[str]:
    sys.path.insert(0, str(TESTS))
    suite = unittest.defaultTestLoader.discover(str(TESTS), top_level_dir=str(TESTS))
    ids = list(iter_test_ids(suite))
    # Import errors surface as synthetic tests; let a worker report them.
    return sorted(ids)


def load_durations(path: Path) -> dict[str, float]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        print(f"run_unit_tests: ignoring {path}: {error}", file=sys.stderr)
        return {}
    return {
        str(key): float(value)
        for key, value in data.items()
        if isinstance(value, (int, float))
    }


def save_durations(path: Path, durations: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(sorted(durations.items())), indent=0))
    temporary.replace(path)


def plan_units(ids: list[str], durations: dict[str, float]) -> list[Unit]:
    """Split the tests into units and order them longest first."""
    units: list[Unit] = []
    fast: dict[str, list[str]] = defaultdict(list)
    unknown: dict[str, list[str]] = defaultdict(list)
    for test in ids:
        module, _, _ = test.partition(".")
        seconds = durations.get(test)
        if seconds is None:
            unknown[test.rpartition(".")[0]].append(test)
        elif seconds >= SLOW_TEST_SECONDS:
            units.append(Unit(test, [test], seconds))
        else:
            fast[module].append(test)
    for module, tests in fast.items():
        estimate = sum(durations[test] for test in tests)
        units.append(Unit(module, tests, estimate))
    for name, tests in unknown.items():
        units.append(Unit(name, tests, float(len(tests)), known=False))
    # Unknown classes first, as they may hide a long test; then LPT.
    units.sort(key=lambda unit: (unit.known, -unit.estimate, unit.name))
    return units


def parse_shard(value: str) -> tuple[int, int]:
    """Parse "INDEX/TOTAL" (1-based) into (index, total)."""
    index, _, total = value.partition("/")
    try:
        shard = int(index), int(total)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected INDEX/TOTAL, got {value!r}")
    if not 1 <= shard[0] <= shard[1]:
        raise argparse.ArgumentTypeError(f"shard {value} is out of range")
    return shard


def shard_units(units: list[Unit], index: int, total: int) -> list[Unit]:
    """Units of shard `index` of `total`, balancing the estimated durations.

    Greedy longest-first: each unit goes to the least loaded shard, the lowest
    index winning ties. The result only depends on the ordered units, so every
    shard computes the same partition.
    """
    loads = [0.0] * total
    mine: list[Unit] = []
    for unit in units:
        target = loads.index(min(loads))
        loads[target] += unit.estimate
        if target == index - 1:
            mine.append(unit)
    return mine


def combine_reports(paths: list[Path], durations_path: Path) -> int:
    """Check the shard reports cover the discovered tests exactly once."""
    reports = [json.loads(path.read_text()) for path in paths]
    if not reports:
        print("run_unit_tests: no shard report to combine", file=sys.stderr)
        return 1
    problems: list[str] = []
    discovered = reports[0]["discovered"]
    totals = {report["shard"][1] for report in reports}
    indexes = sorted(report["shard"][0] for report in reports)
    if len(totals) != 1 or indexes != list(range(1, totals.pop() + 1)):
        problems.append(f"shards found: {indexes}")
    if any(report["discovered"] != discovered for report in reports):
        problems.append("shards discovered different tests")
    ran = [test for report in reports for test in report["ran"]]
    problems += [
        f"run twice: {test}" for test in sorted({t for t in ran if ran.count(t) > 1})
    ]
    problems += [f"never run: {test}" for test in sorted(set(discovered) - set(ran))]
    problems += [
        f"unknown test run: {test}" for test in sorted(set(ran) - set(discovered))
    ]
    if problems:
        print("run_unit_tests: shards do not cover the suite:", file=sys.stderr)
        print("\n".join(f"  {problem}" for problem in problems), file=sys.stderr)
        return 1
    measured = {
        test: seconds
        for report in reports
        for test, seconds in report["measured"].items()
    }
    known = set(discovered)
    save_durations(
        durations_path,
        {
            test: seconds
            for test, seconds in {**load_durations(durations_path), **measured}.items()
            if test in known
        },
    )
    print(f"run_unit_tests: {len(ran)} tests ran once across {len(reports)} shards")
    return 0


def cgroup_values(name: str) -> list[int] | None:
    """Numbers of a cgroup v2 limit file, or None when absent or unlimited."""
    try:
        fields = Path("/sys/fs/cgroup", name).read_text().split()
    except OSError:
        return None
    if not fields or fields[0] == "max":
        return None
    return [int(value) for value in fields]


def default_jobs() -> int:
    """Usable CPUs, capped by the container CPU quota and memory limit."""
    jobs = os.process_cpu_count() or 2
    cpu = cgroup_values("cpu.max")  # "<quota> <period>" in microseconds
    if cpu and len(cpu) == 2:
        jobs = min(jobs, max(1, cpu[0] // cpu[1]))
    memory = cgroup_values("memory.max")
    if memory:
        jobs = min(jobs, max(1, memory[0] // WORKER_MEMORY_BYTES))
    return jobs


def run_unit(unit: Unit, command: list[str], logs: Path) -> Unit:
    unit.log = logs / f"{unit.name}.log"
    timings = logs / f"{unit.name}.json"
    started = time.monotonic()
    with unit.log.open("w") as log:
        result = subprocess.run(
            [*command, "--worker", str(timings), *unit.tests],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    unit.seconds = time.monotonic() - started
    unit.failed = result.returncode != 0
    return unit


def collect_timings(logs: Path) -> dict[str, float]:
    measured: dict[str, float] = {}
    for path in logs.glob("*.json"):
        measured.update(load_durations(path))
    return measured


# unittest's last lines: "Ran 3 tests in 0.1s" then "OK (skipped=1)" or
# "FAILED (failures=1, skipped=2)". A failed play test prints its PLAY RECAP,
# whose "skipped=0    rescued=0" must not be read as a unittest summary.
RAN_LINE = re.compile(r"^Ran (\d+) tests? in ")
SKIPPED_SUMMARY = re.compile(r"^(?:OK|FAILED) \(.*\bskipped=(\d+)")


def summarize(logs: Path) -> tuple[int, int]:
    tests = skipped = 0
    for path in logs.glob("*.log"):
        for line in path.read_text(errors="replace").splitlines():
            if ran := RAN_LINE.match(line):
                tests += int(ran.group(1))
            if summary := SKIPPED_SUMMARY.match(line):
                skipped += int(summary.group(1))
    return tests, skipped


def orchestrate(
    coverage: bool, shard: tuple[int, int] = (1, 1), report: Path | None = None
) -> int:
    python = sys.executable
    command = [python]
    if coverage:
        subprocess.run([python, "-m", "coverage", "erase"], cwd=ROOT, check=True)
        command += ["-m", "coverage", "run", "-p"]
    command.append(str(Path(__file__).resolve()))

    ids = discover()
    if not ids:
        print("run_unit_tests: no test found in tests/test_*.py", file=sys.stderr)
        return 1
    durations_path = Path(os.environ.get("DURATIONS", DEFAULT_DURATIONS))
    durations = load_durations(durations_path)
    units = shard_units(plan_units(ids, durations), *shard)
    expected = sum(len(unit.tests) for unit in units)
    jobs = int(os.environ.get("JOBS") or default_jobs())
    print(
        f"run_unit_tests: shard {shard[0]}/{shard[1]}: {expected} of {len(ids)} "
        f"tests in {len(units)} processes, {jobs} at a time "
        f"({len(durations)} known durations)"
    )

    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        logs = Path(directory)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            done = list(pool.map(lambda unit: run_unit(unit, command, logs), units))
        measured = collect_timings(logs)
        tests, skipped = summarize(logs)
        failed = [unit for unit in done if unit.failed]
        for unit in failed:
            print(f"\n===== FAILED: {unit.name} =====", file=sys.stderr)
            print(unit.log.read_text(errors="replace"), file=sys.stderr)

    if report:
        report.write_text(
            json.dumps(
                {
                    "shard": list(shard),
                    "discovered": ids,
                    "ran": [test for unit in units for test in unit.tests],
                    "measured": measured,
                }
            )
        )
    # Keep only the tests that still exist, refreshed with this run. A shard
    # leaves the file to --combine: the other shards would not see its update.
    known = set(ids)
    if shard[1] == 1:
        save_durations(
            durations_path,
            {t: s for t, s in {**durations, **measured}.items() if t in known},
        )
    if coverage:
        subprocess.run(
            [python, "-m", "coverage", "combine", "-q"], cwd=ROOT, check=True
        )

    print(f"\nSlowest of {len(measured)} timed tests:")
    for test, seconds in sorted(measured.items(), key=lambda item: -item[1])[
        :SLOWEST_SHOWN
    ]:
        print(f"  {seconds:7.1f}s  {test}")
    print(
        f"Ran {tests} tests ({skipped} skipped) in "
        f"{time.monotonic() - started:.0f}s wall time"
    )
    if tests != expected:
        print(
            f"run_unit_tests: planned {expected} tests but ran {tests}",
            file=sys.stderr,
        )
        return 1
    if failed:
        print(f"{len(failed)} test process(es) failed", file=sys.stderr)
        return 1
    print("OK")
    return 0


class TimedResult(unittest.TextTestResult):
    """Text result that also records how long each test took.

    Not named `durations`: TextTestResult already uses that attribute.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.test_seconds: dict[str, float] = {}
        self._started = 0.0

    def startTest(self, test: unittest.TestCase) -> None:  # noqa: N802 unittest API
        self._started = time.monotonic()
        super().startTest(test)

    def stopTest(self, test: unittest.TestCase) -> None:  # noqa: N802 unittest API
        super().stopTest(test)
        self.test_seconds[test.id()] = time.monotonic() - self._started


def work(timings: Path, tests: list[str]) -> int:
    """Run the given test ids in this process and record their durations."""
    # Discovery put tests/ on sys.path; the shared test helpers rely on it.
    sys.path.insert(0, str(TESTS))
    suite = unittest.defaultTestLoader.loadTestsFromNames(tests)
    runner = unittest.TextTestRunner(resultclass=TimedResult, verbosity=1)
    result = runner.run(suite)
    assert isinstance(result, TimedResult)
    timings.write_text(json.dumps(result.test_seconds))
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--shard", type=parse_shard, default=(1, 1))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--combine", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("tests", nargs="*", help="report files with --combine")
    arguments = parser.parse_args()
    if arguments.worker:
        return work(arguments.worker, arguments.tests)
    if arguments.combine:
        durations = Path(os.environ.get("DURATIONS", DEFAULT_DURATIONS))
        return combine_reports([Path(path) for path in arguments.tests], durations)
    return orchestrate(arguments.coverage, arguments.shard, arguments.report)


if __name__ == "__main__":
    sys.exit(main())
