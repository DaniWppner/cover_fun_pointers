#!/usr/bin/python3
import json

INPUT_FILE = "shallow_fpointers.json"
OUTPUT_FILE = "shallow_filtered.json"

with open(INPUT_FILE, "r") as f:
    data = json.load(f)

filtered = [
    obj for obj in data
    if len(obj["InstrumentedStores"]) > 0 and len(obj["functionPointerParameters"]) > 0
]

with open(OUTPUT_FILE, "w") as f:
    json.dump(filtered, f, indent=2)

print(f"Functions with both instrumented stores and function pointer parameters from {INPUT_FILE}: {len(filtered)}")
print(f"Output written to {OUTPUT_FILE}")