# Intro
This README includes the instructions to build and test an instrumented linux kernel with functionality to track execution of instructions that store function pointers into variables. It depends on a series of patches to clang present at [../build_llvm](../build_llvm/)

# Steps to make instrumented kernel with new kcov coverage.

## 0. Apply patch to appropiate kernel.
The [kcov patch](./0001-kcov-add-support-for-fsanitize-coverage-trace-functi.patch) in this repo assumes you're working on the linux source tree v.6.10.0.


```bash
# If you don't have the linux source tree locally available, you can get it with
git clone --branch v6.10 --depth 1 \
    git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
# Then, apply the kcov patch
cd linux
git apply /path/to/build_kernel/0001-kcov-add-support-for-fsanitize-coverage-trace-functi.patch
```

## 0.5 Build custom clang following the appropiate [README.md](../build_llvm/README.md)

## 1. Configure [docker-compose.yaml](../docker-compose.yaml) to point to the local linux source tree

## 2. Make inside the container:
Launch the `build_kernel` service from the docker compose and get inside the container.
Then execute:

```bash
cp /home/build_kernel/configs/syzkaller_def.config /home/linux/.config
cd /home/linux
make LLVM=1 olddefconfig
make LLVM=1 -j $(nproc)
```

Clang will output additional information on the instrumented instructions to stderr. If you pipe stderr to a file, you can use the scripts in [naked_pointer_report_results](./naked_pointer_report_results/README.md) to analyze the instrumented instructions.

### 2.5. Optional: Steps used to create [syzkaller_def.config](./syzkaller_def.config).
(inside the container, run:)

```bash
cd /home/linux
make distclean
make LLVM=1 defconfig
LLVM=1 source scripts/kconfig/merge_config.sh /home/build_kernel/.config /home/build_kernel/configs/syzkaller_kernelversion_geq_5.12.config
make LLVM=1 olddefconfig
make LLVM=1 -j $(nproc)
```
# Steps to test instrumented kernel
Once the kernel is built, you can
follow [this README](QEMU_commands.md) to launch a QEMU VM and run a simple program that captures coverage produced by the new kcov patch
