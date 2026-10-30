#!/usr/bin/env python3
import argparse
import bisect
import itertools
import json
import math
import statistics
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from scipy import stats  # type: ignore[import-untyped]

from logentry_keys import RESULT_KEYS, locInfo
from plotting import plot_metrics_evolution, plot_throughput_evolution
from processing import process_triage_metrics

MAX_RUN_SPAN_DEVIATION = 0.05
BUCKET_SECONDS = 60.0

# (elapsed seconds, value) samples of a single run, in chronological order, starting at 0 seconds
type RunSeries = Sequence[tuple[float, float]]


@dataclass(frozen=True)
class GroupStatistic:
    """
    How the runs of a group are summarized at each sample.

    Attributes:
        description: what the line and the band show, used in plot titles.
        summarize: maps the values of the runs at one sample to (line, band low, band high).
    """
    description: str
    summarize: Callable[[list[float]], tuple[float, float, float]]


@dataclass
class GroupBand:
    """
    Summary of one group for one metric, ready to plot.

    Attributes:
        x: sample index or elapsed seconds of each point.
        line: center value at each point.
        low: lower edge of the band at each point.
        high: upper edge of the band at each point.
    """
    x: list[float]
    line: list[float]
    low: list[float]
    high: list[float]


@dataclass(frozen=True)
class MetricSpec:
    """
    Attributes:
        key: key of the metric in the output of load_group_metrics.
        name: plot title prefix and y axis label.
        index_label: x axis label of the plot by sample index, None if the samples are time buckets and only the
            plot by time is drawn.
        out_subdir: directory, under the current one, of the metric's plots.
        file_stem: prefix of the metric's PNG names.
        skip_by: key of the metric whose samples --skip-first counts to cut the plot by time.
    """
    key: str
    name: str
    index_label: str | None
    out_subdir: str
    file_stem: str
    skip_by: str


METRICS = [
    MetricSpec(
        "exec_total", "Exec total", "Status line number", "exec_over_time", "grouped_exec_total", "exec_total"
    ),
    MetricSpec("exec_rate", "Exec/min", "Status line number", "exec_over_time", "grouped_exec_per_min", "exec_rate"),
    MetricSpec(
        "coverage",
        "Coverage",
        "Triaged prog|call entries finished",
        "coverage_over_time",
        "grouped_coverage",
        "coverage",
    ),
    MetricSpec(
        "stored_fpointers",
        "Unique stored function pointers",
        None,
        "fpointers_over_time",
        "grouped_stored_fpointers",
        "coverage",
    ),
    MetricSpec(
        "executed_fpointers",
        "Unique executed stored function pointers",
        None,
        "fpointers_over_time",
        "grouped_executed_fpointers",
        "coverage",
    ),
]


def mean_min_max(values: list[float]) -> tuple[float, float, float]:
    """
    Args:
        values: values of the runs at one sample.

    Returns:
        A tuple containing:
            - Mean of the runs.
            - Lowest run.
            - Highest run.
    """
    return sum(values) / len(values), min(values), max(values)


MEAN_MIN_MAX = GroupStatistic("mean, band from min to max", mean_min_max)

def mean_t_ci95(values: list[float]) -> tuple[float, float, float]:
    """
    Args:
        values: values of the runs at one sample.

    Returns:
        A tuple containing:
            - Mean of the runs.
            - Lower edge of the 95% confidence interval of the mean, NaN if only one run reached the sample.
            - Upper edge of the 95% confidence interval of the mean, NaN if only one run reached the sample.
    """
    mean = statistics.fmean(values)
    if len(values) == 1:
        return mean, math.nan, math.nan

    critical = float(stats.t.ppf(0.975, df=len(values) - 1))
    half_width = critical * statistics.stdev(values) / math.sqrt(len(values))
    return mean, mean - half_width, mean + half_width


MEAN_T_CI95 = GroupStatistic("mean, band is its 95% t confidence interval", mean_t_ci95)

STATISTICS = {"ci95": MEAN_T_CI95, "minmax": MEAN_MIN_MAX}


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


def time_bucket(timestamp: datetime, t0: datetime) -> int:
    """
    Args:
        timestamp: time of something that happened in the run.
        t0: time of the first status line of the run.

    Returns:
        Index of the first sample, taken every BUCKET_SECONDS from t0, whose state includes it.
    """
    # Triages that finished before the first status line are already part of the state at t=0.
    return max(0, math.ceil((timestamp - t0).total_seconds() / BUCKET_SECONDS))


def cumulative_series(first_buckets: Iterable[int], n_buckets: int) -> RunSeries:
    """
    Args:
        first_buckets: for each counted item, the time bucket where it first appears.
        n_buckets: number of samples of the series.

    Returns:
        Number of items that appeared at or before each sample, every BUCKET_SECONDS from 0 seconds.
    """
    new_per_bucket = Counter(first_buckets)
    running_counts = itertools.accumulate(new_per_bucket[bucket] for bucket in range(n_buckets))
    return [(bucket * BUCKET_SECONDS, count) for bucket, count in zip(range(n_buckets), running_counts)]


def first_stored_buckets(
    sources: list[dict[str, dict[str, Any]]], t0: datetime
) -> tuple[dict[str, int], dict[str, list[locInfo]]]:
    """
    Args:
        sources: prog2log and stored function pointers events of the same run, both converted with
            process_triage_metrics.convert_types_nicely. Their keys may repeat across sources.
        t0: time of the first status line of the run.

    Returns:
        A tuple containing:
            - For each stored function pointer value, the time bucket where it was first stored.
            - For each stored function pointer value, its source locations.
    """
    # Every entry is a slice of its own: the stored function pointers of a set of entries are the union of theirs.
    slices = sorted(
        ((entry[RESULT_KEYS.TIMESTAMP_END], {key: entry}) for source in sources for key, entry in source.items()),
        key=lambda end_and_slice: end_and_slice[0],
    )
    stored_bucket: dict[str, int] = {}
    fpointer_addr2loc: dict[str, list[locInfo]] = {}
    for end, entry_slice in slices:
        _, slice_addr2loc, _, _ = process_triage_metrics.get_fPointerStore_dicts_and_locs(entry_slice)
        for fpointer in slice_addr2loc:
            stored_bucket.setdefault(fpointer, time_bucket(end, t0))
        fpointer_addr2loc.update(slice_addr2loc)
    return stored_bucket, fpointer_addr2loc


def fpointer_series(
    prog2log: dict[str, dict[str, Any]],
    prog2event: dict[str, dict[str, Any]],
    t0: datetime,
    t_last: datetime,
) -> tuple[RunSeries, RunSeries]:
    """
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair,
            converted with process_triage_metrics.convert_types_nicely.
        prog2event: stored function pointers events of the same run (fpointer_events.json), converted the same way.
            Empty for patched syzkaller, which reports them inside the triage entries instead.
        t0: time of the first status line of the run.
        t_last: time of the last status line of the run.

    Returns:
        A tuple containing:
            - Unique stored function pointer values, cumulative.
            - Unique stored function pointer values whose function (the non-inlined frame) had been executed,
              inlined copies included, cumulative. A pointer counts from the time it was both stored and executed.
    """
    stored_bucket, fpointer_addr2loc = first_stored_buckets([prog2log, prog2event], t0)
    function_cover_map = process_triage_metrics.get_function_pointer_coverage_timeline(prog2log)
    first_executed = {
        func_name: min(min_end for _, min_end, _, _ in loc_dict.values())
        for func_name, loc_dict in function_cover_map.items()
    }
    executed_bucket = {
        fpointer: max(stored_bucket[fpointer], time_bucket(first_executed[locs[-1][1]], t0))
        for fpointer, locs in fpointer_addr2loc.items()
        if locs[-1][1] in first_executed
    }
    n_buckets = 1 + max([time_bucket(t_last, t0), *stored_bucket.values(), *executed_bucket.values()])
    return cumulative_series(stored_bucket.values(), n_buckets), cumulative_series(executed_bucket.values(), n_buckets)


def load_run_triage_metrics(run_dir: Path) -> tuple[RunSeries, RunSeries, RunSeries]:
    """
    Args:
        run_dir: `--out-dir` of run_analysis_pipeline.py for the run, holding the run's syz-manager.log too.

    Returns:
        A tuple containing the run's series of:
            - Coverage, by triaged prog|call entry (see plot_metrics_evolution.process_log_json_pair).
            - Unique stored function pointers, by time bucket (see fpointer_series).
            - Unique executed stored function pointers, by time bucket (see fpointer_series).
    """
    with (run_dir / "unified_triage_logs.json").open() as f:
        prog2log = process_triage_metrics.convert_types_nicely(json.load(f))
    prog2event: dict[str, dict[str, Any]] = {}
    # The pipeline only creates it for logs that have events (base syzkaller)
    if (run_dir / "fpointer_events.json").exists():
        with (run_dir / "fpointer_events.json").open() as f:
            prog2event = process_triage_metrics.convert_types_nicely(json.load(f))

    timestamp_x_coverage = plot_metrics_evolution.parse_status_lines(run_dir / "syz-manager.log")
    coverage = plot_metrics_evolution.coverage_by_triage(prog2log, timestamp_x_coverage)
    stored, executed = fpointer_series(
        prog2log, prog2event, timestamp_x_coverage[0][0], timestamp_x_coverage[-1][0]
    )
    return coverage, stored, executed


def load_group_metrics(run_dirs: list[Path]) -> dict[str, list[RunSeries]]:
    """
    Args:
        run_dirs: `--out-dir` of run_analysis_pipeline.py for each run in the group, holding the run's
            syz-manager.log too. All runs must span roughly the same time.

    Returns:
        For each metric key of METRICS, the series of every run in the group.
    """
    run_dirs = [d.resolve() for d in run_dirs]
    logs = [d / "syz-manager.log" for d in run_dirs]
    status_lines = [plot_throughput_evolution.parse_status_lines(log) for log in logs]
    assert_similar_run_spans(status_lines, logs)
    triage_metrics = [load_run_triage_metrics(d) for d in run_dirs]

    return {
        "exec_total": [list(zip(s.timestamps, s.exec_totals)) for s in status_lines],
        "exec_rate": [list(zip(s.timestamps, s.exec_rates)) for s in status_lines],
        "coverage": [coverage for coverage, _, _ in triage_metrics],
        "stored_fpointers": [stored for _, stored, _ in triage_metrics],
        "executed_fpointers": [executed for _, _, executed in triage_metrics],
    }


def resample_into_time_buckets(series: RunSeries, step_seconds: float) -> list[float]:
    """
    Args:
        series: samples of a single run.
        step_seconds: width of each time bucket.

    Returns:
        Value of the run at the end of each bucket: the mean of the samples inside it,
        or the last known value if there are none.
    """
    max_time = series[-1][0]
    bucket_values: list[float] = []
    next_point = 0
    t = 0.0
    while t <= max_time + step_seconds:
        window_start = next_point
        while next_point < len(series) and series[next_point][0] <= t:
            next_point += 1
        if next_point > window_start:
            window_sum = sum(p[1] for p in series[window_start:next_point])
            bucket_values.append(window_sum / (next_point - window_start))
        else:
            assert next_point > 0, f"no sample at or before {t} s: the series must start at 0 seconds"
            bucket_values.append(series[next_point - 1][1])
        t += step_seconds

    return bucket_values


def values_at_step(group_values: Sequence[Sequence[float]], step: int) -> list[float]:
    """
    Args:
        group_values: values of each run in the group, indexed by step.
        step: step to read. At least one run must reach it.

    Returns:
        Values of the runs that reached the given step.
    """
    return [values[step] for values in group_values if len(values) > step]


def band_over_steps(
    group_values: Sequence[Sequence[float]], x_of_step: Callable[[int], float], statistic: GroupStatistic
) -> GroupBand:
    """
    Args:
        group_values: values of each run in the group, indexed by step.
        x_of_step: x coordinate of each step.
        statistic: how the runs are summarized at each step.

    Returns:
        The group summarized at every step reached by at least one run.
    """
    longest = max(len(values) for values in group_values)
    summaries = [statistic.summarize(values_at_step(group_values, step)) for step in range(longest)]

    return GroupBand(
        x=[x_of_step(step) for step in range(longest)],
        line=[s[0] for s in summaries],
        low=[s[1] for s in summaries],
        high=[s[2] for s in summaries],
    )


def band_by_index(group_runs: list[RunSeries], statistic: GroupStatistic) -> GroupBand:
    """
    Args:
        group_runs: series of each run in the group.
        statistic: how the runs are summarized at each sample index.

    Returns:
        The group summarized at the i-th sample of each run, with x being the sample index.
    """
    return band_over_steps([[value for _, value in run] for run in group_runs], float, statistic)


def band_by_time(group_runs: list[RunSeries], statistic: GroupStatistic, step_seconds: float) -> GroupBand:
    """
    Args:
        group_runs: series of each run in the group.
        statistic: how the runs are summarized at each time bucket.
        step_seconds: width of each time bucket.

    Returns:
        The group summarized at the end of each time bucket, with x being elapsed seconds.
    """
    bucketed = [resample_into_time_buckets(run, step_seconds) for run in group_runs]
    return band_over_steps(bucketed, lambda step: step * step_seconds, statistic)


def skip_time_seconds(group_runs: list[list[RunSeries]], skip_first: int) -> float:
    """
    Args:
        group_runs: for each group, the series of every run for one metric.
        skip_first: number of leading samples hidden from the plots by index. Every run must have more.

    Returns:
        Elapsed seconds at which the slowest run of any group reached its sample number skip_first.
        Hiding everything before it on the time plots hides at least those samples of every run.
    """
    return max(run[skip_first][0] for runs in group_runs for run in runs)


def drop_before(band: GroupBand, x_min: float) -> GroupBand:
    """
    Args:
        band: summary of one group, with x in increasing order.
        x_min: first x to keep.

    Returns:
        The points of the band from x_min on.
    """
    first = bisect.bisect_left(band.x, x_min)
    return GroupBand(band.x[first:], band.line[first:], band.low[first:], band.high[first:])


def time_axis_unit(bands: list[GroupBand]) -> tuple[str, float]:
    """
    Args:
        bands: bands plotted against elapsed seconds.

    Returns:
        A tuple containing:
            - "Hours" if the longest band spans more than 2 hours, otherwise "Minutes".
            - Seconds in that unit.
    """
    longest = max(band.x[-1] for band in bands)
    return ("Hours", 3600.0) if longest > 2 * 3600 else ("Minutes", 60.0)


def save_band_plot(
    bands: list[GroupBand],
    labels: Sequence[str],
    title: str,
    xlabel: str,
    ylabel: str,
    x_divisor: float,
    out_file: Path,
) -> None:
    """
    Args:
        bands: one band per group.
        labels: legend name of each group, in the same order.
        title: title of the plot.
        xlabel: label of the x axis.
        ylabel: label of the y axis.
        x_divisor: every x is divided by it before plotting, to change its unit.
        out_file: path of the PNG to write.
    """
    fig = plt.figure(figsize=(10, 4))
    ax = fig.add_subplot(111)

    for band, label, color in zip(bands, labels, ("tab:blue", "tab:orange")):
        x = [v / x_divisor for v in band.x]
        ax.plot(x, band.line, color=color, linewidth=1, label=label)
        ax.fill_between(x, band.low, band.high, color=color, alpha=0.2, linewidth=0)

    ax.set_title(title, loc="left", fontsize="15")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_file)
    plt.close(fig)
    print(f"Saved {out_file}")


def save_metric_plots(
    metric: MetricSpec,
    group_runs: list[list[RunSeries]],
    labels: Sequence[str],
    statistic: GroupStatistic,
    skip_first: int,
    skip_seconds: float,
) -> None:
    """
    Args:
        metric: metric to plot.
        group_runs: for each group, the series of every run for this metric.
        labels: legend name of each group, in the same order.
        statistic: how the runs of a group are summarized.
        skip_first: number of leading samples hidden from the plot by index.
        skip_seconds: elapsed seconds hidden from the plot by time (see skip_time_seconds).
    """
    out_dir = Path.cwd() / metric.out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    title = f"{metric.name} ({statistic.description})"

    if metric.index_label is not None:
        by_index = [drop_before(band_by_index(runs, statistic), skip_first) for runs in group_runs]
        save_band_plot(
            by_index,
            labels,
            title,
            metric.index_label,
            metric.name,
            1.0,
            out_dir / f"{metric.file_stem}_by_index.png",
        )

    by_time = [drop_before(band_by_time(runs, statistic, BUCKET_SECONDS), skip_seconds) for runs in group_runs]
    unit, seconds_per_unit = time_axis_unit(by_time)
    save_band_plot(
        by_time,
        labels,
        title,
        f"Elapsed time ({unit})",
        metric.name,
        seconds_per_unit,
        out_dir / f"{metric.file_stem}_by_time.png",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot the metrics/throughput of one or two groups of campaigns")
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
    parser.add_argument(
        "--skip-first",
        type=int,
        default=0,
        metavar="N",
        help="hide the first N samples (status lines, or triaged prog|call entries for coverage) of the plots by "
        "index, and everything before the slowest run reached its N-th sample on the plots by time. The function "
        "pointer plots, only by time, are cut like coverage",
    )
    parser.add_argument(
        "--statistic",
        choices=STATISTICS,
        default="ci95",
        help="line and band drawn for each group: mean with its 95%% t confidence interval, or mean with the "
        "min/max of the runs",
    )
    args = parser.parse_args()

    groups = [args.group1] if args.group2 is None else [args.group1, args.group2]
    labels = (args.group1_label, args.group2_label)
    group_metrics = [load_group_metrics(run_dirs) for run_dirs in groups]

    for metric in METRICS:
        save_metric_plots(
            metric,
            [metrics[metric.key] for metrics in group_metrics],
            labels,
            STATISTICS[args.statistic],
            args.skip_first,
            skip_time_seconds([metrics[metric.skip_by] for metrics in group_metrics], args.skip_first),
        )


if __name__ == "__main__":
    main()
