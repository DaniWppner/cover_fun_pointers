#!/usr/bin/env python3
"""
Parse syzkaller status lines and plot the evolution of `coverage`.

Example input line format (one per line):

2026/06/26 17:09:24 candidates=143 corpus=39 coverage=6300 exec total=1015 (548/min) pending=0 reproducing=0

The script considers the inputted json to only grab the coverage entries that match the time of a triage
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy

from logentry_keys import RESULT_KEYS

STATUS_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"candidates=\d+\s+corpus=\d+\s+coverage=(?P<coverage>\d+)\s+"
    r"exec total=\d+\s+\(\d+/min\)\s+pending=\d+\s+reproducing=\d+"
)


def parse_status_lines(syz_manager_log: Path) -> list[tuple[datetime, int]]:
    coverages: list[int] = []
    timestamps: list[datetime] = []

    with syz_manager_log.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = STATUS_LINE_RE.match(line)
            if not m:
                continue
            coverages.append(int(m.group("coverage")))
            timestamps.append(datetime.strptime(m.group("ts"), "%Y/%m/%d %H:%M:%S"))

    return list(zip(timestamps, coverages))


def convert_timestamps_nicely(
    prog2log: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:

    for prog_key, entries in prog2log.items():
        entries[RESULT_KEYS.TIMESTAMP] = datetime.strptime(
            entries[RESULT_KEYS.TIMESTAMP], "%Y-%m-%d %H:%M:%S"
        )
    return prog2log


def all_triage_timestamps(prog2log: dict[str, dict[str, Any]]) -> list[datetime]:
    timestamps = [entry[RESULT_KEYS.TIMESTAMP] for entry in prog2log.values()]
    return sorted(timestamps)


def closest_coverage_entries(
    triage_timestamps: list[datetime], ts_x_cov: list[tuple[datetime, int]]
) -> list[tuple[datetime, int]]:
    result_entries: list[tuple[datetime, int]] = []
    i = 0
    for triage_ts in triage_timestamps:
        last_ts: datetime = ts_x_cov[i][0]
        last_cov: int = ts_x_cov[i][1]
        for j, pair in enumerate(ts_x_cov[i:]):
            ts, cov = pair
            if abs((triage_ts - ts).total_seconds()) > abs(
                (triage_ts - last_ts).total_seconds()
            ):
                i += j
                break
            last_ts = ts
            last_cov = cov
        result_entries.append((last_ts, last_cov))
    assert len(result_entries) == len(triage_timestamps)
    return result_entries


def normalize_timestamps(
    ts_x_cov: list[tuple[datetime, int]],
) -> list[tuple[float, int]]:
    ts_0: datetime = ts_x_cov[0][0]
    normalized = [((ts - ts_0).total_seconds(), cov) for ts, cov in ts_x_cov]
    return normalized


def choose_plot_time_unit(timestamps: list[float]) -> tuple[str, list[float]]:
    s_in_h = 3600
    s_in_m = 60
    if timestamps[-1] - timestamps[0] > s_in_h * 2:
        result = "Hours"
        ratio = s_in_h
    else:
        result = "Minutes"
        ratio = s_in_m
    timestamps = [t / ratio for t in timestamps]
    return result, timestamps


def save_coverage_time_series(
    coverage_pairs: list[tuple[float, int]],
    out_file: Path,
    title: str,
) -> None:
    """
    Plot coverage values over time.

    Args:
        coverage_pairs: List of (timestamp, coverage) tuples
        out_file: Output file path for the PNG
        title: Title for the plot
    """
    ts, cvs = zip(*coverage_pairs)
    timestamps = list(ts)
    coverage_values = list(cvs)
    entry_ns = list(range(len(timestamps)))
    time_unit, timestamps = choose_plot_time_unit(timestamps)

    fig = plt.figure(figsize=(10, 4))
    ax = fig.add_subplot(111)

    ax.plot(
        entry_ns,
        coverage_values,
        marker=".",
        linewidth=0.5,
        color="tab:blue",
        label="Coverage",
    )

    ax.set_title(title, loc="left", fontsize="15")
    ax.set_xlabel("Triage job (sorted by finish time)")
    ax.set_ylabel("Coverage score")

    def entry_to_time(entry_n_array: numpy.ndarray) -> numpy.ndarray:
        return numpy.interp(entry_n_array, entry_ns, timestamps, left=0)

    def time_to_entry(timestamp_array: numpy.ndarray) -> numpy.ndarray:
        return numpy.interp(timestamp_array, timestamps, entry_ns, left=0)

    ax2 = ax.secondary_xaxis("top", functions=(entry_to_time, time_to_entry))
    ax2.set_xlabel(f"Elapsed time ({time_unit})")

    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_file)
    plt.close(fig)
    print(f"Saved {out_file}")


def check_file_exists(file_path: Path) -> None:
    if not file_path.exists():
        print(
            f"Error: The specified json file does not exist: {file_path}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse a json file to crosscheck triage job timestamp data with original log coverage information."
    )
    parser.add_argument(
        "unified_json_path",
        type=str,
        nargs="?",
        help="Json file outputted by unify_triage_lines.py",
    )
    parser.add_argument(
        "syz_manager_log",
        type=str,
        nargs="?",
        help="Log file outputted by syzkaller used in to generate the json",
    )

    args = parser.parse_args()

    if not args.unified_json_path or not args.syz_manager_log:
        parser.print_help()
        sys.exit(1)

    unified_json_path = Path(args.unified_json_path)
    syz_manager_log = Path(args.syz_manager_log)
    check_file_exists(unified_json_path)
    check_file_exists(syz_manager_log)

    with open(unified_json_path, "r") as f:
        __contents = f.read()
    triage_json = json.loads(__contents)
    triage_json = convert_timestamps_nicely(triage_json)

    timestamp_x_coverage = parse_status_lines(syz_manager_log)
    triage_timestamps = all_triage_timestamps(triage_json)
    coverage_pairs = closest_coverage_entries(triage_timestamps, timestamp_x_coverage)
    coverage_pairs = normalize_timestamps(coverage_pairs)

    out_dir = Path.cwd() / "coverage_over_time"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_coverage_time_series(
        coverage_pairs,
        out_dir / "coverage_evolution.png",
        "Coverage Evolution over Triages",
    )
