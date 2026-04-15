import json

INPUT_FILE = "naked_pointers.json"
OUTPUT_FILE = "filtered.json"

with open(INPUT_FILE, "r") as f:
    data = json.load(f)

filtered = [
    obj for obj in data
    if len(obj["InstrumentedStores"]) > 0 and len(obj["functionPointerParameters"]) > 0
]

with open(OUTPUT_FILE, "w") as f:
    json.dump(filtered, f, indent=2)

print(f"Functions with both instrumented stores and function pointer parameters: {len(filtered)}")
print(f"Output written to {OUTPUT_FILE}")