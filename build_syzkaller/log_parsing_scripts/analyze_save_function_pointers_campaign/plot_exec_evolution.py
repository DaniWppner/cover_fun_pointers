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
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

import matplotlib.pyplot as plt


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


def parse_skip_time(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("skip-time must use hh:mm:ss format")
    try:
        hours, minutes, seconds = (int(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("skip-time must use hh:mm:ss format") from exc
    if hours < 0 or minutes < 0 or seconds < 0:
        raise argparse.ArgumentTypeError("skip-time values must be non-negative")
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


def save_time_series(
    x: List[float],
    y: List[int],
    out_name: Path,
    title: str,
    ylabel: str,
) -> None:
    if not y:
        print(f"No data for {title}; skipping plot")
        return

    plt.figure(figsize=(10, 4))
    plt.plot(x, y, marker="o", linewidth=1)
    plt.title(title)
    plt.xlabel("Elapsed time since first sample")
    plt.ylabel(ylabel)

    if len(x) > 1:
        step = max(1, len(x) // 8)
        ticks_idx = list(range(0, len(x), step))
        if ticks_idx[-1] != len(x) - 1:
            ticks_idx.append(len(x) - 1)
        tick_positions = [x[i] for i in ticks_idx]
        tick_labels = [format_elapsed_time(pos) for pos in tick_positions]
        plt.xticks(tick_positions, tick_labels, rotation=45, ha="right")

    plt.xlim(left=0)
    plt.tight_layout()
    plt.savefig(out_name)
    plt.close()
    print(f"Saved {out_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot exec totals and exec/min from syzkaller status lines")
    parser.add_argument("input", type=Path, help="Path to the file containing status lines")
    parser.add_argument("--prefix", type=str, default="", help="Output filename prefix")
    parser.add_argument(
        "--skip-time",
        type=parse_skip_time,
        default=0,
        help="Ignore entries until this much elapsed time has passed (format: hh:mm:ss)",
    )
    args = parser.parse_args()

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
    ) = filter_by_elapsed_time(exec_totals, exec_rates, timestamps, args.skip_time)

    prefix = args.prefix
    if prefix and not prefix.endswith("_"):
        prefix = prefix + "_"

    cwd = Path.cwd()
    skip_suffix = f"_skip_{args.skip_time // 3600:02d}_{(args.skip_time % 3600) // 60:02d}_{args.skip_time % 60:02d}"
    out_total = cwd / f"{prefix}exec_total_evolution{skip_suffix}.png"
    out_rate = cwd / f"{prefix}exec_per_min_evolution{skip_suffix}.png"
    out_total_skipped = cwd / f"{prefix}exec_total_evolution_skipped_prefix{skip_suffix}.png"
    out_rate_skipped = cwd / f"{prefix}exec_per_min_evolution_skipped_prefix{skip_suffix}.png"

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
