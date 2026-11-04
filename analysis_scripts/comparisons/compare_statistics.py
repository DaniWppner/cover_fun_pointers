#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any

from comparisons.comparison_commons import (
    add_group_arguments,
    assert_similar_run_spans,
    executed_after_store_universes,
    print_groups,
    print_mann_whitney,
)
from logentry_keys import locInfo
from plotting import plot_throughput_evolution
from processing import process_triage_metrics

METRIC_LABELS = {
    "stored_fpointers": "Unique stored functions",
    "executed_fpointers": "Unique executed stored functions",
    "coverage": "Unique covered locations",
} | {
    key: f"Covered locations of functions executed after being stored in --group1 ({description})"
    for key, (description, _) in process_triage_metrics.EXECUTED_AFTER_STORE_SUBSETS.items()
}


def run_end_metrics(run_dir: Path) -> tuple[dict[str, int], set[locInfo], dict[str, set[str]]]:
    """
    Args:
        run_dir: `--out-dir` of run_analysis_pipeline.py for the run.

    Returns:
        A tuple containing:
            - For each key of METRIC_LABELS that does not depend on --group1, its value at the end of the run.
            - Locations covered by the run.
            - Functions executed after being stored (see process_triage_metrics.get_functions_executed_after_store).
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
    executed_after_store = process_triage_metrics.get_functions_executed_after_store(
        prog2log, process_triage_metrics.get_function_pointer_coverage_timeline(prog2log)
    )
    metrics = {
        "stored_fpointers": len(fpointer_locs),
        "executed_fpointers": len(executed_fpointer_locs),
        "coverage": len(all_pc_locs),
    }
    return metrics, all_pc_locs, executed_after_store


def load_group_end_metrics(run_dirs: list[Path]) -> list[tuple[dict[str, int], set[locInfo], dict[str, set[str]]]]:
    """
    Args:
        run_dirs: `--out-dir` of run_analysis_pipeline.py for each run in the group, holding the run's
            syz-manager.log too. All runs must span roughly the same time.

    Returns:
        For each run of the group, in the same order, the output of run_end_metrics.
    """
    run_dirs = [d.resolve() for d in run_dirs]
    logs = [d / "syz-manager.log" for d in run_dirs]
    assert_similar_run_spans([plot_throughput_evolution.parse_status_lines(log).timestamps[-1] for log in logs], logs)
    return [run_end_metrics(d) for d in run_dirs]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mann-Whitney U test of the end-of-campaign metrics of two groups of campaigns. "
        "One-sided p-values test group 2 scoring higher, or lower, than group 1"
    )
    add_group_arguments(parser, require_group2=True)
    args = parser.parse_args()

    group1_runs = load_group_end_metrics(args.group1)
    group2_runs = load_group_end_metrics(args.group2)
    universes = executed_after_store_universes([executed_after_store for _, _, executed_after_store in group1_runs])
    group1, group2 = (
        [
            metrics | {key: sum(1 for _, fname in covered_locs if fname in funcs) for key, funcs in universes.items()}
            for metrics, covered_locs, _ in group_runs
        ]
        for group_runs in (group1_runs, group2_runs)
    )

    print_groups(args)
    for key, funcs in universes.items():
        print(f"Functions executed after being stored in group 1 ({key}): {len(funcs)}")
    for key, label in METRIC_LABELS.items():
        print_mann_whitney(
            label, args.group1_label, [run[key] for run in group1], args.group2_label, [run[key] for run in group2]
        )


if __name__ == "__main__":
    main()
