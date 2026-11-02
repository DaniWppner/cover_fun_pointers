import argparse
from pathlib import Path

from plotting import plot_throughput_evolution

MAX_RUN_SPAN_DEVIATION = 0.05


def add_group_arguments(parser: argparse.ArgumentParser, require_group2: bool) -> None:
    """
    Args:
        parser: parser of a script comparing groups of runs.
        require_group2: whether the script needs a second group, or can work on a single one.
    """
    parser.add_argument(
        "--group1",
        nargs="+",
        type=Path,
        required=True,
        metavar="RUN_DIR",
        help="run_analysis_pipeline.py output directory of each run, e.g. <experiment>/analysis/run_*",
    )
    parser.add_argument(
        "--group2", nargs="+", type=Path, required=require_group2, metavar="RUN_DIR", help="same as --group1"
    )
    parser.add_argument("--group1-label", type=str, default="Group 1")
    parser.add_argument("--group2-label", type=str, default="Group 2")


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
