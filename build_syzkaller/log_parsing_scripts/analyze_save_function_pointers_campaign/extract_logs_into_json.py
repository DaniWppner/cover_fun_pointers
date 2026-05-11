#!/usr/bin/env python3
"""
FIXME
This script allows parsing of a syzkaller log to generate a json with all
log entries where a syzkaller prog (testcase) produced coverage on a saved
function pointer. The output format will be:
[
    {
        "prog_id": str,
        "call": str,
        "function_pointers": [
            {
                "PC": hex value,
                "StoreAddr": hex value,
                "StoredValue": hex value
            },
            ...
        ]
    },
    ...
]

It takes the path to the syzkaller log and the path to the output JSON file as parameters.
FIXME
"""

import re
import json
import argparse
from pathlib import Path
from enum import Enum
import sys
import itertools


class InvalidTriageLine(Exception):
    pass


class LOGENTRY_KEYS(Enum):
    NEW_FPOINTERS = "new_fpointers"
    NEW_SIGNAL = "new_signal"
    STABLE_FPOINTERS = "stable_fpointers"
    STABLE_SIGNAL = "stable_signal"
    SAVED_ITEM = "saved_item"
    MINIMIZATION_REPORT_NO_DIFF = "minimization_result_equal"
    MINIMIZATION_REPORT_SAVE_FPOINTERS = "minimization_result_no_signal"
    MINIMIZATION_REPORT_SAVE_SIGNAL = "minimization_result_no_fpointer"
    MINIMIZATION_SKIP = "minimization_skip"


class RESULT_KEYS(Enum):
    NEW_FPOINTERS = "new_fpointers"
    NEW_SIGNAL = "new_signal"
    STABLE_FPOINTERS = "stable_fpointers"
    NEW_STABLE_FPOINTERS = "new_stable_fpointers"
    STABLE_SIGNAL = "stable_signal"
    NEW_STABLE_SIGNAL = "new_stable_signal"
    MINIMIZATION_SKIP = "minimization_skip"
    CALL_NAME = "call"
    SAVED_PROG = "prog_in_corpus"
    MINIMIZATION_RESULT = "minimization_result"
    MINIMIZATION_RES_PROG = "result_prog"
    MINIMIZATION_RES_TYPE = "type"


class RESULT_VALUES(Enum):
    MINIMIZATION_RES_NODIFF = "signal_fpointer_equal"
    MINIMIZATION_RES_SAVE_SIGNAL = "save_signal_no_fpointer"
    MINIMIZATION_RES_SAVE_FPOINTER = "save_fpointer_no_signal"


def read_serializaed_prog(line_number: int, og_text: list[int]) -> list[str]:
    """
    Get the prog beginning at line 2 from that look something like this:

      0:  2026/05/07 17:36:32 2026-05-07 17:35:25 [triage-0x2c66bd416580] [prog-3af49541f8b3717b5c63fdff7cadac27035857ab]:
      1:  r0 = syz_io_uring_setup(0xf00, &(0x7f0000000080)={0x0, 0x0, 0xc00, 0x0, 0x0, 0x0, 0x0}, &(0x7f0000000100), &(0x7f0000000140), &(0x7f0000000180))
      2:  io_uring_enter(r0, 0x1, 0x1, 0x1, 0x0, 0x0)
      3:  ioctl$INCFS_IOC_READ_FILE_SIGNATURE(r0, 0x8010671f, &(0x7f0000000040)={&(0x7f0000000000)=""/8, 0x8})
      4:

    @params: line_number will be the first relevant line (1 in the example)
             og_text is a list of the lines in the log file
    """
    return list(itertools.takewhile(lambda line: line != "\n", og_text[line_number:]))


def __create_master_regex(
    patterns: dict[str, str],
) -> tuple[re.Pattern, dict[str, list[int]]]:
    """
    Returns a master regex that can match any of the regexes in patterns,
        where the match will include the name in the dictionary as the name of one of the groups

    Also returns a dictionary mapping the pattern name to the indexes used in a master regex's match
        to find the groups in the actual pattern that matched
    """
    named_patterns = []
    pattern_to_idxs = {}
    current_idx = 1  # re groups are 1-indexed

    for pattern_name, pattern_regex in patterns.items():
        pattern_group_count = re.compile(pattern_regex).groups
        # This is python's re format to giving `name` to `pattern` inside a bigger regex
        named_patterns.append(f"(?P<{pattern_name}>{pattern_regex})")
        # The named group takes 1 index.
        start_idx = current_idx + 1
        end_idx = start_idx + pattern_group_count
        pattern_to_idxs[pattern_name] = list(range(start_idx, end_idx))
        current_idx += 1 + pattern_group_count

    # The master regex is all of the individual pattern groups joined with the '|' regex operator.
    master_re = re.compile("|".join(named_patterns))
    return master_re, pattern_to_idxs


def create_triage_master_regex() -> tuple[re.Pattern, dict[str, list[int]]]:
    # Regex breakdown:
    # call #\d+ \[([^\]]+)\] -> Captures the call name (e.g., syz_genetlink)
    call_pattern = r"call #\d+ \[([^\]]+)\]"

    # Some entries include information from the couple log lines following the entry itself.
    # Those are the onees where the pattern ends in something like "with program:"
    patterns = {
        LOGENTRY_KEYS.NEW_SIGNAL: call_pattern + r": \|new signal\|=(\d+)",
        LOGENTRY_KEYS.NEW_FPOINTERS: call_pattern
        + r": \|new stored function pointers\|=(\d+)",
        LOGENTRY_KEYS.STABLE_SIGNAL: call_pattern
        + r": \|stable signal\|=(\d+)"
        + r", \|new stable signal\|=(\d+)",
        LOGENTRY_KEYS.STABLE_FPOINTERS: call_pattern
        + r": \|stable stored function pointers\|=(\d+)"
        + r", \|new stable stored function pointers\|=(\d+)",
        # Need to retrieve prog after this entry
        LOGENTRY_KEYS.SAVED_ITEM: r"added new input for "
        + call_pattern
        + " to the corpus with program:",
        LOGENTRY_KEYS.MINIMIZATION_REPORT_NO_DIFF: call_pattern
        + r": minimization yielded same prog for signal and stored function pointers",
        # Need to retrieve prog after this entry
        LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_FPOINTERS: call_pattern
        + r": minimization yielded prog for stored function pointers different from signal. New prog \(call #\d+\):",
        # Need to retrieve prog after this entry
        LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_SIGNAL: call_pattern
        + r": minimization yielded prog for signal different from stored function pointers. New prog \(call #\d+\):",
        LOGENTRY_KEYS.MINIMIZATION_SKIP: r"skip minimize",
    }
    return __create_master_regex(patterns)


def parse_raw_triage_logs(log_text: str) -> list[dict]:
    # Regex breakdown:
    # \[(triage-[^\]]+)\] -> Captures the triage-id (e.g., triage-0x2c66bd608c80)
    # \[(prog-[^\]]+)\]   -> Captures the prog-id (e.g., prog-0x351ec85d0480)
    # (.*)                -> Captures the rest of the log entry

    indentify_triage_re = re.compile(r"\[(triage-[^\]]+)\] \[(prog-[^\]]+)\]: (.*)")
    triage_line_re, triage_re_map = create_triage_master_regex()

    parsed_entries = []
    log_lines = log_text.strip().split("\n")
    for line_number, line in enumerate(log_lines):
        match = indentify_triage_re.search(line)
        if match:
            triage_id = match.group(1)
            prog_id = match.group(2)
            triage_log_line = match.group(3)
            entry = match_against_triage_log_line_types(
                triage_log_line, triage_line_re, triage_re_map, line_number, log_lines
            )

            entry["prog_id"] = (prog_id,)
            entry["triage_id"] = triage_id
            parsed_entries.append(entry)
    return parsed_entries


def match_against_triage_log_line_types(
    log_line: str,
    master_re: re.Pattern,
    type_to_idxs: dict[str, list[int]],
    line_number: int,
    og_text: list[str],
) -> dict[str, any]:
    """
    Uses master regex to identify the type of triage log line and capture relevant data from it.
    """

    m = master_re.match(log_line)
    if m is None:
        raise InvalidTriageLine

    matched_type = m.lastgroup
    idxs = type_to_idxs[matched_type]
    match_groups = [m[group_idx] for group_idx in idxs]
    res = {}
    match matched_type:
        # this is nasty. While the items of KEYS were used to identify the type of log line,
        # in the result dict they will be used to hold the value relevant to that log line type.
        case LOGENTRY_KEYS.NEW_SIGNAL:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.NEW_SIGNAL] = match_groups[1]
        case LOGENTRY_KEYS.NEW_FPOINTERS:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.NEW_FPOINTERS] = match_groups[1]
        case LOGENTRY_KEYS.STABLE_FPOINTERS:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.STABLE_FPOINTERS] = match_groups[1]
            res[RESULT_KEYS.NEW_STABLE_FPOINTERS] = match_groups[2]
        case LOGENTRY_KEYS.SAVED_ITEM:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.SAVED_PROG] = read_serializaed_prog(
                line_number + 1, og_text
            )
        case LOGENTRY_KEYS.MINIMIZATION_REPORT_NO_DIFF:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = {
                RESULT_KEYS.MINIMIZATION_RES_TYPE: RESULT_VALUES.MINIMIZATION_RES_NODIFF
            }
        case LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_FPOINTERS:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = {
                RESULT_KEYS.MINIMIZATION_RES_TYPE: RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER,
                RESULT_KEYS.MINIMIZATION_RES_PROG: read_serializaed_prog(
                    line_number + 1, og_text
                ),
            }
        case LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_SIGNAL:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = {
                RESULT_KEYS.MINIMIZATION_RES_TYPE: RESULT_VALUES.MINIMIZATION_RES_SAVE_SIGNAL,
                RESULT_KEYS.MINIMIZATION_RES_PROG: read_serializaed_prog(
                    line_number + 1, og_text
                ),
            }
        case LOGENTRY_KEYS.MINIMIZATION_SKIP:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = {
                RESULT_KEYS.MINIMIZATION_RES_TYPE: RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER,
                RESULT_KEYS.MINIMIZATION_RES_PROG: read_serializaed_prog(
                    line_number + 1, og_text
                ),
            }
    return res


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse a syzkaller log to extract function pointer store entries as JSON."
    )
    parser.add_argument(
        "log_path", type=str, nargs="?", help="Path to the syzkaller log file to parse."
    )
    parser.add_argument(
        "out_path", type=str, nargs="?", help="Path to the output json."
    )
    args = parser.parse_args()

    if not args.log_path or not args.out_path:
        parser.print_help()
        sys.exit(1)

    log_path = Path(args.log_path)
    out_path = Path(args.out_path)
    if not log_path.exists():
        print(
            f"Error: The specified log file does not exist: {log_path}", file=sys.stderr
        )
        sys.exit(1)

    contents = log_path.read_text()
    extracted_json = parse_raw_triage_logs(contents)

    with out_path.open("w") as f:
        f.write(json.dumps(extracted_json, indent=4))
    print(f"Info: Wrote json ({len(extracted_json)} entries)")
