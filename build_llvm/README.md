## Clone LLVM Project

```bash
git clone --branch llvmorg-22.1.1 --depth 1 https://github.com/llvm/llvm-project.git
```

## Compile LLVM

Inside the docker container:

```bash
cmake -S llvm -B build -G "Ninja" \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_PROJECTS="clang;lld" \
  -DLLVM_TARGETS_TO_BUILD=Native

ninja -C build
```