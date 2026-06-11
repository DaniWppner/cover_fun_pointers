#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable, Any

from logentry_keys import RESULT_KEYS, RESULT_VALUES
from termcolor import colored

# First element represents file name and line number in the format file_name:lineno
# Second element represents function containing said line number
type locInfo = tuple[str, str]


def unify_per_prog(json_lines_file: Path) -> dict:
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
    awaiting_corpus_entry: dict[str, str] = {}
    awaiting_pc_cover: dict[str, str] = {}
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
            data_key = override_if_awaiting(
                data_key,
                awaiting_corpus_entry,
                log_entry,
                prog_id,
                triage_id,
                RESULTKEY=RESULT_KEYS.SAVED_PROG,
            )
            data_key = override_if_awaiting(
                data_key,
                awaiting_pc_cover,
                log_entry,
                prog_id,
                triage_id,
                RESULTKEY=RESULT_KEYS.PC_COVER,
            )

            no_new: bool = data_key in result_dict

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
                ## Before we ignore this duplicate entry, queue whatever we're missing
                ## just in case, so that the next entry that would get its key updated
                ## can be recongnized as duplicate properly and be ignored
                if RESULT_KEYS.MINIMIZATION_RESULT in log_entry:
                    minim_entry = log_entry.pop(RESULT_KEYS.MINIMIZATION_RESULT)
                    if successful_minimize(minim_entry):
                        # let's schedule the minimized prog to entry the corpus.
                        update_queues(
                            awaiting_corpus_entry,
                            awaiting_pc_cover,
                            prog_id,
                            data_key,
                            triage_id,
                            minim_entry,
                        )
                ## Now, ignore this entry
                continue

            # minimization result is a list of results, so we need to merge this one
            # manually into the existing one before being able to do update
            minim_key = RESULT_KEYS.MINIMIZATION_RESULT
            if minim_key in log_entry:
                minim_entry = log_entry.pop(minim_key)
                if successful_minimize(minim_entry):
                    # let's schedule the minimized prog to entry the corpus.
                    update_queues(
                        awaiting_corpus_entry,
                        awaiting_pc_cover,
                        prog_id,
                        data_key,
                        triage_id,
                        minim_entry,
                    )

                if no_new and minim_key in result_dict[data_key]:
                    if minimization_would_overwrite(result_dict[data_key], minim_entry):
                        warn_overwrite(
                            result_dict[data_key][minim_key], minim_entry, data_key
                        )
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
                    warn_overwrite(result_dict[data_key], log_entry, data_key)
                    sys.exit(1)
                result_dict[data_key].update(log_entry)
    assert len(awaiting_corpus_entry) == 0
    return result_dict


def successful_minimize(minim_entry: dict) -> bool:
    """
    Return true if this entry indicates that one of the minimization attempts produced something
    """
    return minim_entry[0][RESULT_KEYS.MINIMIZATION_RES_TYPE] not in [
        RESULT_VALUES.MINIMIZATION_SKIP,
        RESULT_VALUES.MINIMIZATION_RES_SIGNAL_SKIP,
        RESULT_VALUES.MINIMIZATION_RES_FPOINTER_SKIP,
    ]


def update_queues(
    awaiting_corpus_entry: dict[str, str],
    awaiting_pc_cover: dict[str, str],
    prog_id: str,
    data_key: str,
    triage_id: str,
    minim_entry: dict,
) -> None:
    """
    Store in awaiting_corpus_entry the data_key used for this prog_id, triage_id pair.
    Also update awaiting_pc_cover if the minimization result was nonempty for pointer coverage,
    since this will trigger a future pc_cover type entry for the same triage job.
    """
    awaiting_corpus_entry[get_ceq_key(prog_id, triage_id)] = data_key

    # additionally, if the prog is entering because of pointer coverage
    # we need to capture the raw pc coverage
    if minim_entry[0][RESULT_KEYS.MINIMIZATION_RES_TYPE] in [
        RESULT_VALUES.MINIMIZATION_RES_NODIFF,
        RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER,
    ]:
        awaiting_pc_cover[get_ceq_key(prog_id, triage_id)] = data_key


def override_if_awaiting(
    data_key: str,
    awaiting_queue: dict[str, str],
    log_entry: dict[str, dict],
    prog_id: str,
    triage_id: str,
    RESULTKEY: str,
) -> str:
    """
    Override data_key with one in the queue if
     (a) This log_entry has a RESULTKEY type entry, and
     (b) The prog_id and triage_id match a pair in the queue
    """
    if RESULTKEY in log_entry:
        if get_ceq_key(prog_id, triage_id) in awaiting_queue:
            # og = data_key
            data_key = awaiting_queue.pop(get_ceq_key(prog_id, triage_id))
            # print(colored(f"INFO: Overriding data key {og} with {data_key} due to queue on key {RESULTKEY}", "cyan"))
    return data_key


def get_ceq_key(prog_id: str, triage_id: str) -> str:
    """
    Returns the key used in awaiting queues for the pair
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


def cleanup_particular_fpointer(entries: dict[str, Any], key2json_entry: str) -> None:
    """
    Receives a key where the value is a literal string containing json
    Parses the string into the nested json and writes it back in dict
    """
    fpointer_json = json.loads(entries[key2json_entry])
    entries[key2json_entry] = fpointer_json


def cleanup_fpointer_jsons(unified_json: dict) -> None:
    for entries in unified_json.values():
        for key in (
            RESULT_KEYS.NEW_FPOINTERS_PAYLOAD,
            RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD,
        ):
            if key in entries:
                cleanup_particular_fpointer(entries, key)


def count_cond(prog2log: dict[str, dict], condition: Callable[[dict], bool]) -> int:
    return len([entry for entry in prog2log.values() if condition(entry)])


def filter_many_cond(
    prog2log: dict[str, dict], *conditions: Callable[[dict], bool]
) -> dict[str, dict]:
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
        f"Number of <prog,call> pairs with multiple saved progs (count={len(multiple_saved_progs)}) saved to {multiple_corpus_fout.name}"
    )
    with open(multiple_corpus_fout, "w") as f:
        json.dump(multiple_saved_progs, f, indent=2)


def has_minimization_result(minimization_result_type: str) -> Callable[[dict], bool]:
    '''
    Args:
        minimization_result_type: desired key in one of the minimization results in an entry

    Returns:
        function that returns True for entries that have the specified minimization result type
    '''
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


def get_duplicate_progs(
    prog2log: dict[str, dict],
) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    prog2_count = defaultdict(list)
    for key, entry in prog2log.items():
        for prog in entry.get(RESULT_KEYS.SAVED_PROG, []):
            prog2_count[hash("".join(prog))].append(key)

    duplicate = {prog: keys for prog, keys in prog2_count.items() if len(keys) > 1}
    return prog2_count, duplicate


def deduplicate_saved_progs(prog2log: dict[str, dict]) -> tuple[dict, dict, int]:
    """
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.

    Returns:
        tuple[dict, dict, int]: A tuple with three elements:
            not_duplicate_dict: sub-dictionary of the input where each saved program in the corpus appears only once
            sorted_by_duplicates: input dictionary sorted in decreasing order by the amount of repetitions of the saved program
            count: amount of programs saved in the corpus that appear more than once in the input
    """
    count, duplicate = get_duplicate_progs(prog2log)
    # we need this so upcoming lists are also sorted in decreasing order of repetitions

    jobids_in_some_duplicate = [
        jobid for listofjobids in duplicate.values() for jobid in listofjobids
    ]
    first_jobid_of_each_duplicate = [
        listofjobids[0] for listofjobids in duplicate.values()
    ]
    # All elements that appear only once
    not_duplicate_dict = {
        key: val for key, val in prog2log.items() if key not in jobids_in_some_duplicate
    }
    # Update with one of the repetitions for each element that appears more than once
    not_duplicate_dict.update(
        (key, val)
        for key, val in prog2log.items()
        if key in first_jobid_of_each_duplicate
    )

    sorted_count = dict(
        sorted(
            count.items(),
            key=lambda key_valueList: len(key_valueList[1]),
            reverse=True,
        )
    )
    sorted_by_duplicates = {}
    for listofjobids in sorted_count.values():
        sub_dict = {jobid: prog2log[jobid] for jobid in listofjobids}
        diff_with_res = {
            jobid: val
            for jobid, val in sub_dict.items()
            if jobid not in sorted_by_duplicates
        }
        sorted_by_duplicates.update(diff_with_res)
    return not_duplicate_dict, sorted_by_duplicates, len(duplicate)


def get_saved_because_skip_signal(prog2log: dict[str, dict]) -> dict[str, dict]:
    '''
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.

    Returns:
        sub-dictionary of the input where only functionPointerCoverage was interesting
    '''
    return filter_many_cond(
        prog2log,
        has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_SIGNAL_SKIP),
        has_minimization_result(RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER),
    )


def check_duplicated_progs(prog2log: dict[str, dict]) -> None:
    prog2_count, duplicate = get_duplicate_progs(prog2log)
    print(f"Number of unique progs saved in corpus: {len(prog2_count)}")
    print(f"Number of progs saved more than once: {len(duplicate)}")


def check_saved_because_fpointer(prog2log: dict[str, dict]) -> None:
    saved_because_skip_signal = get_saved_because_skip_signal(prog2log)
    (
        deduplicate_interesting,
        saved_because_skip_signal,
        count_duplicate_saved_interesting_progs,
    ) = deduplicate_saved_progs(saved_because_skip_signal)

    saved_because_fpointer_Wduplicate_fout = (
        Path.cwd() / "saved_because_fpointer_w_duplicates.json"
    )
    print(
        f"Progs saved with fpointer and skip signal (count={len(saved_because_skip_signal)})",
        f"saved to {saved_because_fpointer_Wduplicate_fout.name}"
    )
    with open(saved_because_fpointer_Wduplicate_fout, "w") as f:
        json.dump(saved_because_skip_signal, f, indent=2)

    saved_deduplicate_fout = Path.cwd() / "saved_because_fpointer.json"
    print(
        f"After deduplication, progs saved with fpointer and skip signal (count={len(deduplicate_interesting)})",
        f"saved to {saved_deduplicate_fout.name}"
    )
    with open(saved_deduplicate_fout, "w") as f:
        json.dump(deduplicate_interesting, f, indent=2)

    print(f"Number of progs saved with fpointer and skip signal more than once: {count_duplicate_saved_interesting_progs}")


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
    print(
        f"Number of minimizations that obtained an unique fpointer: {n_saved_fpointer}"
    )
    print(f"Number of minimizations that obtained an unique signal: {n_saved_signal}")
    print(f"Number of times fpointer minimization was skipped: {n_skip_fpointer}")
    print(f"Number of times signal minimization was skipped: {n_skip_signal}")
    print(f"Number of times minimizationa as a whole was skipped {n_skip_all}")
    both_unique_fout = (
        Path.cwd() / "unique_fpointer_and_signal_minimization_result.json"
    )
    print(
        f"Minimizations that obtained both unique signal and unique fpointer (count={len(unique_signal_and_fpointer)}): "
        + f"saved to {both_unique_fout.name}"
    )
    with open(both_unique_fout, "w") as f:
        json.dump(unique_signal_and_fpointer, f, indent=2)


def update_master_dict_with_fpointer_loc_data(prog2log: dict[str, dict],
                                              fpointer_addr2loc: dict[str, list[locInfo]],
                                              storeinst_addr2loc: dict[str, list[locInfo]]) -> dict[str, dict]:
    for entry in prog2log.values():
        for funcPointer_store_entry in entry.get(RESULT_KEYS.NEW_FPOINTERS_PAYLOAD, []):
            fPointer = funcPointer_store_entry["StoredValue"]
            storeInst = funcPointer_store_entry["PC"]
            # hacky hack: we will not have a location for this "empty" pointer
            fPointer_loc = fpointer_addr2loc[fPointer][0] if fPointer != '0xffffffffffffffff' else ''
            funcPointer_store_entry[RESULT_KEYS.FPOINTER_PAYLOAD_FPOINTER_LOC_KEY] = fPointer_loc
            funcPointer_store_entry[RESULT_KEYS.FPOINTER_PAYLOAD_STOREINST_LOC_KEY] = storeinst_addr2loc[storeInst][0]

        for funcPointer_store_entry in entry.get(RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD, []):
            fPointer = funcPointer_store_entry["StoredValue"]
            storeInst = funcPointer_store_entry["PC"]
            #hacky hack: see above
            fPointer_loc = fpointer_addr2loc[fPointer][0] if fPointer != '0xffffffffffffffff' else ''
            funcPointer_store_entry[RESULT_KEYS.FPOINTER_PAYLOAD_FPOINTER_LOC_KEY] = fPointer_loc
            funcPointer_store_entry[RESULT_KEYS.FPOINTER_PAYLOAD_STOREINST_LOC_KEY] = storeinst_addr2loc[storeInst][0]

    return prog2log


def check_pc_cover_vs_fpointer(prog2log: dict[str, dict]) -> None:
    all_pcs, all_fpointers_stores, all_fpointers, fpointer2storeinst = get_fpointer_store_info(prog2log)

    check_PC_exec_funcStore_literal_diffs(all_pcs, all_fpointers_stores, all_fpointers)
    print(colored("################################################", "cyan"))
    (
        fpointer_addr2loc,
        storeinst_addr2loc,
        uncovered_fpointer_locs,
        covered_fpointer_locs,
    ) = check_source_code_diffs(all_pcs, all_fpointers_stores, all_fpointers)

    prog2log = update_master_dict_with_fpointer_loc_data(prog2log, fpointer_addr2loc, storeinst_addr2loc)
    uncovered_fpointers_out, skip_count = get_fpointer2storeinst_as_source_locations(
        fpointer2storeinst, fpointer_addr2loc, storeinst_addr2loc, uncovered_fpointer_locs,
    )
    assert skip_count == 0
    uncovered_fpointers_file = Path.cwd() / "__uncovered_pairs.py"
    with open(uncovered_fpointers_file, "w") as f:
        print(uncovered_fpointers_out, file=f)
    print(f"Mapping of uncovered function pointer to instructions that store them saved to {uncovered_fpointers_file.name}")

    covered_fpointers_out, skip_count = get_fpointer2storeinst_as_source_locations(
        fpointer2storeinst, fpointer_addr2loc, storeinst_addr2loc, covered_fpointer_locs
    )
    assert skip_count == 0
    covered_fpointers_file = Path.cwd() / "__covered_pairs.py"
    with open(covered_fpointers_file, "w") as f:
        print(covered_fpointers_out, file=f)
    print(f"Mapping of covered function pointer to instructions that store them saved to {covered_fpointers_file.name}")

    print(colored("################################################", "cyan"))
    check_saved_because_skip_signal_vs_fpointers(prog2log, fpointer_addr2loc, storeinst_addr2loc, covered_fpointer_locs, uncovered_fpointer_locs)
    
    return prog2log


def check_saved_because_skip_signal_vs_fpointers(prog2log: dict[str, dict],
                                                fpointer_addr2loc: dict[str, list[locInfo]],
                                                storeinst_addr2loc:  dict[str, list[locInfo]],
                                                covered_fpointer_locs:  set[locInfo],
                                                uncovered_fpointer_locs:  set[locInfo],
                                                ) -> None:
    saved_because_skip_signal = get_saved_because_skip_signal(prog2log)
    _, _, _, skip_signal_fpointer2storeinst = get_fpointer_store_info(saved_because_skip_signal, stable_only=True)
    covered_fpointers_saved_because_skip_signal, missed_covered = get_fpointer2storeinst_as_source_locations(
        skip_signal_fpointer2storeinst, fpointer_addr2loc, storeinst_addr2loc, covered_fpointer_locs
    )
    uncovered_fpointers_saved_because_skip_signal, missed_uncovered = get_fpointer2storeinst_as_source_locations(
        skip_signal_fpointer2storeinst, fpointer_addr2loc, storeinst_addr2loc, uncovered_fpointer_locs
    )

    covered_fpointers_because_skip_signal_file = Path.cwd() / "__covered_pairs_saved_because_fpointer.py"
    with open(covered_fpointers_because_skip_signal_file, "w") as f:
        print(covered_fpointers_saved_because_skip_signal, file=f)
    print(
        "Mapping of covered function pointers to instructions that save them registered in tests that produced no interesting signal",
        f"(count={len(covered_fpointers_saved_because_skip_signal)}",
        f"(ignored due to filter={missed_covered}) saved to {covered_fpointers_because_skip_signal_file.name}"
        )

    uncovered_fpointers_because_skip_signal_file = Path.cwd() / "__uncovered_pairs_saved_because_fpointer.py"
    with open(uncovered_fpointers_because_skip_signal_file, "w") as f:
        print(uncovered_fpointers_saved_because_skip_signal, file=f)
    print(
        "Mapping of uncovered function pointers to instructions that save them registered in tests that produced no interesting signal",
        f"(count={len(uncovered_fpointers_saved_because_skip_signal)}",
        f"(ignored due to filter={missed_uncovered}) saved to {uncovered_fpointers_because_skip_signal_file.name}"
        )
    print("------------------------------------------------")    
    covered_fpointers_subdict = filter_many_cond(saved_because_skip_signal,
                                                 lambda e: any(
                                                     fPointer_entry[RESULT_KEYS.FPOINTER_PAYLOAD_FPOINTER_LOC_KEY] in covered_fpointer_locs
                                                     for fPointer_entry in e.get(RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD, [])
                                                 ))
    uncovered_fpointers_subdict = filter_many_cond(saved_because_skip_signal,
                                                 lambda e: any(
                                                     fPointer_entry[RESULT_KEYS.FPOINTER_PAYLOAD_FPOINTER_LOC_KEY] in uncovered_fpointer_locs
                                                     for fPointer_entry in e.get(RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD, [])
                                                 ))
    
    covered_fpointers_subdict_fout = Path.cwd() / "registered_covered_fpointers_saved_because_fpointer.json"
    with open(covered_fpointers_subdict_fout, "w") as f:
        json.dump(covered_fpointers_subdict, f, indent=2)
    print("Progs saved with fpointer and skip signal that registered a covered function pointer",
         f"(count={len(covered_fpointers_subdict)}) saved to {covered_fpointers_subdict_fout.name}"
    )

    uncovered_fpointers_subdict_fout = Path.cwd() / "registered_uncovered_fpointers_saved_because_fpointer.json"
    with open(uncovered_fpointers_subdict_fout, "w") as f:
        json.dump(uncovered_fpointers_subdict, f, indent=2)
    print("Progs saved with fpointer and skip signal that registered an uncovered function pointer",
         f"(count={len(uncovered_fpointers_subdict)}) saved to {uncovered_fpointers_subdict_fout.name}"
    )

def get_fpointer_store_info(prog2log: dict[str, dict], stable_only = False) -> tuple[set[str], set[str], set[str], dict[str, set[str]]]:
    '''
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.
        stable_only: if true, ignore function pointer stores registered in NEW_FPOINTERS_PAYLOAD.

    Returns:
        tuple[set[str], set[str], set[str], dict[str, set[str]]]: A tuple with four elements:
            all_pcs: set of covered instruction addresses (hexadecimal strings).
            all_fpointers_stores: set of instructions that store a function pointer (hexadecimal strings).
            all_fpointers: set of function pointer values stored (hexadecimal strings).
            fpointer2storeinst: dict function pointer values stored to instructions that store them (hexadecimal strings).
    '''
    all_pcs: set[str] = set()
    all_fpointers_stores: set[str] = set()
    all_fpointers: set[str] = set()
    fpointer2storeinst: dict[str, set[str]] = {}
    for entries in prog2log.values():
        if RESULT_KEYS.PC_COVER in entries:
            all_pcs.update(entries[RESULT_KEYS.PC_COVER])
        if not stable_only and RESULT_KEYS.NEW_FPOINTERS_PAYLOAD in entries:
            for fp in entries[RESULT_KEYS.NEW_FPOINTERS_PAYLOAD]:
                __update_collections(all_fpointers_stores, all_fpointers, fpointer2storeinst, fp)
        if RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD in entries:
            for fp in entries[RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD]:
                __update_collections(all_fpointers_stores, all_fpointers, fpointer2storeinst, fp)
    return all_pcs, all_fpointers_stores, all_fpointers, fpointer2storeinst


def check_PC_exec_funcStore_literal_diffs(
    all_pcs: set[str], all_fpointers_stores: set[str], all_fpointers: set[str]
) -> None:
    """
    Print differences between stored fpointer data and executed PCs using the literal stored numbers
    """

    # First question:
    # How many of the reported instructions that store a value
    #  do not appear in the general log of reported instructions?
    # This should ideally be zero
    store_inst_diff = all_fpointers_stores.difference(all_pcs)
    print(f"Unique function pointer store instructions: (count={len(all_fpointers_stores)})")
    print(f"Function pointer store instructions that don't show up in exec log: (count={len(store_inst_diff)})")
    print("################################################")
    # Second question:
    # How many of the stored function pointers
    #  do not appear as executed instructions in the general log?
    stored_value_diff = all_fpointers.difference(all_pcs)
    print(f"Unique stored function pointers: (count={len(all_fpointers)})")
    print(f"Stored function_pointers that don't show up in exec log: (count={len(stored_value_diff)})")


def check_source_code_diffs(
    all_pcs: set[str], all_fpointers_stores: set[str], all_fpointers: set[str]
) -> tuple[
    dict[str, list[locInfo]], dict[str, list[locInfo]], set[locInfo], set[locInfo]
]:
    """
    Print differences between stored fpointer data and executed PCs using source code location data.

    Args:
        all_pcs: Set of covered instruction addresses (hexadecimal strings).
        all_fpointers_stores: Set of instructions that store a function pointer (hexadecimal strings).
        all_fpointers: Set of function pointer values stored (hexadecimal strings).

    Returns:
        tuple[dict[str, list[locInfo]], dict[str, list[locInfo]], set[locInfo], set[locInfo]]: A tuple with four elements:
            fpointer_addr2location: dict mapping function pointer addresses all its source code locations, including inline resolutions.
            storeinst_addr2location: dict mapping store instruction addresses all its source code locations, including inline resolutions.
            stored_value_diff: set of source code locations for function pointers that were not covered.
            stored_value_intersection: set of source code locations for function pointers that were covered.
    """
    _, pc_locs_all, pc_locs_noinline = get_source_code_refs(all_pcs)
    storeinst_addr2location, storeinst_locs_all, storeinst_locs_noinline = get_source_code_refs(all_fpointers_stores)
    fpointer_addr2location, fpointer_locs, _ = get_source_code_refs(all_fpointers)

    print(f"Unique functions covered: (count={len(pc_locs_all)})")
    print(f"Unique functions covered excluding inlines: (count={len(pc_locs_noinline)})")
    print("------------------------------------------------")
    # First question:
    # How many of the reported instructions that store a value
    #  appear in a function that is not covered by any of the
    #  PCs in the general log of reported instructions?
    store_inst_diff, _ = locInfo_fname_diff(storeinst_locs_all, pc_locs_all)
    # this second one should be smaller
    store_inst_diff_excluding_inlines, _ = locInfo_fname_diff(
        storeinst_locs_noinline, pc_locs_noinline
    )
    print(f"Unique functions of fpointer stores: (count={len(storeinst_locs_all)})")
    print(
        f"Function pointer store instructions in funcions different than PCs: (count={len(store_inst_diff)}):",
        f"\n{sorted(store_inst_diff)}",
    )
    print(
        f"Function pointer store instructions in funcions different than PCs (ignoring inlines in both): (count={len(store_inst_diff_excluding_inlines)}):",
        f"\n{sorted(store_inst_diff_excluding_inlines)}",
    )
    print("------------------------------------------------")
    stored_value_diff, stored_value_intersection = locInfo_fname_diff(fpointer_locs, pc_locs_all)
    stored_value_diff_without_inlines, _ = locInfo_fname_diff(fpointer_locs, pc_locs_noinline)
    print(colored(f"Unique stored functions: (count={len(fpointer_locs)})"))
    print(f"Stored functions that were not executed: (count={len(stored_value_diff)}):")
    print(f"Stored functions that did get executed: (count={len(stored_value_intersection)}):")

    # this second one could be smaller but I expect it to be the same:
    print(
        f"Execution of functions does not depend on inlines: {'Yes' if stored_value_diff_without_inlines == stored_value_diff else 'No'}"
    )
    return (
        fpointer_addr2location,
        storeinst_addr2location,
        stored_value_diff,
        stored_value_intersection,
    )


def locInfo_fname_diff(
    this: set[locInfo], other: set[locInfo]
) -> tuple[set[locInfo], set[locInfo]]:
    """
    Returns two subsets of `this`, using the function name as equality criteria.
    The first set is the difference between `this` and `other, and the second is the intersection.

    i.e all elements in `this` that have a different function name from all elements in `other`
     and all elements in `this` that have the same function name as one element in `other`
    """
    other_fnames = set(fname for floc, fname in other)
    intersection = set()
    diff = set()
    for floc, fname in this:
        new_elem = (floc, fname)
        if fname not in other_fnames:
            diff.add(new_elem)
        else:
            intersection.add(new_elem)
    return diff, intersection


def get_source_code_refs(
    all_pcs: Iterable[str],
) -> tuple[dict[str, list[locInfo]], set[locInfo], set[locInfo]]:
    """
    Receives an iterable of PCs (hexadecimal values)
    Returns a dictionary and two sets.
    The first set is the set of locations those PCs are part of, including inlines.
    The second set is the set of locations those PCs are part of without considering inlines.
    That means for PC 0x00c1, the following function structure:

        // file a.c line 743
        744:    0x00bg    int foo(){
        745:    0x00bf      int x = 7;
                            // inlined "complement_modulo_3"
        746:    0x00c0       int y = -x;
                             //inlined "modulo_3"
        747:    0x00c1        int z = y;
        748:    0x00c2        z = z % 3;
                          (...)
                        }
    Would return {('modulo_3', ??), ('complement_modulo_3', ??) , ('foo', a.c:747)} for 0x00c1 in the first set.
    But it would return just {('foo', a.c:747)} for 0xc00c1 in the second set.
    Finally, the returned dictionary is a mapping from the input PCs to this information for each PC.
    """
    addr2fun_names = _get_source_code_refs_impl(all_pcs)
    pc_info = set(f for flist in addr2fun_names.values() for f in flist)
    pc_info_no_inlines = set(flist[-1] for flist in addr2fun_names.values())
    return addr2fun_names, pc_info, pc_info_no_inlines


def _get_source_code_refs_impl(offsets: Iterable[str]) -> dict[str, list[locInfo]]:
    """
    Returns a mapping containing the source code locations for each
    offset in the input, obtained using addr2line, including inlines
    """
    LINUX_DIR = "/home/dwappner/Desktop/linux"
    # hacky hack:
    # strictly optionally capture the hex value or "(inlined by)"
    output_pattern = re.compile(
        r"^(?:(0x[0-9a-fA-F]+):\s+)?(?:\(inlined by\)\s+)?(.+?)\s+at\s+(.+)$"
    )

    offsets = set(offsets)
    sourceInfo_data: dict[str, list[locInfo]] = {}

    # Pass all addresses via stdin to avoid command-line argument limits
    p = subprocess.Popen(
        args=["addr2line", "-ipfCa", "-e", "vmlinux"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=LINUX_DIR,
        text=True,
        encoding="utf8",
    )
    stdin_data = "\n".join(offsets)
    stdout, _ = p.communicate(input=stdin_data)
    response = [l.strip() for l in stdout.splitlines()]

    for line in response:
        match = output_pattern.match(line)
        if not match:
            # edge case for weird StoredValue values
            if line == "0xffffffffffffffff: ?? ??:0":
                offsets.remove("0xffffffffffffffff")
                continue
            print(colored("ERROR: no match wtf? addr2line line:\n", "red"), line)
            sys.exit(1)
        # 0 is address, 1 is function name, 2 is file location
        addr, fname, floc = match.groups()
        if not addr:
            # hacky hack: if there's no address, we matched "(inlined by)" instead
            sourceInfo_data[current_addr].append((floc, fname))
        else:
            current_addr = addr
            sourceInfo_data[addr] = [(floc, fname)]

    if len(sourceInfo_data) != len(offsets):
        print(
            colored("ERROR: addr2line returned fewer lines than expected. ", "red"),
            colored(f"Sent {len(offsets)}, got {len(sourceInfo_data)}\n", "red"),
        )
        sys.exit(1)

    # hacky hack: since we are operating on PCs as strings instead of as hexadecimal integer values,
    # we need to set the NULL pointer value back to no-trailing-zeroes formatting after addr2line modified it
    if "0x0" in offsets:
        sourceInfo_data["0x0"] = sourceInfo_data.pop("0x0000000000000000")
    return sourceInfo_data


def get_fpointer2storeinst_as_source_locations(
    fpointer2storeinst: dict[str, set[str]],
    fpointer_addr2loc: dict[str, list[locInfo]],
    storeinst_addr2loc: dict[str, list[locInfo]],
    interesting_fpointer_locs: set[locInfo],
) -> tuple[dict[locInfo, set[locInfo]], int]:
    """
    Filters the `fpointer2storeinst` dictionary using `interesting_fpointer_locs`.

    Args:
        fpointer2storeinst: dict from function pointer (hexadecimal strings) to the set of instructions that store it (hexadecimal strings).
        fpointer_addr2loc: dict from function pointer (hexadecimal strings) to source code locations.
        storeinst_addr2loc: dict from store instruction (hexadecimal strings) to source code locations.
        interesting_fpointer_locs: set of source code locations (of function pointers) that must be a key in the output.

    Returns:
        tuple[dict[locInfo, set[locInfo]], set[str], int]: A tuple with two elements:
            output_dir: A dict from source code locations to sets of source code locations.
                        The key represents the source code locations of the interesting function pointers.
                        The values represent the source code locations of the instructions that store them.
            skip_count: The number of `interesting_fpointer_locs` that did not match any fpointer in `fpointer2storeinst`
    """
    interesting_fpointer2loc = {
        fpointer: locs[0]
        for fpointer, locs in fpointer_addr2loc.items()
        if locs[0] in interesting_fpointer_locs
    }
    skip_count = 0
    output_dir: dict[locInfo, set[locInfo]] = {}
    for fpointer_addr, fpointer_loc in interesting_fpointer2loc.items():
        if fpointer_addr not in fpointer2storeinst:
            skip_count += 1
            continue
        if fpointer_loc not in output_dir:
            output_dir[fpointer_loc] = set()
        for storeinst_addr in fpointer2storeinst[fpointer_addr]:
            output_dir[fpointer_loc].update(storeinst_addr2loc[storeinst_addr])
    return output_dir, skip_count


def __update_collections(
    all_fpointers_stores: set[str],
    all_fpointers: set[str],
    fpointer2storeinst: dict[str, set[str]],
    fp: dict[str, str],
) -> None:
    fpointer = fp["StoredValue"]
    storeinst = fp["PC"]
    all_fpointers.add(fpointer)
    all_fpointers_stores.add(storeinst)
    if fpointer not in fpointer2storeinst:
        fpointer2storeinst[fpointer] = set()
    fpointer2storeinst[fpointer].add(storeinst)


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
    cleanup_fpointer_jsons(out_json)
    print(colored("################################################", "cyan"))
    out_json = check_pc_cover_vs_fpointer(out_json)
    print(colored("################################################", "cyan"))
    check_easy_stats(out_json)
    print(colored("################################################", "cyan"))
    check_duplicated_progs(out_json)
    print(colored("################################################", "cyan"))
    check_saved_because_fpointer(out_json)
    print(colored("################################################", "cyan"))
    check_minimization_stats(out_json)

    with out_path.open("w") as f:
        f.write(json.dumps(out_json, indent=2) + "\n")
