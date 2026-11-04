#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from comparisons import compare_groups
from comparisons.comparison_commons import add_group_arguments, print_groups, print_mann_whitney
from logentry_keys import FPOINTERS_PAYLOAD_VALUES, RESULT_KEYS, locInfo
from processing import process_triage_metrics

UNIVERSE_KEY = "after_store_base_events"

METRIC = compare_groups.MetricSpec(
    UNIVERSE_KEY,
    "After-store locs (base store events)",
    None,
    "fpointers_over_time",
    f"grouped_{UNIVERSE_KEY}",
    "coverage",
)


def get_functions_executed_after_store_event(
    prog2log: dict[str, dict[str, Any]],
    prog2event: dict[str, dict[str, Any]],
    fPointer_coverage_timeline: dict[str, dict[locInfo, tuple[datetime, datetime, int, list[str]]]],
    same_triage_window: timedelta,
) -> set[str]:
    """
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.
        prog2event: stored function pointers events of the same run (fpointer_events.json), in the same format.
        fPointer_coverage_timeline: The output of get_function_pointer_coverage_timeline for prog2log.
        same_triage_window: longest delay between a store event and the triage of its own prog|call pair that
            still counts that triage as the one that stored the pointer.

    Returns:
        Names of the functions that a store event stored a pointer to, and whose first executing triage started
        strictly after that event and is not the triage of the event itself.
    """
    first_begin: dict[str, datetime] = {}
    first_jobs: dict[str, set[str]] = {}
    for fname, loc_dict in fPointer_coverage_timeline.items():
        jobs = {job for _, _, _, job_keys in loc_dict.values() for job in job_keys}
        first_begin[fname] = min(prog2log[job][RESULT_KEYS.TIMESTAMP_BEGIN] for job in jobs)
        first_jobs[fname] = {job for job in jobs if prog2log[job][RESULT_KEYS.TIMESTAMP_BEGIN] == first_begin[fname]}

    executed_after_store: set[str] = set()
    for event_key, event in prog2event.items():
        # Base events are instants: TIMESTAMP_BEGIN and TIMESTAMP_END are the same.
        stored_at = event[RESULT_KEYS.TIMESTAMP_END]
        for fPointer_entry in event[RESULT_KEYS.NEW_FPOINTERS_PAYLOAD]:
            fname = fPointer_entry[FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC][-1][1]
            if fname not in first_begin:
                continue
            same_triage = event_key in first_jobs[fname] and first_begin[fname] - stored_at <= same_triage_window
            if first_begin[fname] > stored_at and not same_triage:
                executed_after_store.add(fname)
    return executed_after_store


def base_run_universe(run_dir: Path, same_triage_window: timedelta) -> set[str]:
    """
    Args:
        run_dir: `--out-dir` of run_analysis_pipeline.py for a base syzkaller run.
        same_triage_window: see get_functions_executed_after_store_event.

    Returns:
        The output of get_functions_executed_after_store_event for the run.
    """
    with (run_dir / "unified_triage_logs.json").open() as f:
        prog2log = process_triage_metrics.convert_types_nicely(json.load(f))
    with (run_dir / "fpointer_events.json").open() as f:
        prog2event = process_triage_metrics.convert_types_nicely(json.load(f))
    timeline = process_triage_metrics.get_function_pointer_coverage_timeline(prog2log)
    return get_functions_executed_after_store_event(prog2log, prog2event, timeline, same_triage_window)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two groups of campaigns on the covered locations of the functions that base syzkaller "
        "(--group1) executed after storing a pointer to them: Mann-Whitney U test of the end-of-campaign values on "
        "stdout, and their plot by time under the current directory. One-sided p-values test group 2 scoring higher, "
        "or lower, than group 1"
    )
    add_group_arguments(parser, require_group2=True)
    parser.add_argument(
        "--same-triage-window",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="a store event's own prog|call triage starting at most this long after it counts as the triage that "
        "stored the pointer, so it does not make the function executed after the store",
    )
    parser.add_argument("--statistic", choices=compare_groups.STATISTICS, default="ci95", help="see compare_groups.py")
    args = parser.parse_args()

    window = timedelta(seconds=args.same_triage_window)
    universe: set[str] = set().union(*(base_run_universe(d.resolve(), window) for d in args.group1))
    assert universe, "no function executed after a store event in --group1: is it a base syzkaller group?"

    group_runs = [compare_groups.load_group_metrics(run_dirs)[1] for run_dirs in (args.group1, args.group2)]
    group1, group2 = (
        [sum(1 for _, fname in run.first_covered_bucket if fname in universe) for run in runs] for runs in group_runs
    )

    print_groups(args)
    print(f"Functions executed after a store event in group 1: {len(universe)}")
    print_mann_whitney(
        "Covered locations of functions executed after a store event in --group1",
        args.group1_label,
        group1,
        args.group2_label,
        group2,
    )

    compare_groups.save_metric_plots(
        METRIC,
        [compare_groups.after_store_series(runs, {UNIVERSE_KEY: universe})[UNIVERSE_KEY] for runs in group_runs],
        (args.group1_label, args.group2_label),
        compare_groups.STATISTICS[args.statistic],
        0,
        0.0,
    )


if __name__ == "__main__":
    main()
