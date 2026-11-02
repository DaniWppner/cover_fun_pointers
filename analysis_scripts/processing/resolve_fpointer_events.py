#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any

from logentry_keys import RESULT_KEYS
from processing import unify_triage_lines


def     events_per_prog(events_jsonl: Path) -> dict[str, dict[str, Any]]:
    """
    Args:
        events_jsonl: stored function pointers events written by extract_logs_into_json.py (raw_fpointer_events.jsonl).

    Returns:
        dict[str, dict[str, Any]]: For each prog|call pair, keyed like the triage entries of unified_triage_logs.json,
            its event: NEW_FPOINTERS_PAYLOAD (still a json string) and TIMESTAMP_BEGIN = TIMESTAMP_END, the instant
            the event was logged. The keys of the triage entries let the functions of process_triage_metrics.py
            read it like a prog2log.
    """
    prog2event: dict[str, dict[str, Any]] = {}
    with events_jsonl.open() as f:
        for line in f:
            event = json.loads(line)
            key = f"{event[RESULT_KEYS.PROGID]}|{event[RESULT_KEYS.CALL_NAME]}"
            entry = {
                RESULT_KEYS.NEW_FPOINTERS_PAYLOAD: event[RESULT_KEYS.NEW_FPOINTERS_PAYLOAD],
                RESULT_KEYS.TIMESTAMP_BEGIN: event[RESULT_KEYS.TIMESTAMP],
                RESULT_KEYS.TIMESTAMP_END: event[RESULT_KEYS.TIMESTAMP],
            }
            unify_triage_lines.cleanup_particular_fpointer(entry, RESULT_KEYS.NEW_FPOINTERS_PAYLOAD)
            if key not in prog2event:
                entry[RESULT_KEYS.COUNT] = 1
            else:
                entry[RESULT_KEYS.COUNT] = prog2event[key][RESULT_KEYS.COUNT] + 1
                # Get the union for NEW_FPOINTERS_PAYLOAD.
                # Since Syzkaller base identifies jobs by Go pointers (%p), this is gonna trigger often.
                # FIXME: This is a bug; but since we're not mapping these entries to triages, it seems fine for now.
                stored_fpointers_payload = entry.pop(RESULT_KEYS.NEW_FPOINTERS_PAYLOAD)
                old_payload = prog2event[key][RESULT_KEYS.NEW_FPOINTERS_PAYLOAD]
                # NEW_FPOINTER_PAYLOADS are supposed to be lists of dictionaries where 
                # each dictionary is a PC-FPOINTER pair.
                # Merging payloads means concatenating the lists.
                entry[RESULT_KEYS.NEW_FPOINTERS_PAYLOAD] = old_payload + stored_fpointers_payload 
            prog2event[key] = entry
    return prog2event


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve the source locations of the stored function pointers events logged outside of triage jobs."
    )
    parser.add_argument(
        "events_jsonl",
        type=Path,
        help="raw_fpointer_events.jsonl, written by extract_logs_into_json.py next to its output json",
    )
    parser.add_argument("out_path", type=Path, help="Path to the output json.")
    parser.add_argument(
        "--vmlinux",
        type=Path,
        required=True,
        help="vmlinux of the exact kernel build the campaign ran, used by addr2line.",
    )
    args = parser.parse_args()

    prog2event = events_per_prog(args.events_jsonl)
    prog2event = unify_triage_lines.update_w_address_data(prog2event, args.vmlinux.resolve())

    with args.out_path.open("w") as f:
        f.write(json.dumps(prog2event, indent=2) + "\n")


if __name__ == "__main__":
    main()
