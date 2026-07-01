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
import sys
import itertools
from datetime import datetime
import tqdm.contrib as tcontrib
from typing import Iterable
from pathlib import Path
from termcolor import colored
from logentry_keys import LOGENTRY_KEYS, RESULT_KEYS, MINIMIZATION_RESULT_VALUES, TAG_RESULT_VALUES

class InvalidTriageLine(Exception):
    pass


class TriageSkipLine(Exception):
    pass

TIMESTAMP_RE = r"^(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
TIMESTAMP_TRIAGE_RE = r"^(?P<tstriage>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"

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
    # itertools.islice takes no keyword arguments but this is like:
    #    itertools.islice(Iterable=og_text, start=line_number, stop=None, step=None)
    interesting_lines : Iterable[str] = itertools.islice(og_text, line_number, None, None)
    res = []
    for line in interesting_lines:
        if line == '':
            break
        elif line.startswith("syz_mount_image$"):
            res.append("syz_mount_image$REDACTED")
        elif "(BADINDEX)[prog-" in line:
            # this is a hacky hack that works around syzkaller bugging out
            # during program serialization and outputing weird strings that
            # eat into the beginning of the next triage log.
            res.append(line.split("[prog-")[0])
            break
        else:
            res.append(line)
    return res


def parse_timestamp_from_line(line: str) -> datetime | None:
    match = re.compile(TIMESTAMP_RE).match(line)
    if match is None:
        return None
    return datetime.strptime(match.group("ts"), "%Y/%m/%d %H:%M:%S")

def parse_timestamp_from_triage_line(line: str) -> datetime | None:
    match = re.compile(TIMESTAMP_TRIAGE_RE).match(line)
    if match is None:
        return None
    return datetime.strptime(match.group("tstriage"), "%Y-%m-%d %H:%M:%S")


def find_next_timestamp_on_or_after(lines: list[str], start_index: int) -> tuple[int, datetime] | tuple[None, None]:
    """
    Return the index and timestamp of the first line after `start_index` that has a timestamp.
    """
    for index in range(start_index, len(lines)):
        line_time = parse_timestamp_from_line(lines[index])
        if line_time is not None:
            return index, line_time
    return None, None


def find_first_line_after_timestamp(lines: list[str], cutoff: datetime) -> int:
    """
    Return the index of the first line with a timestamp later than cutoff.
    Uses binary search.
    """
    low = 0
    high = len(lines)
    while low < high:
        mid = (low + high) // 2
        mid_time = parse_timestamp_from_line(lines[mid])
        if mid_time is None:
            next_idx, next_time = find_next_timestamp_on_or_after(lines, mid)
            if next_idx is None:
                high = mid
            elif next_time <= cutoff:
                low = next_idx + 1
            else:
                high = next_idx
            continue

        if mid_time <= cutoff:
            low = mid + 1
        else:
            high = mid

    while low < len(lines):
        line_time = parse_timestamp_from_line(lines[low])
        if line_time is not None:
            if line_time > cutoff:
                return low
            low += 1
        else:
            low += 1
    # fallback: return the last line if we got to the end of the list
    return len(lines)


def find_cutoff_before_status_block(lines: list[str], cutoff: datetime) -> int:
    """
    Return the index of the first line that has the format

        2026/05/11 21:50:37 candidates=0 corpus=287 coverage=14363 exec total=17289 (80/min) pending=0 reproducing=0 

    and has a timestamp later than `cutoff`
    """
    stats_line_re = re.compile(TIMESTAMP_RE +
                               r" candidates=\d+ corpus=\d+ coverage=\d+ exec total=\d+ \(.*\) pending=\d+ reproducing=\d+")

    cutoff_idx = find_first_line_after_timestamp(lines, cutoff)
    for idx in range(cutoff_idx, len(lines)):
        if stats_line_re.match(lines[idx]):
            return idx
    # fallback: return the last line if we got to the end of the list
    return len(lines)


def read_serialized_cover(line_number: int, og_text: list[str]) -> list[str]:
    cover_line = og_text[line_number].strip()
    assert cover_line.startswith("(") and cover_line.endswith(")")
    cover_line = cover_line[1:-1]
    return [x.strip() for x in cover_line.split(",")]

def read_exec_durations(line: str) -> list[dict]:
    return json.loads(line)

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
    call_id = r"(#-?\d+ \[[^\]]+\])"
    call_pattern = "call " + call_id

    # Some entries include information from the couple log lines following the entry itself.
    # Those are the ones where the pattern ends in something like "with program:"
    patterns = {
        LOGENTRY_KEYS.NEW_SIGNAL: call_pattern + r": \|new signal\|=(\d+)",
        LOGENTRY_KEYS.NEW_FPOINTERS: call_pattern
        + r": \|new stored function pointers\|=(\d+)(\[.*\])?",
        LOGENTRY_KEYS.STABLE_SIGNAL: call_pattern
        + r": \|stable signal\|=(\d+)"
        + r", \|new stable signal\|=(\d+)",
        LOGENTRY_KEYS.STABLE_FPOINTERS: call_pattern
        + r": \|stable stored function pointers\|=(\d+)"
        + r", \|new stable stored function pointers\|=(\d+)(\[.*\])?",
        # Need to retrieve prog after this entry
        LOGENTRY_KEYS.SAVED_ITEM: r"added new input for "
        + call_id
        + r" to the corpus with program:",
        LOGENTRY_KEYS.MINIMIZATION_REPORT_NO_DIFF: call_pattern
        + r": minimization yielded same prog for signal and stored function pointers",
        # Need to retrieve prog after this entry
        LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_FPOINTERS: call_pattern
        + r": minimization yielded prog for stored function pointers different from signal. New prog \(call #-?\d+\):",
        # Need to retrieve prog after this entry
        LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_SIGNAL: call_pattern
        + r": minimization yielded prog for signal different from stored function pointers. New prog \(call #-?\d+\):",
        LOGENTRY_KEYS.MINIMIZATION_SPLIT: call_pattern
        + r": minimization step splitted$",
        # The end-of-line anchor '$' here is crucial to be able to distinguish between these three entries
        LOGENTRY_KEYS.MINIMIZATION_WHOLE_SKIP: call_pattern + r": skip minimize$",
        LOGENTRY_KEYS.MINIMIZATION_SIGNAL_SKIP: call_pattern + r": skip minimize of empty new stable signal$",
        LOGENTRY_KEYS.MINIMIZATION_FPOINTER_SKIP: call_pattern + r": skip minimize of empty new stable stored function pointers$",
        LOGENTRY_KEYS.PC_COVER: r"total cover for " + call_pattern + r":",
        # This syzkaller log was actually formatted wrong in some versions, since it's trying to output a float as an integer.
        # But we can still match it. We have to account for the %!(float64=) wrapper.
        LOGENTRY_KEYS.TOTAL_JOB_DURATION: r"total job duration: (?:\%\!d\(float64=)?(\d+\.\d+)\)? seconds$",
        # This other syzkaller log outputs nanoseconds instead of seconds in some versions.
        # We need to match both floating point numbers and integers but also remember to convert between units later.
        LOGENTRY_KEYS.PROG_EXECUTIONS_JOB_DURATION: r"test executions(?: \(total\))? job duration: ((?:\d+)|(?:\d+\.\d+)) seconds$",
        LOGENTRY_KEYS.FPOINTER_PROG_EXECUTIONS_JOB_DURATION: r"test executions \(function pointer coverage\) job duration: (\d+\.\d+) seconds$",
        LOGENTRY_KEYS.TOTAL_PROG_EXECUTIONS: r"(\d+) total test case executions$",
        LOGENTRY_KEYS.FPOINTER_PROG_EXECUTIONS: r"(\d+) new test case executions because of function pointer coverage$",
        # Need to parse the json contained at the end of this entry
        LOGENTRY_KEYS.PROG_EXECUTIONS_ALL_INDIVIDUAL_DURATIONS: r"test executions \(total\) individual durations: (.*)$",
        # Need to parse the json contained at the end of this entry
        LOGENTRY_KEYS.PROG_EXECUTIONS_FPOINTER_INDIVIDUAL_DURATIONS: r"test executions \(function pointer coverage\) individual durations: (.*)$",
        "SKIP": "|".join(
            [
                call_pattern + r": minimize started",
                r"deflake started",
                r"deflake complete",
                call_pattern + r":? minimization step failure",
                call_pattern + r":? minimization step (?:\(.*\) )?success \(\|calls\| = \d+\)",
            ]
        ),
    }
    return __create_master_regex(patterns)


def parse_raw_triage_logs(log_lines: list[str]) -> Iterable[dict]:
    # Regex breakdown:
    # \[(triage-[^\]]+)\] -> Captures the triage-id (e.g., triage-0x2c66bd608c80)
    # \[(prog-[^\]]+)\]   -> Captures the prog-id (e.g., prog-0x351ec85d0480)
    # (.*)                -> Captures the rest of the log entry

    indentify_triage_re = re.compile(r"\[(triage-[^\]]+)\] \[(prog-[^\]]+)\]: (.*)")
    triage_line_re, triage_re_map = create_triage_master_regex()

    for line_number, line in tcontrib.tenumerate(log_lines):
        match = indentify_triage_re.search(line)
        if match:
            fpcov_orig = False
            triage_id = match.group(1)
            prog_id = match.group(2)
            triage_log_line = match.group(3)
            # hackily remove the [fpcov-orig] tag from the begginning of the triage line if it's there
            if triage_log_line.startswith("[fpcov-orig] "):
                fpcov_orig = True
                triage_log_line = triage_log_line[len("[fpcov-orig] "):]
            if triage_log_line == "":
                # this is a hardcoded special case where the serialized prog
                # is logged at the beginning of the triage job
                entry = {
                    RESULT_KEYS.ORIGINAL_PROG: read_serializaed_prog(
                        line_number + 1, log_lines
                    )
                }
            else:
                try:
                    entry = match_against_triage_log_line_types(
                        triage_log_line,
                        triage_line_re,
                        triage_re_map,
                        line_number,
                        log_lines,
                    )
                except TriageSkipLine:
                    continue
                except InvalidTriageLine:
                    print(
                        colored(
                            f"Invalid triage snippet in log (line {line_number}):\n{line}\n"
                            + f"Triage snippet (len {len(triage_log_line)}):\n{triage_log_line}",
                            "red",
                        )
                    )
                    raise
            entry[RESULT_KEYS.TIMESTAMP] = str(parse_timestamp_from_triage_line(line))
            entry[RESULT_KEYS.PROGID] = prog_id
            entry[RESULT_KEYS.TRIAGEID] = triage_id
            if fpcov_orig:
                entry[RESULT_KEYS.TAGS] = [TAG_RESULT_VALUES.FPOINTER_ORIGIN]
            yield entry


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
            # The fpointers payload is optional, it only occurs when the count is > 0
            if match_groups[2] is not None:
                res[RESULT_KEYS.NEW_FPOINTERS_PAYLOAD] = match_groups[2]
        case LOGENTRY_KEYS.STABLE_SIGNAL:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.STABLE_SIGNAL] = match_groups[1]
            res[RESULT_KEYS.NEW_STABLE_SIGNAL] = match_groups[2]
        case LOGENTRY_KEYS.STABLE_FPOINTERS:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.STABLE_FPOINTERS] = match_groups[1]
            res[RESULT_KEYS.NEW_STABLE_FPOINTERS] = match_groups[2]
            # The new stable fpointers payload is optional, it only occurs when the count is > 0
            if match_groups[3] is not None:
                res[RESULT_KEYS.NEW_STABLE_FPOINTERS_PAYLOAD] = match_groups[3]
        case LOGENTRY_KEYS.SAVED_ITEM:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.SAVED_PROG] = read_serializaed_prog(
                line_number + 1, og_text
            )
        case LOGENTRY_KEYS.MINIMIZATION_REPORT_NO_DIFF:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = [{
                RESULT_KEYS.MINIMIZATION_RES_TYPE: MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_NODIFF
            }]
        case LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_FPOINTERS:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = [{
                RESULT_KEYS.MINIMIZATION_RES_TYPE: MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_FPOINTER,
                RESULT_KEYS.MINIMIZATION_RES_PROG: read_serializaed_prog(
                    line_number + 1, og_text
                ),
            }]
        case LOGENTRY_KEYS.MINIMIZATION_REPORT_SAVE_SIGNAL:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = [{
                RESULT_KEYS.MINIMIZATION_RES_TYPE: MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SAVE_SIGNAL,
                RESULT_KEYS.MINIMIZATION_RES_PROG: read_serializaed_prog(
                    line_number + 1, og_text
                ),
            }]
        case LOGENTRY_KEYS.MINIMIZATION_SPLIT:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = [{
                RESULT_KEYS.MINIMIZATION_RES_TYPE: MINIMIZATION_RESULT_VALUES.MINIMIZATION_SPLIT,
            }]
        case LOGENTRY_KEYS.MINIMIZATION_WHOLE_SKIP:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = [{
                RESULT_KEYS.MINIMIZATION_RES_TYPE: MINIMIZATION_RESULT_VALUES.MINIMIZATION_SKIP,
            }]
        case LOGENTRY_KEYS.MINIMIZATION_FPOINTER_SKIP:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = [{
                RESULT_KEYS.MINIMIZATION_RES_TYPE: MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_FPOINTER_SKIP,
            }]
        case LOGENTRY_KEYS.MINIMIZATION_SIGNAL_SKIP:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.MINIMIZATION_RESULT] = [{
                RESULT_KEYS.MINIMIZATION_RES_TYPE: MINIMIZATION_RESULT_VALUES.MINIMIZATION_RES_SIGNAL_SKIP,
            }]
        case LOGENTRY_KEYS.PC_COVER:
            res[RESULT_KEYS.CALL_NAME] = match_groups[0]
            res[RESULT_KEYS.PC_COVER] = read_serialized_cover(line_number + 1, og_text)
        case LOGENTRY_KEYS.TOTAL_JOB_DURATION:
            res[RESULT_KEYS.TOTAL_JOB_DURATION] = float(match_groups[0])
        case LOGENTRY_KEYS.PROG_EXECUTIONS_JOB_DURATION:
            try:
                # try to convert from nanoseconds to seconds if it's an integer
                j_duration = int(match_groups[0]) * 1e-9
            except ValueError:
                # assume seconds if its a float
                j_duration = float(match_groups[0])
            res[RESULT_KEYS.PROG_EXECUTIONS_JOB_DURATION] = j_duration
        case LOGENTRY_KEYS.FPOINTER_PROG_EXECUTIONS_JOB_DURATION:
            res[RESULT_KEYS.FPOINTER_PROG_EXECUTIONS_JOB_DURATION] = float(match_groups[0])            
        case LOGENTRY_KEYS.TOTAL_PROG_EXECUTIONS:
            res[RESULT_KEYS.TOTAL_PROG_EXECUTIONS] = int(match_groups[0])
        case LOGENTRY_KEYS.FPOINTER_PROG_EXECUTIONS:
            res[RESULT_KEYS.FPOINTER_PROG_EXECUTIONS] = int(match_groups[0])
        case LOGENTRY_KEYS.PROG_EXECUTIONS_ALL_INDIVIDUAL_DURATIONS:
                res[RESULT_KEYS.PROG_EXECUTIONS_ALL_INDIVIDUAL_DURATIONS] = read_exec_durations(match_groups[0])
        case LOGENTRY_KEYS.PROG_EXECUTIONS_FPOINTER_INDIVIDUAL_DURATIONS:
                res[RESULT_KEYS.PROG_EXECUTIONS_FPOINTER_INDIVIDUAL_DURATIONS] = read_exec_durations(match_groups[0])                
        case "SKIP":
            raise TriageSkipLine
    if res == {}:
        raise InvalidTriageLine("Empty result even though line matches known pattern")
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
    parser.add_argument(
        "--cutoff-time",
        dest="cutoff_time",
        nargs="+",
        type=str,
        default=None,
        help=(
            "Cut off parsing before the first complete status block after this timestamp. "
            "Expected format: YYYY/MM/DD HH:MM:SS. "
            "If the timestamp is unquoted, it may be passed as two tokens."
        ),
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

    lines = log_path.read_text().strip().split("\n")
    if args.cutoff_time is not None:
        cutoff_time_raw = (
            " ".join(args.cutoff_time)
            if isinstance(args.cutoff_time, list)
            else args.cutoff_time
        )
        try:
            cutoff = datetime.strptime(cutoff_time_raw, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            print(
                "Error: --cutoff-time must use format YYYY/MM/DD HH:MM:SS.",
                file=sys.stderr,
            )
            sys.exit(1)
        cutoff_index = find_cutoff_before_status_block(lines, cutoff)
        lines = lines[:cutoff_index]

    out_str = '\n'.join(
        json.dumps(json_obj, indent=None)
        for json_obj in parse_raw_triage_logs(lines)
    )

    with out_path.open("w") as f:
        f.write(out_str)
