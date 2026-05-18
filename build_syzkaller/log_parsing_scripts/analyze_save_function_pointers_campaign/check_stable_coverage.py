#!/usr/bin/env python3
import json
import argparse
import sys
from pathlib import Path
from termcolor import colored
from typing import Callable
from logentry_keys import RESULT_KEYS, RESULT_VALUES


def unify_per_prog(json_lines_file: Path) -> list[dict]:
    """Parse a JSON lines file and merge entries by prog/call identity.

    The returned dictionary maps a combined key representing pairs of
    <prog_id, call_name> to a single merged entry dict.

    Each value dict contains all relevant information for that <prog, call>
    pair during a triage.
    If more than one repeated occurrence of a specific <prog, call> pair is
    found during different triages, all occurences after the first one are ignored.
    """
    result_dict: dict[str, dict] = {}
    curr_original_prog = None
    curr_prog_id = None
    with open(json_lines_file) as f:
        for line in f:
            log_entry: dict = json.loads(line)
            prog_id = log_entry.pop(RESULT_KEYS.PROGID)

            if RESULT_KEYS.ORIGINAL_PROG in log_entry:
                curr_original_prog = log_entry[RESULT_KEYS.ORIGINAL_PROG]
                curr_prog_id = prog_id
                continue

            assert prog_id == curr_prog_id
            assert curr_original_prog is not None
            # the entries that don't specify the current original prog are relative to a function call
            # use that function call as part of the id for the triage
            call_id = log_entry.pop(RESULT_KEYS.CALL_NAME)
            data_key = f"{prog_id}|{call_id}"
            triage_id = log_entry.pop(RESULT_KEYS.TRIAGEID)
            if data_key not in result_dict:
                log_entry[RESULT_KEYS.ORIGINAL_PROG] = curr_original_prog
                log_entry[RESULT_KEYS.COUNT] = 1
                log_entry[RESULT_KEYS.TRIAGEID] = [triage_id]
                result_dict[data_key] = log_entry
                continue

            # If it is not the first occurence, we want to check that triage_id is the same
            # If it is not, that means we have identical <prog, call> pairs in different triages
            # This probably means that on two different instances the fuzzer generated the same prog
            # and obtained similar (flaky?) coverage to triage.
            # Let's only log the results for the first time the prog gets triaged,
            # but let's also make sure to increase the count.
            if triage_id not in result_dict[data_key][RESULT_KEYS.TRIAGEID]:
                result_dict[data_key][RESULT_KEYS.TRIAGEID].append(triage_id)
                result_dict[data_key][RESULT_KEYS.COUNT] += 1

            if result_dict[data_key][RESULT_KEYS.COUNT] > 1:
                continue

            # minimization result is a list of results, so we need to merge this one
            # manually into the existing one before being able to do update
            minim_key = RESULT_KEYS.MINIMIZATION_RESULT
            if minim_key in log_entry:
                minim_entry = log_entry.pop(minim_key)
                if minim_key in result_dict[data_key]:
                    if minimization_would_overwrite(result_dict[data_key], minim_entry):
                        warn_overwrite(result_dict[data_key][minim_key], minim_entry)
                        sys.exit(1)
                    # the current entry is by default a list of one element.
                    # extend the existing one in result with the new one.
                    result_dict[data_key][minim_key].extend(minim_entry)
                else:
                    # the current entry becomes the whole list in result.
                    result_dict[data_key][minim_key] = minim_entry

            # prog_in_corpus is also a list of results
            if RESULT_KEYS.SAVED_PROG in log_entry:
                saved_prog = log_entry.pop(RESULT_KEYS.SAVED_PROG)
                if RESULT_KEYS.SAVED_PROG in result_dict[data_key]:
                    # add the current saved prog to the list
                    result_dict[data_key][RESULT_KEYS.SAVED_PROG].append(saved_prog)
                else:
                    result_dict[data_key][RESULT_KEYS.SAVED_PROG] = [saved_prog]

            # all remaining keys should appear only once
            # per <prog_id, call> pair. Note that the ones for which
            # this doesn't hold have been removed previously.
            if any(key in result_dict[data_key] for key in log_entry):
                warn_overwrite(result_dict[data_key], log_entry, prog_id)
                sys.exit(1)
            result_dict[data_key].update(log_entry)
    return result_dict


def minimization_would_overwrite(result_entry: dict, minim_entry: dict) -> bool:
    minim_key = RESULT_KEYS.MINIMIZATION_RESULT
    minim_t_key = RESULT_KEYS.MINIMIZATION_RES_TYPE
    return any(
        saved_res[minim_t_key] == minim_entry[0][minim_t_key]
        for saved_res in result_entry[minim_key]
    )


def warn_overwrite(result_entry: dict, log_entry: dict, prog_id: str) -> None:
    print(
        colored(f"ERROR: would overrite key in {prog_id}\n", "red")
        + colored(json.dumps(result_entry, indent=2), "yellow")
        + colored("\nwhen adding\n", "red")
        + colored(json.dumps(log_entry, indent=2), "yellow")
    )


def count_cond(prog2log: dict[str, dict], condition: Callable[[dict], bool]) -> int:
    return len([entry for entry in prog2log.values() if condition(entry)])


def check_easy_stats(prog2log: dict[str, dict]) -> None:
    n_duplicate_progs = count_cond(prog2log, lambda e: e[RESULT_KEYS.COUNT] > 1)
    n_saved_progs = count_cond(prog2log, lambda e: RESULT_KEYS.SAVED_PROG in e)
    n_multiple_saved_progs = count_cond(
        prog2log, lambda e: len(e.get(RESULT_KEYS.SAVED_PROG, [])) > 1
    )

    print(f"Number of unique <prog, call> triaged: {len(prog2log)}")
    print(f"Number of progs triaged twice or more: {n_duplicate_progs}")
    print(
        f"Number of <prog,call> triages that added an item to the corpus: {n_saved_progs}"
    )
    print(
        f"Number of <prog,call> pairs with multiple saved progs: {n_multiple_saved_progs}"
    )


def has_minimization_result(minimization_result_type: str) -> Callable[[dict], bool]:
    def checker(prog_entry: dict) -> bool:
        if RESULT_KEYS.MINIMIZATION_RESULT not in prog_entry:
            return False
        minimization_result: list[dict] = prog_entry[RESULT_KEYS.MINIMIZATION_RESULT]
        if type(minimization_result) != list:
            print(colored("ERROR: type of minimization result is not list. Minimization result:", "red"))
            print(colored(str(minimization_result), "yellow"))
            sys.exit(1)
        return any(
            minimization_result_type == res[RESULT_KEYS.MINIMIZATION_RES_TYPE]
            for res in minimization_result
        )

    return checker


def check_minimization_stats(prog2log: dict[str, dict]) -> None:
    n_skip_all = count_cond(
        prog2log, has_minimization_result(RESULT_VALUES.MINIMIZATION_SKIP)
    )
    n_skip_fpointer = count_cond(
        prog2log, has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_FPOINTER_SKIP)
    )
    n_skip_signal = count_cond(
        prog2log, has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_SIGNAL_SKIP)
    )

    n_saved_fpointer = count_cond(
        prog2log, has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER)
    )

    n_saved_signal = count_cond(
        prog2log, has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_SAVE_SIGNAL)
    )

    n_keep_both = count_cond(
        prog2log, has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_NODIFF)
    )

    print(f"Number of minimizations that keep both: {n_keep_both}")
    print(f"Number of minimizations that obtained an unique fpointer: {n_saved_fpointer}")
    print(f"Number of minimizations that obtained an unique signal: {n_saved_signal}")
    print(f"Number of times fpointer minimization was skipped: {n_skip_fpointer}")
    print(f"Number of times signal minimization was skipped: {n_skip_signal}")
    print(f"Number of times minimizationa as a whole was skipped {n_skip_all}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse a json lines file to extract function pointer store entries data."
    )
    parser.add_argument(
        "json_lines_path",
        type=str,
        nargs="?",
        help="Json lines file outputted by extract_logs_into_json.py",
    )
    parser.add_argument(
        "out_path", type=str, nargs="?", help="Path to the output json."
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

    out_json = unify_per_prog(json_lines_path)
    check_easy_stats(out_json)
    print("--------------------------------------------------------------------")
    check_minimization_stats(out_json)
    with out_path.open("w") as f:
        f.write(json.dumps(out_json, indent=2) + "\n")
