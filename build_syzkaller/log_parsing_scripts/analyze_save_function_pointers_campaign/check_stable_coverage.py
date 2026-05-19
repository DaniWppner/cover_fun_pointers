#!/usr/bin/env python3
import json
import argparse
import sys
from pathlib import Path
from termcolor import colored
from typing import Callable
from collections import defaultdict
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

    # After minimizing a prog, the call_id of that prog when it is saved into the corpus
    # will be different from the original one (since it can have a smaller index now)
    # This should be handled better by the fuzzer when printing the logs.
    # But alas, we have to fix it in post.
    #
    # The queue awaiting_corpus_entry holds all progs that have been minimized, so that they
    # can be matched with a future "save to corpus" log entry via the <prog_id, traige_id> pair.
    # This allows the "save to corpus" entry to be overriden as another entry into the original
    # <prog, call> group instead of creating a lone <prog, newcall> group with just the "save" entry.
    awaiting_corpus_entry = dict()
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

            # before using data_key, let's check if we should update it
            # does this break the "skip repeated traiges rule"?
            data_key = check_for_saved_prog(data_key, awaiting_corpus_entry, log_entry, prog_id, triage_id)

            no_new : bool = data_key in result_dict

            # If it is not the first occurence, we want to check that triage_id is the same
            # If it is not, that means we have identical <prog, call> pairs in different triages
            # This probably means that on two different instances the fuzzer generated the same prog
            # and obtained similar (flaky?) coverage to triage.
            # Let's only log the results for the first time the prog gets triaged,
            # but let's also make sure to increase the count.
            #
            # FIXME: THis breaks in the way that programs triaged multiple times due to race conditions
            # might have the results on the second or greater iteration ignored.
            # In particular for saved_prog, which have a different <prog, call> pair id this creates
            # duplicate entries. 
            if no_new and triage_id not in result_dict[data_key][RESULT_KEYS.TRIAGEID]:
                result_dict[data_key][RESULT_KEYS.TRIAGEID].append(triage_id)
                result_dict[data_key][RESULT_KEYS.COUNT] += 1

            if no_new and result_dict[data_key][RESULT_KEYS.COUNT] > 1:
                continue

            # minimization result is a list of results, so we need to merge this one
            # manually into the existing one before being able to do update
            minim_key = RESULT_KEYS.MINIMIZATION_RESULT
            if minim_key in log_entry:
                minim_entry = log_entry.pop(minim_key)
                if minim_entry[0][RESULT_KEYS.MINIMIZATION_RES_TYPE] not in [
                    RESULT_VALUES.MINIMIZATION_SKIP,
                    RESULT_VALUES.MINIMIZATION_RES_SIGNAL_SKIP,
                    RESULT_VALUES.MINIMIZATION_RES_FPOINTER_SKIP,
                ]:
                    # this means a successful minimize happened, 
                    # let's schedule the minimized prog to entry the corpus.
                    awaiting_corpus_entry[get_ceq_key(prog_id, triage_id)] = data_key
                if no_new and minim_key in result_dict[data_key]:
                    if minimization_would_overwrite(result_dict[data_key], minim_entry):
                        warn_overwrite(result_dict[data_key][minim_key], minim_entry)
                        sys.exit(1)
                    # the current entry is by default a list of one element.
                    # extend the existing one in result with the new one.
                    result_dict[data_key][minim_key].extend(minim_entry)
                else:
                    # setup log_entry so that after assignement
                    # the current entry becomes the whole list in result.
                    log_entry[minim_key] = minim_entry

            # prog_in_corpus is also a list of results
            if RESULT_KEYS.SAVED_PROG in log_entry:
                saved_prog = log_entry.pop(RESULT_KEYS.SAVED_PROG)
                if no_new and RESULT_KEYS.SAVED_PROG in result_dict[data_key]:
                    # add the current saved prog to the list
                    result_dict[data_key][RESULT_KEYS.SAVED_PROG].append(saved_prog)
                else:
                    # setup log_entry so that after assignement
                    # the current entry becomes the whole list
                    log_entry[RESULT_KEYS.SAVED_PROG] = [saved_prog]

            if not no_new:
                log_entry[RESULT_KEYS.ORIGINAL_PROG] = curr_original_prog
                log_entry[RESULT_KEYS.COUNT] = 1
                log_entry[RESULT_KEYS.TRIAGEID] = [triage_id]
                result_dict[data_key] = log_entry
            else:
                # all remaining keys should appear only once
                # per <prog_id, call> pair. Note that the ones for which
                # this doesn't hold have been removed previously.
                if any(key in result_dict[data_key] for key in log_entry):
                    warn_overwrite(result_dict[data_key], log_entry, prog_id)
                    sys.exit(1)
                result_dict[data_key].update(log_entry)
    assert len(awaiting_corpus_entry) == 0
    return result_dict

def check_for_saved_prog(data_key, awaiting_corpus_entry, log_entry, prog_id, triage_id):
    """
    Override data_key with the one in the queue if necessary
    """
    if RESULT_KEYS.SAVED_PROG in log_entry:
        if get_ceq_key(prog_id, triage_id) in awaiting_corpus_entry:
            data_key = awaiting_corpus_entry.pop(get_ceq_key(prog_id, triage_id))
    return data_key

def get_ceq_key(prog_id:str, triage_id:str) -> str:
    """
    Returns the key used in awaiting_corpus_entry for the pair
    prog_id, triage_id
    """
    return f"{triage_id}|{prog_id}"


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


def filter_many_cond(
    prog2log: dict[str, dict], *conditions: Callable[[dict], bool]
) -> int:
    return {
        key: val
        for key, val in prog2log.items()
        if all(cond(val) for cond in conditions)
    }


def check_easy_stats(prog2log: dict[str, dict]) -> None:
    n_duplicate_progs = count_cond(prog2log, lambda e: e[RESULT_KEYS.COUNT] > 1)
    n_saved_progs = count_cond(prog2log, lambda e: RESULT_KEYS.SAVED_PROG in e)
    multiple_saved_progs = filter_many_cond(
        prog2log, lambda e: len(e.get(RESULT_KEYS.SAVED_PROG, [])) > 1
    )

    print(f"Number of unique <prog, call> triaged: {len(prog2log)}")
    print(f"Number of progs triaged twice or more: {n_duplicate_progs}")
    print(
        f"Number of <prog,call> triages that added an item to the corpus: {n_saved_progs}"
    )
    multiple_corpus_fout = Path.cwd() / "multiple_saved_corpus.json"
    print(
        f"Number of <prog,call> pairs with multiple saved progs (count={len(multiple_saved_progs)}) saved to {multiple_corpus_fout}"
    )
    with open(multiple_corpus_fout, 'w') as f:
        json.dump(multiple_saved_progs, f, indent=2)


def has_minimization_result(minimization_result_type: str) -> Callable[[dict], bool]:
    def checker(prog_entry: dict) -> bool:
        if RESULT_KEYS.MINIMIZATION_RESULT not in prog_entry:
            return False
        minimization_result: list[dict] = prog_entry[RESULT_KEYS.MINIMIZATION_RESULT]
        if type(minimization_result) != list:
            print(
                colored(
                    "ERROR: type of minimization result is not list. Minimization result:",
                    "red",
                )
            )
            print(colored(str(minimization_result), "yellow"))
            sys.exit(1)
        return any(
            minimization_result_type == res[RESULT_KEYS.MINIMIZATION_RES_TYPE]
            for res in minimization_result
        )

    return checker

def check_duplicated_progs(prog2log: dict[str, dict]) -> None:
    prog2_count = defaultdict(list)
    for key, entry in prog2log.items():
        for prog in entry.get(RESULT_KEYS.SAVED_PROG, []):
            prog2_count[hash(''.join(prog))].append(key)

    duplicate = {prog: keys for prog,keys in prog2_count.items() if len(keys) > 1}
    print(f"Number of unique progs saved in corpus: {len(prog2_count)}")
    print(f"Number of progs saved more than once: {len(duplicate)}")



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

    unique_signal_and_fpointer = filter_many_cond(
        prog2log,
        has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER),
        has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_SAVE_SIGNAL),
    )

    print(f"Number of minimizations that keep both: {n_keep_both}")
    print(f"Number of minimizations that obtained an unique fpointer: {n_saved_fpointer}")
    print(f"Number of minimizations that obtained an unique signal: {n_saved_signal}")
    print(f"Number of times fpointer minimization was skipped: {n_skip_fpointer}")
    print(f"Number of times signal minimization was skipped: {n_skip_signal}")
    print(f"Number of times minimizationa as a whole was skipped {n_skip_all}")
    both_unique_fout = Path.cwd() / "unique_fpointer_and_signal_minimization_result.json"
    print(
        f"Minimizations that obtained both unique signal and unique fpointer (count={len(unique_signal_and_fpointer)}):\n"
        + f"printed at {both_unique_fout}"
    )
    with open(both_unique_fout, "w") as f:
        json.dump(unique_signal_and_fpointer, f, indent=2)


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
    check_duplicated_progs(out_json)
    print("--------------------------------------------------------------------")
    check_minimization_stats(out_json)
    with out_path.open("w") as f:
        f.write(json.dumps(out_json, indent=2) + "\n")
