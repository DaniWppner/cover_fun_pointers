#!/usr/bin/env python3
import os
import subprocess
import shlex
import sys
import glob
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
QEMU_CMD_TEMPLATE = """
qemu-system-x86_64 \
-m 12288 \
-smp {smp} \
-chardev socket,id=SOCKSYZ,server=on,wait=off,host=localhost,port={qemu_port} \
-mon chardev=SOCKSYZ,mode=control \
-display none \
-serial stdio \
-no-reboot \
-name {vm_name} \
-device virtio-rng-pci \
-enable-kvm \
-cpu host,migratable=off \
-device e1000,netdev=net0 \
-netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:{ssh_port}-:22 \
-hda /mnt/ssd_data/newhome/dwappner/Desktop/syzkaller/qemu-img/trixie.img \
-snapshot \
-kernel /mnt/ssd_data/newhome/dwappner/Desktop/linux/arch/x86/boot/bzImage \
-append "root=/dev/sda console=ttyS0 net.ifnames=0"
"""

SYZKALLER_BIN_DIR = "/mnt/ssd_data/newhome/dwappner/Desktop/syzkaller/bin/linux_amd64"

found_lock = threading.Lock()

class LogBuffer:
    def __init__(self, filepath, max_bytes=10*1024*1024*1024): # 10 GB threshold
        self.filepath = filepath
        self.lines = []
        self.on_disk = False
        self.max_bytes = max_bytes
        self.current_bytes = 0
        
    def write(self, line):
        if self.on_disk:
            with open(self.filepath, 'a') as f:
                f.write(line)
        else:
            self.lines.append(line)
            self.current_bytes += len(line.encode('utf-8'))
            if self.current_bytes > self.max_bytes:
                self.flush()
                
    def flush(self):
        if not self.on_disk:
            with open(self.filepath, 'w') as f:
                f.writelines(self.lines)
            self.lines = []
            self.on_disk = True
            
    def save(self):
        self.flush()
        
    def discard(self):
        self.lines = []
        if self.on_disk and os.path.exists(self.filepath):
            try:
                os.remove(self.filepath)
            except Exception:
                pass


class QEMUInstance:
    def __init__(self, instance_id):
        self.instance_id = instance_id
        self.ssh_port = 59565 + instance_id
        self.qemu_port = 22449 + instance_id
        self.qemu_proc = None
        self.log_file = None
        
        self.ssh_args = [
            "-p", str(self.ssh_port),
            "-F", "/dev/null",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-i", "/mnt/ssd_data/newhome/dwappner/Desktop/syzkaller/qemu-img/trixie.id_rsa"
        ]
        
    def run_ssh(self, cmd, timeout=None, prompt_on_fail=True):
        full_cmd = ["ssh"] + self.ssh_args + ["root@127.0.0.1", cmd]
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode != 0:
                if prompt_on_fail:
                    with found_lock:
                        print(f"\n[!] Instance {self.instance_id} command failed: {' '.join(full_cmd)}")
                        print(f"[!] Stderr: {res.stderr}")
                        input("[?] Press Enter to continue execution, or Ctrl+C to abort everything...")
                return False
            return True
        except subprocess.TimeoutExpired:
            return "TIMEOUT"
        except Exception as e:
            if prompt_on_fail:
                with found_lock:
                    print(f"\n[!] Instance {self.instance_id} command exception: {e}")
                    input("[?] Press Enter to continue execution, or Ctrl+C to abort everything...")
            return False

    def run_scp(self, src, dst, prompt_on_fail=True):
        scp_args = [arg if arg != "-p" else "-P" for arg in self.ssh_args]
        full_cmd = ["scp"] + scp_args + [src, f"root@127.0.0.1:{dst}"]
        res = subprocess.run(full_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            if prompt_on_fail:
                with found_lock:
                    print(f"\n[!] Instance {self.instance_id} SCP failed: {' '.join(full_cmd)}")
                    print(f"[!] Stderr: {res.stderr}")
                    input("[?] Press Enter to continue execution, or Ctrl+C to abort everything...")
            return False
        return True

    def run_scp_from(self, src, dst, prompt_on_fail=True):
        scp_args = [arg if arg != "-p" else "-P" for arg in self.ssh_args]
        full_cmd = ["scp"] + scp_args + [f"root@127.0.0.1:{src}", dst]
        res = subprocess.run(full_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            if prompt_on_fail:
                with found_lock:
                    print(f"\n[!] Instance {self.instance_id} SCP from failed: {' '.join(full_cmd)}")
                    print(f"[!] Stderr: {res.stderr}")
                    input("[?] Press Enter to continue execution, or Ctrl+C to abort everything...")
            return False
        return True

    def run_ssh_monitor(self, cmd, log_buffer, no_output_timeout=180):
        full_cmd = ["ssh"] + self.ssh_args + ["root@127.0.0.1", cmd]
        print(f"[DEBUG {self.instance_id}] Running monitored SSH: {' '.join(full_cmd)}")
        p = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        q = queue.Queue()
        def reader():
            for line in iter(p.stdout.readline, ''):
                q.put(line)
            p.stdout.close()
            
        t = threading.Thread(target=reader, daemon=True)
        t.start()
        
        last_output_time = time.time()
        while True:
            try:
                line = q.get(timeout=1.0)
                if log_buffer:
                    log_buffer.write(line)
                last_output_time = time.time()
            except queue.Empty:
                if p.poll() is not None:
                    return False if p.returncode != 0 else True
                
                if time.time() - last_output_time > no_output_timeout:
                    print(f"\n[!] Instance {self.instance_id}: No output received for {no_output_timeout} seconds! Bug confirmed.")
                    p.kill()
                    return "TIMEOUT"

    def wait_for_ssh(self):
        print(f"[Instance {self.instance_id}] Waiting for SSH...")
        for _ in range(40):
            if self.run_ssh("echo ready", timeout=5, prompt_on_fail=False) == True:
                print(f"[Instance {self.instance_id}] SSH is ready!")
                return True
            time.sleep(0.5)
        return False

    def start(self):
        print(f"[Instance {self.instance_id}] Starting QEMU...")
        cmd = QEMU_CMD_TEMPLATE.format(
            smp=4,
            qemu_port=self.qemu_port,
            ssh_port=self.ssh_port,
            vm_name=f"VM-{self.instance_id}"
        )
        self.log_file = open(f"qemu_output_{self.instance_id}.log", "w")
        self.qemu_proc = subprocess.Popen(shlex.split(cmd), stdout=self.log_file, stderr=subprocess.STDOUT)
        
    def kill(self):
        if self.qemu_proc:
            print(f"[Instance {self.instance_id}] Killing QEMU...")
            self.qemu_proc.kill()
            self.qemu_proc.wait()
            self.log_file.close()
            if os.path.exists(f"qemu_output_{self.instance_id}.log"):
                try:
                    os.remove(f"qemu_output_{self.instance_id}.log")
                except OSError:
                    pass
            self.qemu_proc = None

    def setup_base(self):
        self.kill()
        self.start()
        if not self.wait_for_ssh():
            return False
        if not self.run_scp(os.path.join(SYZKALLER_BIN_DIR, "syz-executor"), "/root/syz-executor"):
            return False
        if not self.run_scp(os.path.join(SYZKALLER_BIN_DIR, "syz-execprog"), "/root/syz-execprog"):
            return False
        return True

def process_program(prog, idx, total, instance_id, instances):
    prog_name = os.path.basename(prog)
    print(f"[Instance {instance_id}] [{idx}/{total}] Testing {prog_name}...")
    
    vm = instances[instance_id]
    
    if not vm.run_scp(prog, f"/root/{prog_name}"):
        print(f"[Instance {instance_id}] Failed to upload {prog_name}. Restarting VM...")
        if not vm.setup_base():
            print(f"[Instance {instance_id}] Failed to restart VM.")
            return
        if not vm.run_scp(prog, f"/root/{prog_name}"):
            return

    # Use 4 procs since we have 4 cores per VM
    exec_cmd = f"/root/syz-execprog -executor /root/syz-executor -repeat 20 -procs 4 -cover=1 -output -coverfile /root/cover_{prog_name} /root/{prog_name}"
    log_filepath = f"ssh_output_{prog_name}.log"
    log_buffer = LogBuffer(log_filepath)
    res = vm.run_ssh_monitor(exec_cmd, log_buffer, no_output_timeout=180)
    
    if res == "TIMEOUT":
        print(f"!!! FOUND IT !!!")
        print(f"Program {prog_name} caused the SSH connection to hang (timeout).")
        log_buffer.save()
        vm.run_scp_from(f"/root/cover_{prog_name}*", ".")
        with found_lock:
            with open("found_reproducers.txt", "a") as f:
                f.write(f"Hanging program: {prog}\n")
        vm.setup_base()
    elif res == False:
        print(f"[Instance {instance_id}] Execution of {prog_name} crashed or dropped SSH.")
        if idx <= 5:
            log_buffer.save()
            vm.run_scp_from(f"/root/cover_{prog_name}*", ".")
        else:
            log_buffer.discard()
        vm.setup_base()
    else:
        print(f"[Instance {instance_id}] Program {prog_name} finished successfully.")
        if idx <= 5:
            log_buffer.save()
            vm.run_scp_from(f"/root/cover_{prog_name}*", ".")
        else:
            log_buffer.discard()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    programs_dir = os.path.join(base_dir, "extracted_reproducers")
    programs = glob.glob(os.path.join(programs_dir, "*.txt"))
    
    if not programs:
        print(f"No programs found in {programs_dir}")
        return

    print(f"Found {len(programs)} programs to test.")
    
    NUM_INSTANCES = 2
    instances = [QEMUInstance(i) for i in range(NUM_INSTANCES)]
    
    try:
        print("Setting up initial VMs...")
        for vm in instances:
            if not vm.setup_base():
                print(f"Failed to setup instance {vm.instance_id}")
                return
        
        print("Beginning concurrent execution loop...")
        
        job_queue = queue.Queue()
        for idx, prog in enumerate(programs, start=1):
            job_queue.put((idx, prog))
            
        def worker(instance_id):
            while True:
                try:
                    idx, prog = job_queue.get_nowait()
                except queue.Empty:
                    break
                process_program(prog, idx, len(programs), instance_id, instances)
                job_queue.task_done()
                
        threads = []
        for vm in instances:
            t = threading.Thread(target=worker, args=(vm.instance_id,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()

        print("Finished testing all programs. Please check found_reproducers.txt")

    except KeyboardInterrupt:
        print("\n[!] Ctrl+C caught! Cancelling operations and cleaning up...")
    finally:
        for vm in instances:
            vm.kill()

if __name__ == "__main__":
    main()
