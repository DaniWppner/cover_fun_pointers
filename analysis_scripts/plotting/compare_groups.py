#!/usr/bin/env python3
import argparse
import bisect
import math
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from scipy import stats  # type: ignore[import-untyped]

from plotting import plot_metrics_evolution, plot_throughput_evolution

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
        index_label: x axis label of the plot by sample index.
        out_subdir: directory, under the current one, of the metric's plots.
        file_stem: prefix of the metric's PNG names.
    """
    key: str
    name: str
    index_label: str
    out_subdir: str
    file_stem: str


METRICS = [
    MetricSpec("exec_total", "Exec total", "Status line number", "exec_over_time", "grouped_exec_total"),
    MetricSpec("exec_rate", "Exec/min", "Status line number", "exec_over_time", "grouped_exec_per_min"),
    MetricSpec(
        "coverage", "Coverage", "Triaged prog|call entries finished", "coverage_over_time", "grouped_coverage"
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


def load_group_metrics(run_files: list[tuple[Path, Path]]) -> dict[str, list[RunSeries]]:
    """
    Args:
        run_files: (triage json, syz-manager log) of each run in the group. All runs must span roughly the same time.

    Returns:
        For each metric key of METRICS, the series of every run in the group.
    """
    logs = [log for _, log in run_files]
    status_lines = [plot_throughput_evolution.parse_status_lines(log) for log in logs]
    assert_similar_run_spans(status_lines, logs)

    return {
        "exec_total": [list(zip(s.timestamps, s.exec_totals)) for s in status_lines],
        "exec_rate": [list(zip(s.timestamps, s.exec_rates)) for s in status_lines],
        "coverage": [plot_metrics_evolution.process_log_json_pair(log, json_path) for json_path, log in run_files],
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
) -> None:
    """
    Args:
        metric: metric to plot.
        group_runs: for each group, the series of every run for this metric.
        labels: legend name of each group, in the same order.
        statistic: how the runs of a group are summarized.
        skip_first: number of leading samples hidden from the plot by index. The plot by time hides
            everything before the time given by skip_time_seconds.
    """
    out_dir = Path.cwd() / metric.out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    title = f"{metric.name} ({statistic.description})"

    by_index = [drop_before(band_by_index(runs, statistic), skip_first) for runs in group_runs]
    save_band_plot(
        by_index, labels, title, metric.index_label, metric.name, 1.0, out_dir / f"{metric.file_stem}_by_index.png"
    )

    skip_seconds = skip_time_seconds(group_runs, skip_first)
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


def run_dir_files(run_dirs: list[Path]) -> list[tuple[Path, Path]]:
    """
    Args:
        run_dirs: `--out-dir` of run_analysis_pipeline.py for each run, holding the run's syz-manager.log too.

    Returns:
        (triage json, syz-manager log) of each run.
    """
    return [(d.resolve() / "unified_triage_logs.json", d.resolve() / "syz-manager.log") for d in run_dirs]


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
        "index, and everything before the slowest run reached its N-th sample on the plots by time",
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
    group_metrics = [load_group_metrics(run_dir_files(run_dirs)) for run_dirs in groups]

    for metric in METRICS:
        save_metric_plots(
            metric,
            [metrics[metric.key] for metrics in group_metrics],
            labels,
            STATISTICS[args.statistic],
            args.skip_first,
        )


if __name__ == "__main__":
    main()
