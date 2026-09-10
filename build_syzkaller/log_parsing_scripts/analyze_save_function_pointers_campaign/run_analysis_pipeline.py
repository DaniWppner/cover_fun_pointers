#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
from pathlib import Path

def print_step(step, total, description):
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    print(f"\n{MAGENTA}" + "="*50 + f"{RESET}")
    print(f"{MAGENTA}[{step}/{total}]{RESET} {BOLD}{description}...{RESET}")
    print(f"{MAGENTA}" + "="*50 + f"{RESET}", flush=True)

def run_cmd(cmd, stdout_file=None, cwd=None):
    if stdout_file:
        with open(stdout_file, "w") as f:
            result = subprocess.run(cmd, stdout=f, cwd=cwd)
    else:
        result = subprocess.run(cmd, cwd=cwd)
    
    if result.returncode != 0:
        print(f"Error: Command failed with return code {result.returncode}", file=sys.stderr)
        print(f"Command: {' '.join(str(c) for c in cmd)}", file=sys.stderr)
        sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser(description="Run the full triage and metrics pipeline.")
    parser.add_argument("log_file", type=str, help="Path to the syz-manager.log file")
    parser.add_argument("--out-dir", type=str, default=".", help="Output directory for intermediate files (default: current directory)")
    args = parser.parse_args()

    log_path = Path(args.log_file).resolve()
    if not log_path.is_file():
        print(f"Error: Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    results_dir = out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Get the directory of this script, to find the subscripts
    script_dir = Path(__file__).resolve().parent

    raw_jsonl = out_dir / "raw_triage_lines.jsonl"
    triage_jsonl = out_dir / "triage_lines.jsonl"
    time_profile_txt = out_dir / "time_profile.txt"
    unified_json = out_dir / "unified_triage_logs.json"
    analysis_txt = results_dir / "analysis.txt"

    total_steps = 7

    # Step 1
    print_step(1, total_steps, "extract_logs_into_json.py")
    if raw_jsonl.exists() and raw_jsonl.stat().st_size > 0:
        print(f"Skipping: Output file {raw_jsonl.name} already exists.", flush=True)
    else:
        run_cmd([
            sys.executable,
            str(script_dir / "extract_logs_into_json.py"),
            str(log_path),
            str(raw_jsonl)
        ])

    # Step 2
    print_step(2, total_steps, "separate_time_profile_entries.py")
    if triage_jsonl.exists() and triage_jsonl.stat().st_size > 0:
        print(f"Skipping: Output file {triage_jsonl.name} already exists.", flush=True)
    else:
        run_cmd([
            sys.executable,
            str(script_dir / "separate_time_profile_entries.py"),
            str(raw_jsonl),
            str(triage_jsonl)
        ], stdout_file=time_profile_txt)

    # Step 3
    print_step(3, total_steps, "unify_triage_lines.py")
    if unified_json.exists() and unified_json.stat().st_size > 0:
        print(f"Skipping: Output file {unified_json.name} already exists.", flush=True)
    else:
        run_cmd([
            sys.executable,
            str(script_dir / "unify_triage_lines.py"),
            str(triage_jsonl),
            str(unified_json)
        ])

    # Step 4
    print_step(4, total_steps, "Creating results directory")
    print(f"Directory already ensured at: {results_dir}", flush=True)

    # Step 5
    print_step(5, total_steps, "process_triage_metrics.py")
    if analysis_txt.exists() and analysis_txt.stat().st_size > 0:
        print(f"Skipping: Output file {analysis_txt.name} already exists.", flush=True)
    else:
        run_cmd([
            sys.executable,
            str(script_dir / "process_triage_metrics.py"),
            str(unified_json)
        ], stdout_file=analysis_txt, cwd=results_dir)

    # Step 6
    print_step(6, total_steps, "plot_metrics_evolution.py")
    cov_plot = out_dir / "coverage_over_time" / "coverage_evolution.png"
    if cov_plot.exists() and cov_plot.stat().st_size > 0:
        print(f"Skipping: Output file {cov_plot.name} already exists.", flush=True)
    else:
        run_cmd([
            sys.executable,
            str(script_dir / "plot_metrics_evolution.py"),
            str(unified_json),
            str(log_path)
        ], cwd=out_dir)

    # Step 7
    print_step(7, total_steps, "plot_throughput_evolution.py")
    exec_plot = out_dir / "exec_over_time" / "exec_total_evolution.png"
    if exec_plot.exists() and exec_plot.stat().st_size > 0:
        print(f"Skipping: Output file {exec_plot.name} already exists.", flush=True)
    else:
        run_cmd([
            sys.executable,
            str(script_dir / "plot_throughput_evolution.py"),
            str(log_path)
        ], cwd=out_dir)

    print(f"\n" + "="*50)
    print("Pipeline completed successfully!")
    print(f"Results are available in: {results_dir}")
    print("="*50)

if __name__ == "__main__":
    main()
