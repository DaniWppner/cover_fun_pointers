#!/usr/bin/env python3
"""Compare two Python literal files containing dicts of tuple->set(tuple).

Usage:
    python compare_pairs.py file1.py file2.py

This prints:
    - number of top-level keys unique to file1
    - number of top-level keys unique to file2
    - number of full records unique to each file

The files are parsed with ast.literal_eval for safety.
"""

import argparse
import ast
import sys


def load_mapping(path):
    text = open(path, "r", encoding="utf-8").read()
    try:
        data = ast.literal_eval(text)
    except Exception as exc:
        raise ValueError(f"Could not parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected a dict in {path}, got {type(data).__name__}")
    return data


def normalize_record(key, value):
    if not isinstance(value, (set, frozenset, list, tuple)):
        raise ValueError(f"Value for key {key!r} is not a set-like object")
    normalized_value = frozenset(value)
    return (key, normalized_value)


def main():
    parser = argparse.ArgumentParser(description="Compare two pair-mapping files.")
    parser.add_argument("file1", help="First file path")
    parser.add_argument("file2", help="Second file path")
    parser.add_argument("--show-unique", action="store_true", help="Print the unique entries for each file")
    args = parser.parse_args()

    dict1 = load_mapping(args.file1)
    dict2 = load_mapping(args.file2)

    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())
    unique_keys_1 = keys1 - keys2
    unique_keys_2 = keys2 - keys1

    records1 = {normalize_record(k, dict1[k]) for k in keys1}
    records2 = {normalize_record(k, dict2[k]) for k in keys2}
    unique_records_1 = records1 - records2
    unique_records_2 = records2 - records1

    print(f"{args.file1}: {len(keys1)} top-level entries")
    print(f"{args.file2}: {len(keys2)} top-level entries")
    print()
    print(f"Entries in {args.file1} but not in {args.file2}: {len(unique_keys_1)}")
    print(f"Entries in {args.file2} but not in {args.file1}: {len(unique_keys_2)}")
    print()
    print(f"Full record differences (key+value) in {args.file1} but not in {args.file2}: {len(unique_records_1)}")
    print(f"Full record differences (key+value) in {args.file2} but not in {args.file1}: {len(unique_records_2)}")

    if args.show_unique:
        if unique_keys_1:
            print(f"\nUnique keys in {args.file1}:")
            for item in sorted(unique_keys_1):
                print(item)
        if unique_keys_2:
            print(f"\nUnique keys in {args.file2}:")
            for item in sorted(unique_keys_2):
                print(item)
        if unique_records_1:
            print(f"\nUnique full records in {args.file1}:")
            for key, value in sorted(unique_records_1):
                print(f"{key}: {sorted(value)}")
        if unique_records_2:
            print(f"\nUnique full records in {args.file2}:")
            for key, value in sorted(unique_records_2):
                print(f"{key}: {sorted(value)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
