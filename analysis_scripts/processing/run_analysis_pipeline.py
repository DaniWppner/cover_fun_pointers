#!/usr/bin/env python3

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

TOTAL_STEPS = 7
SCRIPTS_ROOT = Path(__file__).resolve().parent.parent
# Every pipeline script imports it, so a change to it invalidates all steps.
SHARED_MODULE = SCRIPTS_ROOT / "logentry_keys.py"


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


def make_fingerprint(script: Path, inputs: list[Path]) -> dict[str, object]:
    """
    Args:
        script: Path to the step's script.
        inputs: Files the step reads.

    Returns:
        dict[str, object]: Identity of everything the step's results depend on.
            sources_sha256: hash of the step's script plus the shared module
            inputs: size and mtime (ns) of each input file, keyed by file name
    """
    sources = hashlib.sha256()
    for source in (script, SHARED_MODULE):
        sources.update(source.read_bytes())
    # Inputs can be multi-GB logs, so they are identified by stat instead of by content.
    return {
        "sources_sha256": sources.hexdigest(),
        "inputs": {
            path.name: [path.stat().st_size, path.stat().st_mtime_ns] for path in inputs
        },
    }


def rerun_reason(
    stamp: Path, fingerprint: dict[str, object], outputs: list[Path], forced: bool
) -> str | None:
    """
    Args:
        stamp: Completion stamp written after the last successful run of the step.
        fingerprint: Current identity of the step's sources and inputs.
        outputs: Files the step is expected to produce.
        forced: Whether the user asked to rerun this step regardless.

    Returns:
        str | None: Why the step must run again, or None if its stamped results are up to date.
    """
    if forced:
        return "forced by --force / --from-step"
    if not stamp.exists():
        return "no completion stamp"
    if json.loads(stamp.read_text()) != fingerprint:
        return "sources or inputs changed since the last successful run"
    missing = [output.name for output in outputs if not output.exists()]
    if missing:
        return f"missing outputs: {', '.join(missing)}"
    return None


def main():
    parser = argparse.ArgumentParser(description="Run the full triage and metrics pipeline.")
    parser.add_argument("log_file", type=str, help="Path to the syz-manager.log file")
    parser.add_argument("--vmlinux", type=str, required=True, help="vmlinux of the exact kernel build the campaign ran, used by addr2line in step 3")
    parser.add_argument("--out-dir", type=str, default=".", help="Output directory for intermediate files (default: current directory)")
    forcing = parser.add_mutually_exclusive_group()
    forcing.add_argument("--force", action="store_true", help="Rerun every step even if it is up to date")
    forcing.add_argument("--from-step", type=int, default=TOTAL_STEPS + 1, metavar="N", help="Rerun step N and every later step even if they are up to date")
    args = parser.parse_args()
    force_from = 1 if args.force else args.from_step

    log_path = Path(args.log_file).resolve()
    if not log_path.is_file():
        print(f"Error: Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    vmlinux_path = Path(args.vmlinux).resolve()
    if not vmlinux_path.is_file():
        print(f"Error: vmlinux not found: {vmlinux_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    results_dir = out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    stamps_dir = out_dir / ".stamps"
    stamps_dir.mkdir(parents=True, exist_ok=True)

    raw_jsonl = out_dir / "raw_triage_lines.jsonl"
    triage_jsonl = out_dir / "triage_lines.jsonl"
    time_profile_txt = out_dir / "time_profile.txt"
    time_profile_data = out_dir / "time_profile_data.json"
    unified_json = out_dir / "unified_triage_logs.json"
    analysis_txt = results_dir / "analysis.txt"
    cov_plot = out_dir / "coverage_over_time" / "coverage_evolution.png"
    exec_plot = out_dir / "exec_over_time" / "exec_total_evolution.png"

    def run_step(
        step: int,
        script_name: str,
        inputs: list[Path],
        outputs: list[Path],
        cmd_args: list[Path],
        cwd: Path,
        stdout_file: Path | None = None,
    ) -> None:
        """
        Args:
            step: Step number, used for display and for --from-step.
            script_name: Script of this step, relative to the directory holding processing/ and plotting/.
            inputs: Files the step reads, used to detect stale results.
            outputs: Files the step must produce. They are deleted before running and again on failure.
            cmd_args: Positional arguments passed to the script.
            cwd: Working directory of the script.
            stdout_file: File receiving the script's stdout, if it is one of the step's outputs.

        Returns:
            None
        """
        print_step(step, TOTAL_STEPS, script_name)
        script = SCRIPTS_ROOT / script_name
        fingerprint = make_fingerprint(script, inputs)
        stamp = stamps_dir / f"{script.stem}.json"
        reason = rerun_reason(stamp, fingerprint, outputs, forced=step >= force_from)
        if reason is None:
            print("Skipping: results are up to date.", flush=True)
            return

        print(f"Running: {reason}.", flush=True)
        stamp.unlink(missing_ok=True)
        for output in outputs:
            output.unlink(missing_ok=True)
        try:
            run_cmd(
                [sys.executable, str(script), *map(str, cmd_args)],
                stdout_file=stdout_file,
                cwd=cwd,
            )
        except SystemExit:
            for output in outputs:
                output.unlink(missing_ok=True)
            raise
        stamp.write_text(json.dumps(fingerprint))

    run_step(1, "processing/extract_logs_into_json.py",
             inputs=[log_path],
             outputs=[raw_jsonl],
             cmd_args=[log_path, raw_jsonl],
             cwd=out_dir)

    run_step(2, "processing/separate_time_profile_entries.py",
             inputs=[raw_jsonl],
             outputs=[triage_jsonl, time_profile_txt, time_profile_data],
             cmd_args=[raw_jsonl, triage_jsonl],
             cwd=out_dir,
             stdout_file=time_profile_txt)

    run_step(3, "processing/unify_triage_lines.py",
             inputs=[triage_jsonl, vmlinux_path],
             outputs=[unified_json],
             cmd_args=[triage_jsonl, unified_json, "--vmlinux", vmlinux_path],
             cwd=out_dir)

    print_step(4, TOTAL_STEPS, "Creating results directory")
    print(f"Directory already ensured at: {results_dir}", flush=True)

    run_step(5, "processing/process_triage_metrics.py",
             inputs=[unified_json],
             outputs=[analysis_txt],
             cmd_args=[unified_json],
             cwd=results_dir,
             stdout_file=analysis_txt)

    run_step(6, "plotting/plot_metrics_evolution.py",
             inputs=[unified_json, log_path],
             outputs=[cov_plot],
             cmd_args=[unified_json, log_path],
             cwd=out_dir)

    run_step(7, "plotting/plot_throughput_evolution.py",
             inputs=[log_path],
             outputs=[exec_plot],
             cmd_args=[log_path],
             cwd=out_dir)

    print(f"\n" + "="*50)
    print("Pipeline completed successfully!")
    print(f"Results are available in: {results_dir}")
    print("="*50)

if __name__ == "__main__":
    main()
