## Setup for debugging
These steps fail to attach a working gdb instance to the executor, because the executor is a multiprocess program, which necessitates special gdb flags.
Nevertheless, it is a good first approach.

First, create the following QEMU image with gdb in it

```bash
ADD_PACKAGE="make,sysbench,git,vim,tmux,usbutils,tcpdump,gdb" /path/to/syzkaller/tools/create-image.sh --feature full
```

Second, make sure to build the executor with debug symbols enabled
```bash
#(inside the environment you use to build syzkaller)
ADDCXXFLAGS="-g" make executor
```

# Intro
These commands assume you have a working setup similar to the one used by Syzkaller on a QEMU VM to fuzz linux.
The commands themselves are stripped straight from syzkaller with the -debug flag on.

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
-hda /home/dwappner/Desktop/cover_fun_pointers_prototype/build_syzkaller/syz-executor-test/QEMU-debug-image/trixie.img \
-snapshot \
-kernel /home/dwappner/Desktop/linux/arch/x86/boot/bzImage \
-append "root=/dev/sda console=ttyS0 net.ifnames=0"
```

## Copy syz-executor, syz-execprog and sample.prog into VM
You have to update the last few commands with the appropiate paths local to your environment

```bash
scp -P 59565 \
-F /dev/null \
-o UserKnownHostsFile=/dev/null \
-o IdentitiesOnly=yes \
-o BatchMode=yes \
-o StrictHostKeyChecking=no \
-o ConnectTimeout=10 \
-i /home/dwappner/Desktop/cover_fun_pointers_prototype/build_syzkaller/syz-executor-test/QEMU-debug-image/trixie.id_rsa \
-v \
/home/dwappner/Desktop/syzkaller/bin/linux_amd64/syz-executor \
/home/dwappner/Desktop/syzkaller/bin/linux_amd64/syz-execprog \
/home/dwappner/Desktop/cover_fun_pointers_prototype/build_syzkaller/syz-executor-test/sample.prog \
root@localhost:/
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
-i /home/dwappner/Desktop/cover_fun_pointers_prototype/build_syzkaller/syz-executor-test/QEMU-debug-image/trixie.id_rsa \
-v root@localhost
```

Then you may interactively
```bash
cd /
./syz-execprog -vv 10 -debug -cover -gdb -procs 4 ./sample.prog 
```
