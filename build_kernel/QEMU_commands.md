# Intro
These commands assume that you have a working QEMU setup in your machine, similar to the one used by syzkaller.
The commands themselves are ripped straight from syzkaller. You may look at `./syzkaller_tmp_dir` to get an idea of how to get them.

These steps are meant to make sure that a VM launched with an instrumented kernel reports coverage through kcov correctly.

## Launch QEMU instance
``` bash
qemu-system-x86_64 -m 12288 \
-smp 5 \
-chardev socket,id=SOCKSYZ,server=on,wait=off,host=localhost,port=22449 \
-mon chardev=SOCKSYZ,mode=control \
-display none \
-serial stdio \
-no-reboot \
-name VM-0 \
-device virtio-rng-pci \
-enable-kvm \
-cpu host,migratable=off \
-device e1000,netdev=net0 \
-netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:59565-:22 \
-hda /home/dwappner/Desktop/syzkaller/qemu-img/bullseye.img \
-snapshot \
-kernel /home/dwappner/Desktop/linux/arch/x86/boot/bzImage \
-append "root=/dev/sda console=ttyS0 net.ifnames=0"
```

## Compile sample kcvov test program
```bash
gcc -static -o simple_kcov_test simple_kcov_test.c
```

## Copy simple kcov test to the QEMU VM
```bash
scp -P 59565 \
-F /dev/null \
-o UserKnownHostsFile=/dev/null \
-o IdentitiesOnly=yes \
-o BatchMode=yes \
-o StrictHostKeyChecking=no \
-o ConnectTimeout=10 \
-i /home/dwappner/Desktop/syzkaller/qemu-img/bullseye.id_rsa \
-v /home/dwappner/Desktop/cover_fun_pointers_prototype/build_kernel/simple_kcov_test \
root@localhost:/simple_kcov_test
```

## ssh into the VM
First run
```bash
ssh \
-p 59565 \
-F /dev/null \
-o UserKnownHostsFile=/dev/null \
-o IdentitiesOnly=yes \
-o BatchMode=yes \
-o StrictHostKeyChecking=no \
-o ConnectTimeout=10 \
-i /home/dwappner/Desktop/syzkaller/qemu-img/bullseye.id_rsa \
-v root@localhost
```

Then you may interactively
```bash
cd /
./simple_kcov_test
```