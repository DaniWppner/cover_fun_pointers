#define _GNU_SOURCE
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <stdarg.h>

#define COVER_SIZE (64 << 10)
#define KCOV_TRACE_PC 0
#define KCOV_INIT_TRACE _IOR('c', 1, unsigned long)
#define KCOV_ENABLE _IO('c', 100)
#define KCOV_DISABLE _IO('c', 101)

#define KCOV_ENTRY_TYPE_HEADER_PC (0xdeadbeeffffffffeULL)
#define KCOV_ENTRY_TYPE_HEADER_FUN_POINTER (0xdeadbeefffffffffULL)

static int kcov_fd_global = -1;
static unsigned long *cover_global = NULL;
static unsigned long *shared_cover = NULL;
static int is_child = 0;

static void process_kcov_buffer(unsigned long *cover) {
    unsigned long n, i;
    n = __atomic_load_n(&cover[0], __ATOMIC_RELAXED);
    printf("[*] KCOV Buffer recorded %lu words of trace data.\n", n);
    
    FILE *fout_pcs = fopen("/syz2prog_PCs.cov", "w");
    FILE *fout_FPs = fopen("/syz2prog_FPs.cov", "w");
    if (!fout_pcs || !fout_FPs) {
        perror("[-] Failed to open coverage output files");
        if (fout_pcs) fclose(fout_pcs);
        if (fout_FPs) fclose(fout_FPs);
        return;
    }

    i = 1;
    while (i <= n) {
        unsigned long type = cover[i];
        if (type == KCOV_ENTRY_TYPE_HEADER_PC) {
            unsigned long pc = cover[i + 1];
            fprintf(fout_pcs, "0x%lx\n", pc);
            i += 2; 
        } else if (type == KCOV_ENTRY_TYPE_HEADER_FUN_POINTER) {
            unsigned long pc = cover[i + 1];
            // unsigned long store_addr = cover[i + 2];
            unsigned long stored_value = cover[i + 3];
            fprintf(fout_FPs, "0x%lx 0x%lx\n", pc, stored_value);
            i += 4;
        } else {
            i += 1;
        }
    }
    
    fclose(fout_pcs);
    fclose(fout_FPs);    
    printf("[+] PC coverage data written to syz2prog_PCs.cov\n");
    printf("[+] Function Pointer coverage data written to syz2prog_FPs.cov\n");
}

static int setup_kcov(unsigned long **cover) {
    int kcov_fd = open("/sys/kernel/debug/kcov", O_RDWR);
    if (kcov_fd == -1) {
        perror("[-] open kcov");
        exit(1);
    }
    if (ioctl(kcov_fd, KCOV_INIT_TRACE, COVER_SIZE)) {
        perror("[-] ioctl init");
        exit(1);
    }
    *cover = (unsigned long*)mmap(NULL, COVER_SIZE * sizeof(unsigned long),
                                  PROT_READ | PROT_WRITE, MAP_SHARED, kcov_fd, 0);
    if (*cover == MAP_FAILED) {
        perror("[-] mmap kcov");
        exit(1);
    }
    // We NO LONGER enable KCOV globally here. We let my_syscall toggle it.
    __atomic_store_n(&(*cover)[0], 0, __ATOMIC_RELAXED);
    return kcov_fd;
}

static void parent_atexit_handler(void) {
    if (!is_child && shared_cover != NULL) {
        printf("[*] Parent process exiting. Writing coverage files to original filesystem...\n");
        process_kcov_buffer(shared_cover);
    }
}

// We intercept fork() to detect when the Syzkaller sandbox creates the child process
// that will actually execute loop(). KCOV must be enabled within that specific thread.
static pid_t my_fork(void) {
    if (shared_cover == NULL) {
        shared_cover = (unsigned long *)mmap(NULL, COVER_SIZE * sizeof(unsigned long), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
        if (shared_cover == MAP_FAILED) {
            perror("[-] Failed to allocate shared memory for coverage");
            exit(1);
        }
        atexit(parent_atexit_handler);
    }

    // Call the real fork by undefining the macro temporarily
#undef fork
    pid_t pid = fork();
#define fork my_fork

    if (pid == 0) {
        is_child = 1;
        printf("[*] Sandbox child process created. Initializing KCOV...\n");
        kcov_fd_global = setup_kcov(&cover_global);
    }
    return pid;
}

// We intercept exit() to copy the coverage buffer before the child process dies.
static void my_exit(int status) {
    if (is_child && kcov_fd_global != -1) {
        printf("[*] Sandbox child process exiting. Copying KCOV results to shared memory...\n");
        unsigned long n = __atomic_load_n(&cover_global[0], __ATOMIC_RELAXED);
        
        // Ensure we don't overflow the shared buffer
        if (n >= COVER_SIZE) n = COVER_SIZE - 1;
        
        // Copy the length word and the trace data
        memcpy(shared_cover, cover_global, (n + 1) * sizeof(unsigned long));
        
        if (ioctl(kcov_fd_global, KCOV_DISABLE, 0)) perror("[-] ioctl disable");
        if (munmap(cover_global, COVER_SIZE * sizeof(unsigned long))) perror("munmap");
        if (close(kcov_fd_global)) perror("close kcov_fd");
        
        kcov_fd_global = -1;
    }
    
    // Call the real exit
#undef exit
    exit(status);
}

// We intercept syscall() to toggle KCOV tracing ONLY for the explicitly generated syscalls.
// This prevents overflowing the buffer with massive noisy setup functions like initialize_wifi_devices.
static long my_syscall(long number, ...) {
    va_list args;
    va_start(args, number);
    long a1 = va_arg(args, long);
    long a2 = va_arg(args, long);
    long a3 = va_arg(args, long);
    long a4 = va_arg(args, long);
    long a5 = va_arg(args, long);
    long a6 = va_arg(args, long);
    va_end(args);

    int should_trace = is_child && kcov_fd_global != -1;
    
    if (should_trace) {
        if (ioctl(kcov_fd_global, KCOV_ENABLE, KCOV_TRACE_PC)) perror("[-] ioctl enable");
    }

#undef syscall
    long ret = syscall(number, a1, a2, a3, a4, a5, a6);
#define syscall my_syscall

    if (should_trace) {
        if (ioctl(kcov_fd_global, KCOV_DISABLE, 0)) perror("[-] ioctl disable");
    }
    return ret;
}

// Override fork, exit, and syscall macros before including the generated source
#define fork my_fork
#define exit my_exit
#define syscall my_syscall

// Include the generated Syzkaller C program
#include "syz2progwifi.c"
