#!/usr/bin/env python3
"""
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
"""

import re
import json
import argparse
from pathlib import Path
import sys


def parse_raw_triage_logs(log_text: str) -> list[dict]:
    # Regex breakdown:
    # \[(triage-[^\]]+)\] -> Captures the triage-id (e.g., triage-0x2c66bd608c80)
    # \[(prog-[^\]]+)\]   -> Captures the prog-id (e.g., prog-0x351ec85d0480)
    # (.*)               -> Captures the rest of the log entry
    # 
    # "DEPRECATED"
    # call #\d+ \[([^\]]+)\] -> Captures the call name (e.g., syz_genetlink)
    # :\s*(.*)               -> Captures whatever comes after the colon (the JSON array)
    pattern = re.compile(
        r"\[(triage-[^\]]+)\] \[(prog-[^\]]+)\] (.*)"
    )

    parsed_entries = []

    # Process line by line
    for line in log_text.strip().split("\n"):
        match = pattern.search(line)

        if match:
            triage_id = match.group(1)
            prog_id = match.group(2)
            log_line = match.group(3)
            
            # Append the structured data
            parsed_entries.append(
                {"prog_id": prog_id, "triage_id": triage_id, "log_info": log_line}
            )

    return parsed_entries

def match_against_types_of_log_line(entries: list[dict]) -> list[dict]:
    '''
    we want to identify the following types of log:
    '''

    patterns = {
        "new_fpointers": r"",
        "new_signal": r"",
        "stable_fpointers": r"" ,
        "stable_new_fpointers" : r"",
        "stable_signal" : r"",
        "stable_new_signal" : r"",
        "saved_item" : r"",
        "minimization_result_equal" : r"",
        "minimization_result_no_signal" : r"",
        "minimization_result_no_fpointer" : r"",
        "minimization_skip" : r"",
    }
    combined_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in patterns.items())
    compiled_re = re.compile(combined_regex)
    for match in compiled_re.finditer("SOMEWHERE"):
        # match.lastgroup tells you the NAME of the pattern that hit
        matched_type = match.lastgroup 
        matched_value = match.group()

    raise NotImplementedError


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
    extracted_raw = parse_raw_triage_logs(contents)
    by_types = match_against_types_of_log_line(extracted_raw)
   
    with out_path.open("w") as f:
        f.write(json.dumps(by_types, indent = 4))
    print(f"Info: Wrote json ({len(by_types)} entries)")
