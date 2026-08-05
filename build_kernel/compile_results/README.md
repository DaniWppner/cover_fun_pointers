Script [process_tmp_json.py](./process_tmp_json.py) expects the output produced by running the custom clang on the linux kernel.

If you pipe stderr to a file, you can then edit INPUT_PATH and OUTPUT_PATH in the script to produce a list of the functions that were instrumented with the callback by clang and that also have function pointer arguments as inputs.
