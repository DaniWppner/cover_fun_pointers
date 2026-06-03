## Repro results
This is obtained by running `check_stable_coverage.py` on [`extracted_jsonlines.json`](extracted_jsonlines.json)

### uncovered functions

| Function Name                      | File Location                            | Store Function Name(s)         | Store Location(s)                         | Column 4 | "current" changes when called? |
| ---------------------------------- | ---------------------------------------- | ------------------------------ | ----------------------------------------- | -------- | ----------------------- |
| __per_cpu_start                    | arch/x86/kernel/cpu/common.c:2012        | clear_delayed_call             | ./include/linux/delayed_call.h:33         |          |          |
|                                    |                                          | clear_delayed_call             | ./include/linux/delayed_call.h:?          |          |          |
|                                    |                                          | loopback_xmit                  | ./include/linux/skbuff.h:3212             |          |          |
|                                    |                                          | blk_insert_flush               | block/blk-flush.c:390                     |          |          |
|                                    |                                          | evict                          | fs/inode.c:315                            |          |          |
|                                    |                                          | pick_link                      | fs/namei.c:1771                           |          |          |
|                                    |                                          | drop_links                     | fs/namei.c:669                            |          |          |
|                                    |                                          | terminate_walk                 | fs/namei.c:682                            |          |          |
|                                    |                                          | do_sys_poll                    | fs/select.c:?                             |          |          |
|                                    |                                          | flush_signal_handlers          | kernel/signal.c:538                       |          |          |
|                                    |                                          | init_timer_key                 | kernel/time/timer.c:900                   |          |          |
|                                    |                                          | call_usermodehelper_setup      | kernel/umh.c:378                          |          |          |
|                                    |                                          | percpu_ref_init                | lib/percpu-refcount.c:101                 |          |          |
|                                    |                                          | sort                           | lib/sort.c:295                            |          |          |
|                                    |                                          | bpf_prepare_filter             | net/core/filter.c:1325                    |          |          |
|                                    |                                          | __skb_clone                    | net/core/skbuff.c:1567                    |          |          |
|                                    |                                          | inet_create                    | net/ipv4/af_inet.c:359                    |          |          |
|                                    |                                          | inet6_create                   | net/ipv6/af_inet6.c:219                   |          |          |
|                                    |                                          | netlink_create                 | net/netlink/af_netlink.c:716              |          |          |
|                                    |                                          | netlink_create                 | net/netlink/af_netlink.c:717              |          |          |
|                                    |                                          | netlink_create                 | net/netlink/af_netlink.c:718              |          |          |
|                                    |                                          | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:271               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:273               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:275               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:277               |          |          |
|                                    |                                          | keyring_search                 | security/keys/keyring.c:942               |          |          |
|                                    |                                          | request_key_and_link           | security/keys/request_key.c:583           |          |          |
| ata_scsi_qc_complete               | drivers/ata/libata-scsi.c:1632           | __ata_scsi_queuecmd            | drivers/ata/libata-scsi.c:1709            |          |    No    |
| atapi_qc_complete                  | drivers/ata/libata-scsi.c:2586           | atapi_xlat                     | drivers/ata/libata-scsi.c:2651            |          |    No    |
| audit_multicast_bind               | kernel/audit.c:1631                      | netlink_create                 | net/netlink/af_netlink.c:716              |          |    No    |
| audit_multicast_unbind             | kernel/audit.c:1641                      | netlink_create                 | net/netlink/af_netlink.c:717              |          |    No    |
| autoremove_wake_function           | kernel/sched/wait.c:383                  | bd_prepare_to_claim            | block/bdev.c:552                          |          |    Yes (autoremove_wake_function is used for scheduling)   |
|                                    |                                          | blk_mq_get_tag                 | block/blk-mq-tag.c:138                    |          |    ---   |
|                                    |                                          | device_cache_fw_images         | drivers/base/firmware_loader/main.c:1474  |          |    ---   |
|                                    |                                          | fw_pm_notify                   | drivers/base/firmware_loader/main.c:1536  |          |    ---   |
|                                    |                                          | unix_stream_read_generic       | net/unix/af_unix.c:2517                   |          |    ---   |
| bdev_free_inode                    | block/bdev.c:331                         | evict                          | fs/inode.c:315                            |          |    Yes   |
| bio_copy_kern_endio_read           | block/blk-map.c:450                      | blk_rq_map_kern                | block/blk-map.c:518                       |          |    No    |
| blk_end_sync_rq                    | block/blk-mq.c:1352                      | blk_execute_rq                 | block/blk-mq.c:1399                       |          |    Yes  (is call_rcu macro)  |
| blkg_release                       | block/blk-cgroup.c:201                   | percpu_ref_init                | lib/percpu-refcount.c:100                 |          |    Maybe (can get called during percpu_ref_kill)   |
| bpf_prog_free_deferred             | kernel/bpf/core.c:2768                   | bpf_prog_free                  | kernel/bpf/core.c:2813                    |          |    Yes  (is INIT_WORK macro)    |
| call_usermodehelper_exec_work      | kernel/umh.c:159                         | call_usermodehelper_setup      | kernel/umh.c:367                          |          |    Yes  (is INIT_WORK macro)    |
| cgwb_release                       | mm/backing-dev.c:640                     | percpu_ref_init                | lib/percpu-refcount.c:100                 |          |    Maybe (can get called during percpu_ref_kill)   |
| cgwb_release_workfn                | mm/backing-dev.c:612                     | wb_get_create                  | mm/backing-dev.c:712                      |          |    Yes  (is INIT_WORK macro)    |
| ctnetlink_done                     | net/netfilter/nf_conntrack_netlink.c:865 | ctnetlink_get_conntrack        | net/netfilter/nf_conntrack_netlink.c:1664 |          |    No    |
|                                    |                                          | __netlink_dump_start           | net/netlink/af_netlink.c:2433             |          |    No    |
| default_wake_function              | kernel/sched/core.c:7080                 | netlink_table_grab             | net/netlink/af_netlink.c:439              |          |    Yes (default_wake_function is used for scheduling)  |
| delayed_work_timer_fn              | kernel/workqueue.c:2502                  | init_timer_key                 | kernel/time/timer.c:900                   |          |    Yes (is part of the worqueue API)  |
| device_create_release              | drivers/base/core.c:4336                 | device_create                  | drivers/base/core.c:4364                  |          |    No    |
| do_SAK_work                        | drivers/tty/tty_io.c:3074                | alloc_tty_struct               | drivers/tty/tty_io.c:3140                 |          |    Yes  (is INIT_WORK macro)   |
| do_no_restart_syscall              | kernel/signal.c:3057                     | __do_sys_rt_sigreturn          | arch/x86/kernel/signal_64.c:57            |          |    Maybe (is related to interrupts)   |
|                                    |                                          | __x64_sys_nanosleep            | kernel/time/hrtimer.c:2115                |          |    ---   |
|                                    |                                          | __se_sys_clock_nanosleep       | kernel/time/posix-timers.c:1392           |          |    ---   |
| do_tty_hangup                      | drivers/tty/tty_io.c:668                 | alloc_tty_struct               | drivers/tty/tty_io.c:3134                 |          |    Yes  (is INIT_WORK macro)   |
| dst_discard                        | net/core/dst.c:31                        |                                |                                           |          |    Yes  (is INIT_WORK macro)   |
| dst_discard_out                    | net/core/dst.c:31                        | dst_alloc                      | net/core/dst.c:60                         |          |    No    |
| end_bio_bh_io_sync                 | fs/buffer.c:2773                         | submit_bh_wbc                  | fs/buffer.c:2816                          |          |    No    |
| end_buffer_async_read_io           | fs/buffer.c:348                          | block_read_full_folio          | fs/buffer.c:442                           |          |    Maybe (has to do with async_read)  |
| end_buffer_async_write             | fs/buffer.c:379                          | __block_write_full_folio       | fs/buffer.c:1898                          |          |    Maybe (has to do with async_write) |
|                                    |                                          | mark_buffer_async_write_endio  | fs/buffer.c:449                           |          |    ---   |
| end_buffer_read_sync               | fs/buffer.c:159                          | __bread_gfp                    | fs/buffer.c:1275                          |          |    Maybe (wait_on_buffer gets called right after)   |
|                                    |                                          | __bh_read                      | fs/buffer.c:3100                          |          |    Maybe (on wait=false seems to be async)|
|                                    |                                          | __block_write_begin_int        | fs/buffer.c:3100                          |          |    ---   |
|                                    |                                          | __breadahead                   | fs/buffer.c:3100                          |          |    ---   |
|                                    |                                          | __ext4_read_bh                 | fs/ext4/super.c:173                       |          |    ---   |
|                                    |                                          | ext4_read_bh_nowait            | fs/ext4/super.c:187                       |          |    ---   |
|                                    |                                          | ext4_read_bh                   | fs/ext4/super.c:199                       |          |    ---   |
| end_buffer_write_sync              | fs/buffer.c:166                          | __sync_dirty_buffer            | fs/buffer.c:2869                          |          |    Maybe (wait_on_buffer gets called right after)   |
|                                    |                                          | write_mmp_block_thawed         | fs/ext4/mmp.c:49                          |          |    ---   |
|                                    |                                          | ext4_commit_super              | fs/ext4/super.c:6178                      |          |    Maybe (wait_on_buffer gets called right after)   |
| ethnl_act_cable_test               | net/ethtool/cabletest.c:57               | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |    No    |
| ethnl_act_cable_test_tdr           | net/ethtool/cabletest.c:308              | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |    No    |
| ethnl_default_doit                 | net/ethtool/netlink.c:371                | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |    No    |
| ethnl_default_done                 | net/ethtool/netlink.c:566                | genl_op_iter_next              | net/netlink/genetlink.c:273               |          |    No    |
| ethnl_default_dumpit               | net/ethtool/netlink.c:483                | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |    No    |
| ethnl_default_set_doit             | net/ethtool/netlink.c:576                | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |    No    |
| ethnl_default_start                | net/ethtool/netlink.c:513                | genl_op_iter_next              | net/netlink/genetlink.c:271               |          |    No    |
| ethnl_set_features                 | net/ethtool/features.c:211               | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |    No    |
| ethnl_tunnel_info_doit             | net/ethtool/tunnels.c:166                | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |    No    |
| ethnl_tunnel_info_dumpit           | net/ethtool/tunnels.c:242                | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |    No    |
| ethnl_tunnel_info_start            | net/ethtool/tunnels.c:219                | genl_op_iter_next              | net/netlink/genetlink.c:271               |          |    No    |
| ext4_discard_work                  | fs/ext4/mballoc.c:3541                   | ext4_mb_init                   | fs/ext4/mballoc.c:3676                    |          |    Yes  (is INIT_WORK macro)  |
| ext4_end_bitmap_read               | fs/ext4/ialloc.c:70                      | __ext4_read_bh                 | fs/ext4/super.c:173                       |          |          |
|                                    |                                          | ext4_read_bh_nowait            | fs/ext4/super.c:187                       |          |          |
|                                    |                                          | ext4_read_bh                   | fs/ext4/super.c:199                       |          |          |
| ext4_end_io_rsv_work               | fs/ext4/page-io.c:269                    | ext4_alloc_inode               | fs/ext4/super.c:1421                      |          |          |
| ext4_es_count                      | fs/ext4/extents_status.c:1631            | ext4_es_register_shrinker      | fs/ext4/extents_status.c:1735             |          |          |
| ext4_es_scan                       | fs/ext4/extents_status.c:1643            | ext4_es_register_shrinker      | fs/ext4/extents_status.c:1734             |          |          |
| ext4_fc_info_show                  | fs/ext4/fast_commit.c:2269               | proc_create_single_data        | fs/proc/generic.c:656                     |          |          |
| ext4_free_in_core_inode            | fs/ext4/super.c:1439                     | evict                          | fs/inode.c:315                            |          |          |
| ext4_lazyinit_thread               | fs/ext4/super.c:3777                     | __kthread_create_on_node       | kernel/kthread.c:441                      |          |          |
| ext4_orphan_file_block_trigger     | fs/ext4/orphan.c:555                     | ext4_setup_csum_trigger        | fs/ext4/super.c:4288                      |          |          |
|                                    |                                          | ext4_init_metadata_csum        | fs/ext4/super.c:4599                      |          |          |
|                                    |                                          | __ext4_fill_super              | fs/ext4/super.c:5207                      |          |          |
|                                    |                                          | ext4_fill_super                | fs/ext4/super.c:5676                      |          |          |
| ext4_seq_es_shrinker_info_show     | fs/ext4/extents_status.c:1659            | proc_create_single_data        | fs/proc/generic.c:656                     |          |          |
| ext4_seq_mb_stats_show             | fs/ext4/mballoc.c:3095                   | proc_create_single_data        | fs/proc/generic.c:656                     |          |          |
| ext4_seq_options_show              | fs/ext4/super.c:3052                     | proc_create_single_data        | fs/proc/generic.c:656                     |          |          |
| fat_free_inode                     | fs/fat/inode.c:768                       | evict                          | fs/inode.c:315                            |          |          |
| flush_end_io                       | block/blk-flush.c:220                    | blk_flush_complete_seq         | block/blk-flush.c:337                     |          |          |
| flush_tlb_func                     | arch/x86/mm/tlb.c:741                    | smp_call_function_many_cond    | kernel/smp.c:816                          |          |          |
| flush_to_ldisc                     | drivers/tty/tty_buffer.c:463             | tty_buffer_init                | drivers/tty/tty_buffer.c:587              |          |          |
| free_ioctx_reqs                    | fs/aio.c:639                             | percpu_ref_init                | lib/percpu-refcount.c:100                 |          |          |
| free_ioctx_users                   | fs/aio.c:657                             | percpu_ref_init                | lib/percpu-refcount.c:100                 |          |          |
| genl_bind                          | net/netlink/genetlink.c:1817             | netlink_create                 | net/netlink/af_netlink.c:716              |          |          |
| genl_unbind                        | net/netlink/genetlink.c:1854             | netlink_create                 | net/netlink/af_netlink.c:717              |          |          |
| hrtimer_wakeup                     | kernel/time/hrtimer.c:1918               | hrtimer_init_sleeper_on_stack  | ./include/linux/hrtimer.h:254             |          |          |
|                                    |                                          | __hrtimer_init_sleeper         | kernel/time/hrtimer.c:1983                |          |          |
|                                    |                                          | hrtimer_init_sleeper           | kernel/time/hrtimer.c:1997                |          |          |
|                                    |                                          | hrtimer_nanosleep              | kernel/time/hrtimer.c:2081                |          |          |
|                                    |                                          | schedule_hrtimeout_range_clock | kernel/time/hrtimer.c:2286                |          |          |
| inet6_sock_destruct                | net/ipv6/af_inet6.c:114                  | inet6_create                   | net/ipv6/af_inet6.c:215                   |          |          |
| invalid_mkclean_vma                | mm/rmap.c:1076                           | folio_mkclean                  | mm/rmap.c:1087                            |          |          |
| io_fallback_req_func               | io_uring/io_uring.c:244                  | io_ring_ctx_alloc              | io_uring/io_uring.c:341                   |          |          |
| io_ring_ctx_ref_free               | io_uring/io_uring.c:237                  | percpu_ref_init                | lib/percpu-refcount.c:100                 |          |          |
| io_ring_exit_work                  | io_uring/io_uring.c:2793                 | io_ring_ctx_wait_and_kill      | io_uring/io_uring.c:2900                  |          |          |
| io_sq_thread                       | io_uring/sqpoll.c:270                    | create_io_thread               | kernel/fork.c:2735                        |          |          |
| io_wq_free_work                    | io_uring/io_uring.c:1787                 | io_wq_create                   | io_uring/io-wq.c:1158                     |          |          |
|                                    |                                          | io_uring_alloc_task_context    | io_uring/tctx.c:38                        |          |          |
| io_wq_hash_wake                    | io_uring/io-wq.c:1125                    | io_wq_create                   | io_uring/io-wq.c:1170                     |          |          |
| io_wq_submit_work                  | io_uring/io_uring.c:1800                 | io_wq_create                   | io_uring/io-wq.c:1159                     |          |          |
|                                    |                                          | io_uring_alloc_task_context    | io_uring/tctx.c:39                        |          |          |
| ip_local_deliver                   | net/ipv4/ip_input.c:243                  | ip_route_output_key_hash_rcu   | net/ipv4/route.c:1630                     |          |          |
| isofs_free_inode                   | fs/isofs/inode.c:81                      | evict                          | fs/inode.c:315                            |          |          |
| it_real_fn                         | kernel/time/itimer.c:157                 | copy_signal                    | kernel/fork.c:1882                        |          |          |
| kmmpd                              | fs/ext4/mmp.c:137                        | __kthread_create_on_node       | kernel/kthread.c:441                      |          |          |
| loop_workfn                        | drivers/block/loop.c:1986                | loop_queue_rq                  | drivers/block/loop.c:883                  |          |          |
| lru_add_drain_per_cpu              | mm/swap.c:791                            | __lru_add_drain_all            | mm/swap.c:895                             |          |          |
| mb_cache_count                     | fs/mbcache.c:295                         | mb_cache_create                | fs/mbcache.c:385                          |          |          |
| mb_cache_scan                      | fs/mbcache.c:334                         | mb_cache_create                | fs/mbcache.c:386                          |          |          |
| mb_cache_shrink_worker             | fs/mbcache.c:343                         | mb_cache_create                | fs/mbcache.c:391                          |          |          |
| migration_cpu_stop                 | kernel/sched/core.c:2583                 | stop_one_cpu                   | kernel/stop_machine.c:142                 |          |          |
| mon_bin_complete                   | drivers/usb/mon/mon_bin.c:630            | mon_bin_open                   | drivers/usb/mon/mon_bin.c:718             |          |          |
| mon_bin_error                      | drivers/usb/mon/mon_bin.c:636            | mon_bin_open                   | drivers/usb/mon/mon_bin.c:717             |          |          |
| mon_bin_submit                     | drivers/usb/mon/mon_bin.c:624            | mon_bin_open                   | drivers/usb/mon/mon_bin.c:716             |          |          |
| mpage_end_io                       | fs/ext4/readpage.c:163                   | ext4_mpage_readpages           | fs/ext4/readpage.c:359                    |          |          |
| mpage_read_end_io                  | fs/mpage.c:47                            | do_mpage_readpage              | fs/mpage.c:314                            |          |          |
|                                    |                                          | mpage_readahead                | fs/mpage.c:384                            |          |          |
|                                    |                                          | mpage_bio_submit_read          | fs/mpage.c:80                             |          |          |
| mq_flush_data_end_io               | block/blk-flush.c:356                    | blk_insert_flush               | block/blk-flush.c:391                     |          |          |
| neigh_blackhole                    | net/core/neighbour.c:93                  | ___neigh_create                | net/core/neighbour.c:503                  |          |          |
| neigh_timer_handler                | net/core/neighbour.c:1085                | init_timer_key                 | kernel/time/timer.c:900                   |          |          |
| netlbl_calipso_add                 | net/netlabel/netlabel_calipso.c:121      | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_calipso_list                | net/netlabel/netlabel_calipso.c:156      | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_calipso_listall             | net/netlabel/netlabel_calipso.c:257      | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| netlbl_calipso_remove              | net/netlabel/netlabel_calipso.c:305      | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_cipsov4_add                 | net/netlabel/netlabel_cipso_v4.c:405     | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_cipsov4_list                | net/netlabel/netlabel_cipso_v4.c:449     | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_cipsov4_listall             | net/netlabel/netlabel_cipso_v4.c:654     | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| netlbl_cipsov4_remove              | net/netlabel/netlabel_cipso_v4.c:702     | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_unlabel_accept              | net/netlabel/netlabel_unlabeled.c:808    | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_unlabel_list                | net/netlabel/netlabel_unlabeled.c:835    | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_unlabel_staticadd           | net/netlabel/netlabel_unlabeled.c:877    | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_unlabel_staticadddef        | net/netlabel/netlabel_unlabeled.c:929    | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_unlabel_staticlist          | net/netlabel/netlabel_unlabeled.c:1163   | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| netlbl_unlabel_staticlistdef       | net/netlabel/netlabel_unlabeled.c:1253   | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| netlbl_unlabel_staticremove        | net/netlabel/netlabel_unlabeled.c:978    | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlbl_unlabel_staticremovedef     | net/netlabel/netlabel_unlabeled.c:1020   | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| netlink_sock_destruct              | net/netlink/af_netlink.c:395             | __netlink_create               | net/netlink/af_netlink.c:661              |          |          |
| nfnetlink_bind                     | net/netfilter/nfnetlink.c:706            | netlink_create                 | net/netlink/af_netlink.c:716              |          |          |
| nfnetlink_unbind                   | net/netfilter/nfnetlink.c:726            | netlink_create                 | net/netlink/af_netlink.c:717              |          |          |
| nl80211_abort_scan                 | net/wireless/nl80211.c:9403              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_add_link                   | net/wireless/nl80211.c:16075             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_add_link_station           | net/wireless/nl80211.c:16224             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_add_tx_ts                  | net/wireless/nl80211.c:15308             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_associate                  | net/wireless/nl80211.c:10927             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_authenticate               | net/wireless/nl80211.c:10610             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_cancel_remain_on_channel   | net/wireless/nl80211.c:12454             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_channel_switch             | net/wireless/nl80211.c:10095             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_color_change               | net/wireless/nl80211.c:15947             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_connect                    | net/wireless/nl80211.c:11807             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_crit_protocol_start        | net/wireless/nl80211.c:14860             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_crit_protocol_stop         | net/wireless/nl80211.c:14899             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_deauthenticate             | net/wireless/nl80211.c:11234             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_del_interface              | net/wireless/nl80211.c:4363              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_del_key                    | net/wireless/nl80211.c:4768              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_del_mpath                  | net/wireless/nl80211.c:7905              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_del_pmk                    | net/wireless/nl80211.c:15520             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_del_pmksa                  | net/wireless/nl80211.c:12240             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_del_station                | net/wireless/nl80211.c:7635              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_del_tx_ts                  | net/wireless/nl80211.c:15358             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_disassociate               | net/wireless/nl80211.c:11279             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_disconnect                 | net/wireless/nl80211.c:12129             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_dump_interface             | net/wireless/nl80211.c:3968              | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_dump_mpath                 | net/wireless/nl80211.c:7764              | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_dump_mpp                   | net/wireless/nl80211.c:7964              | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_dump_scan                  | net/wireless/nl80211.c:10404             | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_dump_station               | net/wireless/nl80211.c:6767              | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_dump_survey                | net/wireless/nl80211.c:10544             | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_dump_wiphy                 | net/wireless/nl80211.c:3070              | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_dump_wiphy_done            | net/wireless/nl80211.c:3146              | genl_op_iter_next              | net/netlink/genetlink.c:273               |          |          |
| nl80211_external_auth              | net/wireless/nl80211.c:15542             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_flush_pmksa                | net/wireless/nl80211.c:12292             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_coalesce               | net/wireless/nl80211.c:13840             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_ftm_responder_stats    | net/wireless/nl80211.c:15649             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_interface              | net/wireless/nl80211.c:4047              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_key                    | net/wireless/nl80211.c:4495              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_mesh_config            | net/wireless/nl80211.c:8137              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_mpath                  | net/wireless/nl80211.c:7815              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_mpp                    | net/wireless/nl80211.c:7923              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_power_save             | net/wireless/nl80211.c:12743             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_protocol_features      | net/wireless/nl80211.c:14812             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_reg_do                 | net/wireless/nl80211.c:8609              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_reg_dump               | net/wireless/nl80211.c:8722              | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_get_station                | net/wireless/nl80211.c:6820              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_wiphy                  | net/wireless/nl80211.c:3152              | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_get_wowlan                 | net/wireless/nl80211.c:13325             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_join_ibss                  | net/wireless/nl80211.c:11352             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_join_mesh                  | net/wireless/nl80211.c:13028             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_join_ocb                   | net/wireless/nl80211.c:13006             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_leave_ibss                 | net/wireless/nl80211.c:11508             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_leave_mesh                 | net/wireless/nl80211.c:13149             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_leave_ocb                  | net/wireless/nl80211.c:13020             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_modify_link_station        | net/wireless/nl80211.c:16230             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_nan_add_func               | net/wireless/nl80211.c:14369             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_nan_change_config          | net/wireless/nl80211.c:14630             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_nan_del_func               | net/wireless/nl80211.c:14607             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_new_interface              | net/wireless/nl80211.c:4348              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_new_key                    | net/wireless/nl80211.c:4699              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_new_mpath                  | net/wireless/nl80211.c:7880              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_new_station                | net/wireless/nl80211.c:7349              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_notify_radar_detection     | net/wireless/nl80211.c:10006             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_pmsr_start                 | net/wireless/pmsr.c:261                  | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_post_doit                  | net/wireless/nl80211.c:16499             | genl_get_cmd                   | net/netlink/genetlink.c:277               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:277               |          |          |
| nl80211_probe_client               | net/wireless/nl80211.c:14117             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_probe_mesh_link            | net/wireless/nl80211.c:15746             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_register_beacons           | net/wireless/nl80211.c:14170             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_register_mgmt              | net/wireless/nl80211.c:12492             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_register_unexpected_frame  | net/wireless/nl80211.c:14100             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_reload_regdb               | net/wireless/nl80211.c:8131              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_remain_on_channel          | net/wireless/nl80211.c:12368             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_remove_link                | net/wireless/nl80211.c:16110             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_remove_link_station        | net/wireless/nl80211.c:16236             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_req_set_reg                | net/wireless/nl80211.c:8085              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_beacon                 | net/wireless/nl80211.c:6233              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_bss                    | net/wireless/nl80211.c:8015              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_channel                | net/wireless/nl80211.c:3443              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_coalesce               | net/wireless/nl80211.c:13980             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_cqm                    | net/wireless/nl80211.c:12963             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_fils_aad               | net/wireless/nl80211.c:16053             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_hw_timestamp           | net/wireless/nl80211.c:16256             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_interface              | net/wireless/nl80211.c:4186              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_key                    | net/wireless/nl80211.c:4592              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_mac_acl                | net/wireless/nl80211.c:4895              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_mcast_rate             | net/wireless/nl80211.c:11522             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_mpath                  | net/wireless/nl80211.c:7855              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_multicast_to_unicast   | net/wireless/nl80211.c:15461             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_noack_map              | net/wireless/nl80211.c:4399              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_pmk                    | net/wireless/nl80211.c:15482             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_pmksa                  | net/wireless/nl80211.c:12185             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_power_save             | net/wireless/nl80211.c:12713             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_qos_map                | net/wireless/nl80211.c:15261             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_reg                    | net/wireless/nl80211.c:8814              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_rekey_data             | net/wireless/nl80211.c:14050             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_sar_specs              | net/wireless/nl80211.c:16570             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_station                | net/wireless/nl80211.c:7190              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_tid_config             | net/wireless/nl80211.c:15891             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_ttlm                   | net/wireless/nl80211.c:16279             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_tx_bitrate_mask        | net/wireless/nl80211.c:12472             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_wiphy                  | net/wireless/nl80211.c:3452              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_set_wowlan                 | net/wireless/nl80211.c:13578             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_start_ap                   | net/wireless/nl80211.c:5929              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_start_nan                  | net/wireless/nl80211.c:14248             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_start_p2p_device           | net/wireless/nl80211.c:14204             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_start_radar_detection      | net/wireless/nl80211.c:9924              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_start_sched_scan           | net/wireless/nl80211.c:9845              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_stop_ap                    | net/wireless/nl80211.c:6287              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_stop_nan                   | net/wireless/nl80211.c:14292             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_stop_p2p_device            | net/wireless/nl80211.c:14232             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_stop_sched_scan            | net/wireless/nl80211.c:9898              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_tdls_cancel_channel_switch | net/wireless/nl80211.c:15431             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_tdls_channel_switch        | net/wireless/nl80211.c:15375             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_tdls_mgmt                  | net/wireless/nl80211.c:12307             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_tdls_oper                  | net/wireless/nl80211.c:12346             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_trigger_scan               | net/wireless/nl80211.c:9160              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_tx_control_port            | net/wireless/nl80211.c:15584             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_tx_mgmt                    | net/wireless/nl80211.c:12542             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_tx_mgmt_cancel_wait        | net/wireless/nl80211.c:12678             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_get_cmd                   | net/netlink/genetlink.c:276               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_update_connect_params      | net/wireless/nl80211.c:12054             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_update_ft_ies              | net/wireless/nl80211.c:14838             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_update_mesh_config         | net/wireless/nl80211.c:8515              | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_update_owe_info            | net/wireless/nl80211.c:15721             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_vendor_cmd                 | net/wireless/nl80211.c:14936             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| nl80211_vendor_cmd_dump            | net/wireless/nl80211.c:15128             | genl_op_from_small             | net/netlink/genetlink.c:188               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| nl80211_wiphy_netns                | net/wireless/nl80211.c:12154             | genl_op_from_small             | net/netlink/genetlink.c:187               |          |          |
|                                    |                                          | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| page_mkclean_one                   | mm/rmap.c:1066                           | folio_mkclean                  | mm/rmap.c:1087                            |          |          |
| percpu_ref_noop_confirm_switch     | lib/percpu-refcount.c:210                | __percpu_ref_switch_to_atomic  | lib/percpu-refcount.c:229                 |          |          |
|                                    |                                          | __percpu_ref_switch_mode       | lib/percpu-refcount.c:281                 |          |          |
| ping_queue_rcv_skb                 | net/ipv4/ping.c:957                      | inet_create                    | net/ipv4/af_inet.c:359                    |          |          |
|                                    |                                          | inet6_create                   | net/ipv6/af_inet6.c:219                   |          |          |
| pm_runtime_work                    | drivers/base/power/runtime.c:953         | pm_runtime_init                | drivers/base/power/runtime.c:1764         |          |          |
| pm_suspend_timer_fn                | drivers/base/power/runtime.c:994         | pm_runtime_init                | drivers/base/power/runtime.c:1768         |          |          |
| pollwake                           | fs/select.c:212                          | __pollwait                     | ./include/linux/wait.h:92                 |          |          |
| posix_cpu_timers_work              | kernel/time/posix-cpu-timers.c:1165      | init_task_work                 | ./include/linux/task_work.h:13            |          |          |
|                                    |                                          | clear_posix_cputimers_work     | kernel/time/posix-cpu-timers.c:1222       |          |          |
| print_daily_error_info             | fs/ext4/super.c:3638                     | init_timer_key                 | kernel/time/timer.c:900                   |          |          |
| proc_single_show                   | fs/proc/base.c:767                       | single_open                    | fs/seq_file.c:582                         |          |          |
| process_timeout                    | kernel/time/timer.c:2505                 | schedule_timeout               | kernel/time/timer.c:900                   |          |          |
| pwq_release_workfn                 | kernel/workqueue.c:5052                  | init_pwq                       | kernel/workqueue.c:5120                   |          |          |
| raw_rcv_skb                        | net/ipv4/raw.c:297                       | inet_create                    | net/ipv4/af_inet.c:359                    |          |          |
| rawv6_rcv_skb                      | net/ipv6/raw.c:359                       | inet6_create                   | net/ipv6/af_inet6.c:219                   |          |          |
| receiver_wake_function             | net/core/datagram.c:76                   | __skb_wait_for_more_packets    | net/core/datagram.c:92                    |          |          |
| release_one_tty                    | drivers/tty/tty_io.c:1530                | kref_put                       | ./include/linux/kref.h:65                 |          |          |
|                                    |                                          | queue_release_one_tty          | drivers/tty/tty_io.c:1558                 |          |          |
|                                    |                                          | tty_kref_put                   | drivers/tty/tty_io.c:1572                 |          |          |
| rescuer_thread                     | kernel/workqueue.c:3450                  | __kthread_create_on_node       | kernel/kthread.c:441                      |          |          |
| rhashtable_jhash2                  | lib/rhashtable.c:977                     | rhashtable_init_noprof         | lib/rhashtable.c:1062                     |          |          |
| rht_deferred_worker                | lib/rhashtable.c:415                     | rhashtable_init_noprof         | lib/rhashtable.c:1081                     |          |          |
| rtnetlink_bind                     | net/core/rtnetlink.c:6657                | netlink_create                 | net/netlink/af_netlink.c:716              |          |          |
| scmd_eh_abort_handler              | drivers/scsi/scsi_error.c:148            | scsi_init_command              | drivers/scsi/scsi_lib.c:1260              |          |          |
| scsi_done                          | drivers/scsi/scsi_lib.c:1727             | __ata_scsi_queuecmd            | drivers/ata/libata-scsi.c:687             |          |          |
| seg6_genl_dumphmac                 | net/ipv6/seg6.c:416                      | genl_op_iter_next              | net/netlink/genetlink.c:272               |          |          |
| seg6_genl_dumphmac_done            | net/ipv6/seg6.c:411                      | genl_op_iter_next              | net/netlink/genetlink.c:273               |          |          |
| seg6_genl_dumphmac_start           | net/ipv6/seg6.c:406                      | genl_op_iter_next              | net/netlink/genetlink.c:271               |          |          |
| seg6_genl_get_tunsrc               | net/ipv6/seg6.c:266                      | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| seg6_genl_set_tunsrc               | net/ipv6/seg6.c:237                      | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| seg6_genl_sethmac                  | net/ipv6/seg6.c:230                      | genl_op_iter_next              | net/netlink/genetlink.c:276               |          |          |
| set_is_seen                        | ipc/ipc_sysctl.c:189                     | setup_sysctl_set               | fs/proc/proc_sysctl.c:1530                |          |          |
| shmem_free_in_core_inode           | mm/shmem.c:4486                          | evict                          | fs/inode.c:315                            |          |          |
| single_next                        | fs/seq_file.c:563                        | single_open                    | fs/seq_file.c:580                         |          |          |
| single_start                       | fs/seq_file.c:558                        | single_open                    | fs/seq_file.c:579                         |          |          |
| single_stop                        | fs/seq_file.c:569                        | single_open                    | fs/seq_file.c:581                         |          |          |
| sk_stream_write_space              | net/core/stream.c:31                     | tcp_init_sock                  | net/ipv4/tcp.c:460                        |          |          |
| snd_info_seq_show                  | sound/core/info.c:334                    | single_open                    | fs/seq_file.c:582                         |          |          |
| sock_def_destruct                  | net/core/sock.c:3405                     | sock_init_data_uid             | net/core/sock.c:3479                      |          |          |
| sock_def_write_space               | net/core/sock.c:3360                     | sock_init_data_uid             | net/core/sock.c:3477                      |          |          |
| sock_diag_bind                     | net/core/sock_diag.c:301                 | netlink_create                 | net/netlink/af_netlink.c:716              |          |          |
| sock_free_inode                    | net/socket.c:325                         | evict                          | fs/inode.c:315                            |          |          |
| submit_bio_wait_endio              | block/bio.c:1369                         | submit_bio_wait                | block/bio.c:1390                          |          |          |
| super_cache_count                  | fs/super.c:236                           | alloc_super                    | fs/super.c:384                            |          |          |
| super_cache_scan                   | fs/super.c:179                           | alloc_super                    | fs/super.c:383                            |          |          |
| tcp_compressed_ack_kick            | net/ipv4/tcp_timer.c:845                 | tcp_init_xmit_timers           | net/ipv4/tcp_timer.c:881                  |          |          |
| tcp_delack_timer                   | net/ipv4/tcp_timer.c:362                 | init_timer_key                 | kernel/time/timer.c:900                   |          |          |
| tcp_keepalive_timer                | net/ipv4/tcp_timer.c:757                 | init_timer_key                 | kernel/time/timer.c:900                   |          |          |
| tcp_pace_kick                      | net/ipv4/tcp_output.c:1236               | tcp_init_xmit_timers           | net/ipv4/tcp_timer.c:877                  |          |          |
| tcp_v6_do_rcv                      | net/ipv6/tcp_ipv6.c:1589                 | inet6_create                   | net/ipv6/af_inet6.c:219                   |          |          |
| tcp_write_timer                    | net/ipv4/tcp_timer.c:718                 | init_timer_key                 | kernel/time/timer.c:900                   |          |          |
| tctx_task_work                     | io_uring/io_uring.c:1167                 | init_task_work                 | ./include/linux/task_work.h:13            |          |          |
|                                    |                                          | io_uring_alloc_task_context    | io_uring/tctx.c:90                        |          |          |
| udp_destruct_sock                  | net/ipv4/udp.c:1601                      | udp_init_sock                  | net/ipv4/udp.c:1609                       |          |          |
| udpv6_destruct_sock                | net/ipv6/udp.c:63                        | udpv6_init_sock                | net/ipv6/udp.c:71                         |          |          |
| umh_keys_init                      | security/keys/request_key.c:81           | call_usermodehelper_setup      | kernel/umh.c:378                          |          |          |
| unix_dgram_peer_wake_relay         | net/unix/af_unix.c:437                   | unix_create1                   | ./include/linux/wait.h:92                 |          |          |
| unix_sock_destructor               | net/unix/af_unix.c:570                   | unix_create1                   | net/unix/af_unix.c:974                    |          |          |
| unix_stream_read_actor             | net/unix/af_unix.c:2897                  | unix_stream_recvmsg            | net/unix/af_unix.c:2922                   |          |          |
| unix_write_space                   | net/unix/af_unix.c:534                   | unix_create1                   | net/unix/af_unix.c:972                    |          |          |
| update_super_work                  | fs/ext4/super.c:746                      | ext4_fill_super                | fs/ext4/super.c:5276                      |          |          |
| vc_SAK                             | drivers/tty/vt/vt_ioctl.c:977            | vc_allocate                    | drivers/tty/vt/vt.c:1072                  |          |          |
| wake_bit_function                  | kernel/sched/wait_bit.c:22               | inode_wait_for_writeback       | fs/fs-writeback.c:1512                    |          |          |
| wb_update_bandwidth_workfn         | mm/backing-dev.c:503                     | wb_init                        | mm/backing-dev.c:540                      |          |          |
| wb_workfn                          | fs/fs-writeback.c:2298                   | wb_init                        | mm/backing-dev.c:539                      |          |          |
| woken_wake_function                | kernel/sched/wait.c:439                  | __inet_stream_connect          | net/ipv4/af_inet.c:600                    |          |          |
| wq_barrier_func                    | kernel/workqueue.c:3736                  | __flush_work                   | kernel/workqueue.c:3784                   |          |          |

