{
    ("/home/linux/net/ipv4/ip_output.c:427", "ip_output"): {
        ("/home/linux/net/ipv4/route.c:1628", "ip_route_output_key_hash_rcu")
    },
    ("/home/linux/fs/libfs.c:1616", "kfree_link"): {
        ("/home/linux/fs/proc/self.c:26", "proc_self_get_link"),
        ("/home/linux/./include/linux/delayed_call.h:21", "set_delayed_call"),
        ("/home/linux/fs/proc/thread_self.c:26", "proc_thread_self_get_link"),
    },
    ("/home/linux/net/netlink/af_netlink.c:373", "netlink_skb_destructor"): {
        ("/home/linux/net/netlink/af_netlink.c:389", "netlink_broadcast_filtered"),
        ("/home/linux/net/netlink/af_netlink.c:389", "netlink_unicast"),
        ("/home/linux/net/netlink/af_netlink.c:389", "netlink_attachskb"),
        ("/home/linux/net/netlink/af_netlink.c:389", "netlink_dump"),
    },
    ("/home/linux/net/ipv4/tcp_output.c:1836", "tcp_sync_mss"): {
        ("/home/linux/net/ipv4/tcp.c:463", "tcp_init_sock")
    },
    ("/home/linux/net/core/sock.c:3345", "sock_def_readable"): {
        ("/home/linux/net/core/sock.c:3476", "sock_init_data_uid")
    },
    ("/home/linux/fs/fat/inode.c:185", "fat_get_block"): {
        ("/home/linux/fs/mpage.c:372", "mpage_readahead")
    },
    ("/home/linux/mm/filemap.c:1115", "wake_page_function"): {
        ("/home/linux/mm/filemap.c:1247", "folio_wait_bit_common")
    },
    ("/home/linux/net/wireless/nl80211.c:16397", "nl80211_pre_doit"): {
        ("/home/linux/net/netlink/genetlink.c:275", "genl_op_iter_next"),
        ("/home/linux/net/netlink/genetlink.c:275", "genl_get_cmd"),
    },
    ("/home/linux/net/core/sock.c:2460", "sock_wfree"): {
        ("/home/linux/net/core/sock.c:2516", "skb_set_owner_w")
    },
    ("/home/linux/net/netlink/genetlink.c:698", "genl_release"): {
        ("/home/linux/net/netlink/af_netlink.c:718", "netlink_create")
    },
    ("/home/linux/fs/namespace.c:1273", "__cleanup_mnt"): {
        ("/home/linux/./include/linux/task_work.h:13", "init_task_work"),
        ("/home/linux/fs/namespace.c:1345", "mntput_no_expire"),
    },
    ("/home/linux/net/ipv4/af_inet.c:135", "inet_sock_destruct"): {
        ("/home/linux/net/ipv4/af_inet.c:357", "inet_create")
    },
    ("/home/linux/net/netfilter/nf_conntrack_netlink.c:1054", "ctnetlink_start"): {
        (
            "/home/linux/net/netfilter/nf_conntrack_netlink.c:1664",
            "ctnetlink_get_conntrack",
        )
    },
    ("/home/linux/net/ipv4/ip_output.c:317", "ip_finish_output"): {
        ("/home/linux/./include/linux/netfilter.h:172", "nf_hook")
    },
    ("/home/linux/fs/select.c:224", "__pollwait"): {
        ("/home/linux/./include/linux/poll.h:71", "do_sys_poll")
    },
    ("/home/linux/block/fops.c:404", "blkdev_get_block"): {
        ("/home/linux/fs/mpage.c:372", "mpage_readahead")
    },
    ("/home/linux/net/core/neighbour.c:1546", "neigh_resolve_output"): {
        ("/home/linux/net/ipv4/arp.c:287", "arp_constructor")
    },
    ("/home/linux/mm/workingset.c:627", "workingset_update_node"): {
        ("/home/linux/mm/filemap.c:232", "__filemap_remove_folio"),
        ("/home/linux/./include/linux/xarray.h:1679", "xas_set_update"),
        ("/home/linux/mm/filemap.c:294", "page_cache_delete_batch"),
        ("/home/linux/mm/filemap.c:343", "delete_from_page_cache_batch"),
        ("/home/linux/mm/filemap.c:862", "__filemap_add_folio"),
        ("/home/linux/mm/filemap.c:142", "page_cache_delete"),
        ("/home/linux/mm/filemap.c:132", "mapping_set_update"),
    },
    ("/home/linux/kernel/groups.c:77", "gid_cmp"): {
        ("/home/linux/lib/sort.c:295", "sort")
    },
    ("/home/linux/fs/isofs/inode.c:1120", "isofs_get_block"): {
        ("/home/linux/fs/mpage.c:372", "mpage_readahead")
    },
    ("/home/linux/net/core/sock.c:3333", "sock_def_error_report"): {
        ("/home/linux/net/core/sock.c:3478", "sock_init_data_uid")
    },
    ("/home/linux/fs/readdir.c:352", "filldir64"): {
        ("/home/linux/fs/readdir.c:399", "__se_sys_getdents64")
    },
    ("/home/linux/security/keys/keyring.c:567", "key_default_cmp"): {
        ("/home/linux/security/keys/request_key.c:589", "request_key_and_link"),
        ("/home/linux/security/keys/keyring.c:947", "keyring_search"),
    },
    ("/home/linux/drivers/base/core.c:3119", "klist_children_put"): {
        ("/home/linux/lib/klist.c:90", "klist_init")
    },
    ("/home/linux/security/keys/request_key.c:91", "umh_keys_cleanup"): {
        ("/home/linux/kernel/umh.c:377", "call_usermodehelper_setup")
    },
    ("/home/linux/fs/buffer.c:1520", "invalidate_bh_lru"): {
        ("/home/linux/kernel/smp.c:816", "smp_call_function_many_cond")
    },
    ("/home/linux/security/keys/keyring.c:575", "keyring_search_iterator"): {
        ("/home/linux/security/keys/keyring.c:905", "keyring_search_rcu")
    },
    ("/home/linux/net/netfilter/nf_conntrack_netlink.c:1192", "ctnetlink_dump_table"): {
        ("/home/linux/net/netlink/af_netlink.c:2432", "__netlink_dump_start"),
        (
            "/home/linux/net/netfilter/nf_conntrack_netlink.c:1664",
            "ctnetlink_get_conntrack",
        ),
    },
    ("/home/linux/./include/net/dst.h:449", "dst_output"): {
        ("/home/linux/./include/linux/netfilter.h:172", "nf_hook")
    },
    ("/home/linux/net/core/sock.c:3322", "sock_def_wakeup"): {
        ("/home/linux/net/core/sock.c:3475", "sock_init_data_uid")
    },
    ("/home/linux/kernel/module/kmod.c:67", "free_modprobe_argv"): {
        ("/home/linux/kernel/umh.c:377", "call_usermodehelper_setup")
    },
    ("/home/linux/net/ipv4/tcp_output.c:1189", "tcp_wfree"): {
        ("/home/linux/net/ipv4/tcp_output.c:1373", "__tcp_transmit_skb")
    },
    ("/home/linux/net/ipv4/tcp_ipv4.c:1889", "tcp_v4_do_rcv"): {
        ("/home/linux/net/ipv4/af_inet.c:359", "inet_create")
    },
    ("/home/linux/fs/file_table.c:449", "____fput"): {
        ("/home/linux/./include/linux/task_work.h:13", "init_task_work"),
        ("/home/linux/fs/file_table.c:481", "fput"),
    },
    ("/home/linux/drivers/base/core.c:3111", "klist_children_get"): {
        ("/home/linux/lib/klist.c:89", "klist_init")
    },
    ("/home/linux/./include/linux/jhash.h:71", "jhash"): {
        ("/home/linux/lib/rhashtable.c:1058", "rhashtable_init_noprof")
    },
}
