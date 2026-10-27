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
from numpy.typing import ArrayLike

from logentry_keys import RESULT_KEYS

STATUS_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"candidates=\d+\s+corpus=\d+\s+coverage=(?P<coverage>\d+)\s+"
    r"exec total=\d+\s+\(\d+/(?:sec|min)\)\s+pending=\d+\s+reproducing=\d+"
)


def parse_status_lines(syz_manager_log: Path) -> list[tuple[datetime, int]]:
    """
    Args:
        syz_manager_log: syz-manager log of a single run.

    Returns:
        (timestamp, coverage) of every manager status line, in log order.
    """
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
    """
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.

    Returns:
        The same prog2log, modified in place, with TIMESTAMP_END parsed into a datetime.
        No other field is converted.
    """
    for prog_key, entries in prog2log.items():
        entries[RESULT_KEYS.TIMESTAMP_END] = datetime.strptime(
            entries[RESULT_KEYS.TIMESTAMP_END], "%Y-%m-%d %H:%M:%S"
        )
    return prog2log


def all_triage_timestamps(prog2log: dict[str, dict[str, Any]]) -> list[datetime]:
    """
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.
            TIMESTAMP_END must already be a datetime (see convert_timestamps_nicely).

    Returns:
        End time of every prog|call entry, in chronological order. An entry triaged several
        times (COUNT > 1) contributes a single timestamp.
    """
    timestamps = [entry[RESULT_KEYS.TIMESTAMP_END] for entry in prog2log.values()]
    return sorted(timestamps)


def closest_coverage_entries(
    triage_timestamps: list[datetime], ts_x_cov: list[tuple[datetime, int]]
) -> list[tuple[datetime, int]]:
    """
    Args:
        triage_timestamps: end time of every triage, in chronological order.
        ts_x_cov: (timestamp, coverage) of every status line, in chronological order.

    Returns:
        For each triage, the (timestamp, coverage) of the status line closest in time to its end.
        Both inputs are walked forward together, so an unsorted input silently gives wrong matches.
        On a tie between two status lines, the later one wins.
    """
    result_entries: list[tuple[datetime, int]] = []
    i = 0
    for triage_ts in triage_timestamps:
        while i + 1 < len(ts_x_cov) and abs((triage_ts - ts_x_cov[i + 1][0]).total_seconds()) <= abs(
            (triage_ts - ts_x_cov[i][0]).total_seconds()
        ):
            i += 1
        result_entries.append(ts_x_cov[i])
    return result_entries


def normalize_timestamps(
    ts_x_cov: list[tuple[datetime, int]],
) -> list[tuple[float, int]]:
    """
    Args:
        ts_x_cov: (timestamp, coverage) pairs, in chronological order.

    Returns:
        The same pairs with timestamps as seconds elapsed since the first pair. For the output of
        closest_coverage_entries, t=0 is the status line closest to the first triage, not the
        start of the campaign.
    """
    ts_0: datetime = ts_x_cov[0][0]
    normalized = [((ts - ts_0).total_seconds(), cov) for ts, cov in ts_x_cov]
    return normalized


def choose_plot_time_unit(
    timestamps_a: list[float],
    timestamps_b: list[float] | None,
) -> tuple[str, list[float], list[float] | None, list[float]]:
    """
    Args:
        timestamps_a: elapsed seconds of the first series.
        timestamps_b: elapsed seconds of the second series, if any.

    Returns:
        A tuple containing:
            - "Hours" if the longer series spans more than 2 hours, otherwise "Minutes".
            - timestamps_a converted to that unit.
            - timestamps_b converted to that unit, or None.
            - The timestamps of the longer series converted to that unit.
    """
    s_in_h = 3600
    s_in_m = 60

    duration_s = timestamps_a[-1] - timestamps_a[0]
    largest_series = timestamps_a
    if timestamps_b is not None and duration_s < timestamps_b[-1] - timestamps_b[0]:
        duration_s = timestamps_b[-1] - timestamps_b[0]
        largest_series = timestamps_b

    time_unit = "Hours" if duration_s > s_in_h * 2 else "Minutes"
    ratio = s_in_h if time_unit == "Hours" else s_in_m

    return (
        time_unit,
        [t / ratio for t in timestamps_a],
        None if timestamps_b is None else [t / ratio for t in timestamps_b],
        [t / ratio for t in largest_series],
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
    """
    Draws the series against triage number on ax, and adds a secondary top axis, in the series'
    color, that maps triage number to elapsed time for this series only.

    Args:
        ax: axes to draw on.
        coverage_values: coverage at each triage of the series.
        timestamps: elapsed time at each triage of the series, in time_unit.
        cutoff_point: number of leading triages left out of the plotted line. They still count
            for the triage numbering and the time mapping.
        time_unit: unit of timestamps, used in the axis label.
        color: color of the line and of its time axis.
        label: legend name of the series.
        first_secondary_xaxis: True for the first series drawn on ax. Its time axis is labelled and
            sits right above the plot, while the second series' axis is pushed further out.
        largest_possible_timestamp: last timestamp of the longest series on ax.
        largest_possible_entry_n: last triage number of the longest series on ax. Together with
            largest_possible_timestamp, it extends the time mapping of a shorter series to the
            whole x range.
    """
    entry_ns = list(range(len(timestamps)))
    plot_entry_ns = entry_ns[cutoff_point:]
    coverage_values = coverage_values[cutoff_point:]

    interpolation_entries = entry_ns + [largest_possible_entry_n]
    interpolation_timestamps = timestamps + [largest_possible_timestamp]

    def entry_to_time(entry_n_array: ArrayLike) -> numpy.ndarray:
        return numpy.interp(
            numpy.asarray(entry_n_array, dtype=float), interpolation_entries, interpolation_timestamps, left=0
        )

    def time_to_entry(timestamp_array: ArrayLike) -> numpy.ndarray:
        return numpy.interp(
            numpy.asarray(timestamp_array, dtype=float), interpolation_timestamps, interpolation_entries, left=0
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


def save_coverage_time_series(
    coverage_pairs_a: list[tuple[float, int]],
    coverage_pairs_b: list[tuple[float, int]] | None,
    out_file: Path,
    title: str,
    labels: tuple[str, ...],
) -> None:
    """
    Plots coverage against triage number, with one elapsed-time axis per series on top.
    The first 15 triages of each series are left out of the plotted lines.

    Args:
        coverage_pairs_a: (elapsed seconds, coverage) at each triage of the first series.
        coverage_pairs_b: (elapsed seconds, coverage) at each triage of the second series, if any.
        out_file: path of the PNG to write.
        title: title of the plot.
        labels: legend names of the first and, if any, second series.
    """
    CUT_FIRST_N_TRIAGES = 15
    ts_a = [p[0] for p in coverage_pairs_a]
    ts_b = None if coverage_pairs_b is None else [p[0] for p in coverage_pairs_b]
    time_unit, ts_a, ts_b, largest_series = choose_plot_time_unit(ts_a, ts_b)

    plotted_series = [([p[1] for p in coverage_pairs_a], ts_a)]
    if coverage_pairs_b is not None:
        assert ts_b is not None
        plotted_series.append(([p[1] for p in coverage_pairs_b], ts_b))

    fig = plt.figure(figsize=(10, 4))
    ax = fig.add_subplot(111)

    for series_idx, (coverages, timestamps) in enumerate(plotted_series):
        color = ("Blue", "Red")[series_idx]
        first_plot = series_idx == 0
        plot_single_coverage_series(
            ax,
            coverages,
            timestamps,
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
    """
    Args:
        file_path: input file that must exist. Exits with status 1 if it does not.
    """
    if not file_path.exists():
        print(
            f"Error: The specified json file does not exist: {file_path}",
            file=sys.stderr,
        )
        sys.exit(1)


def process_log_json_pair(
    syz_manager_log: Path, triage_json_path: Path
) -> list[tuple[float, int]]:
    """
    Args:
        syz_manager_log: syz-manager log of the run.
        triage_json_path: unified_triage_logs.json of the same run. Note the order: log first,
            unlike the command line, which takes the json first.

    Returns:
        For each prog|call entry, in order of end time: (elapsed seconds, coverage) of the status
        line closest to its end. Elapsed seconds count from the status line matched to the first
        entry (see normalize_timestamps).
    """
    with open(triage_json_path, "r") as f:
        triage_json = json.load(f)
    triage_json = convert_timestamps_nicely(triage_json)

    timestamp_x_coverage = parse_status_lines(syz_manager_log)
    triage_timestamps = all_triage_timestamps(triage_json)
    return normalize_timestamps(closest_coverage_entries(triage_timestamps, timestamp_x_coverage))


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

    if coverage_series_b is not None and coverage_series_a and coverage_series_b:
        max_time_a = coverage_series_a[-1][0]
        max_time_b = coverage_series_b[-1][0]
        if max_time_a > max_time_b:
            coverage_series_a = [p for p in coverage_series_a if p[0] <= max_time_b]
        elif max_time_b > max_time_a:
            coverage_series_b = [p for p in coverage_series_b if p[0] <= max_time_a]

    out_dir = Path.cwd() / "coverage_over_time"
    out_dir.mkdir(parents=True, exist_ok=True)
    if len(pairs) == 2:
        default1 = pairs[0][0].parent.absolute().name
        label1 = input(f"Enter name for first plot (default '{default1}'): ").strip()
        label1 = label1 if label1 else default1
        
        default2 = pairs[1][0].parent.absolute().name
        label2 = input(f"Enter name for second plot (default '{default2}'): ").strip()
        label2 = label2 if label2 else default2
        
        labels: tuple[str, ...] = (label1, label2)
    else:
        labels = tuple(path.parent.absolute().name for path, _ in pairs)
    
    save_coverage_time_series(
        coverage_series_a,
        coverage_series_b,
        out_dir / "coverage_evolution.png",
        "Coverage Evolution over Triages",
        labels=labels,
    )
