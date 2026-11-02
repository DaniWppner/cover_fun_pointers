#!/usr/bin/env python3
import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scipy import stats  # type: ignore[import-untyped]

from comparison_commons import add_group_arguments, assert_similar_run_spans
from plotting import plot_throughput_evolution
from processing import process_triage_metrics

METRIC_LABELS = {
    "stored_fpointers": "Unique stored functions",
    "executed_fpointers": "Unique executed stored functions",
    "coverage": "Unique covered locations",
}


@dataclass(frozen=True)
class MannWhitneyResult:
    u: float
    a12: float
    p_two_sided: float
    p_greater: float
    p_less: float


def run_end_metrics(run_dir: Path) -> dict[str, int]:
    """
    Args:
        run_dir: `--out-dir` of run_analysis_pipeline.py for the run.

    Returns:
        For each key of METRIC_LABELS, its value at the end of the run.
    """
    with (run_dir / "unified_triage_logs.json").open() as f:
        prog2log = process_triage_metrics.convert_types_nicely(json.load(f))
    prog2event: dict[str, dict[str, Any]] | None = None
    # The pipeline only creates it for logs that have events (base syzkaller)
    if (run_dir / "fpointer_events.json").exists():
        with (run_dir / "fpointer_events.json").open() as f:
            prog2event = process_triage_metrics.convert_types_nicely(json.load(f))

    _, _, _, fpointer_locs = process_triage_metrics.get_fPointerStore_dicts_and_locs(prog2log, prog2event)
    all_pc_locs = process_triage_metrics.get_unique_covered_locations(prog2log)
    _, executed_fpointer_locs = process_triage_metrics.locInfo_fname_diff(fpointer_locs, all_pc_locs)
    return {
        "stored_fpointers": len(fpointer_locs),
        "executed_fpointers": len(executed_fpointer_locs),
        "coverage": len(all_pc_locs),
    }


def load_group_end_metrics(run_dirs: list[Path]) -> list[dict[str, int]]:
    """
    Args:
        run_dirs: `--out-dir` of run_analysis_pipeline.py for each run in the group, holding the run's
            syz-manager.log too. All runs must span roughly the same time.

    Returns:
        For each run of the group, in the same order, the output of run_end_metrics.
    """
    run_dirs = [d.resolve() for d in run_dirs]
    logs = [d / "syz-manager.log" for d in run_dirs]
    assert_similar_run_spans([plot_throughput_evolution.parse_status_lines(log) for log in logs], logs)
    return [run_end_metrics(d) for d in run_dirs]


def mann_whitney(group1: list[int], group2: list[int]) -> MannWhitneyResult:
    """
    Args:
        group1: value of a metric for each run of the first group.
        group2: value of the same metric for each run of the second group.

    Returns:
        MannWhitneyResult with:
            u: U statistic of group2.
            a12: probability that a run of group2 scores higher than a run of group1, ties counting half.
            p_two_sided: p-value of group2 being distributed differently from group1.
            p_greater: p-value of group2 scoring higher than group1.
            p_less: p-value of group2 scoring lower than group1.
    """
    # Enumerating every split of the runs gives an exact p-value that, unlike method="exact", accounts for ties.
    # PermutationMethod falls back to random resamples above n_resamples splits, which would no longer be exact.
    method = stats.PermutationMethod()
    assert math.comb(len(group1) + len(group2), len(group1)) <= method.n_resamples, (
        "too many runs for an exact test"
    )
    two_sided = stats.mannwhitneyu(group2, group1, alternative="two-sided", method=method)
    greater = stats.mannwhitneyu(group2, group1, alternative="greater", method=method)
    less = stats.mannwhitneyu(group2, group1, alternative="less", method=method)
    return MannWhitneyResult(
        u=two_sided.statistic,
        a12=two_sided.statistic / (len(group1) * len(group2)),
        p_two_sided=two_sided.pvalue,
        p_greater=greater.pvalue,
        p_less=less.pvalue,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mann-Whitney U test of the end-of-campaign metrics of two groups of campaigns. "
        "One-sided p-values test group 2 scoring higher, or lower, than group 1"
    )
    add_group_arguments(parser, require_group2=True)
    args = parser.parse_args()

    group1 = load_group_end_metrics(args.group1)
    group2 = load_group_end_metrics(args.group2)

    print(f"Group 1 ({args.group1_label}): {', '.join(str(d) for d in args.group1)}")
    print(f"Group 2 ({args.group2_label}): {', '.join(str(d) for d in args.group2)}")
    for key, label in METRIC_LABELS.items():
        values1 = [run[key] for run in group1]
        values2 = [run[key] for run in group2]
        result = mann_whitney(values1, values2)
        print()
        print(label)
        print(f"  {args.group1_label}: {values1}")
        print(f"  {args.group2_label}: {values2}")
        print(f"  U = {result.u:g}, A12 = {result.a12:.3f}")
        print(f"  p (two-sided) = {result.p_two_sided:.4f}")
        print(f"  p ({args.group2_label} > {args.group1_label}) = {result.p_greater:.4f}")
        print(f"  p ({args.group2_label} < {args.group1_label}) = {result.p_less:.4f}")


if __name__ == "__main__":
    main()
