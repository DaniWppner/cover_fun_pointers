#!/usr/bin/env python3
import os
import re
import sys
import hashlib

def extract_programs_from_log(log_path, out_dir):
    with open(log_path, 'r', errors='ignore') as f:
        content = f.read()
    
    # Find the "last executing test programs:" block
    marker = "last executing test programs:\n\n"
    end_marker = "kernel console output (not intermixed with test programs):"
    
    start_idx = content.find(marker)
    if start_idx == -1:
        return 0
    
    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        end_idx = len(content)
        
    block = content[start_idx + len(marker):end_idx]
    
    # Split by the pattern matching the program header
    # e.g., "3m16.984467729s ago: executing program 32 (id=46):\n"
    pattern = re.compile(r'\d+[ms].*? ago: executing program \d+ \(id=\d+\):\n')
    
    parts = pattern.split(block)
    
    # parts[0] is typically empty string before the first match
    programs = [p.strip() for p in parts if p.strip()]
    
    count = 0
    if programs:
        prog = programs[-1]
        # Generate a hash for the filename to deduplicate
        h = hashlib.sha256(prog.encode('utf-8')).hexdigest()[:16]
        out_file = os.path.join(out_dir, f"prog_{h}.txt")
        if not os.path.exists(out_file):
            with open(out_file, 'w') as outf:
                outf.write(prog + "\n")
            count += 1
            
    return count

def main():
    base_dir = "/mnt/ssd_data/newhome/dwappner/Desktop/cover_fun_pointers/build_syzkaller/syzkaller_patchset/coverage_patchset/log_raw_PCs/crashes"
    
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
        
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted_reproducers")
    os.makedirs(out_dir, exist_ok=True)
    
    total_extracted = 0
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.startswith("log"):
                log_path = os.path.join(root, file)
                count = extract_programs_from_log(log_path, out_dir)
                if count > 0:
                    print(f"Extracted {count} unique programs from {log_path}")
                    total_extracted += count
                    
    print(f"\nTotal newly extracted unique programs: {total_extracted}")
    print(f"Programs saved to: {out_dir}")

if __name__ == "__main__":
    main()
