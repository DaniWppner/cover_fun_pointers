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


def choose_plot_time_unit(
    timestamps_a: list[float],
    timestamps_b: list[float] | None,
) -> tuple[str, list[float], list[float] | None, list[float]]:
    s_in_h = 3600
    s_in_m = 60

    duration_s = timestamps_a[-1] - timestamps_a[0]
    largest_series = timestamps_a
    if timestamps_b is not None and duration_s < timestamps_b[-1] - timestamps_b[0]:
        duration_s = timestamps_b[-1] - timestamps_b[0]
        largest_series = timestamps_b

    time_unit = "Hours" if duration_s > s_in_h * 2 else "Minutes"

    def apply_to_list(ts: list[float] | None):
        if ts is None:
            return None
        ratio = s_in_h if time_unit == "Hours" else s_in_m
        return [t / ratio for t in ts]

    return (
        time_unit,
        apply_to_list(timestamps_a),
        apply_to_list(timestamps_b),
        apply_to_list(largest_series),
    )


def plot_single_coverage_series(
    ax: plt.Axes,
    coverage_values: list[int],
    timestamps: list[float],
    cutoff_point: int,
    time_unit: str,
    color: str,
    label: str,
    first_secondary_xaxis: bool,
    largest_possible_timestamp: float,
    largest_possible_entry_n: int,
) -> None:
    entry_ns = list(range(len(timestamps)))
    plot_entry_ns = entry_ns[cutoff_point:]
    coverage_values = coverage_values[cutoff_point:]

    interploation_entries = entry_ns + [largest_possible_entry_n]
    interploation_timestamps = timestamps + [largest_possible_timestamp]

    def entry_to_time(entry_n_array: numpy.ndarray) -> numpy.ndarray:
        return numpy.interp(
            entry_n_array, interploation_entries, interploation_timestamps, left=0
        )

    def time_to_entry(timestamp_array: numpy.ndarray) -> numpy.ndarray:
        return numpy.interp(
            timestamp_array, interploation_timestamps, interploation_entries, left=0
        )

    ax.plot(
        plot_entry_ns,
        coverage_values,
        marker=".",
        linewidth=0.1,
        color=color,
        label=label,
    )
    ax2 = ax.secondary_xaxis("top", functions=(entry_to_time, time_to_entry))
    ax2.tick_params(axis="x", colors=color)
    ax2.spines["top"].set_color(color)
    # make the top line disappear beyond the last timestamp
    last_ts_view = timestamps[-1]
    ax2.spines["top"].set_bounds(0, last_ts_view)
    ax2.set_xlim(left=0, right=last_ts_view)
    # remove the ticks beyond the last timestamp
    auto_ticks = ax2.get_xticks()
    filtered_ticks = [t for t in auto_ticks if t <= last_ts_view]
    ax2.set_xticks(filtered_ticks + [round(last_ts_view)])

    if first_secondary_xaxis:
        ax2.set_xlabel(f"Elapsed time ({time_unit})")
        ax2.spines["top"].set_position(("outward", 5))
    else:
        ax2.spines["top"].set_position(("outward", 40))
    return ax2


def save_coverage_time_series(
    coverage_pairs_a: list[tuple[float, int]],
    coverage_pairs_b: list[tuple[float, int]] | None,
    out_file: Path,
    title: str,
    labels: tuple[str, str],
) -> None:
    """
    Plot coverage values over time.

    Args:
        coverage_pairs: List of (timestamp, coverage) tuples
        out_file: Output file path for the PNG
        title: Title for the plot
    """
    CUT_FIRST_N_TRIAGES = 15
    ts_series = []
    cov_series = []
    for pairs in coverage_pairs_a, coverage_pairs_b:
        if pairs is None:
            ts, cvs = None, None
        else:
            _ts, _cvs = zip(*pairs)
            ts, cvs = list(_ts), list(_cvs)
        ts_series.append(ts)
        cov_series.append(cvs)
    time_unit, ts_series[0], ts_series[1], largest_series = choose_plot_time_unit(
        ts_series[0], ts_series[1]
    )
    fig = plt.figure(figsize=(10, 4))
    ax = fig.add_subplot(111)

    for series_idx in (0, 1):
        if ts_series[series_idx] is None:
            break
        color = ("Blue", "Red")[series_idx]
        first_plot = series_idx == 0
        plot_single_coverage_series(
            ax,
            cov_series[series_idx],
            ts_series[series_idx],
            CUT_FIRST_N_TRIAGES,
            time_unit,
            color,
            labels[series_idx],
            first_secondary_xaxis=first_plot,
            largest_possible_timestamp=largest_series[-1],
            largest_possible_entry_n=len(largest_series) - 1,
        )

    ax.set_title(title, loc="left", fontsize="15")
    ax.set_xlabel("Number of Triage Jobs finished")
    ax.set_ylabel("Coverage score")
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


def process_log_json_pair(
    syz_manager_log: Path, triage_json_path: Path
) -> list[tuple[float, int]]:
    with open(triage_json_path, "r") as f:
        __contents = f.read()
    triage_json = json.loads(__contents)
    triage_json = convert_timestamps_nicely(triage_json)

    timestamp_x_coverage = parse_status_lines(syz_manager_log)
    triage_timestamps = all_triage_timestamps(triage_json)
    coverage_pairs = closest_coverage_entries(triage_timestamps, timestamp_x_coverage)
    coverage_pairs = normalize_timestamps(coverage_pairs)
    return coverage_pairs


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse a json file to crosscheck triage job timestamp data with original log coverage information."
    )
    parser.add_argument(
        "input_pairs",
        nargs="+",
        help="One or two pairs of files: <unified_json_path> <syz_manager_log> [<unified_json_path_2> <syz_manager_log_2>]",
    )

    args = parser.parse_args()

    if len(args.input_pairs) not in {2, 4}:
        parser.error("Please provide one or two (json, log) file pairs")

    pairs = [
        (Path(args.input_pairs[i]), Path(args.input_pairs[i + 1]))
        for i in range(0, len(args.input_pairs), 2)
    ]
    for unified_json_path, syz_manager_log in pairs:
        check_file_exists(unified_json_path)
        check_file_exists(syz_manager_log)

    coverage_series_a = process_log_json_pair(pairs[0][1], pairs[0][0])
    coverage_series_b = (
        process_log_json_pair(pairs[1][1], pairs[1][0]) if len(pairs) > 1 else None
    )

    out_dir = Path.cwd() / "coverage_over_time"
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = tuple(path.parent.absolute().name for path, _ in pairs)
    save_coverage_time_series(
        coverage_series_a,
        coverage_series_b,
        out_dir / "coverage_evolution.png",
        "Coverage Evolution over Triages",
        labels=labels,
    )
