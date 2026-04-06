## Steps to make kernel with custom clang

#### 1. Configure [docker-compose.yaml](../docker-compose.yaml) to point to the local linux source tree

#### 2. Make inside the container:
Launch the `build_kernel` service from the docker compose and get inside the container.
Then execute:  

```bash
cp /home/build_kernel/syzkaller_def.config /home/linux/.config
cd /home/linux
make LLVM=1 olddefconfig
make LLVM=1 -j $(nproc)
```

##### 2.5. Optional: Steps used to recreate [syzkaller_def.config](./syzkaller_def.config).
(inside the container, run:)

```bash
cd /home/linux
make distclean
make LLVM=1 defconfig
LLVM=1 source scripts/kconfig/merge_config.sh /home/build_kernel/.config syzkaller_kernelversion_geq_5.12.config
make LLVM=1 olddefconfig
make LLVM=1 -j $(nproc)
```
