#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from termcolor import colored

from logentry_keys import (FPOINTERS_PAYLOAD_VALUES,
                           MINIMIZATION_RESULT_VALUES, PC_VALUES, RESULT_KEYS, locInfo)


def unify_per_prog(json_lines_file: Path) -> dict[str, dict[str, Any]]:
    """Parse a JSON lines file and merge entries by prog/call identity.

    The returned dictionary maps a combined key representing pairs of
    <prog_id, call_name> to a single merged entry dict.

    Each value dict contains all relevant information for that <prog, call>
    pair during a triage.
    If more than one repeated occurrence of a specific <prog, call> pair is
    found during different triages, all occurences after the first one are ignored.
    """
    result_dict: dict[str, dict[str, Any]] = {}
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
            log_entry: dict[str, Any] = json.loads(line)
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

            # before using data_key, let's check if we should update it.
            # (does this break the "skip repeated triages rule"?)
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

            # If it is not the first occurence of data_key, we want to check that triage_id is the same.
            # If it is not, that means we have identical <prog, call> pairs in different triages.
            # This probably means that on two different instances the fuzzer generated the same prog
            # and obtained similar (flaky?) coverage to triage.
            # Let's only log the results for the first time the prog gets triaged,
            # but let's also make sure to increase the count.
            if no_new and triage_id not in result_dict[data_key][RESULT_KEYS.TRIAGEID]:
                result_dict[data_key][RESULT_KEYS.TRIAGEID].append(triage_id)
                result_dict[data_key][RESULT_KEYS.COUNT] += 1

            if no_new and result_dict[data_key][RESULT_KEYS.COUNT] > 1:
                ## Before we ignore this duplicate entry, queue whatever we're missing
                ## just in case, so that the next entry that would get its key updated
                ## can be recognized as duplicate properly and be ignored.
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
                            result_dict[data_key][minim_key], minim_entry, data_key, minim_key
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

            # timestamp needs to be joined accross entries for the same triage.
            # we keep the first and latest timestamps.
            if RESULT_KEYS.TIMESTAMP in log_entry:
                timestamp_entry = log_entry.pop(RESULT_KEYS.TIMESTAMP)
                timestamp_value = datetime.strptime(timestamp_entry, '%Y-%m-%d %H:%M:%S')
                if no_new:
                    assert RESULT_KEYS.TIMESTAMP_END in result_dict[data_key]
                    assert RESULT_KEYS.TIMESTAMP_BEGIN in result_dict[data_key]
                    old_ts_end = result_dict[data_key][RESULT_KEYS.TIMESTAMP_END]
                    old_ts_begin = result_dict[data_key][RESULT_KEYS.TIMESTAMP_BEGIN]
                    result_dict[data_key][RESULT_KEYS.TIMESTAMP_END] = max(timestamp_value, old_ts_end)
                    result_dict[data_key][RESULT_KEYS.TIMESTAMP_BEGIN] = min(timestamp_value, old_ts_begin)
                else:
                    log_entry[RESULT_KEYS.TIMESTAMP_END] = timestamp_value
                    log_entry[RESULT_KEYS.TIMESTAMP_BEGIN] = timestamp_value

            # tags also needs to be joined accross entries for the same triage.
            # we keep an union of tags and assume they are incremental.
            if RESULT_KEYS.TAGS in log_entry:
                entry_tags = log_entry.pop(RESULT_KEYS.TAGS)
                if no_new:
                    assert (all(tag in entry_tags for tag in result_dict[data_key][RESULT_KEYS.TAGS]))
                    result_dict[data_key][RESULT_KEYS.TAGS] = entry_tags
                else:
                    log_entry[RESULT_KEYS.TAGS] = entry_tags

            # Get the union for PC_COVER.
            # Ideally we only get duplicate PC_COVER in the case of minimization split.
            # Nevertheless, when two different prog_id + call pairs generate the same program after minimization,
            # this will result in two different triage subjobs mapping into the same json entry (thanks to override_if_awaiting).
            # FIXME: This is a bug; but handling it by joining their PC_COVERAGE together seems fine for now.
            if RESULT_KEYS.PC_COVER in log_entry:
                cover_payload = log_entry.pop(RESULT_KEYS.PC_COVER)
                if no_new and RESULT_KEYS.PC_COVER in result_dict[data_key]:
                    old_payload = set(result_dict[data_key][RESULT_KEYS.PC_COVER])
                    old_payload.update(cover_payload)
                    result_dict[data_key][RESULT_KEYS.PC_COVER] = list(old_payload)
                else:
                    log_entry[RESULT_KEYS.PC_COVER] = cover_payload

            if not no_new:
                log_entry[RESULT_KEYS.ORIGINAL_PROG] = curr_original_prog
                log_entry[RESULT_KEYS.COUNT] = 1
                log_entry[RESULT_KEYS.TRIAGEID] = [triage_id]
                result_dict[data_key] = log_entry
            else:
                # all remaining keys should appear only once
                # per <prog_id, call> pair. Note that the ones for which
                # this doesn't hold have been removed previously.
                for key in log_entry:
                    if key in result_dict[data_key]:
                        warn_overwrite(result_dict[data_key], log_entry, data_key, key)
                        sys.exit(1)
                result_dict[data_key].update(log_entry)

    awaiting_corpus_entry = fix_buggy_awaiting_queue(result_dict, awaiting_corpus_entry)
    if len(awaiting_corpus_entry) > 0:
        print(
            colored(f"ERROR: after parsing all triage lines there is at least one job awaiting entry:", 'red')
            + colored(json.dumps(awaiting_corpus_entry, indent=2), "yellow"),
            file=sys.stderr
        )
        sys.exit(1)
    return result_dict

def fix_buggy_awaiting_queue(result_dict: dict[str, dict[str, Any]], awaiting_corpus_entry: dict[str, str]) -> dict[str, str]:
    '''
    Remove from result_dict and awaiting_corpus_entry
    all entries in awaiting_corpus_entry that have '(BADINDEX)'
    in the description of the original prog, as these are
    instances where syzkaller bugged out.
    '''
    __awaiting = {}
    for awaiting_key, res_dict_key in awaiting_corpus_entry.items():
        progs_to_check = [result_dict[res_dict_key][RESULT_KEYS.ORIGINAL_PROG]]
        if RESULT_KEYS.MINIMIZATION_RESULT in result_dict[res_dict_key]:
            for min_result_entry in result_dict[res_dict_key][RESULT_KEYS.MINIMIZATION_RESULT]:
                progs_to_check.append(min_result_entry.get(RESULT_KEYS.MINIMIZATION_RES_PROG, []))
        if any("(BADINDEX)" in prog_line for check_prog in progs_to_check for prog_line in check_prog):
            result_dict.pop(res_dict_key)
        else:
            # This was not a bugged out syzkaller log, actually keep it in the awaiting dictionary
            __awaiting[awaiting_key] = res_dict_key
    awaiting_corpus_entry = __awaiting
    return awaiting_corpus_entry


def successful_minimize(minim_entry: list[dict[str, Any]]) -> bool:
    """
    Return true if this entry indicates that one of the minimization attempts produced something
    """
    assert len(minim_entry) == 1
    return minim_entry[0][RESULT_KEYS.MINIMIZATION_RES_TYPE] in [
        MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_NODIFF,
        MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER,
        MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_SIGNAL,
    ]


def update_queues(
    awaiting_corpus_entry: dict[str, str],
    awaiting_pc_cover: dict[str, str],
    prog_id: str,
    data_key: str,
    triage_id: str,
    minim_entry: list[dict[str, Any]],
) -> None:
    """
    Store in awaiting_corpus_entry the data_key used for this prog_id, triage_id pair.
    Also update awaiting_pc_cover if the minimization result was nonempty for pointer coverage,
    since this will trigger a future pc_cover type entry for the same triage job.
    """
    awaiting_corpus_entry[get_ceq_key(prog_id, triage_id)] = data_key

    # additionally, if the prog is entering because of pointer coverage
    # we need to capture the raw pc coverage
    assert len(minim_entry) == 1
    if minim_entry[0][RESULT_KEYS.MINIMIZATION_RES_TYPE] in [
        MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_NODIFF,
        MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER,
    ]:
        awaiting_pc_cover[get_ceq_key(prog_id, triage_id)] = data_key


def override_if_awaiting(
    data_key: str,
    awaiting_queue: dict[str, str],
    log_entry: dict[str, dict[str, Any]],
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


def minimization_would_overwrite(result_entry: dict[str, Any], minim_entry: list[dict[str, Any]]) -> bool:
    minim_key = RESULT_KEYS.MINIMIZATION_RESULT
    minim_t_key = RESULT_KEYS.MINIMIZATION_RES_TYPE
    assert len(minim_entry) == 1
    return any(
        saved_res[minim_t_key] == minim_entry[0][minim_t_key]
        for saved_res in result_entry[minim_key]
    )


def warn_overwrite(result_entry: dict[str, Any], log_entry: dict[str, Any], prog_id: str, conflicting_key: str) -> None:
    result_container = {conflicting_key: result_entry}
    entry_container = {conflicting_key: log_entry}
    serialize_datetimes(result_container)
    serialize_datetimes(entry_container)
    print(
        colored(f"ERROR: would overrite key {conflicting_key} in {prog_id}\n", "red")
        + colored(json.dumps(result_container[conflicting_key], indent=2), "yellow")
        + colored("\nwhen adding\n", "red")
        + colored(json.dumps(entry_container[conflicting_key], indent=2), "yellow"),
        file=sys.stderr
    )


def cleanup_particular_fpointer(entries: dict[str, Any], key2json_entry: str) -> None:
    """
    Receives a key where the value is a literal string containing json
    Parses the string into the nested json and writes it back in dict
    """
    fpointer_json = json.loads(entries[key2json_entry])
    entries[key2json_entry] = fpointer_json


def cleanup_fpointer_jsons(unified_json: dict[str, dict[str, Any]]) -> None:
    for entries in unified_json.values():
        for key in (
            RESULT_KEYS.NEW_FPOINTERS_PAYLOAD,
            RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD,
        ):
            if key in entries:
                cleanup_particular_fpointer(entries, key)


def serialize_datetimes(unified_json: dict[str, dict[str, Any]]) -> None:
    '''
    Serializes datetimes in each entry up to the first level (does not look into nested json)
    '''
    for entries in unified_json.values():
        for k, v in entries.items():
            if isinstance(v, datetime):
                entries[k] = str(v)


def cleanup_unified_json(unified_json: dict[str, dict[str, Any]]) -> None:
    cleanup_fpointer_jsons(unified_json)
    serialize_datetimes(unified_json)



def update_master_dict_with_fpointer_loc_data(prog2log: dict[str, dict[str, Any]],
                                              pcs_addr2loc: dict[str, list[locInfo]],
                                              fpointer_addr2loc: dict[str, list[locInfo]],
                                              storeinst_addr2loc: dict[str, list[locInfo]]) -> dict[str, dict[str, Any]]:
    error_locInfo: list[locInfo] = [("err", "err")]
    for entry in prog2log.values():
        if RESULT_KEYS.PC_COVER in entry:
            pc_loc_entries = []
            for pc_value in entry[RESULT_KEYS.PC_COVER]:
                # hacky hack: we will not have a location for this "empty" pointer
                pc_loc = pcs_addr2loc[pc_value] if pc_value != '0xffffffffffffffff' else error_locInfo
                pc_entry = {PC_VALUES.PC_ADDRESS : pc_value,
                            PC_VALUES.PC_LOCATION : pc_loc}
                pc_loc_entries.append(pc_entry)
            entry[RESULT_KEYS.PC_COVER] = pc_loc_entries

        for funcPointer_store_entry in entry.get(RESULT_KEYS.NEW_FPOINTERS_PAYLOAD, []):
            fPointer = funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.FPOINTER_ADDR]
            storeInst = funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.STOREINST_ADDR]
            # hacky hack: we will not have a location for this "empty" pointer
            fPointer_loc = fpointer_addr2loc[fPointer] if fPointer != '0xffffffffffffffff' else error_locInfo
            funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC] = fPointer_loc
            funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.STOREINST_LOC] = storeinst_addr2loc[storeInst]

        for funcPointer_store_entry in entry.get(RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD, []):
            fPointer = funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.FPOINTER_ADDR]
            storeInst = funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.STOREINST_ADDR]
            #hacky hack: see above
            fPointer_loc = fpointer_addr2loc[fPointer] if fPointer != '0xffffffffffffffff' else error_locInfo
            funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.FPOINTER_LOC] = fPointer_loc
            funcPointer_store_entry[FPOINTERS_PAYLOAD_VALUES.STOREINST_LOC] = storeinst_addr2loc[storeInst]

    return prog2log


def update_w_address_data(prog2log: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    all_pcs = set()
    all_fpointers_stores = set()
    all_fpointers = set()

    def _update_fpointers_and_stores(fp: dict[str, str]) -> None:
        fpointer = fp[FPOINTERS_PAYLOAD_VALUES.FPOINTER_ADDR]
        storeinst = fp[FPOINTERS_PAYLOAD_VALUES.STOREINST_ADDR]
        all_fpointers.add(fpointer)
        all_fpointers_stores.add(storeinst)

    for entries in prog2log.values():
        if RESULT_KEYS.PC_COVER in entries:
            all_pcs.update(entries[RESULT_KEYS.PC_COVER])
        if RESULT_KEYS.NEW_FPOINTERS_PAYLOAD in entries:
            for fp in entries[RESULT_KEYS.NEW_FPOINTERS_PAYLOAD]:
                _update_fpointers_and_stores(fp)
        if RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD in entries:
            for fp in entries[RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD]:
                _update_fpointers_and_stores(fp)

    pcs_addr2loc, fpointer_addr2loc, storeinst_addr2loc = get_PCs_to_locs(all_pcs, all_fpointers_stores, all_fpointers)
    prog2log = update_master_dict_with_fpointer_loc_data(prog2log, pcs_addr2loc, fpointer_addr2loc, storeinst_addr2loc)

    return prog2log

def get_PCs_to_locs(all_pcs: set[str], all_fpointers_stores: set[str], all_fpointers: set[str]) -> tuple[
    dict[str, list[locInfo]], dict[str, list[locInfo]], dict[str, list[locInfo]]
]:
    """
    Args:
        all_pcs: Set of covered instruction addresses (hexadecimal strings).
        all_fpointers_stores: Set of instructions that store a function pointer (hexadecimal strings).
        all_fpointers: Set of function pointer values stored (hexadecimal strings).

    Returns:
        tuple[dict[str, list[locInfo]], dict[str, list[locInfo]], dict[str, list[locInfo]]]: A tuple with three elements:
            allpcs_addr2location: dict mapping PC addresses to their source code locations, including inline resolutions.
            fpointer_addr2location: dict mapping function pointer addresses to their source code locations, including inline resolutions.
            storeinst_addr2location: dict mapping store instruction addresses to their source code locations, including inline resolutions.
    """
    allpcs_addr2location = get_source_code_refs(all_pcs)
    storeinst_addr2location = get_source_code_refs(all_fpointers_stores)
    fpointer_addr2location = get_source_code_refs(all_fpointers)
    return allpcs_addr2location, fpointer_addr2location, storeinst_addr2location



def get_source_code_refs(
    all_pcs: Iterable[str],
) -> dict[str, list[locInfo]]:
    """
    Receives an iterable of PCs (hexadecimal values)
    Returns a dictionary mapping from the input PCs to a list of source code locations, including inlines.
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
    Would return [('modulo_3', ??), ('complement_modulo_3', ??) , ('foo', a.c:747)] for 0x00c1.
    """
    addr2fun_names = _get_source_code_refs_impl(all_pcs)
    return addr2fun_names


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
            print(colored("ERROR: no match wtf? addr2line line:\n", "red"), line, file=sys.stderr)
            sys.exit(1)
        # 0 is address, 1 is function name, 2 is file location
        addr, fname, floc = match.groups()
        if not addr:
            # hacky hack: if there's no address, we matched "(inlined by)" instead
            sourceInfo_data[current_addr].append((floc, fname))
        else:
            current_addr : str = addr
            sourceInfo_data[addr] = [(floc, fname)]

    if len(sourceInfo_data) != len(offsets):
        print(
            colored("ERROR: addr2line returned fewer lines than expected. ", "red"),
            colored(f"Sent {len(offsets)}, got {len(sourceInfo_data)}\n", "red"),
            file=sys.stderr
        )
        sys.exit(1)

    # hacky hack: since we are operating on PCs as strings instead of as hexadecimal integer values,
    # we need to set the NULL pointer value back to no-trailing-zeroes formatting after addr2line modified it
    if "0x0" in offsets:
        sourceInfo_data["0x0"] = sourceInfo_data.pop("0x0000000000000000")
    return sourceInfo_data


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
    cleanup_unified_json(out_json)
    out_json = update_w_address_data(out_json)

    with out_path.open("w") as f:
        f.write(json.dumps(out_json, indent=2) + "\n")
