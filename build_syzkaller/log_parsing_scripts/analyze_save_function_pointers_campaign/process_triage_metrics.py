#!/usr/bin/env python3
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

from termcolor import colored

from logentry_keys import (FPOINTERS_PAYLOAD_VALUES,
                           MINIMIZATION_RESULT_VALUES, PC_VALUES, RESULT_KEYS, locInfo)


def convert_types_nicely(prog2log: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:

    def convert_locations_list(dict_entry:dict[str,list[str]], key:str) -> list[locInfo]:
        neat: list[locInfo] = [(funct, line) for funct, line in dict_entry[key]]
        return neat

    for prog_key, entries in prog2log.items():
        key1 = FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC
        key2 = FPOINTERS_PAYLOAD_VALUES.STOREINST_LOC
        for fpointer_payload in entries.get(RESULT_KEYS.NEW_FPOINTERS_PAYLOAD, []):
            neat1 = convert_locations_list(fpointer_payload, key1)
            neat2 = convert_locations_list(fpointer_payload, key2)
            fpointer_payload[key1] = neat1
            fpointer_payload[key2] = neat2
        for fpointer_payload in entries.get(RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD,[]):
            neat1 = convert_locations_list(fpointer_payload, key1)
            neat2 = convert_locations_list(fpointer_payload, key2)
            fpointer_payload[key1] = neat1
            fpointer_payload[key2] = neat2
        for pc_entry in entries.get(RESULT_KEYS.PC_COVER, []):
            neat = convert_locations_list(pc_entry, PC_VALUES.PC_LOCATION)
            pc_entry[PC_VALUES.PC_LOCATION] = neat

    return prog2log

def count_cond(prog2log: dict[str, dict[str, Any]], condition: Callable[[dict[str, Any]], bool]) -> int:
    return len([entry for entry in prog2log.values() if condition(entry)])


def filter_many_cond(
    prog2log: dict[str, dict[str, Any]], *conditions: Callable[[dict[str, Any]], bool]
) -> dict[str, dict[str, Any]]:
    return {
        key: val
        for key, val in prog2log.items()
        if all(cond(val) for cond in conditions)
    }


def check_easy_stats(prog2log: dict[str, dict[str, Any]]) -> None:
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


def has_minimization_result(minimization_result_type: str) -> Callable[[dict[str, Any]], bool]:
    '''
    Args:
        minimization_result_type: desired key in one of the minimization results in an entry

    Returns:
        function that returns True for entries that have the specified minimization result type
    '''
    def checker(prog_entry: dict[str, Any]) -> bool:
        if RESULT_KEYS.MINIMIZATION_RESULT not in prog_entry:
            return False
        minimization_result: list[dict[str, Any]] = prog_entry[RESULT_KEYS.MINIMIZATION_RESULT]
        if type(minimization_result) != list:
            print(
                colored(
                    "ERROR: type of minimization result is not list. Minimization result:",
                    "red",
                )
                + colored(str(minimization_result), "yellow"),
                file=sys.stderr
            )
            sys.exit(1)
        return any(
            minimization_result_type == res[RESULT_KEYS.MINIMIZATION_RES_TYPE]
            for res in minimization_result
        )

    return checker


def get_duplicate_progs(
    prog2log: dict[str, dict[str, Any]],
) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    prog2_count = defaultdict(list)
    for key, entry in prog2log.items():
        for prog in entry.get(RESULT_KEYS.SAVED_PROG, []):
            prog2_count[hash("".join(prog))].append(key)

    duplicate = {prog: keys for prog, keys in prog2_count.items() if len(keys) > 1}
    return prog2_count, duplicate


def deduplicate_saved_progs(prog2log: dict[str, dict[str, Any]]) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    int]:
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


def get_saved_because_skip_signal(prog2log: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    '''
    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.

    Returns:
        sub-dictionary of the input where only functionPointerCoverage was interesting
    '''
    return filter_many_cond(
        prog2log,
        has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SIGNAL_SKIP),
        has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER),
    )


def check_duplicated_progs(prog2log: dict[str, dict[str, Any]]) -> None:
    prog2_count, duplicate = get_duplicate_progs(prog2log)
    print(f"Number of unique progs saved in corpus: {len(prog2_count)}")
    print(f"Number of progs saved more than once: {len(duplicate)}")


def check_saved_because_fpointer(prog2log: dict[str, dict[str, Any]]) -> None:
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


def check_minimization_stats(prog2log: dict[str, dict[str, Any]]) -> None:
    n_skip_all = count_cond(
        prog2log, has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_SKIP)
    )
    n_skip_fpointer = count_cond(
        prog2log, has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_FPOINTER_SKIP)
    )
    n_skip_signal = count_cond(
        prog2log, has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SIGNAL_SKIP)
    )

    n_saved_fpointer = count_cond(
        prog2log, has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER)
    )

    n_saved_signal = count_cond(
        prog2log, has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_SIGNAL)
    )

    n_keep_both = count_cond(
        prog2log, has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_NODIFF)
    )

    unique_signal_and_fpointer = filter_many_cond(
        prog2log,
        has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER),
        has_minimization_result(MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_SIGNAL),
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


def check_pc_cover_vs_fpointer(prog2log: dict[str, dict[str, Any]]) -> None:
    all_pcs, all_fpointers_stores, all_fpointers, fpointer2storeinst = get_fpointer_store_info(prog2log)

    check_PC_exec_funcStore_literal_diffs(all_pcs, all_fpointers_stores, all_fpointers)
    print(colored("################################################", "cyan"))
    (
        fpointer_addr2loc,
        storeinst_addr2loc,
        uncovered_fpointer_locs,
        covered_fpointer_locs,
    ) = check_source_code_diffs(prog2log)

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


def check_saved_because_skip_signal_vs_fpointers(prog2log: dict[str, dict[str, Any]],
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
                                                     # Each entry in FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC a list of locations.
                                                     # The first one is the top-most function, where every other one is an "(inlined-by)" statement.
                                                     # We are asking if a function pointer that was actually stored, was covered,
                                                     # so the list of locations for the function pointer shouldn't have any entries besides the first one.
                                                     fPointer_entry[FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC][0] in covered_fpointer_locs
                                                     for fPointer_entry in e.get(RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD, [])
                                                 ))
    uncovered_fpointers_subdict = filter_many_cond(saved_because_skip_signal,
                                                 lambda e: any(
                                                     # see above
                                                     fPointer_entry[FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC][0] in uncovered_fpointer_locs
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

def get_fpointer_store_info(prog2log: dict[str, dict[str, Any]], stable_only: bool = False) -> tuple[set[str], set[str], set[str], dict[str, set[str]]]:
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
            all_pcs.update(pc_entry[PC_VALUES.PC_ADDRESS] for pc_entry in entries[RESULT_KEYS.PC_COVER])
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
    # This should ideally be zero.
    # It will not be since instruction vs basic block start often misalign
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


def check_source_code_diffs(prog2log: dict[str, dict[str, Any]]) -> tuple[
    dict[str, list[locInfo]],
    dict[str, list[locInfo]],
    set[locInfo],
    set[locInfo]
]:
    """
    Print differences between stored fpointer data and executed PCs using source code location data.

    Args:
        prog2log: dictionary with the standard format for triage entries of each prog|call pair.

    Returns:
        tuple[dict[str, list[locInfo]], dict[str, list[locInfo]], set[locInfo], set[locInfo]]: A tuple with four elements:
            fpointer_addr2location: dict mapping function pointer addresses all its source code locations, including inline resolutions.
            storeinst_addr2location: dict mapping store instruction addresses all its source code locations, including inline resolutions.
            stored_value_diff: set of source code locations for function pointers that were not covered.
            stored_value_intersection: set of source code locations for function pointers that were covered.
    """
    storeinst_addr2location, fpointer_addr2location, storeinst_locs, fpointer_locs = get_fPointeStore_dicts_and_locs(prog2log)

    all_pc_locs = get_unique_covered_functions(prog2log)

    print(f"Unique functions covered: (count={len(all_pc_locs)})")
    print("------------------------------------------------")
    # First question:
    # How many of the reported instructions that store a value
    #  appear in a function that is not covered by any of the
    #  PCs in the general log of reported instructions?
    store_inst_diff, _ = locInfo_fname_diff(storeinst_locs, all_pc_locs)

    print(f"Unique functions of fpointer stores: (count={len(storeinst_locs)})")
    print(
        f"Function pointer store instructions in funcions different than PCs: (count={len(store_inst_diff)}):",
        f"\n{sorted(store_inst_diff)}",
    )
    print("------------------------------------------------")
    stored_value_diff, stored_value_intersection = locInfo_fname_diff(fpointer_locs, all_pc_locs)
    print(colored(f"Unique stored functions: (count={len(fpointer_locs)})"))
    print(f"Stored functions that were not executed: (count={len(stored_value_diff)}):")
    print(f"Stored functions that did get executed: (count={len(stored_value_intersection)}):")
    return (
        fpointer_addr2location,
        storeinst_addr2location,
        stored_value_diff,
        stored_value_intersection,
    )

def get_fPointeStore_dicts_and_locs(prog2log: dict[str, dict[str, Any]]) -> tuple[
    dict[str, list[locInfo]],
    dict[str, list[locInfo]],
    set[locInfo],
    set[locInfo]
]:
    storeinst_addr2location : dict[str, list[locInfo]] = dict()
    fpointer_addr2location : dict[str, list[locInfo]] = dict()
    storeinst_locs : set[locInfo] = set()
    fpointer_locs : set[locInfo] = set()

    def _fill_collections(fp: dict[str, Any]) -> None:
        fp_loc : list[locInfo] = fp[FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC]
        fp_addr : str = fp[FPOINTERS_PAYLOAD_VALUES.FPOINTER_ADDR]
        storeinst_loc : list[locInfo] = fp[FPOINTERS_PAYLOAD_VALUES.STOREINST_LOC]
        storeinst_addr : str = fp[FPOINTERS_PAYLOAD_VALUES.STOREINST_ADDR]

        storeinst_addr2location[storeinst_addr] = storeinst_loc
        storeinst_locs.update(storeinst_loc)
        fpointer_addr2location[fp_addr] = fp_loc
        fpointer_locs.update(fp_loc)

    for e in prog2log.values():
        if RESULT_KEYS.NEW_FPOINTERS_PAYLOAD in e:
            for fp in e[RESULT_KEYS.NEW_FPOINTERS_PAYLOAD]:
                _fill_collections(fp)
        if RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD in e:
            for fp in e[RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD]:
                _fill_collections(fp)
    return storeinst_addr2location,fpointer_addr2location,storeinst_locs,fpointer_locs

def get_unique_covered_functions(prog2log: dict[str, dict[str, Any]]) -> set[locInfo]:
    all_pc_locs: set[locInfo] = set()
    for e in prog2log.values():
        for pc_entry in e.get(RESULT_KEYS.PC_COVER, []):
            all_pc_locs.update(pc_entry[PC_VALUES.PC_LOCATION])
    return all_pc_locs


def locInfo_fname_diff(
    this: Iterable[locInfo], other: Iterable[locInfo]
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
    fpointer = fp[FPOINTERS_PAYLOAD_VALUES.FPOINTER_ADDR]
    storeinst = fp[FPOINTERS_PAYLOAD_VALUES.STOREINST_ADDR]
    all_fpointers.add(fpointer)
    all_fpointers_stores.add(storeinst)
    if fpointer not in fpointer2storeinst:
        fpointer2storeinst[fpointer] = set()
    fpointer2storeinst[fpointer].add(storeinst)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse a json file to process triage job data."
    )
    parser.add_argument(
        "unified_json_path",
        type=str,
        nargs="?",
        help="Json file outputted by unify_triage_lines.py",
    )

    args = parser.parse_args()

    if not args.unified_json_path:
        parser.print_help()
        sys.exit(1)

    unified_json_path = Path(args.unified_json_path)
    if not unified_json_path.exists():
        print(
            f"Error: The specified json file does not exist: {unified_json_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(unified_json_path, 'r') as f:
        __contents = f.read()
    triage_json = json.loads(__contents)
    triage_json = convert_types_nicely(triage_json)

    print(colored("################################################", "cyan"))
    check_pc_cover_vs_fpointer(triage_json)
    print(colored("################################################", "cyan"))
    check_easy_stats(triage_json)
    print(colored("################################################", "cyan"))
    check_duplicated_progs(triage_json)
    print(colored("################################################", "cyan"))
    check_saved_because_fpointer(triage_json)
    print(colored("################################################", "cyan"))
    check_minimization_stats(triage_json)
