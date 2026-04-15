#include <stdio.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <linux/types.h>

#define KCOV_INIT_TRACE                     _IOR('c', 1, unsigned long)
#define KCOV_ENABLE                         _IO('c', 100)
#define KCOV_DISABLE                        _IO('c', 101)

#define COVER_SIZE                          (64 << 10)

#define KCOV_TRACE_PC                       0

#define KCOV_ENTRY_TYPE_PC                  0xdeadbeeffffffffeULL
#define KCOV_ENTRY_TYPE_FUN_POINTER         0xdeadbeefffffffffULL



// Definitions and includes necessary for
// trigger_futex_parse_waitv()
#define _GNU_SOURCE
#include <unistd.h>
#include <time.h>
#include <sys/syscall.h>
#include <linux/futex.h>

#ifndef FUTEX_32
#define FUTEX_32 2
#endif

#ifndef FUTEX_PRIVATE_FLAG
#define FUTEX_PRIVATE_FLAG 128
#endif

/* futex_waitv syscall number for x86_64 */
#ifndef SYS_futex_waitv
#define SYS_futex_waitv 449 
#endif


struct simple_futex_waitv {
    uint64_t val;
    uint64_t uaddr;
    uint32_t flags;
    uint32_t __reserved;
};

void trigger_futex_parse_waitv() {
    // This aims to trigger futex_parse_waitv
    // at kernel/futex/syscalls.c:196
    uint32_t futex_val = 0;
    struct simple_futex_waitv waitv;
    
    waitv.val = 0;
    waitv.uaddr = (uintptr_t)&futex_val;
    waitv.flags = FUTEX_32 | FUTEX_PRIVATE_FLAG;
    waitv.__reserved = 0;

    // Use a tiny timeout so the syscall returns immediately rather than blocking
    struct timespec timeout = {0, 1000}; 
    
    // Invokes the futex_waitv syscall
    syscall(SYS_futex_waitv, &waitv, 1, 0, &timeout, CLOCK_MONOTONIC);
}

void do_something() {
    trigger_futex_parse_waitv();
}

void process_buffer_to_stdout(unsigned long *cover) {
    unsigned long n, i;

    /* Read number of consumed words. */
    n = __atomic_load_n(&cover[0], __ATOMIC_RELAXED);
    printf("Buffer recorded %lu words of trace data.\n", n);
    
    i = 1;
    while (i <= n) {
        unsigned long type = cover[i];

        if (type == KCOV_ENTRY_TYPE_PC) {
            /* 2 words in size
             * word 0 = KCOV_ENTRY_TYPE_PC
             * word 1 = the collected PC (regular KCOV)
             */
            if (i + 1 > n) {
                fprintf(stderr, "[ERROR] Expected PC at position %lu after KCOV_ENTRY_TYPE_PC at position %lu but max size is %lu.\n", i + 1, i, n);
                exit(1);
            }
            unsigned long pc = cover[i + 1];
            printf("[PC TRACE]\n\tPC: 0x%lx\n", pc);
            i += 2; 

        } else if (type == KCOV_ENTRY_TYPE_FUN_POINTER) {
            /* 4 words in size
             * word 0 = KCOV_ENTRY_TYPE_FUN_POINTER
             * word 1 = the PC where the store occured
             * word 2 = the memory address where the value was written
             * word 3 = the value of the function pointer stored
             */
            if (i + 3 > n) {
                fprintf(stderr, "[ERROR]: Expected PC, STORE_ADDR, STORE_VALUE after KCOV_ENTRY_TYPE_FUN_POINTER at positions %lu, %lu, %lu but max size is %lu.\n", i + 1, i + 2, i + 3, n);
                exit(1);
            }
            unsigned long pc = cover[i + 1];
            unsigned long store_addr = cover[i + 2];
            unsigned long stored_value = cover[i + 3];
            
            printf("[FUN PTR]\n\tPC: 0x%lx\n\tDestination: 0x%lx\n\tFunctionPointer: 0x%lx\n", 
                   pc, store_addr, stored_value);
            
            i += 4;

        } else {
            // Fallback for malformed data
            fprintf(stderr, "[ERROR]: Unrecognized entry type 0x%lx at position %lu of %lu in shared buffer.\n", type, i, n);
            exit(1);
        }
    }
}

// This function is ripped straight from https://docs.kernel.org/dev-tools/kcov.html
// The only customization is the handling of the info on the shared buffer.
int main(int argc, char **argv)
{
    int fd;
    unsigned long *cover;

    /* A single fd descriptor allows coverage collection on a single thread. */
    fd = open("/sys/kernel/debug/kcov", O_RDWR);
    if (fd == -1) 
        perror("open /sys/kernel/debug/kcov"), exit(1);

    /* Setup trace mode and trace size. */
    if (ioctl(fd, KCOV_INIT_TRACE, COVER_SIZE)) 
        perror("ioctl KCOV_INIT_TRACE"), exit(1);

    /* Mmap buffer shared between kernel- and user-space. */
    cover = (unsigned long*)mmap(NULL, COVER_SIZE * sizeof(unsigned long),
                                 PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if ((void*)cover == MAP_FAILED)
        perror("mmap"), exit(1);

    /* Enable coverage collection on the current thread. */
    if (ioctl(fd, KCOV_ENABLE, KCOV_TRACE_PC)) 
        perror("ioctl KCOV_ENABLE"), exit(1);

    /* Reset coverage from the tail of the ioctl() call. */
    __atomic_store_n(&cover[0], 0, __ATOMIC_RELAXED);


    /* Trigger coverage */
    do_something();

    /* Read the shared buffer*/
    process_buffer_to_stdout(cover);

    /* Disable coverage collection. After this call
     * coverage can be enabled for a different thread.
     */
    if (ioctl(fd, KCOV_DISABLE, 0)) 
        perror("ioctl KCOV_DISABLE"), exit(1);

    /* Free resources */
    if (munmap(cover, COVER_SIZE * sizeof(unsigned long)))
        perror("munmap"), exit(1);
    if (close(fd))
        perror("close"), exit(1);
    return 0;
}