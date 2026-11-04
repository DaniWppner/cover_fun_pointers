import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from scipy import stats  # type: ignore[import-untyped]

from processing.process_triage_metrics import EXECUTED_AFTER_STORE_SUBSETS

MAX_RUN_SPAN_DEVIATION = 0.05
RUN_DIR_HELP = "run_analysis_pipeline.py output directory of each run, e.g. <experiment>/analysis/run_*"


@dataclass(frozen=True)
class MannWhitneyResult:
    u: float
    a12: float
    p_two_sided: float
    p_greater: float
    p_less: float


def add_group_arguments(
    parser: argparse.ArgumentParser, require_group2: bool, metavar: str = "RUN_DIR", group1_help: str = RUN_DIR_HELP
) -> None:
    """
    Args:
        parser: parser of a script comparing groups of runs.
        require_group2: whether the script needs a second group, or can work on a single one.
        metavar: what the script takes for each run.
        group1_help: help of --group1.
    """
    parser.add_argument("--group1", nargs="+", type=Path, required=True, metavar=metavar, help=group1_help)
    parser.add_argument(
        "--group2", nargs="+", type=Path, required=require_group2, metavar=metavar, help="same as --group1"
    )
    parser.add_argument("--group1-label", type=str, default="Group 1")
    parser.add_argument("--group2-label", type=str, default="Group 2")


def print_groups(args: argparse.Namespace) -> None:
    """
    Args:
        args: parsed arguments of a parser set up by add_group_arguments, with both groups given.
    """
    print(f"Group 1 ({args.group1_label}): {', '.join(str(run) for run in args.group1)}")
    print(f"Group 2 ({args.group2_label}): {', '.join(str(run) for run in args.group2)}")


def assert_similar_run_spans(spans: list[float], group_paths: list[Path]) -> None:
    """
    Args:
        spans: seconds between the first and last status lines of each run in the group.
        group_paths: syz-manager logs of each run in the group, in the same order.
    """
    longest = max(spans)
    for span, path in zip(spans, group_paths, strict=True):
        assert longest - span <= longest * MAX_RUN_SPAN_DEVIATION, (
            f"{path} spans {span / 60:.0f} min, the longest run of its group spans {longest / 60:.0f} min"
        )


def executed_after_store_universes(group1_runs: list[dict[str, set[str]]]) -> dict[str, set[str]]:
    """
    Args:
        group1_runs: output of process_triage_metrics.get_functions_executed_after_store for each run of the first
            group, which must be function pointer campaigns.

    Returns:
        For each key of EXECUTED_AFTER_STORE_SUBSETS, names of the functions executed after being stored by a test
        of that subset in any run of the group.
    """
    universes: dict[str, set[str]] = {
        key: set().union(*(run[key] for run in group1_runs)) for key in EXECUTED_AFTER_STORE_SUBSETS
    }
    for key, funcs in universes.items():
        assert funcs, f"no function executed after being stored ({key}) in --group1: is it a function pointer group?"
    return universes


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


def print_mann_whitney(label: str, group1_label: str, values1: list[int], group2_label: str, values2: list[int]) -> None:
    """
    Args:
        label: name of the metric.
        group1_label: name of the first group.
        values1: value of the metric for each run of the first group.
        group2_label: name of the second group.
        values2: value of the metric for each run of the second group.
    """
    result = mann_whitney(values1, values2)
    print()
    print(label)
    print(f"  {group1_label}: {values1}")
    print(f"  {group2_label}: {values2}")
    print(f"  U = {result.u:g}, A12 = {result.a12:.3f}")
    print(f"  p (two-sided) = {result.p_two_sided:.4f}")
    print(f"  p ({group2_label} > {group1_label}) = {result.p_greater:.4f}")
    print(f"  p ({group2_label} < {group1_label}) = {result.p_less:.4f}")
