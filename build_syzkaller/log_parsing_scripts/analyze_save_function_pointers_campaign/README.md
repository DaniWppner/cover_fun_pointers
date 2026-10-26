# analyze_save_function_pointers_campaign

Post-mortem analysis of a Syzkaller campaign where **function pointer coverage drives corpus saving** (a prog can be saved/minimized because of new stored function pointers, not only because of new PC signal).

Everything is derived from a single `syz-manager.log`. There is no live connection to the fuzzer, the VMs or the kernel, except for `addr2line` on a `vmlinux` (see [Caveats](#caveats)).

## Quick start

```bash
python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
./run_analysis_pipeline.py /path/to/syz-manager.log --vmlinux /path/to/linux/vmlinux --out-dir /path/to/analysis/run_0
```

`--out-dir` defaults to the **current directory**. Every step runs with `out_dir` as its working directory, so all outputs land there.

## Known issues

### `fpointer_origin` tag is not used by any analysis

Triage lines carrying the `[fpcov-orig]` prefix are tagged `fpointer_origin` in step 1 and merged into the entry's `tags` in step 3. The tag is kept in `unified_triage_logs.json`, but nothing reads it.

### `new_covered_functions` lines are dropped
Logs of newer patched Syzkaller versions contain `new_covered_functions: [{"name", "path", "line"}, ...]`. Step 1 discards it through its explicit `SKIP` list. This important data should be included in analysis. This is because the line carries **no call id**, unlike every other per-call entry, and attributing it to the correct `<prog, call>` is cumbersome.

### `candidate_triage` jobs are ignored
Commit `28a0e909a75bc2255460a4bdba5151efe5a7a2d1` introduced the logging of the initial candidate progs, Syzkaller's seeds and the loaded corpus, as a different kind of job for reporting purposes. The scripts are hardcooded to see Jobs logged as `[triage-0x...]`, which ignores these initial `[candidate_triage-0x...]` logs. There are about 150-160 of such jobs on a defconfig linux campaign, all started in a short window at the beginning.

## What the pipeline does

`run_analysis_pipeline.py` chains the scripts below. Each step is skipped only if it completed successfully before and nothing it depends on has changed (see [Caching](#caching)).

| # | Script | Input -> Output | What it does |
|---|--------|-----------------|--------------|
| 1 | `extract_logs_into_json.py` | `syz-manager.log` -> `raw_triage_lines.jsonl` | Regex-parses every `[triage-..] [prog-..]` log line into one JSON object per line. Also pulls the multi-line payloads that follow some entries (serialized progs, PC cover lists, per-exec duration JSON). |
| 2 | `separate_time_profile_entries.py` | `raw_triage_lines.jsonl` -> `triage_lines.jsonl` (+ `time_profile.txt` from stdout, `time_profile_plots/`, `time_profile_data.json`) | Splits job-level timing entries (durations, exec counts, in-flight progs) from the per-call triage entries. Timing entries become plots and stats; the rest is passed on. |
| 3 | `unify_triage_lines.py` | `triage_lines.jsonl` -> `unified_triage_logs.json` | Merges all lines of a triage into one entry per `<prog, call>` (the `prog2log` dictionary used everywhere downstream; see [KI-1](#ki-1-fpointer_origin-tag-is-not-used-by-any-analysis) for the `tags` field it carries but nobody reads), then resolves every PC / stored function pointer / store instruction address to source locations with `addr2line`. |
| 4 | (creates `results/`) | | Only creates the directory. It is a no-op step kept for numbering. |
| 5 | `process_triage_metrics.py` | `unified_triage_logs.json` -> `results/analysis.txt` (+ side files in `results/`) | The actual analysis (see below). |
| 6 | `plot_metrics_evolution.py` | `unified_triage_logs.json` + log -> `coverage_over_time/coverage_evolution.png` | Coverage (from manager status lines) against number of finished triages. |
| 7 | `plot_throughput_evolution.py` | log -> `exec_over_time/exec_total_evolution.png` (+ `exec_per_min_*`) | `exec total` and `exec/min` over time. |

### What `process_triage_metrics.py` reports

All of it is printed to `results/analysis.txt`; the lists of interesting progs and mappings are dumped as JSON/py files next to it.

* Basic stats: unique `<prog, call>` triaged, how many were triaged more than once, how many reached the corpus.
* Duplicates among saved progs (the same prog being saved repeatedly).
* Progs saved *because of* function pointers, i.e. saved when minimization kept the pointer-coverage result but not the syzkaller-signal one.
* Minimization breakdown: kept both, unique signal only, unique fpointer only, skipped fpointer/signal/whole.
* PC coverage vs. function pointers: which stored function pointers (and which store instructions) were ever *executed* (appear in the PC cover of some prog), compared by source location, not raw address.
* Timeline: for each function pointer, was it executed before, during or strictly after the prog that saved it.

Outputs for a finished run:

```
<out-dir>/
  raw_triage_lines.jsonl        step 1
  triage_lines.jsonl            step 2 (no time profile entries)
  time_profile.txt              step 2 stdout (campaign/job timing summary)
  time_profile_plots/           step 2
  unified_triage_logs.json      step 3
  results/analysis.txt          step 5 (+ json/py side files)
  coverage_over_time/           step 6
  exec_over_time/               step 7
  time_profile_data.json        step 2
```

## Caching

Each step records a completion stamp in `<out-dir>/.stamps/<script>.json` **only after it exits with code 0**. The stamp holds a fingerprint of:

* the step's script and `logentry_keys.py` (content hash);
* the size and mtime of each input file (not content, since logs can be multi-GB).

A step is skipped only if its stamp matches the current fingerprint and all its declared outputs exist. Before a step runs, its declared outputs and stamp are deleted, and its outputs are deleted again if it fails, so a crash never leaves something that looks finished. Invalidation cascades: rerunning a step changes its outputs' mtimes, which invalidates the steps that read them.

* `--force` reruns everything; `--from-step N` reruns step N and every later step.
* Runs produced before stamps existed have no stamps, so the first run rebuilds everything.
* Only declared output *files* are tracked. The side files in `results/` and `time_profile_plots/` are overwritten by a rerun, but stale files from an older script version are not removed.
* Copying a run directory without preserving mtimes just causes a rebuild.
* Script arguments are not part of the fingerprint (the pipeline passes only paths).

## Other scripts (not in the pipeline)

* `compare_groups.py`: plots the average coverage / throughput of one or two *groups* of runs (`--group1 <run_dir> ...`, `--group2 <run_dir> ...`, e.g. `--group1 <experiment>/analysis/run_*`). Each run directory is a pipeline `--out-dir` that must also hold the run's `syz-manager.log`. All runs of a group must span roughly the same time.
* `plot_metrics_evolution.py` and `plot_throughput_evolution.py` can also be called directly with two runs to overlay them (and `plot_throughput_evolution.py --cut-after hh:mm:ss`).
* `extract_logs_into_json.py --cutoff-time "YYYY/MM/DD HH:MM:SS"` truncates the log before the first status line after that time. The pipeline does not expose it.
* `logentry_keys.py`: the enums (`LOGENTRY_KEYS`, `RESULT_KEYS`, ...) shared by all scripts. Single source of truth for the intermediate JSON format.
* `example_usage/`: a `sample.log` and `FINDINGS.md` (duplicate triage analysis on a real run). `uncovered_functions_analysis/`: manual write-ups of stored function pointers that never got executed. `extracted_sample.json` and `no_output_debug/` are leftover debugging artifacts.

## Caveats
### Inputs and environment

* **The log must come from the patched Syzkaller** that prints the triage lines (`[triage-0x..] [prog-..]`, `|new stored function pointers|=`, `[fpcov-orig]`, job duration lines, ...).
* **`addr2line` runs against the `--vmlinux` you pass** (required by both `run_analysis_pipeline.py` and `unify_triage_lines.py`). That vmlinux must be the exact build the campaign ran, otherwise locations are silently wrong.
* `addr2line` must be on `PATH`. It is invoked once per address set (PCs, store instructions, stored values) with all addresses piped through stdin.
* **Memory:** the log, `raw_triage_lines.jsonl` and `unified_triage_logs.json` are loaded whole (`read_text`, `readlines`, `json.loads`). Multi-GB logs need a lot of RAM.
* Timestamps have 1 second resolution and come from two clocks/formats: the manager log (`2026/05/11 ...`) and the fuzzer's own triage timestamps (`2026-05-11 ...`). Cross-referencing them (step 6) assumes both machines are in sync.

### Pipeline behavior

* **Caching is stamp-based, see [Caching](#caching).** The `--vmlinux` file is tracked like any other input (size and mtime), so rebuilding or swapping it reruns step 3.
* Steps abort on the first failure (`sys.exit`) and many consistency checks are `assert`s / `sys.exit(1)` by design (fail fast). A crash in step 3 about an overwritten key or a job still awaiting a corpus entry means the log violates one of the assumptions below, not that the script is flaky.

### How entries are interpreted (things that bend the numbers)

* **Identity is `<prog_id, call>`.** Only the **first** triage of a given pair is kept; later triages of the same pair (different `triage_id`s) only increment `count` and extend the timestamp range. Repeated progs are therefore not counted as separate triages in the stats, and `TIMESTAMP_BEGIN/END` span all triages of the pair.
* **PC cover only exists for triaged progs that reached a successful minimization** (the `total cover for ...` entry is matched to the minimized prog through `awaiting_pc_cover`). "Executed" in the analysis therefore means "executed in one of those logged covers", not anywhere in the campaign. Take "never executed" with caution. (Not verified against the Syzkaller patch that emits this line; check the reproduction package if it matters.)
* Pointer vs. PC comparisons are done by **source location** (file:line + function, including inlined frames). The raw addresses of the stored value and of the covered PCs are different kinds of address, so they are never compared directly.
* `syz_mount_image$...` lines are replaced by `syz_mount_image$REDACTED` (the images are huge).
