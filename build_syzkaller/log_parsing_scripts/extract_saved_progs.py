#!/usr/bin/env python3
"""
This script allows parsing of a syzkaller log to generate a json with all
log entries where a syzkaller prog was added to the corpus. The output format will be:
[
    {
        "prog_id": str,
        "call": str,
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


def parse_fuzzer_log(log_text: str) -> list[dict]:
    # Regex breakdown:
    # \[(prog-[^\]]+)\]    -> Captures the prog-id (e.g., prog-0x351ec85d0480)
    # call (#\d+ \[[^\]]+\]) -> Captures the call info (e.g., #2 [syz_genetlink...])
    # :\s*(.*)               -> Captures whatever comes after the colon (the JSON array)
    pattern = re.compile(
        r"\[(prog-[^\]]+)\]: added new input for #\d+ \[([^\]]+)\] to the corpus with program:"
    )

    parsed_entries = []

    # Process line by line
    for line in log_text.strip().split("\n"):
        match = pattern.search(line)

        if match:
            prog_id = match.group(1)
            call_info = match.group(2)

            parsed_entries.append(
                {"prog_id": prog_id, "call": call_info}
            )

    return parsed_entries


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse a syzkaller log to extract corpus program additions."
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
    extracted_json = parse_fuzzer_log(contents)
    with out_path.open("w") as f:
        f.write(json.dumps(extracted_json, indent=4))
    print(f"Info: Wrote json ({len(extracted_json)} entries)")
