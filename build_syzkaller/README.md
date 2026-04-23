# Steps to run syzkaller with an instrumented kernel that reports function pointer stores

## 1. Build the modified syzkaller
Use git to apply the patches in [syzkaller_patchset](./syzkaller_patchset/) or pull
from https://github.com/DaniWppner/syzkaller/tree/handle_kcov_store_instructions

## 2. Run the syz-manager-automation script in [this repo](https://github.com/DaniWppner/tutorials/tree/main/syzkaller_tutorial/syz-manager-atomation)
To Do:
Remove the instruction on where to download the automation script once the script itself writes a better reproduction package

Use your local versions of linux, syzkaller, etc. and the sample.cfg in this directory.
Make sure to edit the .cfg to point to the local QEMU-img.