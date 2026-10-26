# Summary
This directory holds reproduction steps in order to try to cover function `nl80211_get_key` of linux `nl80211.c` module that is assigned to `.doit` inside `netlink/genetlink.c` but never executed.

# Executing syz-progs directly in a VM to check their coverage.
You can see in [`uncovered_example.prog`](uncovered_example.prog) the generated test case by syzkaller that attempted to execute `nl80211_get_key`.
This program fails to do so because it was generated in a fuzzing campaign that lacked `CONFIG_MAC80211_HWSIM=y` but also because not all prerequisites of syscall `sendmsg$NL80211_CMD_GET_KEY` were satisfied.

These are the steps to run this program, or [`fixed_example.prog`](fixed_example.prog) directly in a VM with syz-executor.
### Launch VM
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

### copy prog to VM
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

### launch syz-executor
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
/syz-execprog -executor /syz-executor -repeat 1 -procs 2 -cover=1 -output -coverfile /cover_{prog_name} /{prog_name}
## wait until it's finished
exit
```

### recover results from running syz-executor to host machine
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

### parse contents with addr2line
If the file is a .fp file, make sure to edit it so all offsets appear as its own line each in the file.
For example:
```bash
addr2line -ipfCa -e ~/Desktop/linux/vmlinux < cover_fixed_example_log_prog_prog1.2.fp > stored_functions_fixed_call2.txt
```

## Executing `nl80211_get_key` directly with a C program
[`nl80211_test.cc`](./nl80211_test.cc) is a standalone program that relies on syz-executor to open `MAC80211_HWSIM` devices to allow message `NL80211_CMD_GET_KEY` to trigger execution of the function `nl80211_get_key` dispatched trhough the `netlink` module.

In order for this to work, the kernel must be compiled with `CONFIG_MAC80211_HWSIM=y`.
### Enabling `CONFIG_MAC80211_HWSIM`
The .config file [`enable_wifi_fuzzing.config`](./enable_wifi_fuzzing.config) copied from syzbot has all necesary kernel configurations to create `MAC80211_HWSIM` devices. Make sure to include it in the kernel config, similar to this:
```bash
cp ./enable_wifi_fuzzing.config /path/to/linux && cd /path/to/linux
scripts/kconfig/merge_config.sh .config enable_wifi_fuzzing.config
make
```

### Compiling nl80211_test.cc
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

### Executing and checking results
You can follow the above instructions to roughly follow these steps:
 * Launch a VM running the updated kernel using QEMU
 * Copy the `nl80211_test` binary inside the VM with scp
 * ssh into the VM and run the `nl80211_test` program
 * Copy the generated `nl80211_test_FPs.cov` and `nl80211_test_PCs.cov` to the host using scp
 * Verify with addr2line that function `nl80211_get_key` was executed