#!/usr/bin/env python3
import argparse
import intervaltree
import json
import matplotlib.pyplot as plt
import sys
from datetime import datetime, timedelta
from pathlib import Path
from termcolor import colored
from typing import Callable, Iterable

from logentry_keys import RESULT_KEYS

INTERESTING_KEYS = [
    RESULT_KEYS.TOTAL_JOB_DURATION,
    RESULT_KEYS.TOTAL_PROG_EXECUTIONS,
    RESULT_KEYS.FPOINTER_PROG_EXECUTIONS,
    RESULT_KEYS.PROG_EXECUTIONS_JOB_DURATION,
    RESULT_KEYS.FPOINTER_PROG_EXECUTIONS_JOB_DURATION,
    RESULT_KEYS.PROG_EXECUTIONS_ALL_INDIVIDUAL_DURATIONS,
    RESULT_KEYS.PROG_EXECUTIONS_FPOINTER_INDIVIDUAL_DURATIONS,
]
N_INTERESTING_KEYS = len(INTERESTING_KEYS)


def filter_time_profile_lines(json_lines_path: Path) -> tuple[list[dict], list[dict]]:
    """
    Returns two lists
        The first one is the the list of json lines that are time profiling information
        The second one is the list of json lines that are not time profiling information
    """

    with open(json_lines_path, "r") as f:
        lines = f.readlines()
    interesting_lines, not_interesting_lines = [], []
    for l in lines:
        triage_entry = json.loads(l)
        if any(result_key in triage_entry for result_key in INTERESTING_KEYS):
            interesting_lines.append(triage_entry)
        else:
            not_interesting_lines.append(triage_entry)
    return interesting_lines, not_interesting_lines


def save_plot(
    values: list[float],
    output_name: str,
    title: str,
    ylabel: str,
    plot_type: str = "line",
    bins: int = 20,
    x_values: Iterable[float | datetime] | None = None,
    x_label: str = "Entry",
) -> None:
    """
    plot_type can be one of: "line", "scatter", or "hist".
    For histograms, `ylabel` is used as the x-axis label.
    """

    if not values:
        return

    plt.figure(figsize=(8, 4))
    if plot_type == "line":
        x_vals = list(x_values) if x_values is not None else list(range(1, len(values) + 1))
        plt.plot(x_vals, values, marker=".")
        plt.xlabel(x_label)
        plt.ylabel(ylabel)
    elif plot_type == "scatter":
        x_vals = list(x_values) if x_values is not None else list(range(1, len(values) + 1))
        plt.scatter(x_vals, values, marker=".")
        plt.xlabel(x_label)
        plt.ylabel(ylabel)
    elif plot_type == "hist":
        plt.hist(values, bins=bins)
        plt.xlabel(ylabel)
        plt.ylabel("Count")
    else:
        raise ValueError(f"Unsupported plot type: {plot_type}")

    plt.title(title)
    plt.tight_layout()

    out_path = Path.cwd() / output_name
    plt.savefig(out_path)
    plt.close()
    print(f"Saved plot to {out_path}")


def save_line_plot(
    values: list[float],
    output_name: str,
    title: str,
    ylabel: str,
    x_values: Iterable[float | datetime] | None = None,
    x_label: str = "Entry",
) -> None:
    save_plot(
        values,
        output_name,
        title,
        ylabel,
        plot_type="line",
        x_values=x_values,
        x_label=x_label,
    )


def save_scatter_plot(
    values: list[float],
    output_name: str,
    title: str,
    ylabel: str,
    x_values: Iterable[float | datetime] | None = None,
    x_label: str = "Entry",
) -> None:
    save_plot(
        values,
        output_name,
        title,
        ylabel,
        plot_type="scatter",
        x_values=x_values,
        x_label=x_label,
    )


def save_histogram_plot(
    values: list[float], output_name: str, title: str, xlabel: str, bins: int = 20
) -> None:
    save_plot(values, output_name, title, xlabel, plot_type="hist", bins=bins, x_label=xlabel)


def show_plots(all_execs, function_pointer_execs, prog_exec_times, job_times):
    save_line_plot(
        [t / 3600 for t in job_times],
        "job_duration_series.png",
        "Job duration over time",
        "Hours",
    )
    save_line_plot(
        [t / 3600 for t in prog_exec_times],
        "prog_exec_duration_series.png",
        "Prog execution duration over time",
        "Hours",
    )
    if all_execs is not None:
        save_scatter_plot(
            all_execs,
            "all_execs_series.png",
            "Prog executions per job over time",
            "",
        )
        save_histogram_plot(
            all_execs,
            "all_execs_histogram.png",
            "Frequency of prog executions per job",
            "Number of prog executions in a single job",
        )
    if function_pointer_execs is not None:
        save_scatter_plot(
            function_pointer_execs,
            "function_pointer_exec_series.png",
            "Prog executions per job over time triggered by new coverage",
            "",
        )
        save_histogram_plot(
            function_pointer_execs,
            "function_pointer_histogram.png",
            "Frequency of prog executions per job triggered by new coverage",
            "Number of prog executions in a single job",
        )


def show_info(all_execs, function_pointer_execs, prog_exec_times_w_celiing, job_times):
    print("-------------------------------------")
    print(f"Total job execution time: {timedelta(seconds=sum(job_times))}")
    print("-------------------------------------")
    print(f"Total prog execution time during jobs: {timedelta(seconds=sum(prog_exec_times_w_celiing))}")
    if all_execs is not None:
        print("-------------------------------------")
        print(f"Total prog executions during jobs: {sum(all_execs)}")
    if function_pointer_execs is not None:
        print("-------------------------------------")
        print(f"Total prog executions during jobs triggered due to our new coverage: {sum(function_pointer_execs)}")


def show_in_flight_timelapse(
    in_flight_fn: Callable[[datetime], list[dict[str, str]]],
    start_time: datetime,
    end_time: datetime,
    output_name: str,
    title: str = "In-flight prog executions over time",
    ylabel: str = "In-flight prog executions",
) -> None:
    assert end_time > start_time
    if start_time is None or end_time is None:
        return

    relative_times: list[float] = []
    counts: list[int] = []
    current_time = start_time
    while current_time <= end_time:
        relative_times.append((current_time - start_time).total_seconds() / 3600)
        counts.append(len(in_flight_fn(current_time)))
        current_time += timedelta(seconds=10)

    if relative_times[-1] < (end_time - start_time).total_seconds() / 3600:
        relative_times.append((end_time - start_time).total_seconds() / 3600)
        counts.append(len(in_flight_fn(end_time)))

    save_line_plot(
        counts,
        output_name,
        title,
        ylabel,
        x_values=relative_times,
        x_label="Hours since start",
    )


def process_time_profile_lines(lines: list[dict]):
    unified_dict = unify_per_job(lines)

    all_execs, function_pointer_execs = None, None
    try:
        all_execs = [
            entry[RESULT_KEYS.TOTAL_PROG_EXECUTIONS] for entry in unified_dict.values()
        ]
    except KeyError:
        pass
    try:
        function_pointer_execs = [
            entry[RESULT_KEYS.FPOINTER_PROG_EXECUTIONS]
            for entry in unified_dict.values()
        ]
    except KeyError:
        pass

    # some times a single execution of a job can trigger many prog executions in parallel.
    # that's why the total prog executions can be larger than the (linear) time of the job itself.
    # we just want to prove that the time of a job is not bigger than the time of its executions, so taking this ceiling is OK.
    prog_exec_times_w_celiing = []
    for entry in unified_dict.values():
        exec_duration = entry[RESULT_KEYS.PROG_EXECUTIONS_JOB_DURATION]
        job_duration = entry[RESULT_KEYS.TOTAL_JOB_DURATION]
        prog_exec_times_w_celiing.append(min(exec_duration, job_duration))

    prog_exec_times = [
        entry[RESULT_KEYS.PROG_EXECUTIONS_JOB_DURATION]
        for entry in unified_dict.values()
    ]

    job_times = [
        entry[RESULT_KEYS.TOTAL_JOB_DURATION] for entry in unified_dict.values()
    ]

    in_flight_generic_progs_at, generic_start_time, generic_end_time = calculate_in_flight_progs([
        entry[RESULT_KEYS.PROG_EXECUTIONS_ALL_INDIVIDUAL_DURATIONS]
        for entry in unified_dict.values()
        ])
    in_flight_fpointer_progs_at, fpointer_start_time, fpointer_end_time = calculate_in_flight_progs([
        entry[RESULT_KEYS.PROG_EXECUTIONS_FPOINTER_INDIVIDUAL_DURATIONS]
        for entry in unified_dict.values()
        ])

    show_in_flight_timelapse(
        in_flight_generic_progs_at,
        generic_start_time,
        generic_end_time,
        output_name="all_progs_flight_timelapse.png",
        title="In-flight prog executions over time",
        ylabel="In-flight prog executions",
    )
    show_in_flight_timelapse(
        in_flight_fpointer_progs_at,
        fpointer_start_time,
        fpointer_end_time,
        output_name="fpointer_progs_in_flight_timelapse.png",
        title="In-flight function-pointer prog executions over time",
        ylabel="In-flight prog executions",
    )

    show_plots(all_execs, function_pointer_execs, prog_exec_times, job_times)
    show_info(all_execs, function_pointer_execs, prog_exec_times_w_celiing, job_times)
    return unified_dict


def calculate_in_flight_progs(unified: Iterable[list[dict[str, str]]]) -> tuple[Callable[[datetime], list[dict[str, str]]], datetime | None, datetime | None]:
    """

    Receives a list of json entries in the following format:
      [
        {
        "DurationSeconds": "2.985523",
        "TimeEnd": "2026-07-01 18:19:05",
        "TimeStart": "2026-07-01 18:19:02"
        },
        ...
      ]
    Returns:
        A callable that calculates the entries that entries in-flight for any point in time
        The first point in time an entry started at
        The last point in time an entry ended at
    """
    timestart_key = "TimeStart"
    timeend_key = "TimeEnd"
    duration_key = "DurationSeconds"
    flattened = sum(unified, start=[])

    def convert_timestamp(timestamp: str) -> datetime:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

    converted = [
        {
            timestart_key: convert_timestamp(e[timestart_key]),
            timeend_key: convert_timestamp(e[timeend_key]),
            duration_key: float(e[duration_key]),
        }
        for e in flattened
    ]

    if not converted:
        def entries_in_flight(t: datetime) -> list[dict[str, str]]:
            return []

        return entries_in_flight, None, None

    intervals = [
        intervaltree.Interval(begin=e[timestart_key], end=e[timeend_key], data=e)
        for e in converted
    ]
    filtered_null = [i for i in intervals if not i.is_null()]
    print(colored(f"[INFO] filtered {len(intervals) - len(filtered_null)}" +
                  f" empty intervals out of {len(intervals)} total intervals", "light_red"))
    interval_tree = intervaltree.IntervalTree(filtered_null)

    def entries_in_flight(t: datetime) -> list[dict[str, str]]:
        return [i.data for i in interval_tree.at(t)]

    start_time = min(converted, key=lambda e: e[timestart_key])[timestart_key]
    end_time = max(converted, key=lambda e: e[timeend_key])[timeend_key]
    return entries_in_flight, start_time, end_time


def unify_per_job(lines):
    unified_dict = {}

    # we can have any number of the interesting keys for each job, but all jobs must have the same
    # (perhaps this syzkaller run was not outputting one kind of log)
    present_keys = []
    for i in range(N_INTERESTING_KEYS):
        if INTERESTING_KEYS[i] in lines[len(present_keys)]:
            present_keys.append(INTERESTING_KEYS[i])

    n_interesting_keys = len(present_keys)
    for start_idx in range(0, len(lines), n_interesting_keys):
        job_lines = lines[start_idx : start_idx + n_interesting_keys]
        # check that our assumption that all entries for a given job are consecutive holds
        job_ids = [(l[RESULT_KEYS.TRIAGEID], l[RESULT_KEYS.PROGID]) for l in job_lines]
        assert all(job_ids[0] == jid for jid in job_ids)
        unified_key = job_ids[0][0] + "|" + job_ids[0][1]
        unified_dict[unified_key] = {
            i_key: j_line[i_key] for i_key, j_line in zip(present_keys, job_lines)
        }
    return unified_dict


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse a json lines file to extract time profiling data and remove it."
    )
    parser.add_argument(
        "json_lines_path",
        type=str,
        nargs="?",
        help="Json lines file outputted by extract_logs_into_json.py",
    )
    parser.add_argument(
        "out_path", type=str, nargs="?", help="Path to the output json lines file."
    )
    args = parser.parse_args()

    if not args.json_lines_path or not args.out_path:
        parser.print_help()
        sys.exit(1)

    json_lines_path = Path(args.json_lines_path)
    out_path = Path(args.out_path)
    if not json_lines_path.exists():
        print(
            f"Error: The specified json lines file does not exist: {json_lines_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    time_profile_jsonl, not_time_profile_jsonl = filter_time_profile_lines(
        json_lines_path
    )

    unified_time_profile = process_time_profile_lines(time_profile_jsonl)

    out_str = "\n".join(
        json.dumps(json_obj, indent=None) for json_obj in not_time_profile_jsonl
    )
    with out_path.open("w") as f:
        f.write(out_str)
    print("##############################")
    print(f"Cleaned up json lines outputted to {out_path.name}")
    with open("time_profile_data.json", "w") as f:
        f.write(json.dumps(unified_time_profile, indent=1))
    print("##############################")
    print(f"Time profile data outputted to time_profile_data.json")
