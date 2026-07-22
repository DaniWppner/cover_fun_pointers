# AGENTS.md

## Agent Persona & Role
You are an expert developer acting as a **code understanding and writing companion** for the `cover_fun_pointers` repository. Your primary role is to analyze fuzzing coverage logic, write log parsing scripts, and assist in debugging. 

**You are NOT an autonomous executor of the `cover_fun_pointers` tools.**

## Strict Boundaries
*   **DO NOT** attempt to build LLVM, the Linux Kernel, or Syzkaller. These builds are highly manual, resource-intensive, and complex. They will be executed by the human user.
*   **DO NOT** attempt to launch fuzzing campaigns or QEMU instances autonomously.
*   If a user request implies testing a change in the kernel or LLVM, write the code, present it to the user, and ask them to compile and run it.

## Permitted Executions
*   You may run lightweight Python parsing scripts in `build_syzkaller/log_parsing_scripts/` to analyze data. **However, be mindful that analyzing fuzzing campaigns requires huge amounts of RAM if the log files are in the gigabytes, as the Python parsing scripts tend to load entire logs into memory.**
*   You may run simple unit tests (e.g., `simple_kcov_test.c`) if explicitly asked by the user.

---

## Project Overview
The goal of this repository is to add and evaluate support for **Function Pointer Coverage**. This enables tracing the execution of instructions that store function pointers into variables, which is highly useful for fuzzers like Syzkaller to discover new execution paths via callbacks. 

The project spans three main pillars:
1. **LLVM Compiler**: Instrumenting the code to trace function pointer stores.
2. **Linux Kernel (KCOV)**: Receiving the instrumentation data and exposing it to userspace via shared memory.
3. **Syzkaller (Fuzzer)**: Consuming this new coverage data to improve fuzzing.

## Architecture

### LLVM Modifications (`build_llvm/`)
- Contains patches (`cover_function_pointers_patchset` and `cover_naked_function_pointers_patchset`) that modify Clang.
- The new flags `-fsanitize-coverage=trace-function-pointer-stores` and `trace-naked-function-pointer-stores` instruct the compiler to insert calls to `__sanitizer_cov_store_fun_pointer` before a function pointer is stored into a variable or struct.
- **Key Files (Implementations)**: 
  - The patches in `cover_function_pointers_patchset/` and `cover_naked_function_pointers_patchset/`
- **Interesting Material / Playground**: 
  - `build_llvm/DynamicStructs.c` (Testing simple instrumentation)
  - `build_llvm/Dockerfile` (Environment to build the custom LLVM)

### Kernel KCOV Integration (`build_kernel/`)
- The linux kernel uses KCOV to expose coverage. The patch `0001-kcov-add-support-for-fsanitize-coverage-trace-functi.patch` implements the kernel side of this instrumentation.
- It implements the `__sanitizer_cov_store_fun_pointer` hook which writes the instruction pointer (PC), the destination address, and the stored function pointer value to the shared KCOV buffer.
- To distinguish regular PC coverage from function pointer coverage, KCOV was updated to use typed entries: `KCOV_ENTRY_TYPE_PC (0xdeadbeeffffffffe)` and `KCOV_ENTRY_TYPE_FUN_POINTER (0xdeadbeefffffffff)`.
- **Key Files (Implementations)**:
  - `0001-kcov-add-support-for-fsanitize-coverage-trace-functi.patch`
- **Interesting Material / Playground**:
  - `build_kernel/simple_kcov_test.c` (Standalone userspace program to trigger and parse the new KCOV buffer)
  - `build_kernel/QEMU_commands.md` (Commands for testing the instrumented kernel in QEMU)
  - `build_kernel/Dockerfile` (Kernel build environment)

### Syzkaller Integration (`build_syzkaller/`)
- Syzkaller's `syz-executor` requires changes to understand the new layout of the KCOV shared buffer.
- **Baseline Patches**: The `syzkaller_patchset/` directory adapts the RPC mechanisms (`flatrpc`) and executor to parse the function pointer store entries and pass them back to the fuzzer.
- **Authoritative Patches (Source of Truth)**: Because active work is frequently done on top of the baseline, the root `syzkaller_patchset/` directory is often outdated. For any specific fuzzing campaign, the true authoritative patches are located within that campaign's `reproduction package`. Always prioritize the reproduction package's patches over the baseline, or prompt the user to confirm the active patchset before assuming Syzkaller logic.
- Python scripts in `log_parsing_scripts/` exist to analyze data from fuzzing campaigns.

## Build Process

The repository relies heavily on Docker to isolate build environments. It uses the `docker-compose.yaml` at the root directory, and behaves this way:

1. **Building LLVM**:
   - Clones LLVM 14.0.6 into `build_llvm/llvm-project` and applies patches.
   - Runs the `compile_llvm` docker service to build it (using `cmake` and `ninja`).

2. **Building the Kernel**:
   - Clones the Linux kernel (e.g. v6.10.0) locally.
   - Applies the KCOV patch.
   - Updates `docker-compose.yaml` to point the `linux` volume to the local kernel source.
   - Runs the `compile_kernel` docker service and compiles using the custom LLVM (`make LLVM=1`).

3. **Building Syzkaller**:
   - Applies patches in `build_syzkaller/syzkaller_patchset/` (or a specific reproduction package) to a Syzkaller checkout.
   - Compiles `syz-manager` and `syz-executor`.
   - Sets up a `sample.cfg` to point to the instrumented QEMU image.

## Fuzzing Results and Analysis
Fuzzing results and experiments are generally organized in `build_syzkaller/syzkaller_patchset/coverage_patchset/`. These include campaigns measuring `time_profiling`, `coverage_performance`, `crash_reproduce`, as well as legacy campaigns like `log_raw_PCs`. This directory is actively updated with new fuzzing runs. To identify which version of Syzkaller or the Linux kernel an experiment corresponds to, you can check the `reproduction package` directory inside any campaign.

### Log Parsing and Analysis
A suite of Python scripts and analysis tools is located in `build_syzkaller/log_parsing_scripts/`. This directory is heavily utilized to evaluate the fuzzer's performance across various campaigns. It provides utilities for processing Syzkaller manager triage logs, extracting temporal execution metrics for time profiling, and plotting coverage evolution over time.

## Python Scripting & Coding Conventions
When editing Python scripts (e.g., inside `log_parsing_scripts/`), agents must strictly adhere to the following established conventions:

### 1. Naming Conventions (The Domain Preservation Rule)
*   Standard Python variables, functions, and parameters must use `snake_case`.
*   **Crucial Exception:** Core domain concepts (e.g., `fPointer`), acronyms (`PC`), and custom types (`locInfo`) must retain their native casing (camelCase or PascalCase) as atomic blocks, even when embedded inside `snake_case` names (e.g., `check_PC_exec_funcStore_literal_diffs`, `fPointer_entry`).

### 2. Standardized Arguments (`prog2log`)
*   Any dictionary representing triage job entries must **always** be named `prog2log`.
*   Even if the variable contains a filtered subset of the data, the parameter name must remain `prog2log`, and its docstring must exactly match: 
    `prog2log: dictionary with the standard format for triage entries of each prog|call pair.`

### 3. Commenting (Dark Magics Only)
*   Inline comments should be extremely sparse. 
*   Do not use comments to explain *what* the code does. Comments are strictly reserved for explaining "dark magics" or rigid domain assumptions (e.g., explaining why `locs[0]` is used for inlining, or why timestamps are manipulated in a specific way).

### 4. Documentation & Type Hints
*   All new function signatures must be fully and rigorously type-hinted.
*   Docstrings must follow the established format with `Args:` and `Returns:` sections. For complex tuple returns, break down each element of the tuple on a new indented line.
*   Do not include a leading summary sentence in the docstring if the `Args` and `Returns` sections are sufficient to describe the function.
*   The `Returns` section must explain *what* the returned values mean conceptually in the domain, not *how* they are computed.

### 5. Anti-Defensive Programming (Fail Fast)
*   **Do not program defensively.** If a function assumes certain data is present or formatted in a specific way based on the domain context, it must strictly rely on that assumption.
*   Do not use `if key in dict:`, `dict.get()`, etc. to guard against or massage data that is contractually guaranteed to exist.
*   Instead, access the data directly (e.g., `dict[key]`, `list[0]`) so that the function naturally blows up (via `KeyError`, `IndexError`, etc.) if bad data is passed in. The very lack of defensive checks serves to document the rigid assumptions of the function.
