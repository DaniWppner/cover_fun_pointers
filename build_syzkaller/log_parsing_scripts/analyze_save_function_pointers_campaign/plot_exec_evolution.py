#!/usr/bin/env python3
"""
Parse syzkaller status lines and plot the evolution of `exec total` and `exec/min`.

Example input line format (one per line):

2026/06/26 17:09:24 candidates=143 corpus=39 coverage=6300 exec total=1015 (548/min) pending=0 reproducing=0

The script writes two PNG files to the current working directory:
- exec_total_evolution.png
- exec_per_min_evolution.png

X-axis is normalized time in seconds since the first timestamp in the file.
"""
from __future__ import annotations

import re
import argparse
import numpy
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

import matplotlib.pyplot as plt


def entry_to_time(entry_n_array: numpy.ndarray) -> numpy.ndarray:
    assert ENTRY_NUMBER_VALUES_GLOBAL is not None
    assert TIMESTAMP_VALUES_GLOBAL is not None
    return numpy.interp(entry_n_array, ENTRY_NUMBER_VALUES_GLOBAL, TIMESTAMP_VALUES_GLOBAL, left=0)


def time_to_entry(timestamp_array: numpy.ndarray) -> numpy.ndarray:
    assert ENTRY_NUMBER_VALUES_GLOBAL is not None
    assert TIMESTAMP_VALUES_GLOBAL is not None
    return numpy.interp(timestamp_array, TIMESTAMP_VALUES_GLOBAL, ENTRY_NUMBER_VALUES_GLOBAL, left=0)


def initialize_convertion_functions(entry_values, timestamp_values):
    global ENTRY_NUMBER_VALUES_GLOBAL, TIMESTAMP_VALUES_GLOBAL
    ENTRY_NUMBER_VALUES_GLOBAL = entry_values
    TIMESTAMP_VALUES_GLOBAL = timestamp_values


def format_elapsed_time(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    if days:
        return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

STATUS_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"candidates=\d+\s+corpus=\d+\s+coverage=\d+\s+"
    r"exec total=(?P<exec_total>\d+)\s+\((?P<exec_rate>\d+)/min\)\s+pending=\d+\s+reproducing=\d+"
)


def parse_status_lines(path: Path) -> Tuple[List[int], List[int], List[datetime]]:
    exec_totals: List[int] = []
    exec_rates: List[int] = []
    timestamps: List[datetime] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = STATUS_LINE_RE.match(line)
            if not m:
                continue
            exec_totals.append(int(m.group("exec_total")))
            exec_rates.append(int(m.group("exec_rate")))
            timestamps.append(datetime.strptime(m.group("ts"), "%Y/%m/%d %H:%M:%S"))

    return exec_totals, exec_rates, timestamps


def normalize_timestamps(timestamps: List[datetime]) -> List[float]:
    if not timestamps:
        return []
    start = timestamps[0]
    return [(ts - start).total_seconds() for ts in timestamps]


def parse_time_value(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("time value must use hh:mm:ss format")
    try:
        hours, minutes, seconds = (int(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("time value must use hh:mm:ss format") from exc
    if hours < 0 or minutes < 0 or seconds < 0:
        raise argparse.ArgumentTypeError("time values must be non-negative")
    return hours * 3600 + minutes * 60 + seconds


def filter_by_elapsed_time(
    exec_totals: List[int],
    exec_rates: List[int],
    timestamps: List[datetime],
    skip_seconds: int,
) -> Tuple[List[int], List[int], List[datetime], List[float], List[int], List[int], List[datetime], List[float]]:
    if not timestamps:
        return [], [], [], [], [], [], [], []

    normalized = normalize_timestamps(timestamps)
    keep_mask = [elapsed >= skip_seconds for elapsed in normalized]
    filtered_totals = [value for value, keep in zip(exec_totals, keep_mask) if keep]
    filtered_rates = [value for value, keep in zip(exec_rates, keep_mask) if keep]
    filtered_timestamps = [ts for ts, keep in zip(timestamps, keep_mask) if keep]
    filtered_x = [elapsed for elapsed, keep in zip(normalized, keep_mask) if keep]

    skipped_totals = [value for value, keep in zip(exec_totals, keep_mask) if not keep]
    skipped_rates = [value for value, keep in zip(exec_rates, keep_mask) if not keep]
    skipped_timestamps = [ts for ts, keep in zip(timestamps, keep_mask) if not keep]
    skipped_x = [elapsed for elapsed, keep in zip(normalized, keep_mask) if not keep]
    return (
        filtered_totals,
        filtered_rates,
        filtered_timestamps,
        filtered_x,
        skipped_totals,
        skipped_rates,
        skipped_timestamps,
        skipped_x,
    )


def filter_by_max_elapsed_time(
    exec_totals: List[int],
    exec_rates: List[int],
    timestamps: List[datetime],
    max_seconds: int,
) -> Tuple[List[int], List[int], List[datetime], List[float]]:
    normalized = normalize_timestamps(timestamps)
    keep_mask = [elapsed <= max_seconds for elapsed in normalized]
    filtered_totals = [value for value, keep in zip(exec_totals, keep_mask) if keep]
    filtered_rates = [value for value, keep in zip(exec_rates, keep_mask) if keep]
    filtered_timestamps = [ts for ts, keep in zip(timestamps, keep_mask) if keep]
    filtered_x = [elapsed for elapsed, keep in zip(normalized, keep_mask) if keep]
    return (
        filtered_totals,
        filtered_rates,
        filtered_timestamps,
        filtered_x,
    )


def save_time_series(
    timestamps: List[float],
    y_values: List[int],
    out_name: Path,
    title: str,
    ylabel: str,
) -> None:
    '''
    timestamps is in seconds
    y_values, out_name, ylabel, title can be whatever

    Plot with two x_axes: entry number and timestamp on two modes:
        If the total elapsed time in timestamps is less than 2 hours, use minutes as the time unit.
        Else, use hours.
    '''
    s_in_h = 3600
    s_in_m = 60
    if not y_values:
        print(f"No data for {title}; skipping plot")
        return

    time_unit = None
    if timestamps[-1] - timestamps[0] > s_in_h * 2:
        timestamps = [t / s_in_h for t in timestamps]
        time_unit = "Hours"
    else:
        timestamps = [t / s_in_m for t in timestamps]
        time_unit = "Minutes"
    assert time_unit is not None
    initialize_convertion_functions(list(range(len(timestamps))), timestamps)


    fig = plt.figure(figsize=(10, 4))
    ax = fig.add_subplot(111)
    ax.plot(range(len(timestamps)), y_values, marker=".", linewidth=0.2)
    ax.set_title(title,loc="left",fontsize="15")
    ax.set_xlabel("Number of sample")
    ax.set_ylabel(ylabel)
    ax2 = ax.secondary_xaxis("top",functions=(entry_to_time,time_to_entry))
    ax2.set_xlabel(f"Elapsed time since first sample ({time_unit})")

    fig.tight_layout()
    fig.savefig(out_name)
    plt.close(fig)
    print(f"Saved {out_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot exec totals and exec/min from syzkaller status lines")
    parser.add_argument("input", type=Path, help="Path to the file containing status lines")
    parser.add_argument("--prefix", type=str, default="", help="Output filename prefix")
    parser.add_argument(
        "--skip-beginning",
        "--skip-time",
        dest="skip_beginning",
        type=parse_time_value,
        default=None,
        help="Ignore entries before this much elapsed time has passed (format: hh:mm:ss)",
    )
    parser.add_argument(
        "--cut-after",
        dest="cut_after_time",
        type=parse_time_value,
        default=None,
        help="Discard entries after this much elapsed time has passed (format: hh:mm:ss)",
    )
    args = parser.parse_args()

    skip_seconds = args.skip_beginning if args.skip_beginning is not None else 0
    cut_after_seconds = args.cut_after_time

    exec_totals, exec_rates, timestamps = parse_status_lines(args.input)
    (
        exec_totals,
        exec_rates,
        timestamps,
        x,
        skipped_totals,
        skipped_rates,
        skipped_timestamps,
        skipped_x,
    ) = filter_by_elapsed_time(exec_totals, exec_rates, timestamps, skip_seconds)

    if cut_after_seconds is not None:
        (
            exec_totals,
            exec_rates,
            timestamps,
            x,
        ) = filter_by_max_elapsed_time(exec_totals, exec_rates, timestamps, cut_after_seconds)

    prefix = args.prefix
    if prefix and not prefix.endswith("_"):
        prefix = prefix + "_"

    out_dir = Path.cwd() / "exec_over_time"
    suffix_parts = []
    if args.skip_beginning is not None:
        suffix_parts.append(
            f"skip_{args.skip_beginning // 3600:02d}_{(args.skip_beginning % 3600) // 60:02d}_{args.skip_beginning % 60:02d}"
        )
    if args.cut_after_time is not None:
        suffix_parts.append(
            f"cut_{args.cut_after_time // 3600:02d}_{(args.cut_after_time % 3600) // 60:02d}_{args.cut_after_time % 60:02d}"
        )
    suffix = ""
    if suffix_parts:
        suffix = "_" + "_".join(suffix_parts)
    out_total = out_dir / f"{prefix}exec_total_evolution{suffix}.png"
    out_rate = out_dir / f"{prefix}exec_per_min_evolution{suffix}.png"
    out_total_skipped = out_dir / f"{prefix}exec_total_evolution_skipped_prefix{suffix}.png"
    out_rate_skipped = out_dir / f"{prefix}exec_per_min_evolution_skipped_prefix{suffix}.png"

    save_time_series(x, exec_totals, out_total, "Exec total over time", "Exec total")
    save_time_series(x, exec_rates, out_rate, "Exec/min over time", "Exec/min")
    save_time_series(
        skipped_x,
        skipped_totals,
        out_total_skipped,
        "Exec total over skipped prefix",
        "Exec total",
    )
    save_time_series(
        skipped_x,
        skipped_rates,
        out_rate_skipped,
        "Exec/min over skipped prefix",
        "Exec/min",
    )


if __name__ == "__main__":
    main()
