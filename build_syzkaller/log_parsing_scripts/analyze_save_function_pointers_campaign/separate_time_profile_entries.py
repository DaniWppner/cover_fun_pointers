#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from datetime import timedelta

import matplotlib.pyplot as plt

from logentry_keys import RESULT_KEYS

INTERESTING_KEYS = [
    RESULT_KEYS.TOTAL_JOB_DURATION,
    RESULT_KEYS.TOTAL_PROG_EXECUTIONS,
    RESULT_KEYS.FPOINTER_PROG_EXECUTIONS,
    RESULT_KEYS.PROG_EXECUTIONS_JOB_DURATION,
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
) -> None:
    """
    plot_type can be one of: "line", "scatter", or "hist".
    For histograms, `ylabel` is used as the x-axis label.
    """

    if not values:
        return

    plt.figure(figsize=(8, 4))
    if plot_type == "line":
        x_vals = list(range(1, len(values) + 1))
        plt.plot(x_vals, values, marker=".")
        plt.xlabel("Entry")
        plt.ylabel(ylabel)
    elif plot_type == "scatter":
        x_vals = list(range(1, len(values) + 1))
        plt.scatter(x_vals, values, marker=".")
        plt.xlabel("Entry")
        plt.ylabel(ylabel)
    elif plot_type == "hist":
        plt.hist(values, bins=bins)
        plt.xlabel(ylabel)
        plt.ylabel("Count")
    else:
        raise ValueError(f"Unsupported plot type: {plot_type}")

    plt.title(title)

    out_path = Path.cwd() / output_name
    plt.savefig(out_path)
    plt.close()
    print(f"Saved plot to {out_path}")


def save_line_plot(values: list[float], output_name: str, title: str, ylabel: str) -> None:
    save_plot(values, output_name, title, ylabel, plot_type="line")


def save_scatter_plot(values: list[float], output_name: str, title: str, ylabel: str) -> None:
    save_plot(values, output_name, title, ylabel, plot_type="scatter")


def save_histogram_plot(
    values: list[float], output_name: str, title: str, xlabel: str, bins: int = 20
) -> None:
    save_plot(values, output_name, title, xlabel, plot_type="hist", bins=bins)


def process_time_profile_lines(lines: list[dict]):
    unified_dict = {}
    
    # we can have any number of the interesting keys for each job, but all jobs must have the same
    # (perhaps this syzkaller run was not outputting one kind of log)
    present_keys = []
    for i in range(N_INTERESTING_KEYS):
        if INTERESTING_KEYS[i] in lines[len(present_keys)]:
            present_keys.append(INTERESTING_KEYS[i])

    n_interesting_keys = len(present_keys)
    for start_idx in range(0, len(lines), n_interesting_keys):
        job_lines = lines[start_idx: start_idx + n_interesting_keys]
        # check that our assumption that all entries for a given job are consecutive holds
        job_ids =  [(l[RESULT_KEYS.TRIAGEID], l[RESULT_KEYS.PROGID]) for l in job_lines]
        assert all(job_ids[0] == jid for jid in job_ids)
        unified_key = job_ids[0][0] + '|' + job_ids[0][1]
        unified_dict[unified_key] = {i_key: j_line[i_key] for i_key, j_line in zip(present_keys, job_lines)}

    all_execs, function_pointer_execs = None, None
    try:
        all_execs = [entry[RESULT_KEYS.TOTAL_PROG_EXECUTIONS] for entry in unified_dict.values()]
    except KeyError:
        pass
    try:
        function_pointer_execs = [entry[RESULT_KEYS.FPOINTER_PROG_EXECUTIONS] for entry in unified_dict.values()]
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

    prog_exec_times = [entry[RESULT_KEYS.PROG_EXECUTIONS_JOB_DURATION] for entry in unified_dict.values()]

    job_times = [entry[RESULT_KEYS.TOTAL_JOB_DURATION] for entry in unified_dict.values()]
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

    process_time_profile_lines(time_profile_jsonl)

    out_str = "\n".join(
        json.dumps(json_obj, indent=None) for json_obj in not_time_profile_jsonl
    )
    with out_path.open("w") as f:
        f.write(out_str)
    print("##############################")
    print(f"Cleaned up json lines outputted to {out_path.name}")
