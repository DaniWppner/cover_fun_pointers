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

It takes the path to the syzkaller log as parameters and prints the JSON to stdout
"""

import re
import json
import argparse
from pathlib import Path
import sys


def parse_fuzzer_log(log_text: str) -> str:
    # Regex breakdown:
    # \[(prog-[^\]]+)\]    -> Captures the prog-id (e.g., prog-0x351ec85d0480)
    # call (#\d+ \[[^\]]+\]) -> Captures the call info (e.g., #2 [syz_genetlink...])
    # :\s*(.*)               -> Captures whatever comes after the colon (the JSON array)
    pattern = re.compile(
        r"\[(prog-[^\]]+)\] stored function pointers in call (#\d+ \[[^\]]+\]):\s*(.*)"
    )

    parsed_entries = []

    # Process line by line
    for line in log_text.strip().split("\n"):
        match = pattern.search(line)

        if match:
            prog_id = match.group(1)
            call_info = match.group(2)
            json_string = match.group(3).strip()

            # Default to an empty list if there's no JSON data on that line
            json_data = []
            if json_string:
                try:
                    json_data = json.loads(json_string)
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON for {prog_id} {call_info}")

            # Append the structured data
            parsed_entries.append(
                {"prog_id": prog_id, "call": call_info, "function_pointers": json_data}
            )

    return parsed_entries


def filter_populated_pointers(data: list[dict]):

    filtered_data = [entry for entry in data if len(entry["function_pointers"]) > 0]

    # Convert the filtered list back to a formatted JSON string
    return json.dumps(filtered_data, indent=4)


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
    extracted_json = parse_fuzzer_log(contents)
    filtered_json = filter_populated_pointers(extracted_json)
    with out_path.open("w") as f:
        f.write(filtered_json)
