#!/usr/bin/env python3
import argparse
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt

from plotting import plot_metrics_evolution, plot_throughput_evolution

MAX_RUN_SPAN_DEVIATION = 0.05


def assert_similar_run_spans(group_series: list[plot_throughput_evolution.SeriesData], group_paths: list[Path]) -> None:
    """
    Args:
        group_series: parsed status lines of each run in the group.
        group_paths: syz-manager logs of each run in the group, in the same order.
    """
    spans = [s.timestamps[-1] for s in group_series]
    longest = max(spans)
    for span, path in zip(spans, group_paths):
        assert longest - span <= longest * MAX_RUN_SPAN_DEVIATION, (
            f"{path} spans {span / 60:.0f} min, the longest run of its group spans {longest / 60:.0f} min"
        )


def compute_group_time_mapping(group_series: list[list[float]]) -> list[float]:
    """
    Args:
        group_series: normalized timestamps of each run in the group, indexed by sample number.

    Returns:
        Synthetic timestamp of each sample number for the whole group: starts at the average first
        timestamp and advances by the average gap between consecutive samples of the runs still alive.
    """
    max_len = max(len(s) for s in group_series)
    t0_vals = [s[0] for s in group_series]
    mapping = [sum(t0_vals) / len(t0_vals)]

    for i in range(1, max_len):
        deltas = [s[i] - s[i - 1] for s in group_series if len(s) > i]
        mapping.append(mapping[-1] + sum(deltas) / len(deltas))

    return mapping


def average_values_at_step(series_list: list[list[int]], step: int) -> int:
    """
    Args:
        series_list: values of each run in the group, indexed by sample number.
        step: sample number to average at. At least one run must reach it.

    Returns:
        Integer average of the runs that reached the given sample number.
    """
    vals = [s[step] for s in series_list if len(s) > step]
    return sum(vals) // len(vals)


def aggregate_throughput(group_paths: list[Path]) -> plot_throughput_evolution.SeriesData:
    """
    Args:
        group_paths: syz-manager logs of each run in the group. All runs must span roughly the same time.

    Returns:
        Average exec totals and exec rates of the group per status line number, on the synthetic group time axis.
    """
    parsed_series = [plot_throughput_evolution.parse_status_lines(p) for p in group_paths]
    assert_similar_run_spans(parsed_series, group_paths)
    synthetic_timestamps: list[datetime | float] = list(
        compute_group_time_mapping([s.timestamps for s in parsed_series])
    )

    synthetic_exec_totals = [
        average_values_at_step([s.exec_totals for s in parsed_series], i) for i in range(len(synthetic_timestamps))
    ]
    synthetic_exec_rates = [
        average_values_at_step([s.exec_rates for s in parsed_series], i) for i in range(len(synthetic_timestamps))
    ]

    return plot_throughput_evolution.SeriesData(
        exec_totals=synthetic_exec_totals,
        exec_rates=synthetic_exec_rates,
        timestamps=synthetic_timestamps,
    )


def parse_group_coverage(group_pairs: list[tuple[Path, Path]]) -> list[list[tuple[float, int]]]:
    """
    Args:
        group_pairs: (triage json, syz-manager log) of each run in the group.

    Returns:
        For each run, the (elapsed seconds, coverage) pair at the end of every triage job.
    """
    return [plot_metrics_evolution.process_log_json_pair(log_path, json_path) for json_path, log_path in group_pairs]


def aggregate_coverage_by_triage(group_coverage: list[list[tuple[float, int]]]) -> list[tuple[float, int]]:
    """
    Args:
        group_coverage: for each run, the (elapsed seconds, coverage) pair at the end of every triage job.

    Returns:
        Average coverage of the group per triage job number, paired with the synthetic group time axis.
    """
    synthetic_timestamps = compute_group_time_mapping([[p[0] for p in series] for series in group_coverage])
    coverages = [[p[1] for p in series] for series in group_coverage]

    return [(ts, average_values_at_step(coverages, i)) for i, ts in enumerate(synthetic_timestamps)]


def resample_into_time_buckets(series: list[tuple[float, int]], step_seconds: float) -> list[float]:
    """
    Args:
        series: (elapsed seconds, coverage) pairs of a single run, starting at 0 seconds.
        step_seconds: width of each time bucket.

    Returns:
        Coverage of the run at the end of each bucket: the mean of the triages that finished inside it,
        or the last known coverage if none did.
    """
    max_time = series[-1][0]
    time_steps = []
    t = 0.0
    while t <= max_time + step_seconds:
        time_steps.append(t)
        t += step_seconds

    aggregated_cov: list[float] = []
    for t_val in time_steps:
        window_points = [p for p in series if t_val - step_seconds < p[0] <= t_val]
        if window_points:
            aggregated_cov.append(sum(p[1] for p in window_points) / len(window_points))
        else:
            aggregated_cov.append([p for p in series if p[0] <= t_val][-1][1])

    return aggregated_cov


def average_bucketed_series(group_bucketed: list[list[float]]) -> list[float]:
    """
    Args:
        group_bucketed: coverage of each run in the group per time bucket.

    Returns:
        Average coverage of the runs still alive at each time bucket.
    """
    max_len = max(len(s) for s in group_bucketed)
    avg_coverages = []
    for i in range(max_len):
        vals = [s[i] for s in group_bucketed if len(s) > i]
        avg_coverages.append(sum(vals) / len(vals))

    return avg_coverages


def aggregate_coverage_by_time(
    group_coverage: list[list[tuple[float, int]]], step_seconds: float = 60.0
) -> tuple[list[float], list[float]]:
    """
    Args:
        group_coverage: for each run, the (elapsed seconds, coverage) pair at the end of every triage job.
        step_seconds: width of each time bucket.

    Returns:
        A tuple containing:
            - Elapsed seconds at the end of each time bucket.
            - Average coverage of the group at that time.
    """
    avg_coverages = average_bucketed_series([resample_into_time_buckets(s, step_seconds) for s in group_coverage])
    time_steps = [i * step_seconds for i in range(len(avg_coverages))]

    return time_steps, avg_coverages


def save_time_aligned_coverage(
    group_a: tuple[list[float], list[float]],
    group_b: tuple[list[float], list[float]] | None,
    out_file: Path,
    labels: tuple[str, str],
) -> None:
    """
    Args:
        group_a: (elapsed seconds, average coverage) per time bucket of the first group.
        group_b: (elapsed seconds, average coverage) per time bucket of the second group, if any.
        out_file: path of the PNG to write.
        labels: legend names of the first and second group.
    """
    fig = plt.figure(figsize=(10, 4))
    ax = fig.add_subplot(111)

    groups = [group_a] if group_b is None else [group_a, group_b]
    for (time_steps, coverages), label, color in zip(groups, labels, ("Blue", "Red")):
        ax.plot([t / 60 for t in time_steps], coverages, label=label, color=color, marker=".", linewidth=1)

    ax.set_title("Coverage Evolution (Time-Aligned)", loc="left", fontsize="15")
    ax.set_xlabel("Elapsed Time (Minutes)")
    ax.set_ylabel("Coverage Score")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_file)
    plt.close(fig)
    print(f"Saved {out_file}")


def run_dir_files(run_dirs: list[Path]) -> list[tuple[Path, Path]]:
    """
    Args:
        run_dirs: `--out-dir` of run_analysis_pipeline.py for each run, holding the run's syz-manager.log too.

    Returns:
        (triage json, syz-manager log) of each run.
    """
    return [(d.resolve() / "unified_triage_logs.json", d.resolve() / "syz-manager.log") for d in run_dirs]


def main() -> None:
    parser = argparse.ArgumentParser(description="Wrapper to plot average metrics/throughput of groups of campaigns")
    parser.add_argument(
        "--group1",
        nargs="+",
        type=Path,
        required=True,
        metavar="RUN_DIR",
        help="run_analysis_pipeline.py output directory of each run, e.g. <experiment>/analysis/run_*",
    )
    parser.add_argument("--group2", nargs="+", type=Path, metavar="RUN_DIR", help="same as --group1")
    parser.add_argument("--group1-label", type=str, default="Group 1")
    parser.add_argument("--group2-label", type=str, default="Group 2")
    args = parser.parse_args()

    g1_pairs = run_dir_files(args.group1)
    g2_pairs = run_dir_files(args.group2) if args.group2 is not None else None
    labels = (args.group1_label, args.group2_label)

    throughput_series_list = [aggregate_throughput([log for _, log in g1_pairs])]
    if g2_pairs is not None:
        throughput_series_list.append(aggregate_throughput([log for _, log in g2_pairs]))

    out_dir_t = Path.cwd() / "exec_over_time"
    out_dir_t.mkdir(parents=True, exist_ok=True)
    throughput_labels = labels[: len(throughput_series_list)]
    plot_throughput_evolution.save_time_series(
        throughput_series_list,
        out_dir_t / "grouped_exec_total_evolution.png",
        "Exec total over time (Group Average)",
        "Exec total",
        "exec_totals",
        throughput_labels,
    )
    plot_throughput_evolution.save_time_series(
        throughput_series_list,
        out_dir_t / "grouped_exec_per_min_evolution.png",
        "Exec/min over time (Group Average)",
        "Exec/min",
        "exec_rates",
        throughput_labels,
    )

    g1_coverage = parse_group_coverage(g1_pairs)
    g2_coverage = parse_group_coverage(g2_pairs) if g2_pairs is not None else None

    by_triage_a = aggregate_coverage_by_triage(g1_coverage)
    by_triage_b = aggregate_coverage_by_triage(g2_coverage) if g2_coverage is not None else None

    out_dir_m = Path.cwd() / "coverage_over_time"
    out_dir_m.mkdir(parents=True, exist_ok=True)
    plot_metrics_evolution.save_coverage_time_series(
        by_triage_a,
        by_triage_b,
        out_dir_m / "grouped_coverage_evolution.png",
        "Coverage Evolution over Triages (Index-Aligned Average)",
        labels=labels,
    )

    save_time_aligned_coverage(
        aggregate_coverage_by_time(g1_coverage),
        aggregate_coverage_by_time(g2_coverage) if g2_coverage is not None else None,
        out_dir_m / "grouped_coverage_evolution_time_aligned.png",
        labels,
    )


if __name__ == "__main__":
    main()
