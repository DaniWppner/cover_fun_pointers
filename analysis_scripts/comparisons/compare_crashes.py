#!/usr/bin/env python3
import argparse
import gzip
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TextIO

from comparisons.comparison_commons import add_group_arguments, assert_similar_run_spans, mann_whitney, print_groups
from plotting import plot_throughput_evolution

# Only the first report of a VM's output is saved in crashes/; the "crash(tailN):" lines after it are not counted.
CRASH_REGEX = re.compile(r"^\S+ \S+ VM \d+: crash: (.*?)( \[corrupted\])?( \[suppressed\])?$")
# syz-manager saves every suppressed crash under this title.
SUPPRESSED_TITLE = "suppressed report"


def open_log(log: Path) -> TextIO:
    """
    Args:
        log: a syz-manager.log, plain or gzipped (`.gz`).

    Returns:
        The log opened for reading text lines.
    """
    if log.suffix == ".gz":
        return gzip.open(log, "rt", errors="replace")
    return log.open(errors="replace")


def run_crashes(log: Path) -> tuple[Counter[str], float]:
    """
    Args:
        log: syz-manager.log of the run.

    Returns:
        A tuple containing:
            - Number of crashes of each title, as syz-manager titles them in crashes/.
            - Seconds between the first and last status lines of the run.
    """
    crashes: Counter[str] = Counter()
    status_timestamps: list[str] = []
    with open_log(log) as f:
        for line in f:
            line = line.strip()
            status = plot_throughput_evolution.STATUS_LINE_RE.match(line)
            if status is not None:
                status_timestamps.append(status["ts"])
                continue
            crash = CRASH_REGEX.match(line)
            if crash is not None:
                crashes[SUPPRESSED_TITLE if crash[3] else crash[1]] += 1
    first, last = (datetime.strptime(ts, "%Y/%m/%d %H:%M:%S") for ts in (status_timestamps[0], status_timestamps[-1]))
    return crashes, (last - first).total_seconds()


def load_group_crashes(logs: list[Path]) -> list[Counter[str]]:
    """
    Args:
        logs: syz-manager.log of each run in the group. All runs must span roughly the same time.

    Returns:
        For each run of the group, in the same order, the number of crashes of each title.
    """
    runs = [run_crashes(log) for log in logs]
    assert_similar_run_spans([span for _, span in runs], logs)
    return [crashes for crashes, _ in runs]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Number of crashes of each title in each run of two groups of campaigns, with the two-sided "
        "Mann-Whitney U p-value of the groups' per-run counts. Titles are sorted by p-value"
    )
    add_group_arguments(
        parser,
        require_group2=True,
        metavar="LOG",
        group1_help="syz-manager.log of each run, plain or .gz, e.g. <experiment>/previous_run_*/syz-manager.log.gz",
    )
    args = parser.parse_args()

    group1 = load_group_crashes(args.group1)
    group2 = load_group_crashes(args.group2)
    rows = []
    for title in set().union(*group1, *group2):
        counts1 = [run[title] for run in group1]
        counts2 = [run[title] for run in group2]
        rows.append((mann_whitney(counts1, counts2).p_two_sided, -sum(counts1) - sum(counts2), title, counts1, counts2))
    rows.sort()

    print_groups(args)
    print(
        f"Total crashes: {args.group1_label} {[sum(run.values()) for run in group1]}, "
        f"{args.group2_label} {[sum(run.values()) for run in group2]}"
    )
    print()
    print(
        f"{'p':>6} | {args.group1_label + ' per run':>24} {'runs':>5} | {args.group2_label + ' per run':>24} "
        f"{'runs':>5} | title"
    )
    for p, _, title, counts1, counts2 in rows:
        present1 = f"{sum(c > 0 for c in counts1)}/{len(counts1)}"
        present2 = f"{sum(c > 0 for c in counts2)}/{len(counts2)}"
        print(f"{p:6.3f} | {str(counts1):>24} {present1:>5} | {str(counts2):>24} {present2:>5} | {title}")


if __name__ == "__main__":
    main()
