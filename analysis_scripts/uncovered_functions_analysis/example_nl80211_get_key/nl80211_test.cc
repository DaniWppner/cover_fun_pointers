// Rename executor's main so we can define our own
#define main syz_executor_main
#include "executor/executor.cc"
#undef main

#define COVER_SIZE (64 << 10)
#define KCOV_TRACE_PC 0
#define KCOV_INIT_TRACE _IOR('c', 1, unsigned long)

// KCOV Constants are actually defined in Syzkaller's executor.cc as:
// KCOV_ENTRY_TYPE_HEADER_PC (0xdeadbeeffffffffeULL)
// KCOV_ENTRY_TYPE_HEADER_FUN_POINTER (0xdeadbeefffffffffULL)

void process_kcov_buffer(unsigned long *cover) {
    unsigned long n, i;

    /* Read number of consumed words. */
    n = __atomic_load_n(&cover[0], __ATOMIC_RELAXED);
    printf("[*] KCOV Buffer recorded %lu words of trace data.\n", n);
    
    FILE *fout_pcs = fopen("nl80211_test_PCs.cov", "w");
    FILE *fout_FPs = fopen("nl80211_test_FPs.cov", "w");
    if (!fout_pcs) {
        perror("[-] Failed to open nl80211_test_PCs.cov for writing");
        return;
    }
    if (!fout_FPs) {
        perror("[-] Failed to open nl80211_test_FPs.cov for writing");
        return;
    }    

    i = 1;
    while (i <= n) {
        unsigned long type = cover[i];

        if (type == KCOV_ENTRY_TYPE_HEADER_PC) {
            if (i + 1 > n) {
                fprintf(stderr, "[ERROR] Expected PC at position %lu after KCOV_ENTRY_TYPE_PC at position %lu but max size is %lu.\n", i + 1, i, n);
                break;
            }
            unsigned long pc = cover[i + 1];
            fprintf(fout_pcs, "0x%lx\n", pc);
            i += 2; 

        } else if (type == KCOV_ENTRY_TYPE_HEADER_FUN_POINTER) {
            if (i + 3 > n) {
                fprintf(stderr, "[ERROR]: Expected PC, STORE_ADDR, STORE_VALUE after KCOV_ENTRY_TYPE_FUN_POINTER at positions %lu, %lu, %lu but max size is %lu.\n", i + 1, i + 2, i + 3, n);
                break;
            }
            unsigned long pc = cover[i + 1];
            // store_addr is ignored for now
            // unsigned long store_addr = cover[i + 2];
            unsigned long stored_value = cover[i + 3];
            
            fprintf(fout_FPs, "0x%lx 0x%lx\n", 
                   pc, stored_value);
            
            i += 4;

        } else {
            // Unpatched kernels or standard PCs are written directly as words without headers if the patch isn't exactly applied this way,
            // but since GEMINI.md says the kernel was updated to use typed entries, we can assume the header exists.
            fprintf(stderr, "[ERROR] Unrecognized KCOV header 0x%lx at position %lu of %lu in shared buffer.\n", type, i, n);
            // If it's a raw PC, we just advance by 1
            i += 1;
        }
    }
    
    fclose(fout_pcs);
    fclose(fout_FPs);    
    printf("[+] PC coverage data written to nl80211_test_PCs.cov\n");
    printf("[+] Function Pointer coverage data written to nl80211_test_FPs.cov\n");
}

void trigger_nl80211_get_key(int sd, int family_id, unsigned int ifindex) {
    // Build the generic netlink message
    struct genlmsghdr genlhdr;
    memset(&genlhdr, 0, sizeof(genlhdr));
    genlhdr.cmd = NL80211_CMD_GET_KEY;
    genlhdr.version = 1;
    
    // Syzkaller's helper
    netlink_init(&nlmsg, family_id, 0, &genlhdr, sizeof(genlhdr));
    
    uint32_t index_data = ifindex;
    netlink_attr(&nlmsg, NL80211_ATTR_IFINDEX, &index_data, sizeof(index_data));

    printf("[*] Sending NL80211_CMD_GET_KEY request...\n");
    
    int err = netlink_send_ext(&nlmsg, sd, 0, NULL, false);
    
    if (err < 0) {
        struct nlmsghdr *nlh = (struct nlmsghdr*)nlmsg.buf;
        if (nlh->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *nlerr = (struct nlmsgerr *)NLMSG_DATA(nlh);
            printf("[+] Received expected kernel Netlink response! Error Code: %d (%s)\n", 
                   nlerr->error, strerror(-nlerr->error));
            if (nlerr->error == -EOPNOTSUPP) {
                printf("[+] SUCCESS! pre_doit passed and nl80211_get_key returned EOPNOTSUPP.\n");
            } else if (nlerr->error == -ENOENT) {
                printf("[+] SUCCESS! pre_doit passed and nl80211_get_key returned ENOENT.\n");
            } else if (nlerr->error == -EINVAL) {
                printf("[-] FAILED with EINVAL.\n");
            }
        } else {
            printf("[-] netlink_send_ext failed for unknown reasons.\n");
        }
    } else {
        printf("[+] netlink_send_ext succeeded without any kernel errors!\n");
    }
}

// Initialize syz-executor wifi devices and socket connection, etc.
// Return socket, family_id, interface index via input integer pointers
void setup_wifi(int *res_sd, int *res_family_id, int *res_ifindex) {
    printf("[*] Initializing wifi devices using syzkaller libraries...\n");
    initialize_wifi_devices();
    printf("[+] Done! Virtual wlan0 interface should now be UP and in IBSS mode.\n");
    int sd = socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC);
    if (sd < 0) fail("socket AF_NETLINK failed");

    int family_id = netlink_query_family_id(&nlmsg, sd, "nl80211", true);
    if (family_id < 0) fail("failed to resolve nl80211 family");

    int ifindex = if_nametoindex("wlan0");
    if (ifindex == 0) {
        fail("if_nametoindex failed. wlan0 does not exist! initialize_wifi_devices() must have failed.");
    }
    printf("[+] Target interface: wlan0 (index %u)\n", ifindex);
    *res_sd = sd;
    *res_family_id = family_id;
    *res_ifindex = ifindex;
}

int setup_kcov(unsigned long **cover) {
    int kcov_fd = open("/sys/kernel/debug/kcov", O_RDWR);
    if (kcov_fd == -1) {
        perror("[-] Failed to open /sys/kernel/debug/kcov");
        exit(1);
    }

    if (ioctl(kcov_fd, KCOV_INIT_TRACE, COVER_SIZE)) {
        perror("[-] ioctl KCOV_INIT_TRACE failed");
        exit(1);
    }

    *cover = (unsigned long*)mmap(NULL, COVER_SIZE * sizeof(unsigned long),
                                  PROT_READ | PROT_WRITE, MAP_SHARED, kcov_fd, 0);
    if ((void*)(*cover) == MAP_FAILED) {
        perror("[-] mmap kcov failed");
        exit(1);
    }

    if (ioctl(kcov_fd, KCOV_ENABLE, KCOV_TRACE_PC)) {
        perror("[-] ioctl KCOV_ENABLE failed");
        exit(1);
    }

    __atomic_store_n(&(*cover)[0], 0, __ATOMIC_RELAXED);
    return kcov_fd;
}

void process_kcov_result(int kcov_fd, unsigned long *cover) {
    if (ioctl(kcov_fd, KCOV_DISABLE, 0)) {
        perror("[-] ioctl KCOV_DISABLE failed");
        exit(1);
    }

    process_kcov_buffer(cover);

    if (munmap(cover, COVER_SIZE * sizeof(unsigned long)))
        perror("munmap");
    if (close(kcov_fd))
        perror("close kcov_fd");
}

int main(int argc, char** argv) {
    printf("[*] Starting standalone test inside executor context.\n");

    flag_wifi = true;
    flag_debug = true; 
    in_execute_one = false; 
    
    int sd, family_id, ifindex;
    setup_wifi(&sd, &family_id, &ifindex);


    unsigned long *cover;
    int kcov_fd = setup_kcov(&cover);

    trigger_nl80211_get_key(sd, family_id, ifindex);

    process_kcov_result(kcov_fd, cover);

    close(sd);
    return 0;
}
