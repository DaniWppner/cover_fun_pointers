## Clone LLVM Project

```bash
git clone --branch llvmorg-14.0.6 --depth 1 https://github.com/llvm/llvm-project.git
```

## Apply patchset

Before compiling LLVM, make sure to apply the appropiate git patches, like the ones in `./cover_function_pointers_patchset` or `./cover_naked_function_pointers_patchset`

## Compile LLVM

Inside the docker container:

```bash
cmake -S llvm -B build -G "Ninja" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DLLVM_ENABLE_PROJECTS="clang;lld" \
  -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_USE_LINKER=lld-14 \
  -DLLVM_TARGETS_TO_BUILD=Native
  
ninja -C build
```

## Test new clang on sample DynamicStructs.c

After building, and having the appropiate c libraries for linking (probably inside one of the containers in this repo):
```
path/to/clang -g -O0 -fsanitize-coverage=trace-function-pointer-stores DynamicStructs.c -o DynamicStructs.o
```
Make sure that `path/to/clang` refers to the custom installation.
One way do this is adding the `llvm-project/build/bin` directory to your PATH in a Docker container with no other clang installation available. 

This should produce a binary where you can check that on runtime the callback receives a pointer to the dynamically chosen function.
