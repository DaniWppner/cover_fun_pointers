## Launch VM
```bash
qemu-system-x86_64 -m 6144 \
-smp 2 \
-chardev socket,id=SOCKSYZ,server=on,wait=off,host=localhost,port=22449 \
-mon chardev=SOCKSYZ,mode=control \
-display none \
-serial stdio \
-no-reboot \
-name VM-SIMPLE-TEST \
-device virtio-rng-pci \
-enable-kvm \
-cpu host,migratable=off \
-device e1000,netdev=net0 \
-netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:59565-:22 \
-hda /home/dwappner/Desktop/syzkaller/qemu-img/trixie.img \
-snapshot \
-kernel /home/dwappner/Desktop/linux/arch/x86/boot/bzImage \
-append "root=/dev/sda console=ttyS0 net.ifnames=0"
```

## copy prog to VM
```bash
scp -P 59565 \
-F /dev/null \
-o UserKnownHostsFile=/dev/null \
-o IdentitiesOnly=yes \
-o BatchMode=yes \
-o StrictHostKeyChecking=no \
-o ConnectTimeout=10 \
-i /home/dwappner/Desktop/syzkaller/qemu-img/trixie.id_rsa \
/home/dwappner/Desktop/syzkaller/bin/linux_amd64/syz-executor \
/home/dwappner/Desktop/syzkaller/bin/linux_amd64/syz-execprog \
/mnt/ssd_data/newhome/dwappner/Desktop/cover_fun_pointers/build_syzkaller/log_parsing_scripts/analyze_save_function_pointers_campaign/uncovered_functions_analysis/wip_fixed_example.prog \
root@localhost:/
```

## launch syz-executor
(Make sure to include patch [77c26ae](https://github.com/DaniWppner/syzkaller/commit/77c26aec13ffbd45564064970d9754395820f474))

```bash
ssh -p 59565 \
-F /dev/null \
-o UserKnownHostsFile=/dev/null \
-o IdentitiesOnly=yes \
-o BatchMode=yes \
-o StrictHostKeyChecking=no \
-o ConnectTimeout=10 \
-i /home/dwappner/Desktop/syzkaller/qemu-img/trixie.id_rsa \
root@localhost
```
once connected,
```bash
/syz-execprog -executor /syz-executor -repeat 2 -procs 2 -cover=1 -output -coverfile /cover_{prog_name} /{prog_name}
# wait until it's finished
exit
```

## recover results from running syz-executor to host machine
```bash
scp -P 59565 \
-F /dev/null \
-o UserKnownHostsFile=/dev/null \
-o IdentitiesOnly=yes \
-o BatchMode=yes \
-o StrictHostKeyChecking=no \
-o ConnectTimeout=10 \
-i /home/dwappner/Desktop/syzkaller/qemu-img/trixie.id_rsa \
root@localhost:/cover_fixed_example* \
/mnt/ssd_data/newhome/dwappner/Desktop/cover_fun_pointers/build_syzkaller/log_parsing_scripts/analyze_save_function_pointers_campaign/uncovered_functions_analysis/
```

## parse contents with addr2line
If the file is a .fp file, make sure to edit it so all offsets appear as its own line each in the file.
For example:
```bash
addr2line -ipfCa -e ~/Desktop/linux/vmlinux < cover_fixed_example_log_prog_prog1.2.fp > stored_functions_fixed_call2.txt
```

## Compiling nl80211_test.cc
This standalone c program relies on syz-executor's infraestructure for operating with the kernel.
To this end, it imports all of executor.cc in order to use any of the functions defined therein.
Run this command **in syzkaller's root directory**:
```bash
cd path/to/syzkaller && \
/usr/bin/g++ \
-static \
-pthread \
-m64 \
-O2 \
-Wall \
-std=c++17 \
-I. -Iexecutor/_include \
-DGOOS_linux=1 \
-DGOARCH_amd64=1 \
-DHOSTGOOS_linux=1 \
-o /mnt/ssd_data/newhome/dwappner/Desktop/cover_fun_pointers/build_syzkaller/log_parsing_scripts/analyze_save_function_pointers_campaign/uncovered_functions_analysis/nl80211_test /mnt/ssd_data/newhome/dwappner/Desktop/cover_fun_pointers/build_syzkaller/log_parsing_scripts/analyze_save_function_pointers_campaign/uncovered_functions_analysis/nl80211_test.cc
```