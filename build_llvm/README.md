## Clone LLVM Project

```bash
git clone --branch llvmorg-14.0.6 --depth 1 https://github.com/llvm/llvm-project.git
```

## Compile LLVM

Inside the docker container:

```bash
cmake -S llvm -B build -G "Ninja" \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_PROJECTS="clang;lld" \
  -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
  -DLLVM_TARGETS_TO_BUILD=Native
  
ninja -C build
```

## Test new clang on sample DynamicStructs.c

After building, and having the appropiate c libraries for linking:
```
clang -g -O0 -fsanitize-coverage=trace-function-pointer-stores DynamicStructs.c -o DynamicStructs.o
```

This should produce a binary where you can check that on runtime the callback receives a pointer to the dynamically chosen function.
