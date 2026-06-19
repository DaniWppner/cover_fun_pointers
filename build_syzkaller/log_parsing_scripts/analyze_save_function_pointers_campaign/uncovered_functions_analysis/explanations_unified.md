# Detailed Explanations for Function Pointer Context Execution

## Task 0: `ethnl_act_cable_test` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function `ethnl_act_cable_test` is a generic netlink `doit` handler for the `ETHTOOL_MSG_CABLE_TEST_ACT` command. The task notes that the function is stored during `genl_op_iter_next` at `net/netlink/genetlink.c:276`, which corresponds to `op->doit = full->doit;`. This happens during generic netlink command resolution (e.g., in `genl_get_cmd` calling `genl_cmd_full_to_split`) when processing an incoming netlink message.

When a user-space process sends a netlink message using the `sendmsg` system call, the kernel handles the message through the netlink subsystem. For generic netlink, the message is dispatched to `genl_rcv`, which executes synchronously in the context of the user process making the `sendmsg` call. Specifically, the call chain is:
1. `sys_sendmsg` -> `netlink_sendmsg`
2. `netlink_sendmsg` -> `netlink_unicast` -> `netlink_unicast_kernel`
3. `netlink_unicast_kernel` invokes `nlk->netlink_rcv(skb)` which is set to `genl_rcv` for generic netlink.
4. `genl_rcv` -> `netlink_rcv_skb` -> `genl_rcv_msg` -> `genl_family_rcv_msg_doit`.
5. Finally, `genl_family_rcv_msg_doit` invokes the stored `doit` function (`ethnl_act_cable_test`).

Since the execution remains strictly synchronous along this entire path, the function pointer is executed in the context of the sending task. There is no context switch, workqueue, or asynchronous delivery mechanism involved here. Therefore, the function executes synchronously, and the "current" task context does not change.
---

## Task 1: `ethnl_act_cable_test_tdr` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function `ethnl_act_cable_test_tdr` is stored into the `doit` function pointer of a `struct genl_split_ops` inside `genl_cmd_full_to_split` (net/netlink/genetlink.c:276). 
This function pointer is part of the generic netlink (genetlink) framework used by the kernel to process netlink messages from userspace.

When a userspace program sends a genetlink message using the `sendmsg` system call, the kernel processes it via `netlink_sendmsg`. 
For messages directed to the kernel, `netlink_sendmsg` calls `netlink_unicast`, which in turn calls `netlink_unicast_kernel`.
Inside `netlink_unicast_kernel`, the netlink receive callback (`nlk->netlink_rcv`) is invoked synchronously. For genetlink, this callback is `genl_rcv`.
`genl_rcv` then calls `netlink_rcv_skb` with `genl_rcv_msg` as the message processing callback.
`genl_rcv_msg` ultimately looks up the appropriate `doit` callback (in this case, `ethnl_act_cable_test_tdr`) and invokes it directly via `genl_family_rcv_msg_doit`.

Because the entire call chain from the `sendmsg` syscall to the `doit` callback is executed synchronously within the context of the system call, the "current" task context does not change. Therefore, the function is not executed asynchronously.
---

## Task 2: `ethnl_default_doit` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `ethnl_default_doit` is stored in the `doit` field of a `genl_split_ops` structure inside `genl_cmd_full_to_split` (net/netlink/genetlink.c:276).
This function pointer represents a Generic Netlink "doit" callback.

When a user-space application sends a Generic Netlink message, the message is received by the kernel via a syscall like `sendmsg`. 
This invokes the Generic Netlink receive handler `genl_rcv()` which calls `netlink_rcv_skb()` with `genl_rcv_msg()`.
`genl_rcv_msg()` eventually calls `genl_family_rcv_msg_doit()`, which directly executes the `doit` function pointer: `err = ops->doit(skb, &info);`.

Because netlink message processing for `doit` operations happens synchronously in the context of the sending task (during the `sendmsg` system call), the task context does NOT change. Therefore, it is executed synchronously, not asynchronously.
---

## Task 3: `ethnl_default_done` at `net/netlink/genetlink.c:273`
**Verdict:** Yes

The function pointer `ethnl_default_done` is stored into `op->done` within `genl_cmd_full_to_split` when initializing a `genl_split_ops` structure. This structure is then used during the generic netlink dump operations.

Specifically, in `genl_family_rcv_msg_dumpit`, this operation is used to start a netlink dump. The `done` callback is set to `genl_done`, which retrieves the `genl_split_ops` structure and calls its `done` function pointer (`ops->done(cb)`).

The execution of the dump and its completion callback (`cb->done`) can happen asynchronously relative to the task that initiated the dump request (`sendmsg`). For instance:
1. The dump is continued and finished in subsequent `recvmsg` syscalls from userspace, which could potentially be invoked by a different thread or task sharing the socket.
2. If the socket is closed or the process terminates while the dump is still running (`nlk->cb_running` is true), the `netlink_sock_destruct` function will be invoked (potentially via a deferred workqueue). This destruct function explicitly calls `nlk->cb.done(&nlk->cb)`.

Because the function can be executed in a different task context (e.g., another thread calling `recvmsg`, or socket destruction in a workqueue), this constitutes asynchronous execution.
---

## Task 4: `ethnl_default_dumpit` at `net/netlink/genetlink.c:272`
**Verdict:** No

The function pointer `ethnl_default_dumpit` is stored in the `dumpit` field of a `genl_split_ops` structure inside `genl_cmd_full_to_split` (net/netlink/genetlink.c:272).
This function pointer represents a Generic Netlink "dumpit" callback, which is used to dump data back to userspace in chunks.

The `dumpit` callback is initially called synchronously when the user task sends a netlink dump request via `sendmsg` (through `__netlink_dump_start`).
If the dump requires multiple parts because it exceeds the buffer size, the continuation of the dump (and thus subsequent calls to the `dumpit` callback) happens synchronously during the user task's `recvmsg` syscalls (via `netlink_recvmsg` -> `netlink_dump`).

In both cases, the callback executes synchronously in the context of the user process making the system call (`sendmsg` or `recvmsg`). Thus, the task context does NOT change.
---

## Task 5: `ethnl_default_set_doit` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function `ethnl_default_set_doit` is stored into the `doit` function pointer of a `struct genl_split_ops` inside `genl_cmd_full_to_split` (net/netlink/genetlink.c:276). 
This function pointer is part of the generic netlink (genetlink) framework used by the kernel to process netlink messages from userspace.

When a userspace program sends a genetlink message using the `sendmsg` system call, the kernel processes it via `netlink_sendmsg`. 
For messages directed to the kernel, `netlink_sendmsg` calls `netlink_unicast`, which in turn calls `netlink_unicast_kernel`.
Inside `netlink_unicast_kernel`, the netlink receive callback (`nlk->netlink_rcv`) is invoked synchronously. For genetlink, this callback is `genl_rcv`.
`genl_rcv` then calls `netlink_rcv_skb` with `genl_rcv_msg` as the message processing callback.
`genl_rcv_msg` ultimately looks up the appropriate `doit` callback (in this case, `ethnl_default_set_doit`) and invokes it directly via `genl_family_rcv_msg_doit`.

Because the entire call chain from the `sendmsg` syscall to the `doit` callback is executed synchronously within the context of the system call, the "current" task context does not change. Therefore, the function is not executed asynchronously.
---

## Task 6: `ethnl_default_start` at `net/netlink/genetlink.c:271`
**Verdict:** No

The function `ethnl_default_start` is stored as the `start` callback for various generic netlink operations (e.g., `ETHTOOL_MSG_STRSET_GET`) in the `ethtool_genl_ops` array. The assignment at `net/netlink/genetlink.c:271` (`op->start = full->start;`) copies this function pointer to a temporary `op` structure during operation resolution.

When a dump request is received, the generic netlink subsystem calls `genl_family_rcv_msg_dumpit`, which invokes `__netlink_dump_start`. Inside `__netlink_dump_start`, the `control->start` callback (which resolves to `genl_start`) is executed immediately and synchronously. `genl_start` in turn calls the family-specific `ops->start` function, which is `ethnl_default_start`.

Because this entire chain (`sys_sendmsg` -> `netlink_sendmsg` -> `netlink_unicast_kernel` -> `genl_rcv` -> `__netlink_dump_start` -> `genl_start` -> `ethnl_default_start`) executes within the same task that invoked the `sendmsg` system call, the execution is synchronous. The "current" task context does not change when the stored function pointer is executed.
---

## Task 7: `ethnl_set_features` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `ethnl_set_features` is stored in the `doit` field of a `genl_split_ops` structure via `genl_cmd_full_to_split` (net/netlink/genetlink.c:276).
Similar to other Generic Netlink `doit` callbacks, this function represents the operation to execute when a specific netlink command is received.

The `doit` callback is executed directly and synchronously by `genl_family_rcv_msg_doit()`, which is called during the processing of a netlink message in the `sendmsg` system call context.
As it executes within the context of the user process making the system call, the task context does not change. Thus, the execution is synchronous.
---

## Task 8: `ethnl_tunnel_info_doit` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function `ethnl_tunnel_info_doit` is stored into the `doit` function pointer of a `struct genl_split_ops` inside `genl_cmd_full_to_split` (net/netlink/genetlink.c:276). 
This function pointer is part of the generic netlink (genetlink) framework used by the kernel to process netlink messages from userspace.

When a userspace program sends a genetlink message using the `sendmsg` system call, the kernel processes it via `netlink_sendmsg`. 
For messages directed to the kernel, `netlink_sendmsg` calls `netlink_unicast`, which in turn calls `netlink_unicast_kernel`.
Inside `netlink_unicast_kernel`, the netlink receive callback (`nlk->netlink_rcv`) is invoked synchronously. For genetlink, this callback is `genl_rcv`.
`genl_rcv` then calls `netlink_rcv_skb` with `genl_rcv_msg` as the message processing callback.
`genl_rcv_msg` ultimately looks up the appropriate `doit` callback (in this case, `ethnl_tunnel_info_doit`) and invokes it directly via `genl_family_rcv_msg_doit`.

Because the entire call chain from the `sendmsg` syscall to the `doit` callback is executed synchronously within the context of the system call, the "current" task context does not change. Therefore, the function is not executed asynchronously.
---

## Task 9: `ethnl_tunnel_info_dumpit` at `net/netlink/genetlink.c:272`
**Verdict:** Yes

The function pointer `ethnl_tunnel_info_dumpit` is stored into `op->dumpit` within `genl_cmd_full_to_split` when a generic netlink dump operation is initialized. This structure is subsequently used to manage the dump.

In `genl_family_rcv_msg_dumpit`, a netlink dump is started with `genl_dumpit` as the dump callback. `genl_dumpit` retrieves the operation structure and executes `ops->dumpit`.

The execution of the `dump` callback can happen asynchronously relative to the initial request. When userspace sends a dump request via `sendmsg`, the kernel may return a partial result if the buffer fills up. In that case, the `netlink_dump` state is saved (with `nlk->cb_running` set to true). A subsequent `recvmsg` syscall from userspace will resume the dump by calling `cb->dump(skb, cb)`. 

Because the `dump` function is executed during subsequent `recvmsg` system calls—which could potentially be invoked by a different thread or task sharing the socket—this constitutes asynchronous execution compared to the task context that initially processed the `sendmsg` and set up the dump.
---

## Task 10: `ethnl_tunnel_info_start` at `net/netlink/genetlink.c:271`
**Verdict:** No

The function pointer `ethnl_tunnel_info_start` is stored in the `start` field of a `genl_split_ops` structure via `genl_cmd_full_to_split` (net/netlink/genetlink.c:271).
This function pointer represents a Generic Netlink "start" callback for a dump operation.

When a dump request is received via a `sendmsg` system call, the kernel sets up the dump operation in `__netlink_dump_start()`.
During this setup phase, `__netlink_dump_start()` directly and synchronously executes the `start` callback (`control->start(cb)`) to initialize the dump context.
Since this happens synchronously within the context of the user process making the `sendmsg` system call, the task context does NOT change. Therefore, it is executed synchronously.
---

## Task 11: `ext4_discard_work` at `fs/ext4/mballoc.c:3676`
**Verdict:** Yes

The function `ext4_discard_work` is assigned to a work_struct via the `INIT_WORK` macro at `fs/ext4/mballoc.c:3676` within the `ext4_mb_init` function. 

In the Linux kernel, workqueues are a mechanism for deferring work to be executed later by a dedicated worker thread (such as `kworker`). When work is needed, the kernel adds the initialized work_struct to a workqueue using the `queue_work` function. For `s_discard_work`, this happens at `fs/ext4/mballoc.c:3932` where it is queued to `system_unbound_wq`.

Because `ext4_discard_work` is executed by a kernel worker thread instead of the thread that originally scheduled it, the execution context changes. Thus, the stored function is executed asynchronously.
---

## Task 12: `ext4_end_bitmap_read` at `fs/ext4/super.c:173`
**Verdict:** Yes

The function pointer `ext4_end_bitmap_read` is passed to `__ext4_read_bh` (via `ext4_read_bh` or `ext4_read_bh_nowait`) and is stored into the `b_end_io` field of the `buffer_head` structure (`bh->b_end_io`).

After storing the callback, `__ext4_read_bh` calls `submit_bh(REQ_OP_READ | op_flags, bh)`. This submits the buffer head to the block layer for asynchronous I/O execution. 

When the block device completes the read operation, the block layer will invoke the `b_end_io` callback to notify the filesystem that the I/O has finished. This completion is typically handled in an interrupt context (hard IRQ or softirq) or a block completion workqueue, which is a completely different execution context from the task that originally submitted the I/O request. Therefore, the execution of the `ext4_end_bitmap_read` callback is asynchronous.
---

## Task 13: `ext4_end_bitmap_read` at `fs/ext4/super.c:187`
**Verdict:** Yes

The function pointer `ext4_end_bitmap_read` is passed as an argument (`end_io`) into `ext4_read_bh_nowait`, which in turn passes it down to `__ext4_read_bh`.

Inside `__ext4_read_bh`, this callback is stored into the `b_end_io` field of the `buffer_head` structure (`bh->b_end_io`). Afterwards, `submit_bh` is called to submit the buffer for a block device read operation. 

The execution of this `end_io` callback is performed by the block layer upon the completion of the asynchronous I/O operation. This completion occurs in an interrupt handler (hard or soft IRQ) or via a block completion workqueue. Because the context in which the I/O completion is handled is distinct from the context of the task that originally called `ext4_read_bh_nowait` and submitted the I/O, the function pointer is executed asynchronously.
---

## Task 14: `ext4_end_bitmap_read` at `fs/ext4/super.c:199`
**Verdict:** Yes

The function `ext4_end_bitmap_read` is stored as an I/O completion callback for a buffer head (`bh->b_end_io`) in `__ext4_read_bh` (called via `ext4_read_bh`). This occurs when the filesystem needs to read an inode or block bitmap from disk and the buffer is not already up-to-date.

After setting this callback, `__ext4_read_bh` calls `submit_bh` to dispatch the read request to the block layer, and the caller typically goes to sleep waiting for the I/O to complete (e.g., via `wait_on_buffer(bh)`).

When the disk controller finishes the read operation, it triggers a hardware interrupt. The block layer processes this completion, usually deferring the final callback execution to a softirq (like `BLOCK_SOFTIRQ`). The softirq executes the bio completion routine, which in turn calls the buffer head's `b_end_io` callback (`ext4_end_bitmap_read`).

Because this callback is invoked from the block I/O completion path (hardware interrupt or softirq context), it runs asynchronously with respect to the original thread that initiated the read. The "current" task context during execution will be the interrupted task or a kernel daemon (like `ksoftirqd`), not the original task. Therefore, the task context changes.
---

## Task 15: `ext4_end_io_rsv_work` at `fs/ext4/super.c:1421`
**Verdict:** Yes

The function pointer `ext4_end_io_rsv_work` is stored during the initialization of an ext4 inode in `ext4_alloc_inode` (fs/ext4/super.c:1421).
It is passed to the `INIT_WORK()` macro to initialize the `i_rsv_conversion_work` work_struct for the inode.

The `INIT_WORK` macro assigns the provided function pointer as the callback function (`work->func`) for the work item.
When this work item is later scheduled using `queue_work()`, it is placed on a workqueue. A kernel worker thread (e.g., `kworker/...`) will eventually dequeue the work item and execute the callback function.
Because the callback function is executed by a separate kernel worker thread rather than the thread that initiated or queued the work, the "current" task context changes. Therefore, the function pointer is executed asynchronously.
---

## Task 16: `ext4_es_count` at `fs/ext4/extents_status.c:1735`
**Verdict:** Yes

The function `ext4_es_count` is stored into the `count_objects` field of a `struct shrinker` at `fs/ext4/extents_status.c:1735` during the registration of the extents status tree shrinker (`ext4_es_register_shrinker`).

In the Linux kernel, shrinkers are invoked by the memory management subsystem when the system is under memory pressure and needs to reclaim memory. This process is typically handled by either the `kswapd` kernel daemon (a dedicated background thread for page reclaim) or by "direct reclaim," which occurs when an arbitrary task attempts to allocate memory and must first free some up.

In either case, the shrinker's `count_objects` callback is invoked from `do_shrink_slab` (in `mm/shrinker.c`), which is completely decoupled from the task that originally registered the shrinker or added items to the cache. Because the shrinker is called in the context of the memory reclaim path (e.g., `kswapd` or an unrelated task's direct reclaim), the execution of `ext4_es_count` happens asynchronously relative to its registration, and the "current" task context will be different.
---

## Task 17: `ext4_es_scan` at `fs/ext4/extents_status.c:1734`
**Verdict:** Yes

The function pointer `ext4_es_scan` is stored into the `scan_objects` field of a `shrinker` structure (`sbi->s_es_shrinker->scan_objects`) inside `ext4_es_register_shrinker`. This shrinker is then registered with the kernel memory management subsystem via `shrinker_register`.

Shrinker callbacks are invoked by the Linux kernel when the system is under memory pressure and needs to reclaim memory. This reclaim process can be executed by dedicated kernel threads (such as `kswapd`) or by arbitrary tasks undergoing direct reclaim when allocating memory. 

Because the callback is triggered by memory management events and executed in the context of `kswapd` or other random tasks—completely independently from the task that initially mounted the filesystem and registered the shrinker—it is executed asynchronously.
---

## Task 18: `ext4_fc_info_show` at `fs/proc/generic.c:656`
**Verdict:** No

The function pointer `ext4_fc_info_show` is passed to `proc_create_single_data()` when creating a procfs entry (fs/ext4/fast_commit.c:2269) and stored in `p->single_show` (fs/proc/generic.c:656).
This function serves as the `show` callback for a sequential file (seq_file) representation of the proc entry.

When a user process opens this proc file, the `proc_single_open` callback passes the `single_show` function pointer to `single_open()`.
Subsequently, when the user process issues a `read` system call on this open file descriptor, the kernel executes the `show` callback (`ext4_fc_info_show`) to generate the output data for the user.
Because this callback is executed synchronously within the context of the user process making the `read` system call, the "current" task context does NOT change. Therefore, it is executed synchronously.
---

## Task 19: `ext4_free_in_core_inode` at `fs/inode.c:315`
**Verdict:** Yes

The function `ext4_free_in_core_inode` is the `free_inode` callback in the ext4 `super_operations` struct. In `destroy_inode` (fs/inode.c:315), this function pointer is copied from `ops->free_inode` into `inode->free_inode` before freeing the inode.

Immediately after this assignment, the kernel calls `call_rcu(&inode->i_rcu, i_callback);` to schedule the actual freeing of the inode. The `call_rcu` function does not execute the callback synchronously; instead, it registers the callback (`i_callback`) to be executed by the RCU (Read-Copy-Update) subsystem after a grace period has elapsed. 

When the grace period finishes, an RCU worker thread (or a softirq context) will execute `i_callback`, which in turn calls the stored `inode->free_inode` pointer (i.e., `ext4_free_in_core_inode`). Because the execution is deferred via RCU, it happens asynchronously in a completely different task context than the one that initiated the inode destruction.
---

## Task 20: `ext4_lazyinit_thread` at `kernel/kthread.c:441`
**Verdict:** Yes

The function pointer `ext4_lazyinit_thread` is passed to `__kthread_create_on_node` and stored into the `threadfn` field of a `kthread_create_info` structure (`create->threadfn = threadfn`).

This structure is used to instruct the `kthreadd` daemon to spawn a new kernel thread. Once the new kernel thread is created and woken up, it begins its execution starting from the function pointer stored in `threadfn` (in this case, `ext4_lazyinit_thread`).

Because the function serves as the entry point for a newly spawned kernel thread, it will run in a completely new task context that is distinct from the task that called `__kthread_create_on_node`. Therefore, the execution of the stored function is asynchronous.
---

## Task 21: `ext4_orphan_file_block_trigger` at `fs/ext4/super.c:4288`
**Verdict:** Yes

The function pointer `ext4_orphan_file_block_trigger` is stored as the `t_frozen` callback in a `jbd2_buffer_trigger_type` struct via `ext4_setup_csum_trigger` (fs/ext4/super.c:4288).
This callback is part of the JBD2 (Journaling Block Device) trigger system, which acts on journaled metadata blocks.

The `t_frozen` trigger is called when data is being frozen for a journal commit. This execution occurs via `jbd2_buffer_frozen_trigger()`.
This function is invoked in two main scenarios:
1. Synchronously by the task modifying the buffer (via `do_get_write_access() -> jbd2_freeze_jh_data()`).
2. Asynchronously by the `kjournald2` kernel thread during a transaction commit (via `jbd2_journal_write_metadata_buffer()`).

Because the commit process is typically handled by the background `kjournald2` worker thread, the trigger callback will be executed asynchronously in a task context separate from the one that initially modified the buffer. Therefore, the task context does change.
---

## Task 22: `ext4_orphan_file_block_trigger` at `fs/ext4/super.c:4599`
**Verdict:** Yes

The function `ext4_orphan_file_block_trigger` is stored as a `t_frozen` journal trigger callback inside the ext4 superblock initialization (`ext4_init_metadata_csum`), using `ext4_setup_csum_trigger`. It is registered with the JBD2 journalling subsystem to be executed when a journaled buffer containing orphan file blocks is "frozen" for commit.

This `t_frozen` callback can be executed in two scenarios:
1. When a user task modifies a buffer that is already participating in an ongoing commit, the JBD2 subsystem (in `do_get_write_access`) freezes the buffer synchronously to prevent the committing transaction from seeing partial updates.
2. During the normal commit process, when the JBD2 commit thread (`kjournald2`) iterates over all metadata buffers (in `jbd2_journal_write_metadata_buffer`) and prepares them to be written to the journal.

The second scenario is the primary execution path for this trigger. The original task that dirtied the buffer simply marks it dirty and proceeds with its execution. Later, the dedicated `kjournald2` kernel thread wakes up, processes the dirty buffer, and fires the `t_frozen` trigger to calculate the block's checksum before writing it out.

Since the execution happens primarily within the `kjournald2` kernel thread during an asynchronous background commit, the "current" task context changes from the process that originally modified the block. Thus, the callback is executed asynchronously.
---

## Task 23: `ext4_orphan_file_block_trigger` at `fs/ext4/super.c:5207`
**Verdict:** Yes

The `ext4_orphan_file_block_trigger` function pointer is passed as a callback into the `struct jbd2_buffer_trigger_type` by `ext4_setup_csum_trigger`, which is called during filesystem mount/remount (via `ext4_init_metadata_csum` -> `__ext4_fill_super`). This trigger structure is stored in the ext4 superblock info (`sbi->s_journal_triggers[type]`).

JBD2 uses this trigger as the `t_frozen` callback, which fires just before JBD2 makes a copy of a metadata buffer (or writes it out) to ensure the data is complete and checksums are computed before the commit process persists it to the journal.

The `t_frozen` callback is invoked from `jbd2_buffer_frozen_trigger`, which gets called primarily from two places:
1. `jbd2_journal_write_metadata_buffer()` inside `jbd2_journal_commit_transaction()` (`fs/jbd2/commit.c`).
2. `jbd2_freeze_jh_data()` in `fs/jbd2/transaction.c`, which handles copy-out during concurrent writes.

The primary caller, `jbd2_journal_commit_transaction`, is the main commit loop of JBD2, which is executed by the `kjournald2` kernel thread. Because `kjournald2` is a background kernel thread responsible for asynchronous commits, the context in which `ext4_orphan_file_block_trigger` runs will be `kjournald2` rather than the user-space process that originally triggered the filesystem modification. Thus, the "current" task context changes when this function is called.

Therefore, the function pointer is executed asynchronously.
---

## Task 24: `ext4_orphan_file_block_trigger` at `fs/ext4/super.c:5676`
**Verdict:** Maybe

The function pointer `ext4_orphan_file_block_trigger` is stored in the `t_frozen` field of a `struct jbd2_buffer_trigger_type` via `ext4_setup_csum_trigger()`.

This function pointer is invoked when `jbd2_buffer_frozen_trigger()` is called, which happens in two distinct code paths with different execution contexts:

1. **Asynchronously:** The primary path occurs during a journal commit. The background JBD2 commit thread (`kjournald2`) executes `jbd2_journal_commit_transaction()`, which calls `jbd2_journal_write_metadata_buffer()`, and ultimately `jbd2_buffer_frozen_trigger()`. When executed here, the "current" task context is `kjournald2`, making the execution asynchronous relative to the task that initially triggered the filesystem modification.

2. **Synchronously:** A secondary path occurs if a user task attempts to modify a metadata block (via `ext4_journal_get_write_access()` -> `do_get_write_access()`) while that block is already part of an ongoing, committing transaction. To preserve the old data for the commit, `do_get_write_access()` calls `jbd2_freeze_jh_data()`, which then synchronously invokes `jbd2_buffer_frozen_trigger()`. In this scenario, the function pointer is executed in the context of the user task.

Since the execution context depends on runtime timing and contention, the function pointer can be executed either synchronously or asynchronously. Therefore, the verdict is Maybe.
---

## Task 25: `ext4_seq_es_shrinker_info_show` at `fs/proc/generic.c:656`
**Verdict:** Yes

The function `ext4_seq_es_shrinker_info_show` is passed to `proc_create_single_data` when initializing the ext4 extent status cache shrinker procfs file.
`proc_create_single_data` assigns this function pointer to the `single_show` field of a `proc_dir_entry` and sets the file operations for this procfs entry to `proc_single_ops`.
When a userspace process opens and reads this procfs file, the `single_open` and `seq_read_iter` VFS operations are invoked in the context of that userspace process. `seq_read_iter` will call our stored `show` function pointer (`ext4_seq_es_shrinker_info_show`) to generate the contents of the procfs file.
Since the function pointer is stored during initialization (or mount) but executed later by an arbitrary userspace process reading the proc file, the "current" task context changes between the time the pointer is stored and the time it is executed. Thus, the execution is asynchronous.
---

## Task 26: `ext4_seq_mb_stats_show` at `fs/proc/generic.c:656`
**Verdict:** Yes

The function pointer `show` (in this case `ext4_seq_mb_stats_show`) is passed to `proc_create_single_data` and stored into the `single_show` field of a `proc_dir_entry` struct.
When a userspace process opens the corresponding procfs file, the kernel invokes `proc_single_open`, which in turn passes the stored `de->single_show` pointer to `single_open()`.
The pointer is then saved in a `seq_file` structure and is eventually executed when the userspace process reads from the file (via `seq_read` or `seq_read_iter`).
Because the process creating the procfs entry (e.g., during module initialization or filesystem mounting) is different from the arbitrary userspace process that opens and reads the procfs file later, the context executing the function pointer changes.
Therefore, the execution of the stored function pointer is asynchronous.
---

## Task 27: `ext4_seq_options_show` at `fs/proc/generic.c:656`
**Verdict:** Yes

The function `ext4_seq_options_show` is passed to `proc_create_single_data` when initializing the ext4 mount options procfs file.
`proc_create_single_data` assigns this function pointer to the `single_show` field of a `proc_dir_entry` and sets the file operations for this procfs entry to `proc_single_ops`.
When a userspace process opens and reads this procfs file, the `single_open` and `seq_read_iter` VFS operations are invoked in the context of that userspace process. `seq_read_iter` will call our stored `show` function pointer (`ext4_seq_options_show`) to generate the contents of the procfs file.
Since the function pointer is stored during initialization (or mount) but executed later by an arbitrary userspace process reading the proc file, the "current" task context changes between the time the pointer is stored and the time it is executed. Thus, the execution is asynchronous.
---

## Task 28: `fat_free_inode` at `fs/inode.c:315`
**Verdict:** Yes

In `destroy_inode`, the function pointer `ops->free_inode` (which corresponds to `fat_free_inode` in this context) is stored into `inode->free_inode`.
Immediately after this, the kernel calls `call_rcu(&inode->i_rcu, i_callback)`.
The `call_rcu` function schedules the `i_callback` function to be executed asynchronously after an RCU grace period elapses, typically in the context of an RCU softirq or a dedicated RCU worker thread.
Inside `i_callback`, the stored `inode->free_inode(inode)` pointer is executed.
Since the execution is deferred via RCU, the context executing the function pointer is different from the task that initiated the inode destruction. Thus, the execution is asynchronous.
---

## Task 29: `flush_end_io` at `block/blk-flush.c:337`
**Verdict:** Yes

In `block/blk-flush.c`, `blk_kick_flush` assigns the `flush_end_io` function to the `end_io` callback of `flush_rq`.
`flush_rq` is a special internal request used to send actual flush commands to the block device hardware.
After setting the callback, the request is added to the requeue list and dispatched to the device.
When the hardware completes the flush operation, the block layer's interrupt or softirq handling will invoke the request's `end_io` callback, which is `flush_end_io`.
Because this callback is invoked from an IRQ or block softirq context (or a completion thread), the "current" task context will be different from the task that initially triggered the flush. Thus, the stored function pointer `flush_end_io` is executed asynchronously.
---

## Task 30: `flush_tlb_func` at `kernel/smp.c:816`
**Verdict:** Yes

In `smp_call_function_many_cond`, the function pointer (e.g., `flush_tlb_func`) is stored into the `func` field of a `call_single_data_t` (CSD) structure associated with the target CPUs (`csd->func = func`).
The CSD is then added to the per-CPU `call_single_queue` of the target CPUs, and an Inter-Processor Interrupt (IPI) is sent to those CPUs.
The target CPUs receive the IPI and process their `call_single_queue` in the IPI handler context (e.g., via `__flush_smp_call_function_queue`), executing the stored function pointer.
Since the function pointer is executed by a different CPU in an interrupt context rather than the task that called `smp_call_function_many_cond`, the execution occurs asynchronously and the context changes.
---

## Task 31: `flush_to_ldisc` at `drivers/tty/tty_buffer.c:587`
**Verdict:** Yes

In `drivers/tty/tty_buffer.c`, `tty_buffer_init` initializes a `work_struct` (`buf->work`) using `INIT_WORK`, passing the `flush_to_ldisc` function pointer as the work handler.
When there is data in the flip buffer to be pushed to the line discipline, `tty_flip_buffer_push` schedules this work on the `system_unbound_wq` workqueue using `queue_work`.
The function `flush_to_ldisc` is then executed by a kernel worker thread asynchronously. Since the scheduling task (e.g. an interrupt handler or a driver context producing tty data) is different from the worker thread executing the function, the "current" task context changes. Therefore, `flush_to_ldisc` is executed asynchronously.
---

## Task 32: `free_ioctx_reqs` at `lib/percpu-refcount.c:100`
**Verdict:** Yes

The function pointer `release` (e.g. `free_ioctx_reqs`) is passed to `percpu_ref_init` and stored into `data->release`.
This function pointer serves as the destructor callback for the percpu reference count.
It is executed in `percpu_ref_put_many` (or `percpu_ref_put`) when the reference count drops to 0.
Since a reference count is typically dropped by various contexts (e.g., worker threads, I/O completion interrupts, or other tasks using the object), the task context that executes the `release` function is generally different from the one that initialized the refcount and stored the pointer.
Therefore, the execution is asynchronous.
---

## Task 33: `free_ioctx_users` at `lib/percpu-refcount.c:100`
**Verdict:** Yes

The function `free_ioctx_users` is passed as the `release` callback to `percpu_ref_init` when initializing the `users` percpu refcount of a `kioctx` in `ioctx_alloc`.
The release callback of a `percpu_ref` is executed when the reference count reaches zero.
In the lifecycle of a `kioctx`, `percpu_ref_kill` is called on the `users` refcount during context destruction (e.g., via `io_destroy` or `exit_aio`). `percpu_ref_kill` marks the refcount as dead and initiates a switch to atomic mode using an RCU callback (`percpu_ref_switch_to_atomic_rcu`).
The RCU callback sums the per-CPU counters and performs a `percpu_ref_put`. If this is the last reference (which is typically the case for the initial reference dropped by the kill operation), the `release` function (`free_ioctx_users`) will be invoked directly from the RCU softirq context.
Because the release function is called from the RCU callback (or from whichever thread happens to drop the final reference), it executes asynchronously with respect to the task that created the `kioctx` and initialized the refcount.
---

## Task 34: `genl_bind` at `net/netlink/af_netlink.c:716`
**Verdict:** No

The task asks whether the `genl_bind` function pointer, stored in `nlk->netlink_bind` during `netlink_create()` (`net/netlink/af_netlink.c:716`), will be executed asynchronously.

The function pointer `nlk->netlink_bind` is invoked in two places in `net/netlink/af_netlink.c`:
1. In `netlink_bind()` (around line 1047), which is the socket `.bind` operation for netlink sockets.
2. In `netlink_setsockopt()` (around line 1684) when handling the `NETLINK_ADD_MEMBERSHIP` option.

Both of these functions are direct handlers for user-space system calls (`bind()` and `setsockopt()`). When a user-space process invokes either of these system calls on a netlink socket, the kernel executes these handlers synchronously within the context of the calling process.

Because the `genl_bind` function is invoked directly in the system call execution path, the "current" task context remains the same as the process making the system call. Therefore, the function is executed synchronously, not asynchronously.
---

## Task 35: `genl_unbind` at `net/netlink/af_netlink.c:717`
**Verdict:** Yes

In `netlink_create`, the unbind function pointer for the requested netlink protocol (such as `genl_unbind` for `NETLINK_GENERIC`) is fetched from the `nl_table` and stored into `nlk->netlink_unbind` of the newly created netlink socket.
This pointer acts as a callback that is executed later when an application drops group memberships via `setsockopt(..., NETLINK_DROP_MEMBERSHIP, ...)` or when the socket is closed and released.
Because socket file descriptors can be shared, inherited via fork, or passed between processes (e.g., via `SCM_RIGHTS`), the task invoking `setsockopt` or `close` (and thus executing the `netlink_unbind` callback) might be different from the task that initially created the socket.
Even when it is the same task, the execution is deferred to an entirely separate system call at an arbitrary future time. Therefore, the execution of the stored function pointer is asynchronous.
---

## Task 36: `hrtimer_wakeup` at `./include/linux/hrtimer.h:254`
**Verdict:** Yes

The function pointer `hrtimer_wakeup` is stored into the `timer.function` field of a `struct hrtimer` (part of a `struct hrtimer_sleeper`) by `hrtimer_init_sleeper()` (which is called by `hrtimer_init_sleeper_on_stack()`).

This function pointer acts as the callback for the high-resolution timer. It is executed when the timer expires. Timer expiration is managed by the hrtimer core subsystem, which processes active timers in `__hrtimer_run_queues()` and invokes the callback via `__run_hrtimer()`.

Depending on the timer's mode, this expiration processing runs either in Hard IRQ context (e.g., triggered by `hrtimer_interrupt()`) or in SoftIRQ context (e.g., triggered by `hrtimer_run_softirq()`). In either case, the callback is executed asynchronously in an interrupt context, completely independent of the task that originally configured and started the timer (which is typically sleeping and waiting to be awoken by this very callback). Therefore, the "current" task context is guaranteed to change when the function is called.
---

## Task 37: `hrtimer_wakeup` at `kernel/time/hrtimer.c:1983`
**Verdict:** Yes

In `kernel/time/hrtimer.c`, `__hrtimer_init_sleeper` initializes a high-resolution sleeper timer and assigns `hrtimer_wakeup` to the `function` field of the `hrtimer` struct.
This function acts as the callback that will be executed when the timer expires.
The timer is then started (e.g. via `hrtimer_sleeper_start_expires`) and the calling task will typicaly suspend execution (e.g. calling `schedule()`).
When the time expires, the hardware timer interrupt fires and the `hrtimer_wakeup` callback is executed asynchronously in the context of the timer interrupt (hardirq) or the timer softirq, which is separate from the context of the task that originally stored the function pointer and went to sleep.
Since the context changes when the function is called, the execution is asynchronous.
---

## Task 38: `hrtimer_wakeup` at `kernel/time/hrtimer.c:1997`
**Verdict:** Yes

The `hrtimer_wakeup` function is assigned to the `function` field of an `hrtimer` object inside `__hrtimer_init_sleeper()` (which is called by `hrtimer_init_sleeper()`). This function serves as the callback for a high-resolution timer.

When the timer expires, the kernel invokes the callback via `__run_hrtimer()`, which is called from the timer interrupt handler (`hrtimer_interrupt()`) or the timer softirq handler (`hrtimer_run_softirq()`).

Because the callback is executed in hardirq or softirq context, it is executed asynchronously. The timer interrupt can interrupt any arbitrary task that happens to be running on the CPU at the time of expiration, meaning the `current` task context during the callback's execution will not be the context of the task that originally started the timer (which is usually sleeping). Therefore, the "current" task context changes, and the execution is asynchronous.
---

## Task 39: `hrtimer_wakeup` at `kernel/time/hrtimer.c:2081`
**Verdict:** Yes

In `kernel/time/hrtimer.c`, the `hrtimer_nanosleep` function initializes a high-resolution sleeper timer on the stack using `hrtimer_init_sleeper_on_stack` (which internally calls `__hrtimer_init_sleeper`), assigning `hrtimer_wakeup` to the `function` field of the timer structure.
This function acts as the callback that will be executed when the timer expires.
After initialization, the timer is started and the calling task suspends execution (via `do_nanosleep` which calls `schedule()`).
When the sleep duration expires, the hardware timer interrupt fires and the `hrtimer_wakeup` callback is executed asynchronously in the context of the timer interrupt (hardirq) or the timer softirq.
Because the callback execution occurs in the interrupt context rather than the context of the sleeping task, the "current" task context changes. Therefore, the stored function pointer is executed asynchronously.
---

## Task 40: `hrtimer_wakeup` at `kernel/time/hrtimer.c:2286`
**Verdict:** Yes

In `schedule_hrtimeout_range_clock`, the function `hrtimer_init_sleeper_on_stack` is called, which initializes a high-resolution timer (`hrtimer_sleeper`).
As part of this initialization, the function pointer `hrtimer_wakeup` is stored into `sl->timer.function`.
The task then arms the timer and calls `schedule()` to put itself to sleep.
When the specified timeout expires, the hardware timer interrupt triggers, and the hrtimer subsystem executes the stored function pointer (`hrtimer_wakeup`).
This execution happens in a hardware interrupt (hardirq) or software interrupt (softirq) context, which interrupts whatever task happens to be running on the CPU at that moment.
Since the function is executed in an interrupt context rather than the task context of the original sleeping process, the execution is asynchronous and the context changes.
---

## Task 41: `inet6_sock_destruct` at `net/ipv6/af_inet6.c:215`
**Verdict:** Yes

The function pointer `inet6_sock_destruct` is assigned to the `sk->sk_destruct` callback during `inet6_create()` (`net/ipv6/af_inet6.c:215`), which is responsible for creating IPv6 sockets.

This callback is invoked when the socket is being destroyed and its memory freed. The destruction path begins when the last reference to the socket is dropped, which can happen asynchronously. For example:
1. The last reference (tracked by `sk->sk_wmem_alloc` or `sk->sk_refcnt`) might be dropped when the network driver finishes transmitting the final queued packet (`kfree_skb()` -> `sock_wfree()` -> `__sk_free()`), which occurs in softirq or hardirq context.
2. For certain types of sockets (like UDP or TCP listeners), the `SOCK_RCU_FREE` flag is set. In this case, `sk_destruct()` delegates the final destruction step to an RCU callback via `call_rcu()`. The `__sk_destruct()` function (which directly calls `sk->sk_destruct()`) will therefore run asynchronously in an RCU softirq context.

In both of these scenarios, the "current" task context changes (to an interrupt or RCU softirq context) and is disconnected from the user process that originally closed the socket. Thus, the function is executed asynchronously.
---

## Task 42: `invalid_mkclean_vma` at `mm/rmap.c:1087`
**Verdict:** No

In `mm/rmap.c`, `invalid_mkclean_vma` is assigned to the `invalid_vma` field of a `rmap_walk_control` struct within `folio_mkclean`.
This struct is then immediately passed to `rmap_walk(folio, &rwc)`, which traverses the reverse mapping structures of the folio.
During this traversal, `rmap_walk` synchronously calls the `invalid_vma` callback (`invalid_mkclean_vma`) to determine if a given VMA should be skipped.
Since the callback is invoked synchronously within the same execution path as the caller of `folio_mkclean`, the "current" task context does not change. Therefore, it is not executed asynchronously.
---

## Task 43: `io_fallback_req_func` at `io_uring/io_uring.c:341`
**Verdict:** Yes

In `io_ring_ctx_alloc`, the function pointer `io_fallback_req_func` is passed to the `INIT_DELAYED_WORK` macro.
This macro initializes a delayed work item (`ctx->fallback_work`) and stores the function pointer as its work callback.
When this delayed work is later scheduled (e.g., via `queue_delayed_work` or `schedule_delayed_work`), the kernel's workqueue subsystem queues it to be executed after a specified delay.
The execution of the callback function will take place in the context of a kernel worker thread (e.g., a `kworker` process), not in the context of the task that originally queued the work or created the io_uring context.
Because the function executes in a separate worker thread, the execution is asynchronous.
---

## Task 44: `io_ring_ctx_ref_free` at `lib/percpu-refcount.c:100`
**Verdict:** Yes

The function pointer `io_ring_ctx_ref_free` is stored as the `release` callback for a `percpu_ref` object (`ctx->refs`) using `percpu_ref_init()`.

A `percpu_ref` release callback executes when its reference count drops to zero. In `io_uring`, the base reference to the context is dropped by calling `percpu_ref_kill()` (typically from `io_ring_ctx_wait_and_kill()` during teardown). 

Crucially, `percpu_ref_kill()` does not allow the reference count to reach zero synchronously in the calling thread. Instead, it calls `__percpu_ref_switch_to_atomic()`, which grabs a temporary extra reference and schedules an RCU callback (`percpu_ref_switch_to_atomic_rcu`) to switch the reference counting mechanism. After scheduling this RCU work, `percpu_ref_kill()` drops the base reference.

Because of this temporary RCU reference, the refcount cannot drop to zero in the task that calls `percpu_ref_kill()`. The final drop will occur either:
1. In the RCU SoftIRQ context, when the RCU callback finishes the switch and drops the temporary reference.
2. In the context of a background worker (e.g., `io_wq`) or a deferred `task_work` handler, if transient references were still held when the RCU callback completed.

In all scenarios, the execution of `io_ring_ctx_ref_free` is deferred and runs asynchronously with respect to the task that initiated the destruction, ensuring the "current" task context changes.
---

## Task 45: `io_ring_exit_work` at `io_uring/io_uring.c:2900`
**Verdict:** Yes

In `io_uring/io_uring.c`, the `io_ring_ctx_wait_and_kill` function initializes a `work_struct` (`ctx->exit_work`) by calling `INIT_WORK` and passing the `io_ring_exit_work` function pointer as the work handler.
It then schedules this work for execution using `queue_work(iou_wq, &ctx->exit_work)`.
As a result, the `io_ring_exit_work` function is executed by a kernel worker thread associated with the `iou_wq` workqueue.
Since the work is queued by the task that is closing the io_uring file descriptor (e.g., during process exit) and is actually executed later by a different worker thread, the "current" task context changes. Thus, the execution is asynchronous.
---

## Task 46: `io_sq_thread` at `kernel/fork.c:2735`
**Verdict:** Yes

In `create_io_thread`, the provided function pointer `fn` (e.g., `io_sq_thread`) is stored into the `fn` field of a `kernel_clone_args` structure.
This structure is then passed to `copy_process` to spawn a new io_uring worker thread.
The stored function pointer serves as the entry point for the newly created thread.
Since the function is executed as the main routine of a brand new task rather than by the task that called `create_io_thread`, the execution happens in a different task context.
Thus, the execution is asynchronous.
---

## Task 47: `io_wq_free_work` at `io_uring/io-wq.c:1158`
**Verdict:** Yes

The `io_wq_free_work` function pointer is passed via `io_wq_data` and stored into `wq->free_work` during the creation of an io-wq instance (`io_wq_create()` in `io_uring/io-wq.c:1158`).

This function pointer is used to free an `io_wq_work` item after it has been executed.
It is primarily invoked through `wq->free_work(work)` within `io_worker_handle_work()`, which is called by the `io_wq_worker` kernel threads.

Since `io_wq_worker` threads are separate kernel threads created (via `create_io_thread`) to handle io_uring work asynchronously in the background, the execution of `wq->free_work()` happens in the context of these worker threads. Therefore, the "current" task context changes from the user process that originally submitted the I/O request to the `io_wq_worker` kernel thread.

Thus, the stored function is executed asynchronously.
---

## Task 48: `io_wq_free_work` at `io_uring/tctx.c:38`
**Verdict:** Yes

In `io_uring/tctx.c`, `io_uring_alloc_task_context` calls `io_init_wq_offload` to allocate and initialize an `io_wq` for the task.
During this initialization, `io_wq_free_work` is assigned to the `free_work` field of the `io_wq_data` structure, which is then passed to `io_wq_create`.
This function pointer is stored in the resulting `io_wq` object and is later invoked as `wq->free_work(work)` by the io_uring worker threads (e.g. inside `io_worker_handle_work`).
These worker threads are spawned to handle I/O requests asynchronously in the background.
Because `io_wq_free_work` is executed by a background worker thread rather than the user task that originally initialized the `io_wq` and submitted the I/O request, the "current" task context changes. Therefore, the stored function pointer is executed asynchronously.
---

## Task 49: `io_wq_hash_wake` at `io_uring/io-wq.c:1170`
**Verdict:** Yes

In `io_wq_create`, the function pointer `io_wq_hash_wake` is stored into `wq->wait.func`, initializing a wait queue entry.
Later, this wait queue entry is added to a wait queue (`wq->hash->wait`) via `__add_wait_queue`.
When another thread or interrupt handler signals that the waited-on condition has changed (e.g., via `wake_up` on the wait queue), the kernel iterates over the wait queue and executes the stored callback function (`io_wq_hash_wake`).
Because the callback is executed by the task or interrupt handler that calls `wake_up`, rather than the task that created the `io_wq` and initialized the wait queue entry, the execution happens in a different context.
Therefore, the execution is asynchronous.
---

## Task 50: `io_wq_submit_work` at `io_uring/io-wq.c:1159`
**Verdict:** Yes

In `io_uring/io-wq.c`, the `io_wq_create` function initializes a new `io_wq` structure and copies the `do_work` function pointer from the provided `io_wq_data`. In this case, `do_work` points to `io_wq_submit_work`.
This function pointer is later invoked as `wq->do_work(work)` by the io_uring worker threads (specifically within `io_worker_handle_work`).
Since the worker threads run in the background to handle I/O operations asynchronously, the execution of `io_wq_submit_work` occurs in a different task context than the one that created the workqueue and submitted the work.
Because the "current" task context is different (it is now the worker thread), the stored function pointer is executed asynchronously.
---

## Task 51: `io_wq_submit_work` at `io_uring/tctx.c:39`
**Verdict:** Yes

The `io_wq_submit_work` function pointer is assigned to `data.do_work` inside `io_init_wq_offload()` (called from `io_uring_alloc_task_context()` in `io_uring/tctx.c:39`). This configuration data is then used to initialize a new `io_wq` via `io_wq_create()`, storing the function in `wq->do_work`.

This `do_work` callback represents the actual work function that io-wq must execute for each queued work item. It is invoked as `wq->do_work(work)` inside `io_worker_handle_work()`, which is executed by the dedicated `io_wq_worker` kernel threads (created to handle asynchronous io_uring requests).

Because `io_wq_submit_work` is run by these separate worker threads, the "current" task context during execution is the worker thread (e.g., `iou-wrk-XXX`) rather than the user process that submitted the request. Therefore, the execution of the stored function pointer happens asynchronously.
---

## Task 52: `ip_local_deliver` at `net/ipv4/route.c:1630`
**Verdict:** Yes

In `rt_dst_alloc` (called from routing functions like `ip_route_output_key_hash_rcu`), the function pointer `ip_local_deliver` is stored into `rt->dst.input` for routes that are destined to the local machine.
This function pointer is later invoked via `dst_input()` when a packet destined for the local host is received.
Packet reception processing generally happens in the context of the networking softirq (`NET_RX_SOFTIRQ`), which is triggered by hardware interrupts from network interface cards or by virtual devices like the loopback interface.
Because softirqs interrupt whatever task happens to be running on the CPU at the time of the interrupt, or they are processed by dedicated `ksoftirqd` kernel threads, the `current` task context during the execution of `ip_local_deliver` will generally be completely unrelated to the task that originally configured the route.
Thus, the execution of the stored function pointer is asynchronous.
---

## Task 53: `isofs_free_inode` at `fs/inode.c:315`
**Verdict:** Yes

In `fs/inode.c`, the `evict` function calls `destroy_inode` as part of the process of removing an inode.
Within `destroy_inode`, the `free_inode` function pointer from the filesystem's `super_operations` (in this case, `isofs_free_inode` for the isofs filesystem) is assigned to `inode->free_inode`.
The execution of the actual freeing is then deferred using `call_rcu(&inode->i_rcu, i_callback)`.
The `call_rcu` function schedules `i_callback` to run after an RCU grace period. When `i_callback` is eventually invoked by the RCU subsystem (typically from a softirq or an RCU kthread), it calls `inode->free_inode()`.
Because the execution is deferred via RCU, the callback runs in a different task context than the one that originally called `evict`. Thus, the execution is asynchronous.
---

## Task 54: `it_real_fn` at `kernel/fork.c:1882`
**Verdict:** Yes

The function pointer `it_real_fn` is assigned to `sig->real_timer.function` during `copy_signal()` (`kernel/fork.c:1882`), which is called when creating a new process to initialize its signal structures.

The `real_timer` field is a high-resolution timer (`struct hrtimer`) used to implement POSIX interval timers (specifically, the `ITIMER_REAL` timer which sends `SIGALRM` upon expiration).
When this timer expires, the kernel invokes the callback `it_real_fn` via the hrtimer expiration path (e.g., `__run_hrtimer()`), which is executed from the timer interrupt handler (hardirq) or the timer softirq handler.

Because the timer expires asynchronously, the callback will be executed in interrupt or softirq context, interrupting whichever task happens to be currently running on the CPU. Therefore, the "current" task context changes to an interrupt context when `it_real_fn` is called, meaning it is executed asynchronously.
---

## Task 55: `kmmpd` at `kernel/kthread.c:441`
**Verdict:** Yes

In `kernel/kthread.c`, `__kthread_create_on_node` assigns the provided `threadfn` (which in this case is `kmmpd` from `fs/ext4/mmp.c`) to the `threadfn` field of a `kthread_create_info` structure.
This structure is then queued for `kthreadd`, which creates a new kernel thread. The newly spawned kernel thread executes the `kthread` wrapper function, which in turn calls the stored `threadfn`.
Because `kmmpd` is executed by the newly created kernel thread rather than the task that called `__kthread_create_on_node`, the "current" task context changes. Therefore, the execution is asynchronous.
---

## Task 56: `loop_workfn` at `drivers/block/loop.c:883`
**Verdict:** Yes

The function pointer `loop_workfn` is stored in the `func` field of a `work_struct` when `INIT_WORK(&worker->work, loop_workfn)` is called. This occurs dynamically during I/O request queuing (inside `loop_queue_work()`, which is called by the block layer's `loop_queue_rq()`).

The `worker->work` item is then submitted to the loop device's workqueue (`lo->workqueue`) via `queue_work()`.
Because this is a workqueue item, the function `loop_workfn` will be executed by a kernel worker thread (managed by the workqueue subsystem) in the background.

Since it runs in a background worker thread rather than in the context of the task that originally submitted the block I/O request, the "current" task context will change to the kernel worker thread when the callback is executed. Therefore, the function pointer is executed asynchronously.
---

## Task 57: `lru_add_drain_per_cpu` at `mm/swap.c:895`
**Verdict:** Yes

In `__lru_add_drain_all`, the function pointer `lru_add_drain_per_cpu` is passed to the `INIT_WORK` macro to initialize a work item for each online CPU that requires draining.
The work item is then scheduled for execution on its respective CPU using `queue_work_on` onto the `mm_percpu_wq` workqueue.
Although the caller subsequently waits for these work items to complete via `flush_work`, the actual execution of `lru_add_drain_per_cpu` takes place in the context of the workqueue's worker threads (e.g., `kworker`).
Since the function is executed by a separate kernel worker thread rather than the task that called `__lru_add_drain_all`, the `current` task context changes. Thus, the execution is asynchronous.
---

## Task 58: `mb_cache_count` at `fs/mbcache.c:385`
**Verdict:** Yes

In `fs/mbcache.c`, the `mb_cache_create` function allocates a shrinker and assigns `mb_cache_count` to the `count_objects` field of the shrinker structure.
This shrinker is then registered with the memory management subsystem using `shrinker_register`.
Shrinker callbacks, such as `count_objects`, are invoked by the memory management subsystem during memory reclaim operations. These operations are typically performed asynchronously by kernel threads like `kswapd` or directly by arbitrary tasks that are attempting to allocate memory and have triggered direct reclaim.
Because the `mb_cache_count` function is called by the memory reclaim subsystem in a context separate from the task that created the `mb_cache`, the "current" task context changes. Therefore, the execution is asynchronous.
---

## Task 59: `mb_cache_scan` at `fs/mbcache.c:386`
**Verdict:** Yes

The function pointer `mb_cache_scan` is stored in the `scan_objects` field of a `struct shrinker` during the execution of `mb_cache_create()`.

This function serves as a shrinker callback for the kernel's memory management subsystem. It is invoked when the system faces memory pressure and needs to reclaim memory by shrinking caches. The invocation occurs in `do_shrink_slab()`, which is called during memory reclaim.

Memory reclaim is performed either by the background kernel thread `kswapd` or via direct reclaim by any arbitrary process that attempts to allocate memory when memory is low. In both cases, the callback is executed in a task context (kswapd or a random allocating process) that is completely independent of and decoupled from the task that originally registered the shrinker (e.g., the process that mounted the filesystem). As a result, the "current" task context changes when the function is called, making its execution asynchronous with respect to the initial store operation.
---

## Task 60: `mb_cache_shrink_worker` at `fs/mbcache.c:391`
**Verdict:** Yes

In `mb_cache_create`, the function pointer `mb_cache_shrink_worker` is passed to the `INIT_WORK` macro to initialize a work item (`cache->c_shrink_work`).
When certain conditions are met (e.g., when the cache size needs to be reduced), `schedule_work(&cache->c_shrink_work)` is called to queue this work item on the system workqueue.
The kernel's workqueue subsystem then schedules the work to be executed by a worker thread (such as `kworker`).
Because the callback function is executed in the context of this worker thread rather than the task that created the cache or the task that called `schedule_work`, the execution context changes.
Thus, the execution is asynchronous.
---

## Task 61: `migration_cpu_stop` at `kernel/stop_machine.c:142`
**Verdict:** Yes

In `kernel/stop_machine.c`, the `stop_one_cpu` function receives a function pointer (`fn`) and an argument, and assigns them to a `cpu_stop_work` structure.
This work structure is then queued to the `cpu_stopper` associated with the specified target CPU via `cpu_stop_queue_work`.
Each CPU has a dedicated `cpu_stopper` kernel thread (named `migration/%u`). This stopper thread wakes up, retrieves the queued work, and executes the provided function (`fn(arg)`).
Because the function (in this case `migration_cpu_stop`) is executed by the target CPU's stopper thread rather than the task that called `stop_one_cpu`, the execution context changes. Thus, the execution is asynchronous.
---

## Task 62: `mon_bin_complete` at `drivers/usb/mon/mon_bin.c:718`
**Verdict:** Yes

The function pointer `mon_bin_complete` is stored in the `rnf_complete` field of a `mon_reader` structure inside `mon_bin_open()` (`drivers/usb/mon/mon_bin.c:718`), which is called when a userspace application opens a `usbmon` device to trace USB traffic.

The `rnf_complete` callback is invoked by the USB monitor core (`mon_bus_complete()` in `mon_main.c`) whenever an outstanding USB Request Block (URB) completes.
URB completion is driven by the USB Host Controller Driver (HCD) upon receiving hardware interrupts indicating that a USB transfer has finished. The HCD then gives back the URB, which propagates to the `urb_complete` hook and eventually calls `rnf_complete`.

Because this callback is executed as part of the USB hardware interrupt or softirq completion path, the "current" task context will be whatever process happens to be executing when the interrupt occurs, or a kernel softirq thread. It is completely independent of the task that originally opened the device or submitted the URB. Therefore, the function pointer is executed asynchronously.
---

## Task 63: `mon_bin_error` at `drivers/usb/mon/mon_bin.c:717`
**Verdict:** Yes

The `mon_bin_open` function serves as the `.open` callback for `usbmon` device files (e.g., `/dev/usbmon1`). When a userspace process opens this file, `mon_bin_open` runs in the context of that process. During initialization, it stores the function pointer `mon_bin_error` into `rp->r.rnf_error` and adds the reader structure `rp->r` to the USB monitor bus's reader list (`mbus->r_list`).

The stored function pointer, `mon_bin_error`, is invoked when an URB (USB Request Block) submission fails synchronously. This happens in `usb_hcd_submit_urb`, which calls `usbmon_urb_submit_error`. This cascades down to `mon_submit_error` and then `mon_bus_submit_error`, which iterates through the readers in `mbus->r_list` and calls their `rnf_error` callbacks. 

Because URB submissions are performed by various USB device drivers across the system (often in different process contexts, kernel threads, or even interrupt contexts), the context in which `mon_bin_error` is executed will be completely unrelated to the original process that opened the `usbmon` device file. Therefore, the execution of the stored function pointer is asynchronous and occurs in a different "current" task context.
---

## Task 64: `mon_bin_submit` at `drivers/usb/mon/mon_bin.c:716`
**Verdict:** Yes

The stored function pointer `mon_bin_submit` is assigned to the `rnf_submit` field of a `struct mon_reader` during the execution of `mon_bin_open`. `mon_bin_open` is the open handler for the usbmon device and executes in the context of the task that opens the device file (e.g., during `sys_open`). The stored function `mon_bin_submit` is later called by the USB core via `usbmon_urb_submit()` -> `mon_submit()` -> `mon_bus_submit()` whenever an URB is submitted to the monitored USB bus. URB submission (`usb_submit_urb`) can be performed by various USB drivers running in different task contexts (e.g., a driver submitting an URB from its own worker thread, or a different process calling into USB devio). Therefore, the stored function will be executed asynchronously in a different task context from where it was originally stored.
---

## Task 65: `mpage_end_io` at `fs/ext4/readpage.c:359`
**Verdict:** Yes

The function pointer `mpage_end_io` is assigned to the `bi_end_io` field of a `struct bio` object in `ext4_mpage_readpages`.
A `bio` structure represents an in-flight block I/O operation. The `bi_end_io` callback is invoked by the block layer when the I/O operation completes.
Because block I/O is asynchronous, the completion callback is generally executed in a different context than the submitting thread, typically in a softirq (e.g., `BLOCK_SOFTIRQ`), interrupt context, or a separate worker thread handling completions.
Consequently, the "current" task context will change between the time the function pointer is stored (during I/O submission) and when it is executed (during I/O completion).
Therefore, the execution is asynchronous.
---

## Task 66: `mpage_read_end_io` at `fs/mpage.c:314`
**Verdict:** Yes

The function pointer `mpage_read_end_io` is stored into `bio->bi_end_io` within the inline function `mpage_bio_submit_read` (which is inlined into `do_mpage_readpage` at line 314 in `fs/mpage.c`).
After setting the `bi_end_io` callback, the bio is submitted to the block layer via `submit_bio(bio)`.
The block layer handles the bio and sends it to the device driver. When the block I/O operation completes, the block device driver will trigger an interrupt. The completion is typically processed in a softirq context (e.g., `BLOCK_SOFTIRQ`), where `bio_endio()` is called. `bio_endio()` in turn invokes the `bi_end_io` callback (which is `mpage_read_end_io`).
Because the completion runs in an interrupt/softirq context or a worker thread, the "current" task context at the time `mpage_read_end_io` is executed will be different from the context of the task that originally called `do_mpage_readpage`. Therefore, it will be executed asynchronously.
---

## Task 67: `mpage_read_end_io` at `fs/mpage.c:384`
**Verdict:** Yes

The function pointer `mpage_read_end_io` is assigned to the `bi_end_io` field of a `struct bio` object in `mpage_bio_submit_read`, which is called from `mpage_readahead`.
A `bio` represents a block I/O operation (a read in this case). The `bi_end_io` callback is invoked by the block layer when the I/O operation completes.
Block I/O is asynchronous, meaning the completion callback is executed in a different context than the submitting thread—typically in a softirq (e.g., `BLOCK_SOFTIRQ`), interrupt context, or a separate worker thread handling completions.
Consequently, the "current" task context will change between the time the function pointer is stored (during I/O submission) and when it is executed (during I/O completion).
Therefore, the execution is asynchronous.
---

## Task 68: `mpage_read_end_io` at `fs/mpage.c:80`
**Verdict:** Yes

The function pointer `mpage_read_end_io` is stored into `bio->bi_end_io` within `mpage_bio_submit_read` at line 80 in `fs/mpage.c`.
After setting the `bi_end_io` callback, the bio is submitted to the block layer via `submit_bio(bio)`.
The block layer handles the bio and sends it to the device driver. When the block I/O operation completes, the block device driver will trigger an interrupt. The completion is typically processed in a softirq context (e.g., `BLOCK_SOFTIRQ`), where `bio_endio()` is called. `bio_endio()` in turn invokes the `bi_end_io` callback (which is `mpage_read_end_io`).
Because the completion runs in an interrupt/softirq context or a worker thread, the "current" task context at the time `mpage_read_end_io` is executed will be different from the context of the task that originally submitted the bio. Therefore, it will be executed asynchronously.
---

## Task 69: `mq_flush_data_end_io` at `block/blk-flush.c:391`
**Verdict:** Yes

The function pointer `mq_flush_data_end_io` is assigned to the `end_io` field of a `struct request` object in `blk_rq_init_flush`, called by `blk_insert_flush`.
A `struct request` in the block layer represents a pending block I/O command sent to a block device.
The `end_io` callback is executed when the block device completes the I/O request. Because hardware I/O is asynchronous, this completion occurs in a different context from the submitting thread, typically in an interrupt handler or a softirq (like `BLOCK_SOFTIRQ`).
Therefore, the "current" task context will change between the time the function pointer is stored and when it is executed.
The execution is asynchronous.
---

## Task 70: `neigh_blackhole` at `net/core/neighbour.c:503`
**Verdict:** Yes

The function pointer `neigh_blackhole` is stored into `n->output` within `___neigh_create` at line 503 in `net/core/neighbour.c`.
This assigns the default output function for a newly allocated `neighbour` structure. The `output` function pointer in the neighbour structure acts as an indirect call for transmitting packets to this neighbour. It is invoked during the packet transmission path (e.g., `neigh_output`, `dst_neigh_output`).
Because the `neighbour` entry is added to a global hash table and can be accessed by the network stack to route packets, the `output` function will be called by whatever task or softirq context (such as `NET_TX_SOFTIRQ` or a different user process) happens to be transmitting a packet to this network neighbor. While the creating task might occasionally call it immediately, it is fundamentally an asynchronous callback mechanism used by the network stack's transmit path, and its context will change.
---

## Task 71: `neigh_timer_handler` at `kernel/time/timer.c:900`
**Verdict:** Yes

The function pointer `neigh_timer_handler` is used as a timer callback, assigned during timer initialization.
Kernel timers are executed asynchronously. When a timer expires, its callback is invoked by the kernel's timer softirq (`TIMER_SOFTIRQ`) via `run_timer_softirq`.
Because the timer is scheduled in one context (e.g., during network neighbor creation or an ARP event) and executed later in the softirq context, the "current" task context will inevitably change between the store and the execution.
Therefore, the execution of the stored function pointer is asynchronous.
---

## Task 72: `netlbl_calipso_add` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `netlbl_calipso_add` is stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 73: `netlbl_calipso_add` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `netlbl_calipso_add` is assigned to the `.doit` member of the `netlbl_calipso_ops` generic netlink operations array in `net/netlabel/netlabel_calipso.c`. This array is passed during the registration of the NetLabel CALIPSO generic netlink family (`netlbl_calipso_gnl_family`) at kernel/module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback around (for example, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `netlbl_calipso_add` function pointer happens when a userspace process sends a generic netlink message with the command `NLBL_CALIPSO_C_ADD` over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) will look up the registered operation and call `ops->doit(skb, &info)`.

Because the function pointer is stored during module/kernel initialization but executed much later in the context of whatever arbitrary userspace process sends the corresponding netlink message, its execution is completely asynchronous, and the "current" task context changes.
---

## Task 74: `netlbl_calipso_list` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `netlbl_calipso_list` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit` (or `genl_dumpit` via the dump control structure if it's a dump).
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 75: `netlbl_calipso_list` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_calipso_list` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata (like policies and flags).
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 76: `netlbl_calipso_listall` at `net/netlink/genetlink.c:188`
**Verdict:** No

The function pointer `netlbl_calipso_listall` is loaded from a static array and stored into the local `op->dumpit` field inside `genl_op_from_small()`. This occurs during the processing of a netlink message within `genl_rcv_msg()`. Following the store, the execution continues synchronously down the call stack: `genl_family_rcv_msg()` calls `genl_family_rcv_msg_dumpit()`, which calls `__netlink_dump_start()`. Inside `__netlink_dump_start()`, the `ops` structure is copied to a heap allocation via `genl_start()`, and then `netlink_dump()` is immediately invoked. `netlink_dump()` synchronously calls the callback `cb->dump` (`genl_dumpit()`), which in turn executes the stored `ops->dumpit` function (`netlbl_calipso_listall`). Because this entire sequence from the store operation to the first execution of the function pointer happens synchronously within the same netlink message processing path (typically the `sendmsg` syscall), the "current" task context remains exactly the same.
---

## Task 77: `netlbl_calipso_listall` at `net/netlink/genetlink.c:272`
**Verdict:** Yes

The function pointer `netlbl_calipso_listall` is assigned to the `.dumpit` member of the `netlbl_calipso_ops` generic netlink operations array in `net/netlabel/netlabel_calipso.c`. This array is registered as part of the NetLabel CALIPSO generic netlink family (`netlbl_calipso_gnl_family`) during kernel or module initialization.

During internal processing, the generic netlink (`genetlink`) core propagates this callback (e.g., in `genl_cmd_full_to_split` where `op->dumpit = full->dumpit` occurs).

The execution of `netlbl_calipso_listall` occurs when a userspace process sends a generic netlink dump request using the command `NLBL_CALIPSO_C_LISTALL`. The kernel's netlink receive path handles this via `genl_rcv_msg` and `genl_family_rcv_msg_dumpit`, setting up a netlink dump. The `dumpit` callback is subsequently invoked through `genl_dumpit` calling `ops->dumpit(skb, cb)`.

Since the function pointer is registered during the system initialization context but is later executed on-demand in the context of whichever userspace process initiates the netlink dump (via socket receive operations), its execution is entirely asynchronous and involves a different "current" task context.
---

## Task 78: `netlbl_calipso_remove` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `netlbl_calipso_remove` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 79: `netlbl_calipso_remove` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `netlbl_calipso_remove` is assigned to the `.doit` member of the `netlbl_calipso_ops` generic netlink operations array in `net/netlabel/netlabel_calipso.c`. This array is passed during the registration of the NetLabel CALIPSO generic netlink family (`netlbl_calipso_gnl_family`) at kernel/module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback around (for example, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `netlbl_calipso_remove` function pointer happens when a userspace process sends a generic netlink message with the command `NLBL_CALIPSO_C_REMOVE` over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) will look up the registered operation and call `ops->doit(skb, &info)`.

Because the function pointer is stored during module/kernel initialization but executed much later in the context of whatever arbitrary userspace process sends the corresponding netlink message, its execution is completely asynchronous, and the "current" task context changes.
---

## Task 80: `netlbl_cipsov4_add` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `netlbl_cipsov4_add` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 81: `netlbl_cipsov4_add` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_cipsov4_add` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata (like policies and flags).
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 82: `netlbl_cipsov4_list` at `net/netlink/genetlink.c:187`
**Verdict:** Yes

The function `netlbl_cipsov4_list` is assigned to the `.doit` member of the `netlbl_cipsov4_ops` generic netlink operations array in `net/netlabel/netlabel_cipso_v4.c`. This array is provided during the registration of the NetLabel CIPSOv4 generic netlink family (`netlbl_cipsov4_gnl_family`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_op_from_small` where `op->doit = family->small_ops[i].doit` is executed). 

The actual execution of the `netlbl_cipsov4_list` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NLBL_CIPSOV4_C_LIST`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 83: `netlbl_cipsov4_list` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_cipsov4_list` is stored into `op->doit` within `genl_cmd_full_to_split` at line 276 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation. This conversion is called during the generic netlink message receive process (via `genl_get_cmd`) and during iteration (via `genl_op_iter_next`).
When called during message reception (`genl_family_rcv_msg`), the `op` variable is allocated on the stack. Immediately after lookup and conversion, the generic netlink core invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 84: `netlbl_cipsov4_listall` at `net/netlink/genetlink.c:188`
**Verdict:** No

The function pointer `netlbl_cipsov4_listall` is assigned to `op->dumpit` inside `genl_op_from_small` to handle a Generic Netlink dump request.
When a dump request is received, the pointer is ultimately passed to the netlink dump infrastructure (e.g., stored in `genl_dumpit_info`) and executed by `genl_dumpit`.
Netlink dumps are executed synchronously in the context of the user-space process making the system call. The initial execution occurs during the `sendmsg` syscall. If the dump requires multiple messages, it is paused and later resumed when the user-space process makes subsequent `recvmsg` syscalls to retrieve the remaining data.
Because the dump is always executed by the user thread actively making the system call, the "current" task context remains that of the invoking user process and does not change to a background kernel thread or softirq.
Therefore, the execution is not asynchronous.
---

## Task 85: `netlbl_cipsov4_listall` at `net/netlink/genetlink.c:272`
**Verdict:** No

The function pointer `netlbl_cipsov4_listall` is stored into `iter->dumpit.dumpit` by `genl_cmd_full_to_split()` when invoked via `genl_op_iter_next()`. The `genl_op_iter_next()` function is merely an iterator used to extract metadata about generic netlink family operations (such as command IDs, policy flags, and attributes) in order to validate them during registration or report them to userspace via the generic netlink control commands (e.g., in `ctrl_fill_info()`). The function pointer stored within the `struct genl_op_iter` instance is solely used to check for the presence of the operation (or its associated policy) and is never actually executed from this structure. Since the function is never executed as a result of this specific store operation, it is not executed asynchronously.
---

## Task 86: `netlbl_cipsov4_remove` at `net/netlink/genetlink.c:187`
**Verdict:** Yes

The function `netlbl_cipsov4_remove` is assigned to the `.doit` member of the `netlbl_cipsov4_ops` generic netlink operations array in `net/netlabel/netlabel_cipso_v4.c`. This array is provided during the registration of the NetLabel CIPSOv4 generic netlink family (`netlbl_cipsov4_gnl_family`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_op_from_small` where `op->doit = family->small_ops[i].doit` is executed). 

The actual execution of the `netlbl_cipsov4_remove` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NLBL_CIPSOV4_C_REMOVE`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 87: `netlbl_cipsov4_remove` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_cipsov4_remove` is stored into `op->doit` within `genl_cmd_full_to_split` at line 276 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation. This conversion is called during the generic netlink message receive process (via `genl_get_cmd`) and during iteration (via `genl_op_iter_next`).
When called during message reception (`genl_family_rcv_msg`), the `op` variable is allocated on the stack. Immediately after lookup and conversion, the generic netlink core invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 88: `netlbl_unlabel_accept` at `net/netlink/genetlink.c:187`
**Verdict:** Yes

The function `netlbl_unlabel_accept` is assigned to the `.doit` member of the `netlbl_unlabel_ops` generic netlink operations array in `net/netlabel/netlabel_unlabeled.c`. This array is provided during the registration of the NetLabel Unlabeled generic netlink family (`netlbl_unlabel_gnl_family`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_op_from_small` where `op->doit = family->small_ops[i].doit` is executed). 

The actual execution of the `netlbl_unlabel_accept` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NLBL_UNLABEL_C_ACCEPT`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 89: `netlbl_unlabel_accept` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_unlabel_accept` is stored into `op->doit` within `genl_cmd_full_to_split` at line 276 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation. This conversion is called during the generic netlink message receive process (via `genl_get_cmd`) and during iteration (via `genl_op_iter_next`).
When called during message reception (`genl_family_rcv_msg`), the `op` variable is allocated on the stack. Immediately after lookup and conversion, the generic netlink core invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 90: `netlbl_unlabel_list` at `net/netlink/genetlink.c:187`
**Verdict:** Yes

The function `netlbl_unlabel_list` is assigned to the `.doit` member of the `netlbl_unlabel_ops` generic netlink operations array in `net/netlabel/netlabel_unlabeled.c`. This array is provided during the registration of the NetLabel Unlabeled generic netlink family (`netlbl_unlabel_gnl_family`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_op_from_small` where `op->doit = family->small_ops[i].doit` is executed). 

The actual execution of the `netlbl_unlabel_list` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NLBL_UNLABEL_C_LIST`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 91: `netlbl_unlabel_list` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_unlabel_list` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata (like policies and flags).
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 92: `netlbl_unlabel_staticadd` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `netlbl_unlabel_staticadd` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 93: `netlbl_unlabel_staticadd` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `netlbl_unlabel_staticadd` is assigned to the `.doit` member of the `netlbl_unlabel_ops` generic netlink operations array in `net/netlabel/netlabel_unlabeled.c`. This array is provided during the registration of the NetLabel Unlabeled generic netlink family (`netlbl_unlabel_gnl_family`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `netlbl_unlabel_staticadd` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NLBL_UNLABEL_C_STATICADD`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 94: `netlbl_unlabel_staticadddef` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `netlbl_unlabel_staticadddef` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 95: `netlbl_unlabel_staticadddef` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_unlabel_staticadddef` is stored into `op->doit` within `genl_cmd_full_to_split` at line 276 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation. This conversion is called during the generic netlink message receive process (via `genl_get_cmd`) and during iteration (via `genl_op_iter_next`).
When called during message reception (`genl_family_rcv_msg`), the `op` variable is allocated on the stack. Immediately after lookup and conversion, the generic netlink core invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 96: `netlbl_unlabel_staticlist` at `net/netlink/genetlink.c:188`
**Verdict:** No

The function pointer `netlbl_unlabel_staticlist` is loaded from a static array and stored into the local `op->dumpit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a netlink message within `genl_rcv_msg()`. Following the store, execution continues synchronously down the call stack: `genl_family_rcv_msg()` calls `genl_family_rcv_msg_dumpit()`, which calls `__netlink_dump_start()`. Inside `__netlink_dump_start()`, the `ops` structure is copied to a heap allocation via `genl_start()`, and then `netlink_dump()` is immediately invoked. `netlink_dump()` synchronously calls the callback `cb->dump` (`genl_dumpit()`), which in turn executes the stored `ops->dumpit` function (`netlbl_unlabel_staticlist`). Because this entire sequence from the store operation to the first execution of the function pointer happens synchronously within the same netlink message processing path (typically the `sendmsg` syscall), the "current" task context remains exactly the same.
---

## Task 97: `netlbl_unlabel_staticlist` at `net/netlink/genetlink.c:272`
**Verdict:** Yes

The function `netlbl_unlabel_staticlist` is assigned to the `.dumpit` member of the `netlbl_unlabel_ops` generic netlink operations array in `net/netlabel/netlabel_unlabeled.c`. This array is registered as part of the NetLabel Unlabeled generic netlink family (`netlbl_unlabel_gnl_family`) during kernel or module initialization.

During internal processing, the generic netlink (`genetlink`) core propagates this callback (e.g., in `genl_cmd_full_to_split` where `op->dumpit = full->dumpit` occurs).

The execution of `netlbl_unlabel_staticlist` occurs when a userspace process sends a generic netlink dump request using the corresponding command (`NLBL_UNLABEL_C_STATICLIST`). The kernel's netlink receive path handles this via `genl_rcv_msg` and `genl_family_rcv_msg_dumpit`, setting up a netlink dump. The `dumpit` callback is subsequently invoked through `genl_dumpit` calling `ops->dumpit(skb, cb)`.

Since the function pointer is registered during the system initialization context but is later executed on-demand in the context of whichever userspace process initiates the netlink dump (via socket receive operations), its execution is entirely asynchronous and involves a different "current" task context.
---

## Task 98: `netlbl_unlabel_staticlistdef` at `net/netlink/genetlink.c:188`
**Verdict:** No

The function pointer `netlbl_unlabel_staticlistdef` is assigned to `op->dumpit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink dump request.
When a dump request is received, the pointer is ultimately executed by `genl_dumpit` within the netlink dump infrastructure.
Netlink dumps are executed synchronously in the context of the user-space process making the system call. The initial execution occurs during the `sendmsg` syscall. If the dump requires multiple messages, it is paused and later resumed when the user-space process makes subsequent `recvmsg` syscalls.
Because the dump is always executed by the user thread actively making the system call, the "current" task context remains that of the invoking user process and does not change to an asynchronous background context.
Therefore, the execution is not asynchronous.
---

## Task 99: `netlbl_unlabel_staticlistdef` at `net/netlink/genetlink.c:272`
**Verdict:** No

The function pointer `netlbl_unlabel_staticlistdef` is stored into `op->dumpit` within `genl_cmd_full_to_split` at line 272 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation during the generic netlink message receive process (`genl_family_rcv_msg`).
When it is a dump operation, the `op` structure (allocated on the stack) is subsequently copied into a heap-allocated `struct genl_dumpit_info` within `genl_start`. The generic netlink core then invokes the stored `dumpit` function pointer via `ops->dumpit(skb, cb)` within `genl_dumpit`.
This invocation occurs synchronously in the context of the user space process interacting with the netlink socket (initially during `sendmsg`, and for subsequent chunks during `recvmsg`). The execution is not deferred to an asynchronous background worker or softirq, meaning the "current" task context remains the process performing the netlink dump. Therefore, it is executed synchronously.
---

## Task 100: `netlbl_unlabel_staticremove` at `net/netlink/genetlink.c:187`
**Verdict:** Yes

The function `netlbl_unlabel_staticremove` is assigned to the `.doit` member of the `netlbl_unlabel_ops` generic netlink operations array in `net/netlabel/netlabel_unlabeled.c`. This array is provided during the registration of the NetLabel Unlabeled generic netlink family (`netlbl_unlabel_gnl_family`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_op_from_small` where `op->doit = family->small_ops[i].doit` is executed). 

The actual execution of the `netlbl_unlabel_staticremove` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NLBL_UNLABEL_C_STATICREMOVE`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 101: `netlbl_unlabel_staticremove` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_unlabel_staticremove` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata.
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 102: `netlbl_unlabel_staticremovedef` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `netlbl_unlabel_staticremovedef` is loaded from a static array and stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 103: `netlbl_unlabel_staticremovedef` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `netlbl_unlabel_staticremovedef` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata.
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 104: `netlink_sock_destruct` at `net/netlink/af_netlink.c:661`
**Verdict:** Yes

The function `netlink_sock_destruct` is assigned to `sk->sk_destruct` within `__netlink_create` in `net/netlink/af_netlink.c`. This happens when a userspace process creates a netlink socket using the `socket(AF_NETLINK, ...)` system call.

The `sk_destruct` callback is invoked when the socket's reference count drops to zero and it is being destroyed. This occurs in `__sk_destruct`, which is called by `sk_destruct` (in `net/core/sock.c`). 

Crucially, the invocation of `__sk_destruct` can be deferred via RCU (`call_rcu(&sk->sk_rcu, __sk_destruct)`) if the socket is flagged for RCU free (e.g., `SOCK_RCU_FREE` or via `reuseport`). When executed via an RCU callback, the `sk_destruct` function pointer runs in the context of an RCU softirq or an RCU kthread, which is completely different from the context of the task that originally called `socket()`.

Furthermore, even in synchronous cases, the socket might be closed and destroyed by a completely different process (if the file descriptor was inherited or passed over a Unix domain socket) or by a kernel thread dropping the last reference.

Because the execution of this callback happens during object destruction—which can be deferred to an RCU softirq context or triggered by a different task dropping the last reference—it is fundamentally asynchronous, and the "current" task context changes.
---

## Task 105: `nfnetlink_bind` at `net/netlink/af_netlink.c:716`
**Verdict:** Yes

The function pointer `nfnetlink_bind` is stored in the `netlink_bind` field of a `struct netlink_sock` during the execution of `netlink_create()`. `netlink_create()` is invoked when a user-space application creates a new netlink socket using the `socket()` system call. The stored function pointer is not executed immediately. Instead, it is executed later when the application invokes the `bind()` or `setsockopt(..., NETLINK_ADD_MEMBERSHIP, ...)` system calls on that socket file descriptor. Because the execution is deferred to a subsequent, distinct system call, the function pointer is executed asynchronously relative to its store location, and potentially in a different task context if the socket file descriptor is shared across multiple tasks.
---

## Task 106: `nfnetlink_unbind` at `net/netlink/af_netlink.c:717`
**Verdict:** Yes

The function pointer `nfnetlink_unbind` is stored into `nlk->netlink_unbind` within `netlink_create` at line 717 (or 718 depending on exact alignment) in `net/netlink/af_netlink.c`.
This assignment occurs during the creation of a netlink socket (in the `socket()` syscall path). The stored `unbind` callback is later invoked to clean up netlink multicast group bindings when the socket is closed (via `netlink_release`) or if a bind operation fails (`netlink_undo_bind`).
Because the socket is exposed to userspace as a file descriptor, it can be shared with other processes (e.g., via `fork()` or Unix domain sockets), and its final reference may be dropped by a different task than the one that created it. Furthermore, the final `fput()` that triggers `netlink_release` can sometimes be deferred to a background worker. Therefore, the function acts as an object lifecycle callback and its execution context can change, meaning it is executed asynchronously relative to the socket creation.
---

## Task 107: `nl80211_abort_scan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_abort_scan` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 108: `nl80211_abort_scan` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_abort_scan` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_abort_scan` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_ABORT_SCAN`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 109: `nl80211_add_link` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_add_link` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 110: `nl80211_add_link` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_add_link` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_add_link` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_ADD_LINK`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 111: `nl80211_add_link_station` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_add_link_station` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer copying happens when copying a generic netlink operation from a statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 112: `nl80211_add_link_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_add_link_station` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata (like policies and flags).
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 113: `nl80211_add_tx_ts` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_add_tx_ts` is loaded from a static array and stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 114: `nl80211_add_tx_ts` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_add_tx_ts` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata.
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 115: `nl80211_associate` at `net/netlink/genetlink.c:187`
**Verdict:** Yes

The function `nl80211_associate` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_op_from_small` where `op->doit = family->small_ops[i].doit` is executed). 

The actual execution of the `nl80211_associate` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_ASSOCIATE`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 116: `nl80211_associate` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_associate` is stored into `op->doit` within `genl_cmd_full_to_split` at line 276 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation. This conversion is called during the generic netlink message receive process (via `genl_get_cmd`) and during iteration (via `genl_op_iter_next`).
When called during message reception (`genl_family_rcv_msg`), the `op` variable is allocated on the stack. Immediately after lookup and conversion, the generic netlink core invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 117: `nl80211_authenticate` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_authenticate` is loaded from a static array and stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 118: `nl80211_authenticate` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_authenticate` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata.
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 119: `nl80211_cancel_remain_on_channel` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_cancel_remain_on_channel` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 120: `nl80211_cancel_remain_on_channel` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_cancel_remain_on_channel` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_cancel_remain_on_channel` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_CANCEL_REMAIN_ON_CHANNEL`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 121: `nl80211_channel_switch` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_channel_switch` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 122: `nl80211_channel_switch` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_channel_switch` is loaded from a static array and stored into `op->doit` inside `genl_cmd_full_to_split()`. The static analysis tool identified this store via the `genl_op_iter_next()` call path. `genl_op_iter_next()` is an iterator used to extract metadata about generic netlink family operations (such as command IDs and policies) and the function pointer stored within its `struct genl_op_iter` instance is never actually executed. However, the same code path in `genl_cmd_full_to_split()` is also used by `genl_get_cmd()` during the actual processing of a netlink message in `genl_rcv_msg()`. In that case, the function pointer is copied into a local `struct genl_split_ops` variable and then executed immediately and synchronously by `genl_family_rcv_msg_doit()`. In both scenarios—whether the pointer is never executed, or executed synchronously during message processing—it is not executed asynchronously, and the "current" task context remains unchanged.
---

## Task 123: `nl80211_color_change` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_color_change` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 124: `nl80211_color_change` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_color_change` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_color_change` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_COLOR_CHANGE`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 125: `nl80211_connect` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_connect` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 127: `nl80211_connect` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_connect` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_connect` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_CONNECT`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 127: `nl80211_connect` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_connect` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_connect` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_CONNECT`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 128: `nl80211_crit_protocol_start` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_crit_protocol_start` is loaded from a static array and stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 129: `nl80211_crit_protocol_start` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_crit_protocol_start` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata (like policies and flags).
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 130: `nl80211_crit_protocol_stop` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_crit_protocol_stop` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 131: `nl80211_crit_protocol_stop` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_crit_protocol_stop` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_crit_protocol_stop` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_CRIT_PROTOCOL_STOP`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 132: `nl80211_deauthenticate` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_deauthenticate` is loaded from a static array and stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 133: `nl80211_deauthenticate` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_deauthenticate` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata.
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 134: `nl80211_del_interface` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_del_interface` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 135: `nl80211_del_interface` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_del_interface` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_del_interface` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_DEL_INTERFACE`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 136: `nl80211_del_key` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_del_key` is loaded from a static array and stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 137: `nl80211_del_key` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_del_key` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata.
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 138: `nl80211_del_mpath` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_del_mpath` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 139: `nl80211_del_mpath` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_del_mpath` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_del_mpath` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_DEL_MPATH`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 140: `nl80211_del_pmk` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_del_pmk` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 141: `nl80211_del_pmk` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_del_pmk` is stored into `op->doit` within `genl_cmd_full_to_split` at line 276 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation. This conversion is called during the generic netlink message receive process (via `genl_get_cmd`) and during iteration (via `genl_op_iter_next`).
When called during message reception (`genl_family_rcv_msg`), the `op` variable is allocated on the stack. Immediately after lookup and conversion, the generic netlink core invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 142: `nl80211_del_pmksa` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_del_pmksa` is loaded from a static array and stored into the local `op->doit` field inside `genl_op_from_small()`. This occurs during the synchronous processing of a generic netlink message via `genl_rcv_msg()`. The call stack goes through `genl_family_rcv_msg()`, which calls `genl_get_cmd()` -> `genl_get_cmd_small()` -> `genl_op_from_small()` to populate a local `struct genl_split_ops` variable. Immediately after this function pointer is copied into the local struct, `genl_family_rcv_msg_doit()` is invoked, which synchronously executes the function pointer by calling `ops->doit(skb, &info)`. Since the storing of the function pointer and its execution happen sequentially within the exact same function call tree and task context, it is not executed asynchronously.
---

## Task 143: `nl80211_del_pmksa` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_del_pmksa` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_del_pmksa` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_DEL_PMKSA`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 144: `nl80211_del_station` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_del_station` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 146: `nl80211_del_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_del_station` is loaded from a static array and stored into `op->doit` inside `genl_cmd_full_to_split()`. The static analysis tool identified this store via the `genl_op_iter_next()` call path. `genl_op_iter_next()` is an iterator used to extract metadata about generic netlink family operations (such as command IDs and policies) and the function pointer stored within its `struct genl_op_iter` instance is never actually executed. However, the same code path in `genl_cmd_full_to_split()` is also used by `genl_get_cmd()` during the actual processing of a netlink message in `genl_rcv_msg()`. In that case, the function pointer is copied into a local `struct genl_split_ops` variable and then executed immediately and synchronously by `genl_family_rcv_msg_doit()`. In both scenarios—whether the pointer is never executed, or executed synchronously during message processing—it is not executed asynchronously, and the "current" task context remains unchanged.
---

## Task 146: `nl80211_del_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_del_station` is loaded from a static array and stored into `op->doit` inside `genl_cmd_full_to_split()`. The static analysis tool identified this store via the `genl_op_iter_next()` call path. `genl_op_iter_next()` is an iterator used to extract metadata about generic netlink family operations (such as command IDs and policies) and the function pointer stored within its `struct genl_op_iter` instance is never actually executed. However, the same code path in `genl_cmd_full_to_split()` is also used by `genl_get_cmd()` during the actual processing of a netlink message in `genl_rcv_msg()`. In that case, the function pointer is copied into a local `struct genl_split_ops` variable and then executed immediately and synchronously by `genl_family_rcv_msg_doit()`. In both scenarios—whether the pointer is never executed, or executed synchronously during message processing—it is not executed asynchronously, and the "current" task context remains unchanged.
---

## Task 147: `nl80211_del_tx_ts` at `net/netlink/genetlink.c:187`
**Verdict:** Yes

The function `nl80211_del_tx_ts` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_op_from_small` where `op->doit = family->small_ops[i].doit` is executed). 

The actual execution of the `nl80211_del_tx_ts` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_DEL_TX_TS`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 148: `nl80211_del_tx_ts` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_del_tx_ts` is stored into `iter->doit.doit` (via `genl_cmd_full_to_split`) during the execution of `genl_op_iter_next`.
The `genl_op_iter_next` function is used solely to iterate over the operations registered for a Generic Netlink family. This iteration is performed for introspection purposes—such as validating the operations (`genl_validate_ops`) or dumping the family's capabilities and policies to user-space (`ctrl_fill_info`, `ctrl_dumppolicy`).
The function pointer stored in the `struct genl_op_iter` is never actually executed through this specific path; it is only read for its metadata.
Since it is never executed from this store, it is not executed asynchronously.
---

## Task 149: `nl80211_disassociate` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_disassociate` is stored into `op->doit` within `genl_op_from_small` at line 187 in `net/netlink/genetlink.c`.
This function pointer is copied from the statically defined `family->small_ops` array into a local stack-allocated `struct genl_ops` (and subsequently into a `struct genl_split_ops` in the caller) during the generic netlink message receive process (`genl_family_rcv_msg`).
After the lookup and the store of the `doit` and `dumpit` function pointers, the generic netlink core immediately invokes the stored function pointer via `ops->doit(skb, &info)` within `genl_family_rcv_msg_doit`.
Because the copying of the function pointer into the `op` structure and its subsequent invocation occur sequentially within the same network message processing path, the "current" task context does not change. Therefore, it is executed synchronously.
---

## Task 150: `nl80211_disassociate` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `nl80211_disassociate` is loaded from a static array and stored into `op->doit` inside `genl_cmd_full_to_split()`. The static analysis tool identified this store via the `genl_op_iter_next()` call path. `genl_op_iter_next()` is an iterator used to extract metadata about generic netlink family operations (such as command IDs and policies) and the function pointer stored within its `struct genl_op_iter` instance is never actually executed. However, the same code path in `genl_cmd_full_to_split()` is also used by `genl_get_cmd()` during the actual processing of a netlink message in `genl_rcv_msg()`. In that case, the function pointer is copied into a local `struct genl_split_ops` variable and then executed immediately and synchronously by `genl_family_rcv_msg_doit()`. In both scenarios—whether the pointer is never executed, or executed synchronously during message processing—it is not executed asynchronously, and the "current" task context remains unchanged.
---

## Task 151: `nl80211_disconnect` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer `nl80211_disconnect` is assigned to `op->doit` inside the `genl_op_from_small` helper function.
This helper is used by the Generic Netlink subsystem (e.g., inside `genl_get_cmd_small`) to populate a stack-allocated operation structure before executing a netlink command.
When the user-space process issues a `sendmsg` system call containing the Generic Netlink request, the kernel processes it synchronously in the context of the user process. The `doit` callback is executed directly from `genl_family_rcv_msg_doit` within the system call path.
Because the callback is executed by the thread that initiated the system call, the "current" task context remains the same and does not switch to an asynchronous background task or interrupt.
Therefore, the execution is not asynchronous.
---

## Task 152: `nl80211_disconnect` at `net/netlink/genetlink.c:276`
**Verdict:** Yes

The function `nl80211_disconnect` is assigned to the `.doit` member of the generic netlink operations array in `net/wireless/nl80211.c`. This array is provided during the registration of the `nl80211` generic netlink family (`nl80211_fam`) at kernel or module initialization.

During internal processing, the `genetlink` core copies this `.doit` callback into an internal structure (for instance, in `genl_cmd_full_to_split` where `op->doit = full->doit` is executed). 

The actual execution of the `nl80211_disconnect` function pointer takes place when a userspace process sends a generic netlink message with the corresponding command (`NL80211_CMD_DISCONNECT`) over a netlink socket. The netlink receive handler in the kernel (`genl_rcv_msg` -> `genl_family_rcv_msg_doit`) looks up the registered operation and dynamically calls `ops->doit(skb, &info)`.

Because the function pointer is stored during module or kernel initialization but is executed asynchronously much later in the context of an arbitrary userspace process sending a netlink message, its execution definitely entails a different "current" task context.
---

## Task 153: `nl80211_dump_interface` at `net/netlink/genetlink.c:188`
**Verdict:** No

The function pointer `nl80211_dump_interface` is loaded from a static array and stored into the local `op->dumpit` field inside `genl_op_from_small()`. This occurs during the processing of a netlink message within `genl_rcv_msg()`. Following the store, the execution continues synchronously down the call stack: `genl_family_rcv_msg()` calls `genl_family_rcv_msg_dumpit()`, which calls `__netlink_dump_start()`. Inside `__netlink_dump_start()`, the `ops` structure is copied to a heap allocation via `genl_start()`, and then `netlink_dump()` is immediately invoked. `netlink_dump()` synchronously calls the callback `cb->dump` (`genl_dumpit()`), which in turn executes the stored `ops->dumpit` function (`nl80211_dump_interface`). Because this entire sequence from the store operation to the first execution of the function pointer happens synchronously within the same netlink message processing path (typically the `sendmsg` syscall), the "current" task context remains exactly the same.
---

## Task 154: `nl80211_dump_interface` at `net/netlink/genetlink.c:272`
**Verdict:** No

The function pointer `nl80211_dump_interface` is stored into `op->dumpit` within `genl_cmd_full_to_split` at line 272 in `net/netlink/genetlink.c`.
This function pointer copying happens when converting a legacy "full" generic netlink operation into a "split" operation during the generic netlink message receive process (`genl_family_rcv_msg`).
When it is a dump operation, the `op` structure (allocated on the stack) is subsequently copied into a heap-allocated `struct genl_dumpit_info` within `genl_start`. The generic netlink core then invokes the stored `dumpit` function pointer via `ops->dumpit(skb, cb)` within `genl_dumpit`.
This invocation occurs synchronously in the context of the user space process interacting with the netlink socket (initially during `sendmsg`, and for subsequent chunks during `recvmsg`). The execution is not deferred to an asynchronous background worker or softirq, meaning the "current" task context remains the process performing the netlink dump. Therefore, it is executed synchronously.
---

## Task 155: `nl80211_dump_mpath` at `net/netlink/genetlink.c:188`
**Verdict:** No

The store operation occurs in `genl_op_from_small()` where a `dumpit` function pointer (e.g., `nl80211_dump_mpath`) is copied from `family->small_ops` into a local stack variable `op` of type `struct genl_ops`. 

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()` and subsequently `genl_op_from_small()` to perform the function pointer store.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_dumpit()`. This function sets up the netlink dump control block and calls `__netlink_dump_start()`. Within `__netlink_dump_start()`, `genl_start()` is called to copy the `op` structure into a dynamically allocated `genl_dumpit_info`, and then `netlink_dump()` is executed immediately.

`netlink_dump()` calls the registered dump callback, which is `genl_dumpit()`. `genl_dumpit()` then directly executes the stored `dumpit` pointer. 

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 156: `nl80211_dump_mpath` at `net/netlink/genetlink.c:272`
**Verdict:** No

The store of the function pointer `nl80211_dump_mpath` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:272`. The target is the `dumpit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink dump operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_dumpit()` and runs synchronously in `netlink_dump()` during the `recvmsg` or `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 157: `nl80211_dump_mpp` at `net/netlink/genetlink.c:188`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_dump_mpp` stored at `net/netlink/genetlink.c:188` inside `genl_op_from_small` will be executed asynchronously.

1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 188, it copies the `dumpit` function pointer (`op->dumpit = family->small_ops[i].dumpit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a dump operation, it then calls `genl_family_rcv_msg_dumpit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_dumpit` allocates a context, stores the `ops` pointer, and calls `__netlink_dump_start`.
5. `__netlink_dump_start` calls `genl_start` synchronously, which copies the `op` structure from the stack to a heap-allocated `struct genl_dumpit_info`.
6. `__netlink_dump_start` then immediately calls `netlink_dump(sk, true)`.
7. `netlink_dump` invokes `cb->dump(...)`, which is mapped to `genl_dumpit`.
8. `genl_dumpit` retrieves the `dumpit` function pointer from the heap-allocated info structure and calls it (`ops->dumpit(skb, cb)`).

Since `netlink_dump` (and thus `genl_dumpit` and `nl80211_dump_mpp`) is executed directly within the call stack of `__netlink_dump_start` originating from the `sendmsg` syscall, the first execution of the function pointer happens synchronously within the same task context that performed the store. 
(Subsequent executions may occur during a `recvmsg` syscall on the same socket, but these are typically done by the same thread, and the initial execution already confirms the synchronous nature of the execution path relative to the store).

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 158: `nl80211_dump_mpp` at `net/netlink/genetlink.c:272`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:272` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `doit` and `dumpit` function pointers from the family's definitions into `iter->doit` and `iter->dumpit`.

However, the iterator is only used for inspection and metadata exposure. For example, functions like `ctrl_dumppolicy_put_op()` inspect the operations' `.policy` fields to dump policy information to userspace, or `genl_validate_ops()` uses it to ensure operation IDs are valid. The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically in `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 159: `nl80211_dump_scan` at `net/netlink/genetlink.c:188`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_dump_scan` stored at `net/netlink/genetlink.c:188` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_dump_mpp`. 
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 188, it copies the `dumpit` function pointer (`op->dumpit = family->small_ops[i].dumpit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a dump operation, it then calls `genl_family_rcv_msg_dumpit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_dumpit` allocates a context, stores the `ops` pointer, and calls `__netlink_dump_start`.
5. `__netlink_dump_start` calls `genl_start` synchronously, which copies the `op` structure from the stack to a heap-allocated `struct genl_dumpit_info`.
6. `__netlink_dump_start` then immediately calls `netlink_dump(sk, true)`.
7. `netlink_dump` invokes `cb->dump(...)`, which is mapped to `genl_dumpit`.
8. `genl_dumpit` retrieves the `dumpit` function pointer from the heap-allocated info structure and calls it (`ops->dumpit(skb, cb)`).

Since `netlink_dump` (and thus `genl_dumpit` and `nl80211_dump_scan`) is executed directly within the call stack of `__netlink_dump_start` originating from the `sendmsg` syscall, the first execution of the function pointer happens synchronously within the same task context that performed the store. 
(Subsequent executions may occur during a `recvmsg` syscall on the same socket, but these are typically done by the same thread, and the initial execution already confirms the synchronous nature of the execution path relative to the store).

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 160: `nl80211_dump_scan` at `net/netlink/genetlink.c:272`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_dump_scan` stored at `net/netlink/genetlink.c:272` inside `genl_cmd_full_to_split` will be executed asynchronously.

1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 272, it copies the `dumpit` function pointer (`op->dumpit = full->dumpit;`).
2. This helper is called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace. (It is also called during `genl_validate_ops` and `ctrl_fill_info`, but neither of these execution paths result in invoking the function pointer).
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated via `genl_get_cmd` (which calls `genl_cmd_full_to_split`). For a dump operation, it then calls `genl_family_rcv_msg_dumpit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_dumpit` allocates a context, stores the `ops` pointer, and calls `__netlink_dump_start`.
5. `__netlink_dump_start` calls `genl_start` synchronously, which copies the `op` structure from the stack to a heap-allocated `struct genl_dumpit_info`.
6. `__netlink_dump_start` then immediately calls `netlink_dump(sk, true)`.
7. `netlink_dump` invokes `cb->dump(...)`, which is mapped to `genl_dumpit`.
8. `genl_dumpit` retrieves the `dumpit` function pointer from the heap-allocated info structure and calls it (`ops->dumpit(skb, cb)`).

Since `netlink_dump` (and thus `genl_dumpit` and `nl80211_dump_scan`) is executed directly within the call stack of `__netlink_dump_start` originating from the `sendmsg` syscall, the first execution of the function pointer happens synchronously within the same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 161: `nl80211_dump_station` at `net/netlink/genetlink.c:188`
**Verdict:** No

The store operation occurs in `genl_op_from_small()` where a `dumpit` function pointer (e.g., `nl80211_dump_station`) is copied from `family->small_ops` into a local stack variable `op` of type `struct genl_ops`. 

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()` and subsequently `genl_op_from_small()` to perform the function pointer store.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_dumpit()`. This function sets up the netlink dump control block and calls `__netlink_dump_start()`. Within `__netlink_dump_start()`, `genl_start()` is called to copy the `op` structure into a dynamically allocated `genl_dumpit_info`, and then `netlink_dump()` is executed immediately.

`netlink_dump()` calls the registered dump callback, which is `genl_dumpit()`. `genl_dumpit()` then directly executes the stored `dumpit` pointer. 

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 162: `nl80211_dump_station` at `net/netlink/genetlink.c:272`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_dump_station` stored at `net/netlink/genetlink.c:272` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 272, it copies the `dumpit` function pointer (`op->dumpit = full->dumpit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_dumpit` -> `__netlink_dump_start` -> `netlink_dump` -> `genl_dumpit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 163: `nl80211_dump_survey` at `net/netlink/genetlink.c:188`
**Verdict:** No

The store operation occurs in `genl_op_from_small()` where a `dumpit` function pointer (e.g., `nl80211_dump_survey`) is copied from `family->small_ops` into a local stack variable `op` of type `struct genl_ops`. 

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()` and subsequently `genl_op_from_small()` to perform the function pointer store.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_dumpit()`. This function sets up the netlink dump control block and calls `__netlink_dump_start()`. Within `__netlink_dump_start()`, `genl_start()` is called to copy the `op` structure into a dynamically allocated `genl_dumpit_info`, and then `netlink_dump()` is executed immediately.

`netlink_dump()` calls the registered dump callback, which is `genl_dumpit()`. `genl_dumpit()` then directly executes the stored `dumpit` pointer. 

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 164: `nl80211_dump_survey` at `net/netlink/genetlink.c:272`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:272`), where a `dumpit` function pointer (e.g., `nl80211_dump_survey`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_dumpit()`. This function sets up the netlink dump control block and calls `__netlink_dump_start()`. Within `__netlink_dump_start()`, `genl_start()` is called to copy the `op` structure into a dynamically allocated `genl_dumpit_info`, and then `netlink_dump()` is executed immediately.

`netlink_dump()` calls the registered dump callback, which is `genl_dumpit()`. `genl_dumpit()` then directly executes the stored `dumpit` pointer. 

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 165: `nl80211_dump_wiphy` at `net/netlink/genetlink.c:272`
**Verdict:** No

The store of the function pointer `nl80211_dump_wiphy` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:272`. The target is the `dumpit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink dump operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_dumpit()` and runs synchronously in `netlink_dump()` during the `recvmsg` or `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 166: `nl80211_dump_wiphy_done` at `net/netlink/genetlink.c:273`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:273` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `start`, `dumpit`, and `done` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 167: `nl80211_external_auth` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_external_auth` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_external_auth`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 168: `nl80211_external_auth` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_external_auth` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 169: `nl80211_flush_pmksa` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 170: `nl80211_flush_pmksa` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_flush_pmksa`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 171: `nl80211_get_coalesce` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_coalesce` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth`.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_get_coalesce`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 172: `nl80211_get_coalesce` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_get_coalesce` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 173: `nl80211_get_ftm_responder_stats` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 174: `nl80211_get_ftm_responder_stats` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_get_ftm_responder_stats`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 175: `nl80211_get_interface` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_get_interface` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 176: `nl80211_get_interface` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_interface` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 177: `nl80211_get_key` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 178: `nl80211_get_key` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_get_key`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 179: `nl80211_get_mesh_config` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_mesh_config` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_get_mesh_config`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 180: `nl80211_get_mesh_config` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 181: `nl80211_get_mpath` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_get_mpath`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 182: `nl80211_get_mpath` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_mpath` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 183: `nl80211_get_mpp` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 185: `nl80211_get_mpp` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_mpp` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 185: `nl80211_get_mpp` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_mpp` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 186: `nl80211_get_power_save` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_get_power_save` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 187: `nl80211_get_power_save` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 188: `nl80211_get_protocol_features` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_get_protocol_features`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 189: `nl80211_get_protocol_features` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_protocol_features` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 190: `nl80211_get_reg_do` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_get_reg_do` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 191: `nl80211_get_reg_do` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 192: `nl80211_get_reg_dump` at `net/netlink/genetlink.c:188`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_reg_dump` stored at `net/netlink/genetlink.c:188` inside `genl_op_from_small` will be executed asynchronously.

1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 188, it copies the `dumpit` function pointer (`op->dumpit = family->small_ops[i].dumpit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a dump operation, it then calls `genl_family_rcv_msg_dumpit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_dumpit` allocates a context, stores the `ops` pointer, and calls `__netlink_dump_start`.
5. `__netlink_dump_start` calls `genl_start` synchronously, which copies the `op` structure from the stack to a heap-allocated `struct genl_dumpit_info`.
6. `__netlink_dump_start` then immediately calls `netlink_dump(sk, true)`.
7. `netlink_dump` invokes `cb->dump(...)`, which is mapped to `genl_dumpit`.
8. `genl_dumpit` retrieves the `dumpit` function pointer from the heap-allocated info structure and calls it (`ops->dumpit(skb, cb)`).

Since `netlink_dump` (and thus `genl_dumpit` and `nl80211_get_reg_dump`) is executed directly within the call stack of `__netlink_dump_start` originating from the `sendmsg` syscall, the first execution of the function pointer happens synchronously within the same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 193: `nl80211_get_reg_dump` at `net/netlink/genetlink.c:272`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:272`), where a `dumpit` function pointer (e.g., `nl80211_get_reg_dump`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_dumpit()`. This function sets up the netlink dump control block and calls `__netlink_dump_start()`. Within `__netlink_dump_start()`, `genl_start()` is called to copy the `op` structure into a dynamically allocated `genl_dumpit_info`, and then `netlink_dump()` is executed immediately.

`netlink_dump()` calls the registered dump callback, which is `genl_dumpit()`. `genl_dumpit()` then directly executes the stored `dumpit` pointer. 

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 194: `nl80211_get_station` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 195: `nl80211_get_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_get_station` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 196: `nl80211_get_wiphy` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_get_wiphy` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 197: `nl80211_get_wowlan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_get_wowlan`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 198: `nl80211_get_wowlan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_get_wowlan` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 199: `nl80211_join_ibss` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 200: `nl80211_join_ibss` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_join_ibss` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 201: `nl80211_join_mesh` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_join_mesh`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 203: `nl80211_join_mesh` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_join_mesh` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 203: `nl80211_join_mesh` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_join_mesh` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 204: `nl80211_join_ocb` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 205: `nl80211_join_ocb` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_join_ocb`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 206: `nl80211_leave_ibss` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_leave_ibss` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_leave_ibss`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 207: `nl80211_leave_ibss` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_leave_ibss` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 208: `nl80211_leave_mesh` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 209: `nl80211_leave_mesh` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_leave_mesh`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 210: `nl80211_leave_ocb` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_leave_ocb` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_leave_ocb`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 211: `nl80211_leave_ocb` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_leave_ocb` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 212: `nl80211_modify_link_station` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 213: `nl80211_modify_link_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_modify_link_station` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 214: `nl80211_nan_add_func` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_nan_add_func`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 215: `nl80211_nan_add_func` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_nan_add_func` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 216: `nl80211_nan_change_config` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 217: `nl80211_nan_change_config` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_nan_change_config` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 218: `nl80211_nan_del_func` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_nan_del_func`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 219: `nl80211_nan_del_func` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_nan_del_func` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 220: `nl80211_new_interface` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 221: `nl80211_new_interface` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_new_interface` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 222: `nl80211_new_key` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_new_key`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 223: `nl80211_new_key` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_new_key` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 224: `nl80211_new_mpath` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 225: `nl80211_new_mpath` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_new_mpath` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 226: `nl80211_new_station` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_new_station`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 227: `nl80211_new_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_new_station` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 228: `nl80211_notify_radar_detection` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_notify_radar_detection` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_notify_radar_detection`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 229: `nl80211_notify_radar_detection` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 230: `nl80211_pmsr_start` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_pmsr_start`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 231: `nl80211_pmsr_start` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_pmsr_start` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 233: `nl80211_post_doit` at `net/netlink/genetlink.c:277`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:277` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 233: `nl80211_post_doit` at `net/netlink/genetlink.c:277`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:277` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 234: `nl80211_probe_client` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_probe_client`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 235: `nl80211_probe_client` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_probe_client` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 236: `nl80211_probe_mesh_link` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 237: `nl80211_probe_mesh_link` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_probe_mesh_link` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 238: `nl80211_register_beacons` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_register_beacons` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 239: `nl80211_register_beacons` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_register_beacons`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 240: `nl80211_register_mgmt` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_register_mgmt` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_register_mgmt`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 241: `nl80211_register_mgmt` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 242: `nl80211_register_unexpected_frame` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_register_unexpected_frame` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 243: `nl80211_register_unexpected_frame` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_register_unexpected_frame`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 244: `nl80211_reload_regdb` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_reload_regdb` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_reload_regdb`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 245: `nl80211_reload_regdb` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 246: `nl80211_remain_on_channel` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_remain_on_channel` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 247: `nl80211_remain_on_channel` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_remain_on_channel`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 248: `nl80211_remove_link` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_remove_link` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_remove_link`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 249: `nl80211_remove_link` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 250: `nl80211_remove_link_station` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_remove_link_station` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 251: `nl80211_remove_link_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_remove_link_station`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 252: `nl80211_req_set_reg` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_req_set_reg` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_req_set_reg`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 253: `nl80211_req_set_reg` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 254: `nl80211_set_beacon` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_beacon` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 255: `nl80211_set_beacon` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_set_beacon`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 256: `nl80211_set_bss` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_bss` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_bss`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 257: `nl80211_set_bss` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 258: `nl80211_set_channel` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_channel` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 259: `nl80211_set_channel` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_channel` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 260: `nl80211_set_coalesce` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_coalesce`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 261: `nl80211_set_coalesce` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 262: `nl80211_set_cqm` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_cqm` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_cqm`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 263: `nl80211_set_cqm` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_set_cqm` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 264: `nl80211_set_fils_aad` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_fils_aad`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 265: `nl80211_set_fils_aad` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 266: `nl80211_set_hw_timestamp` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_hw_timestamp` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_hw_timestamp`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 267: `nl80211_set_hw_timestamp` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_set_hw_timestamp` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 268: `nl80211_set_interface` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_interface`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 270: `nl80211_set_interface` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 270: `nl80211_set_interface` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 271: `nl80211_set_key` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_key` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 272: `nl80211_set_key` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_set_key`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 273: `nl80211_set_mac_acl` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_mac_acl` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_mac_acl`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 274: `nl80211_set_mac_acl` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 275: `nl80211_set_mcast_rate` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_mcast_rate` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 276: `nl80211_set_mcast_rate` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_set_mcast_rate`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 277: `nl80211_set_mpath` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_mpath` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_mpath`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 278: `nl80211_set_mpath` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 279: `nl80211_set_multicast_to_unicast` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_multicast_to_unicast` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 280: `nl80211_set_multicast_to_unicast` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_set_multicast_to_unicast`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 281: `nl80211_set_noack_map` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_noack_map` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_noack_map`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 282: `nl80211_set_noack_map` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 283: `nl80211_set_pmk` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_pmk` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 284: `nl80211_set_pmk` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_set_pmk`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 285: `nl80211_set_pmksa` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_pmksa` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_pmksa`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 286: `nl80211_set_pmksa` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 287: `nl80211_set_power_save` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_power_save` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 288: `nl80211_set_power_save` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_power_save` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 289: `nl80211_set_qos_map` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_qos_map`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 290: `nl80211_set_qos_map` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 291: `nl80211_set_reg` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_reg` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 292: `nl80211_set_reg` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_reg` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 293: `nl80211_set_rekey_data` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_rekey_data`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 294: `nl80211_set_rekey_data` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 295: `nl80211_set_sar_specs` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_sar_specs` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 296: `nl80211_set_sar_specs` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_sar_specs` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 297: `nl80211_set_station` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_station`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 298: `nl80211_set_station` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 299: `nl80211_set_tid_config` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_set_tid_config` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 300: `nl80211_set_tid_config` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_tid_config` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 301: `nl80211_set_ttlm` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_ttlm`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 302: `nl80211_set_ttlm` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 303: `nl80211_set_tx_bitrate_mask` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_tx_bitrate_mask` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_tx_bitrate_mask`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 304: `nl80211_set_tx_bitrate_mask` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_set_tx_bitrate_mask` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 305: `nl80211_set_wiphy` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_set_wiphy`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 306: `nl80211_set_wiphy` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 307: `nl80211_set_wowlan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_set_wowlan` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_set_wowlan`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 308: `nl80211_set_wowlan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_set_wowlan` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 309: `nl80211_start_ap` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_start_ap`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 311: `nl80211_start_ap` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 311: `nl80211_start_ap` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 312: `nl80211_start_nan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_start_nan` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 313: `nl80211_start_nan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_start_nan`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 314: `nl80211_start_p2p_device` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_start_p2p_device` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_start_p2p_device`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 315: `nl80211_start_p2p_device` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 316: `nl80211_start_radar_detection` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_start_radar_detection` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 317: `nl80211_start_radar_detection` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_start_radar_detection` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 318: `nl80211_start_sched_scan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_start_sched_scan`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 319: `nl80211_start_sched_scan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 320: `nl80211_stop_ap` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_stop_ap` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 321: `nl80211_stop_ap` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_stop_ap` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 322: `nl80211_stop_nan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_stop_nan`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 323: `nl80211_stop_nan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 324: `nl80211_stop_p2p_device` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_stop_p2p_device` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 325: `nl80211_stop_p2p_device` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_stop_p2p_device` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 326: `nl80211_stop_sched_scan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_stop_sched_scan`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 327: `nl80211_stop_sched_scan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_stop_sched_scan` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 328: `nl80211_tdls_cancel_channel_switch` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 329: `nl80211_tdls_cancel_channel_switch` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_tdls_cancel_channel_switch` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 330: `nl80211_tdls_channel_switch` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_tdls_channel_switch`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 331: `nl80211_tdls_channel_switch` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_tdls_channel_switch` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 332: `nl80211_tdls_mgmt` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_tdls_mgmt` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 333: `nl80211_tdls_mgmt` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 334: `nl80211_tdls_oper` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_tdls_oper` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_tdls_oper`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 335: `nl80211_tdls_oper` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_tdls_oper`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 336: `nl80211_trigger_scan` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_trigger_scan` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 338: `nl80211_trigger_scan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_trigger_scan` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 338: `nl80211_trigger_scan` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_trigger_scan` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 339: `nl80211_tx_control_port` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_tx_control_port`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 340: `nl80211_tx_control_port` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_tx_control_port` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 341: `nl80211_tx_mgmt` at `net/netlink/genetlink.c:187`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_tx_mgmt` stored at `net/netlink/genetlink.c:187` inside `genl_op_from_small` will be executed asynchronously.

This is structurally identical to the situation for `nl80211_external_auth` and other `doit` generic netlink operations.
1. `genl_op_from_small` is a helper function that copies a generic netlink operation definition from a `struct genl_small_ops` to a `struct genl_ops`. At line 187, it copies the `doit` function pointer (`op->doit = family->small_ops[i].doit;`).
2. This helper is called by `genl_get_cmd_small`, which is in turn called by `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`), usually triggered by a `sendmsg()` syscall from userspace.
3. In `genl_family_rcv_msg`, a local stack variable `op` of type `struct genl_split_ops` is populated with the result of `genl_get_cmd`. For a `doit` operation, it then calls `genl_family_rcv_msg_doit`, passing a pointer to this stack variable.
4. `genl_family_rcv_msg_doit` parses the netlink attributes, populates a `struct genl_info` object on the stack, and then synchronously executes the `doit` function pointer (`ops->doit(skb, &info)`).

Since `ops->doit` (and thus `nl80211_tx_mgmt`) is executed directly within the call stack of `genl_family_rcv_msg` originating from the `sendmsg` syscall, the execution of the function pointer happens synchronously within the exact same task context that performed the store. 

Therefore, the `current` task context does not change between the store and the execution, meaning it is not executed asynchronously.
---

## Task 342: `nl80211_tx_mgmt` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split()`. The instrumentation reports this store as happening within `genl_op_iter_next()`, meaning we are analyzing the specific instance where `genl_cmd_full_to_split()` is inlined or called by `genl_op_iter_next()`.

`genl_op_iter_next()` is used to iterate over generic netlink operations for a family. It populates a local `struct genl_op_iter` iterator with operation metadata, which includes copying the `pre_doit`, `doit`, and `post_doit` function pointers from the family's definitions into the iterator.

However, the iterator is only used for inspection and metadata exposure (such as dumping policy information to userspace or validating operation IDs). The function pointers stored inside this iterator are never actually invoked.

The actual execution of these netlink operations happens elsewhere (specifically via `genl_family_rcv_msg()`), which resolves the command via `genl_get_cmd()` and executes the callback synchronously within the user process's syscall context. Since the stored function pointer inside `genl_op_iter_next()` is never executed from the iterator, it is not executed asynchronously.
---

## Task 343: `nl80211_tx_mgmt_cancel_wait` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_tx_mgmt_cancel_wait`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 345: `nl80211_tx_mgmt_cancel_wait` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_tx_mgmt_cancel_wait` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 345: `nl80211_tx_mgmt_cancel_wait` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_tx_mgmt_cancel_wait` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 346: `nl80211_update_connect_params` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_update_connect_params`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 347: `nl80211_update_connect_params` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_update_connect_params` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 348: `nl80211_update_ft_ies` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 349: `nl80211_update_ft_ies` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_update_ft_ies` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 350: `nl80211_update_mesh_config` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store operation occurs at `genl_op_from_small()` (at `net/netlink/genetlink.c:187`), where a `doit` function pointer (e.g., `nl80211_update_mesh_config`) is copied from a `small_ops` struct into a `genl_ops` struct. This `genl_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_op_from_small()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 351: `nl80211_update_mesh_config` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store of the function pointer `nl80211_update_mesh_config` happens inside `genl_cmd_full_to_split()` (which is inlined into `genl_op_iter_next()`) at `net/netlink/genetlink.c:276`. The target is the `doit` member of a `struct genl_split_ops` inside a `struct genl_op_iter`. 

The `genl_op_iter_next()` function is used strictly as an iterator to inspect the generic netlink family operations metadata (e.g., in `genl_validate_ops`, `ctrl_getfamily`, and `ctrl_dumppolicy_start`). It is used to query `.flags`, `.cmd`, and `.policy` to dump the capabilities of the netlink family over a socket.

The copied function pointer within the `struct genl_op_iter` instance is never actually executed. (The actual execution path of generic netlink doit operations goes through `genl_get_cmd()` -> `genl_family_rcv_msg_doit()` and runs synchronously during the `sendmsg` system call, but the specific store reported here belongs to the non-executing introspection iterator).

Therefore, from the context of this specific store, the function is never executed, and so it is not executed asynchronously. Verdict: No.
---

## Task 352: `nl80211_update_owe_info` at `net/netlink/genetlink.c:187`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:187` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg`), the kernel processes it through `netlink_sendmsg()` -> `genl_rcv()` -> `genl_family_rcv_msg()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`). 

Since the execution occurs entirely within the system call path of the process sending the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 353: `nl80211_update_owe_info` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_update_owe_info` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 354: `nl80211_vendor_cmd` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_vendor_cmd` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 355: `nl80211_vendor_cmd` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_vendor_cmd`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 356: `nl80211_vendor_cmd_dump` at `net/netlink/genetlink.c:188`
**Verdict:** No

The function pointer store occurs at `net/netlink/genetlink.c:188` inside `genl_op_from_small()`. The function copies operation metadata, including `doit` and `dumpit` function pointers, from a `genl_small_ops` structure into a `genl_ops` structure.

This function is called from two main paths:
1. `genl_op_iter_next()`: used to iterate over netlink operations for inspection and dumping to userspace. In this path, the function pointers are never executed.
2. `genl_get_cmd()` -> `genl_get_cmd_small()`: used to resolve an incoming generic netlink command. In this path, the `doit` or `dumpit` function pointer is retrieved to handle an incoming netlink message.

In the second path, where the function pointer is actually executed, the execution happens synchronously. When a user process sends a netlink message (e.g., via `sendmsg` or `recvmsg` for dumps), the kernel processes it through `netlink_recvmsg()` -> `netlink_dump()` (for dumps) or `netlink_sendmsg()` -> `genl_rcv()`. The operation is resolved using `genl_get_cmd_small()` and then immediately executed via `genl_family_rcv_msg_doit()` (which calls `ops->doit`) or `genl_family_rcv_msg_dumpit()` (which calls `ops->dumpit`). 

Since the execution occurs entirely within the system call path of the process sending or receiving the netlink message, the "current" task context does not change. There are no workqueues, timers, or background threads involved. Therefore, the stored function is not executed asynchronously.
---

## Task 357: `nl80211_vendor_cmd_dump` at `net/netlink/genetlink.c:272`
**Verdict:** No

The task asks to determine if the function pointer `nl80211_vendor_cmd_dump` stored at `net/netlink/genetlink.c:272` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `dumpit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 272, it copies the `dumpit` function pointer (`op->dumpit = full->dumpit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_dumpit` and `__netlink_dump_start`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 358: `nl80211_wiphy_netns` at `net/netlink/genetlink.c:187`
**Verdict:** No

The store of the function pointer `nl80211_wiphy_netns` occurs inside `genl_op_from_small()` at `net/netlink/genetlink.c:187`. The pointer is copied from the netlink family's `small_ops` array into a local `struct genl_ops` object.

This copying occurs when `genl_get_cmd_small()` (called by `genl_get_cmd()`) resolves the netlink command during message reception in `genl_family_rcv_msg()`. Once the command operation is resolved and copied into the `ops` structure, the execution proceeds to `genl_family_rcv_msg_doit()`. 

Inside `genl_family_rcv_msg_doit()`, the `doit` function pointer is executed synchronously (`err = ops->doit(skb, &info);`). This entire flow runs in the context of the user process making the `sendmsg` (or `sendto`) system call to the generic netlink socket. Because the execution is strictly synchronous and inline with the netlink message processing, it does not defer to a workqueue, softirq, or other kernel thread.

Therefore, the "current" task context does not change when the stored function is called. Verdict: No.
---

## Task 359: `nl80211_wiphy_netns` at `net/netlink/genetlink.c:276`
**Verdict:** No

The store operation occurs at `genl_cmd_full_to_split()` (at `net/netlink/genetlink.c:276`), where a `doit` function pointer (e.g., `nl80211_wiphy_netns`) is copied from a `genl_ops` struct into a `genl_split_ops` struct. This `genl_split_ops` struct is a local stack variable (`op`) in `genl_rcv_msg()`.

This store is triggered when a user process sends a netlink message, invoking the `sendmsg()` system call on a genetlink socket. The kernel processes this synchronously: `netlink_sendmsg()` calls `netlink_unicast()`, which calls `netlink_unicast_kernel()`. This invokes the registered netlink receive handler `genl_rcv()`, which leads to `genl_rcv_msg()`. Inside `genl_rcv_msg()`, `genl_get_cmd()` is called, which calls `genl_cmd_full_to_split()` to perform the function pointer store into the stack variable.

Immediately following the store, in the same `genl_rcv_msg()` function, the local `op` struct is passed to `genl_family_rcv_msg_doit()`. This function parses the netlink attributes and then directly executes the stored `doit` pointer by calling `ops->doit(skb, &info)`.

Since all of this occurs synchronously within the context of the user process executing the `sendmsg()` system call, the "current" task context does not change between the store of the function pointer and its execution. Thus, it is not executed asynchronously.
---

## Task 360: `page_mkclean_one` at `mm/rmap.c:1087`
**Verdict:** No

The function pointer store occurs at `mm/rmap.c:1087` within `folio_mkclean()`, where the function `page_mkclean_one` is assigned to `rwc.rmap_one` of a `struct rmap_walk_control`.

This structure is then immediately passed to `rmap_walk(folio, &rwc)`. `rmap_walk` synchronously iterates over all virtual memory areas (VMAs) where the given folio is mapped. Depending on the type of folio (file-backed, anonymous, KSM), it calls functions like `rmap_walk_file()`, which iterate using `vma_interval_tree_foreach()` and call the `rwc->rmap_one` callback directly for each matching VMA.

Since `page_mkclean_one` is invoked inline during this synchronous walk, the execution happens entirely within the same task context that called `folio_mkclean()` (e.g., page reclaim, msync, or other memory management paths). The task context does not change, and there are no workqueues or asynchronous threads involved. Therefore, the stored function pointer is not executed asynchronously.
---

## Task 361: `percpu_ref_noop_confirm_switch` at `lib/percpu-refcount.c:229`
**Verdict:** Yes

The task asks to determine if the function pointer `percpu_ref_noop_confirm_switch` stored at `lib/percpu-refcount.c:229` inside `__percpu_ref_switch_to_atomic` will be executed asynchronously.

1. At `lib/percpu-refcount.c:229` in `__percpu_ref_switch_to_atomic`, the function stores a pointer to `percpu_ref_noop_confirm_switch` (or a provided `confirm_switch` function) into `ref->data->confirm_switch`.
2. Immediately following this store, the function calls `call_rcu_hurry(&ref->data->rcu, percpu_ref_switch_to_atomic_rcu);`. This schedules the RCU callback `percpu_ref_switch_to_atomic_rcu` to run after a grace period.
3. The original execution path of `__percpu_ref_switch_to_atomic` then finishes and returns.
4. Later, the RCU subsystem invokes the callback `percpu_ref_switch_to_atomic_rcu`, which in turn calls `percpu_ref_call_confirm_rcu`.
5. Inside `percpu_ref_call_confirm_rcu`, the stored function pointer is executed: `data->confirm_switch(ref);`.

Because the execution of the `confirm_switch` function pointer happens within an RCU callback, it executes in a different context (typically SoftIRQ context handling RCU callbacks) than the one that originally stored the pointer and initiated the atomic switch. Therefore, the execution of this stored function pointer is definitively asynchronous, and the "current" task context changes when it is called.
---

## Task 362: `percpu_ref_noop_confirm_switch` at `lib/percpu-refcount.c:281`
**Verdict:** Yes

The function pointer `percpu_ref_noop_confirm_switch` is used as a default callback when switching a percpu-refcount to atomic mode inside `__percpu_ref_switch_to_atomic()`. If a mode switch is actually required (from percpu to atomic), this function pointer is stored into `ref->data->confirm_switch`. 

Subsequently, the code calls `call_rcu_hurry(&ref->data->rcu, percpu_ref_switch_to_atomic_rcu)` to defer the rest of the mode switch until after an RCU grace period. 

When the RCU callback `percpu_ref_switch_to_atomic_rcu` executes later, it calls `percpu_ref_call_confirm_rcu()` which finally executes the stored function pointer (`data->confirm_switch(ref)`). Because this execution occurs inside an RCU softirq or RCU callback thread context, the "current" task context will be different from the process that initiated the mode switch. Thus, the function is executed asynchronously. Verdict: Yes.
---

## Task 363: `ping_queue_rcv_skb` at `net/ipv4/af_inet.c:359`
**Verdict:** Yes

The store operation occurs in `inet_create()` (at `net/ipv4/af_inet.c:359`), where `sk->sk_backlog_rcv` is assigned the `backlog_rcv` function pointer from the protocol's operations struct (`sk->sk_prot->backlog_rcv`). For an ICMP ping socket, this pointer resolves to `ping_queue_rcv_skb()`.

This store happens synchronously during the `socket()` system call when the user space application creates a new socket. 

The execution of the stored function pointer (`sk_backlog_rcv()`), however, occurs completely asynchronously. It is triggered when network packets destined for this socket arrive. If the socket is currently locked by the user space process (e.g., executing a system call like `recvmsg()`), the incoming packets are appended to the socket's backlog queue by the network softirq. Later, when the user space process releases the socket lock (via `release_sock()`), `__release_sock()` iterates through the queued packets and executes `sk_backlog_rcv()` for each one to process them. 

Alternatively, if the socket is not locked, the network stack (running in softirq context, like `NET_RX_SOFTIRQ`) might execute the receive path which can also call into the backlog receive function directly or queue it for later processing. 

In all scenarios, the execution of `sk_backlog_rcv()` is tied to network packet reception events that happen long after the `socket()` system call has completed. Therefore, the "current" task context at the time of execution (which could be a softirq context or the user task during a subsequent `recvmsg()`/`release_sock()`) is completely asynchronous relative to the context that stored the function pointer.
---

## Task 364: `ping_queue_rcv_skb` at `net/ipv6/af_inet6.c:219`
**Verdict:** Yes

The task asks to determine if the function pointer `ping_queue_rcv_skb` stored at `net/ipv6/af_inet6.c:219` inside `inet6_create` will be executed asynchronously.

1. In `inet6_create` at `net/ipv6/af_inet6.c:219`, the `sk_backlog_rcv` function pointer of the newly created socket `sk` is initialized from the protocol operations (`answer->prot->backlog_rcv`). For the ICMP/ping protocol, this pointer is `ping_queue_rcv_skb`.
2. This store happens synchronously during the `socket()` system call when creating an IPv6 ping socket.
3. The `sk_backlog_rcv` function pointer is used by the network stack to process packets that were queued to the socket's backlog because the socket was locked by a user thread at the time the packet arrived.
4. It is executed via the `sk_backlog_rcv()` helper when the socket is unlocked (`release_sock()`) or during SoftIRQ packet reception (`__sk_receive_skb`). 
5. Because this execution happens during the processing of incoming network packets (often in SoftIRQ context or when another thread unlocks the socket), it occurs at an arbitrary time later and in a different context from the task that originally created the socket (which performed the store).

Therefore, the function pointer is executed asynchronously, and the "current" task context can change when called.
---

## Task 365: `pm_runtime_work` at `drivers/base/power/runtime.c:1764`
**Verdict:** Yes

The function pointer store occurs at `drivers/base/power/runtime.c:1764` within `pm_runtime_init()`. The macro `INIT_WORK(&dev->power.work, pm_runtime_work)` is called, which stores the function pointer `pm_runtime_work` into the work struct (`dev->power.work.func`).

A work struct is used to defer execution to a background kernel worker thread (via the Linux workqueue subsystem). When the runtime power management subsystem queues this work (e.g., via `queue_work()` or `schedule_work()`), the callback `pm_runtime_work()` is executed later by a workqueue worker thread.

Because the function executes in a dedicated kernel thread rather than in the context of the task that scheduled the work, the "current" task context changes when it is called. Therefore, the stored function is executed asynchronously.
---

## Task 366: `pm_suspend_timer_fn` at `drivers/base/power/runtime.c:1768`
**Verdict:** Yes

The task asks to determine if the function pointer `pm_suspend_timer_fn` stored at `drivers/base/power/runtime.c:1768` inside `pm_runtime_init` will be executed asynchronously.

1. At `drivers/base/power/runtime.c:1768` in `pm_runtime_init`, the function pointer `pm_suspend_timer_fn` is assigned to `dev->power.suspend_timer.function`.
2. `dev->power.suspend_timer` is an `hrtimer` (high-resolution timer) initialized just before this line.
3. This timer is used by the runtime PM subsystem to schedule delayed autosuspend operations. It is started using `hrtimer_start` (e.g., in `pm_schedule_suspend`).
4. When the timer expires, the kernel's timer subsystem executes the stored callback function (`pm_suspend_timer_fn`).
5. Because `hrtimer` callbacks are executed in hard interrupt context (or softirq context depending on the timer configuration), they run asynchronously relative to the task that originally initialized the timer or started it.

Therefore, the function pointer is executed asynchronously, and the "current" task context definitively changes when it is called.
---

## Task 367: `pollwake` at `./include/linux/wait.h:92`
**Verdict:** Yes

The store operation occurs in `__pollwait()` (which calls `init_waitqueue_func_entry()` at `include/linux/wait.h:92`), where the `pollwake` function pointer is stored into the `func` field of a `wait_queue_entry` struct (`entry->wait.func = pollwake`).

This store happens when a user space process invokes the `poll()`, `select()`, or `epoll` system calls. During the system call, the kernel iterates over the provided file descriptors and calls their respective `f_op->poll` handlers. These handlers call `poll_wait()`, which in turn executes `__pollwait()` to add the process to the file's waitqueue and perform the store operation. The process then typically goes to sleep waiting for an event.

The execution of the stored function pointer (`pollwake`) occurs when the watched event actually happens (e.g., data arrives on a socket, a pipe becomes writable, a device interrupt fires). The component that detects the event (such as a hardware interrupt handler, a network softirq, or another user process performing a `write()`) will call a wakeup function like `wake_up()` on the waitqueue. The `wake_up()` mechanism iterates over the queue and calls the stored `func` pointer (which is `pollwake`) to wake up the sleeping process.

Since the store is performed by the process executing the `poll()` system call, but the execution of `pollwake` is performed by whatever context triggers the wakeup (e.g., an IRQ, softirq, or a completely different process), the "current" task context changes between the store and the execution. Therefore, the function is executed asynchronously.
---

## Task 368: `posix_cpu_timers_work` at `./include/linux/task_work.h:13`
**Verdict:** Yes

The function pointer `posix_cpu_timers_work` is stored into a `task_work` struct via the `init_task_work()` macro. This macro is called from `clear_posix_cputimers_work()`, which is used during `fork()` to initialize the POSIX CPU timers for a newly created child process.

During `fork()`, the "current" task context is the parent process. The `task_work` structure is prepared and embedded inside the child process's `task_struct`.

Later, when the child process is executing and a timer interrupt fires, `run_posix_cpu_timers()` will schedule this work by calling `task_work_add()` with `TWA_RESUME`. The function pointer will then be executed by `task_work_run()` just before the child process returns to userspace.

Since the store happens in the context of the parent process (during fork) but the execution happens asynchronously in the context of the child process when returning to userspace after a timer interrupt, the "current" task context changes. Verdict: Yes.
---

## Task 369: `posix_cpu_timers_work` at `kernel/time/posix-cpu-timers.c:1222`
**Verdict:** Yes

The function pointer store occurs at `kernel/time/posix-cpu-timers.c:1222` inside `clear_posix_cputimers_work()`. The `init_task_work()` function is called to initialize a task work entry (`p->posix_cputimers_work.work`) with the callback function `posix_cpu_timers_work`.

Task work (using `struct callback_head` and `task_work_add()`) is a mechanism to defer execution of a function until the target task returns to userspace or exits. In this case, when a POSIX CPU timer expires (which happens in hardware timer interrupt context), the timer subsystem queues this task work to the target process. 

The callback `posix_cpu_timers_work` is then executed later by the target task itself (e.g., during `resume_user_mode_work`). Because the execution is deferred from the hardirq/timer context where it was scheduled to the specific task's context returning to userspace, the "current" task context changes when the function is finally called. Therefore, the stored function is executed asynchronously.
---

## Task 370: `print_daily_error_info` at `kernel/time/timer.c:900`
**Verdict:** Yes

The task asks to determine if the function pointer `print_daily_error_info` stored at `kernel/time/timer.c:900` inside `init_timer_key` will be executed asynchronously.

1. At `fs/ext4/super.c:3638`, `timer_setup(&sbi->s_err_report, print_daily_error_info, 0);` is called. The macro `timer_setup` expands to a call to `init_timer_key` passing `print_daily_error_info` as the callback function pointer.
2. Inside `init_timer_key` at `kernel/time/timer.c:900`, the function pointer is stored: `timer->function = func;`.
3. The `s_err_report` timer is scheduled to fire periodically using `mod_timer`.
4. When the scheduled time (in jiffies) arrives, the kernel's timer wheel processing (typically executed in softirq context `TIMER_SOFTIRQ`) dequeues the timer and executes the stored callback: `timer->function(timer);`.

Because the execution of the callback function occurs in the context of the timer softirq, which handles expired timers independently of the task that set or started the timer, the execution is asynchronous. The "current" task context definitively changes (usually running in the context of the softirq daemon or an interrupted process).
---

## Task 371: `proc_single_show` at `fs/seq_file.c:582`
**Verdict:** No

The store operation occurs in `single_open()` (at `fs/seq_file.c:582`), where the `show` function pointer (in this case, `proc_single_show`) is stored into the `show` field of a dynamically allocated `seq_operations` structure (`op->show = show`). 

This store happens synchronously during the `open()` system call when a user space process opens a file in the procfs filesystem that is configured to use the sequential file (seq_file) interface. The `single_open()` function associates the `seq_operations` structure with the open `struct file`.

The execution of the stored function pointer occurs later, when a user space process invokes the `read()` system call on the opened file descriptor. During the `read()` syscall, the kernel's `seq_read()` function is executed, which calls `op->show()` to generate the sequential file data and copy it to the user's buffer. 

While the store and execution happen in separate system calls (`open()` vs. `read()`), both operations are performed synchronously in the context of the user process executing the respective system calls. There is no background thread, interrupt, or softirq executing the function. Even though it is possible for a process to pass the file descriptor to another process before reading, the execution is fundamentally synchronous to the `read()` syscall. Therefore, the function is not executed asynchronously.
---

## Task 372: `process_timeout` at `kernel/time/timer.c:900`
**Verdict:** Yes

The task asks to determine if the function pointer `process_timeout` stored at `kernel/time/timer.c:900` inside `schedule_timeout` will be executed asynchronously.

1. Inside `schedule_timeout`, a timer is set up on the stack using `timer_setup_on_stack(&timer.timer, process_timeout, 0);`. This macro expands to `init_timer_key`, where the function pointer `process_timeout` is assigned to `timer->function` at `kernel/time/timer.c:900`.
2. After setting up the timer and configuring its expiration time, `schedule_timeout` calls `schedule()` to yield the CPU and put the current task to sleep.
3. When the configured timeout expires, the kernel's timer subsystem processes the timer queue in the `TIMER_SOFTIRQ` softirq context.
4. During this processing, the timer subsystem dequeues the expired timer and invokes its stored callback: `timer->function(timer)`, which resolves to `process_timeout`.
5. `process_timeout` then wakes up the sleeping task that originally called `schedule_timeout`.

Because `process_timeout` is invoked from a softirq context (specifically `TIMER_SOFTIRQ`) when the timer expires, its execution happens in a different context than the task that stored the pointer and went to sleep. Thus, the function pointer is executed asynchronously, and the "current" task context changes when called.
---

## Task 373: `pwq_release_workfn` at `kernel/workqueue.c:5120`
**Verdict:** Yes

The function pointer store occurs at `kernel/workqueue.c:5120` inside `init_pwq()`. The function `kthread_init_work()` is called to initialize a `kthread_work` structure (`pwq->release_work`) with the callback function `pwq_release_workfn`.

The `kthread_work` mechanism is designed to queue functions to be executed by a dedicated kernel thread worker (a `kthread_worker`). When the structure is eventually queued (e.g., via `kthread_queue_work()` or similar variants), the target kthread wakes up and executes the callback. 

Because the callback is executed by the kthread worker instead of the thread that queued the work, the "current" task context changes when the function is finally called. Therefore, the stored function is executed asynchronously.
---

## Task 374: `raw_rcv_skb` at `net/ipv4/af_inet.c:359`
**Verdict:** Yes

The task asks to determine if the function pointer `raw_rcv_skb` stored at `net/ipv4/af_inet.c:359` inside `inet_create` will be executed asynchronously.

1. In `inet_create` at `net/ipv4/af_inet.c:359`, the `sk_backlog_rcv` function pointer of the newly created socket `sk` is initialized from the protocol operations (`answer->prot->backlog_rcv`). For a raw IPv4 socket, this pointer corresponds to `raw_rcv_skb`.
2. This store happens synchronously during the `socket()` system call when a user task creates a raw socket.
3. The `sk_backlog_rcv` function pointer is utilized by the network stack to process packets that were queued to the socket's backlog because the socket was locked by a user thread at the time the packet arrived (for example, during a concurrent `recvmsg` call).
4. The pointer is invoked via the `sk_backlog_rcv()` helper when the socket is unlocked (`release_sock()`) or during SoftIRQ packet reception if memory allows (`__sk_receive_skb`). 
5. Because this execution happens during the processing of incoming network packets (often in SoftIRQ context or when another thread unlocks the socket), it occurs at an arbitrary time later and in a different context from the task that originally created the socket and performed the store.

Therefore, the function pointer is executed asynchronously, and the "current" task context changes when called.
---

## Task 375: `rawv6_rcv_skb` at `net/ipv6/af_inet6.c:219`
**Verdict:** Yes

The store operation occurs in `inet6_create()` (at `net/ipv6/af_inet6.c:219`), where `sk->sk_backlog_rcv` is assigned the `backlog_rcv` function pointer from the protocol's operations struct (`answer->prot->backlog_rcv`). For an IPv6 raw socket, this pointer resolves to `rawv6_rcv_skb()`.

This store happens synchronously during the `socket()` system call when the user space application creates a new socket. 

The execution of the stored function pointer (`sk_backlog_rcv()`), however, occurs completely asynchronously. It is triggered when network packets destined for this socket arrive. If the socket is currently locked by the user space process (e.g., executing a system call like `recvmsg()`), the incoming packets are appended to the socket's backlog queue by the network softirq. Later, when the user space process releases the socket lock (via `release_sock()`), `__release_sock()` iterates through the queued packets and executes `sk_backlog_rcv()` for each one to process them. 

Alternatively, if the socket is not locked, the network stack (running in softirq context, like `NET_RX_SOFTIRQ`) might execute the receive path which can also call into the backlog receive function directly or queue it for later processing. 

In all scenarios, the execution of `sk_backlog_rcv()` is tied to network packet reception events that happen long after the `socket()` system call has completed. Therefore, the "current" task context at the time of execution (which could be a softirq context or the user task during a subsequent `recvmsg()`/`release_sock()`) is completely asynchronous relative to the context that stored the function pointer.
---

## Task 376: `receiver_wake_function` at `net/core/datagram.c:92`
**Verdict:** Yes

The task asks to determine if the function pointer `receiver_wake_function` stored at `net/core/datagram.c:92` inside `__skb_wait_for_more_packets` will be executed asynchronously.

1. At `net/core/datagram.c:92`, the `DEFINE_WAIT_FUNC(wait, receiver_wake_function)` macro is used. This expands to initializing a `wait_queue_entry_t` variable named `wait`, with its `.func` field set to the function pointer `receiver_wake_function`.
2. This wait queue entry is then added to the socket's wait queue via `prepare_to_wait_exclusive()`, and the current task goes to sleep to wait for more network packets to arrive.
3. The stored function pointer `receiver_wake_function` is used as the custom wake-up callback. It is executed by the kernel's scheduler/wait-queue machinery when another task or an interrupt handler calls a wake-up function on the socket's wait queue (e.g., when a new packet is received in softirq context, or an error occurs).
4. Because the wake-up happens from a different execution context (typically a network softirq processing incoming packets, or another thread) rather than the sleeping task itself, the callback function is executed asynchronously. The `current` task context during the execution of this callback will be the context of the waker, not the task that went to sleep.

Therefore, the function pointer is executed asynchronously.
---

## Task 377: `release_one_tty` at `./include/linux/kref.h:65`
**Verdict:** No

The function pointer "store" occurs at `include/linux/kref.h:65` within `kref_put()`, where the function pointer `release_one_tty` is passed as the `release` parameter. The instrumentation likely catches the argument passing (e.g., spilling to the stack) or an assignment related to the inline function's execution.

At this location, `kref_put()` checks if the reference count has reached zero. If it has, it immediately and directly invokes the `release` callback (`release_one_tty`) on the same line: `release(kref);`.

Because the function pointer is executed immediately and inline within the same function call, there is no deferral of execution. The execution happens synchronously in the context of whichever task called `kref_put()`. The "current" task context does not change between the moment the function pointer is passed/stored and the moment it is executed. Therefore, it is not executed asynchronously.
---

## Task 378: `release_one_tty` at `drivers/tty/tty_io.c:1558`
**Verdict:** Yes

The store of the function pointer `release_one_tty` happens inside the `queue_release_one_tty()` function at `drivers/tty/tty_io.c:1558` via the `INIT_WORK()` macro.

Immediately following the initialization, `schedule_work(&tty->hangup_work)` is called to schedule the work. 

The `release_one_tty` function will therefore be executed asynchronously by a worker thread in the system workqueue (e.g., `kworker`). Because the execution runs in a kernel worker thread instead of the process context that dropped the last kref of the TTY, the "current" task context will be completely different. Thus, the function is executed asynchronously. Verdict: Yes.
---

## Task 379: `release_one_tty` at `drivers/tty/tty_io.c:1572`
**Verdict:** Yes

The task asks to determine if the function pointer `release_one_tty` stored at `drivers/tty/tty_io.c:1572` inside `tty_kref_put` will be executed asynchronously.

1. At `drivers/tty/tty_io.c:1572` in `tty_kref_put`, there is a call to `kref_put(&tty->kref, queue_release_one_tty)`. If the reference count drops to zero, the function `queue_release_one_tty` is executed.
2. Inside `queue_release_one_tty`, the function `INIT_WORK(&tty->hangup_work, release_one_tty)` is called. This macro initializes a `work_struct` by storing the function pointer `release_one_tty` into it.
3. Immediately after, `schedule_work(&tty->hangup_work)` is called to queue the work item to the global system workqueue.
4. The worker thread associated with the system workqueue will later dequeue this work item and execute the stored function pointer `release_one_tty`.
5. Because the callback function is executed by a kernel worker thread and not by the task that originally called `tty_kref_put`, the execution is definitively asynchronous, and the "current" task context changes when the function is called.

Therefore, the function pointer is executed asynchronously.
---

## Task 380: `rescuer_thread` at `kernel/kthread.c:441`
**Verdict:** Yes

The store operation occurs in `__kthread_create_on_node()` (at `kernel/kthread.c:441`), where the `threadfn` pointer (in this case, `rescuer_thread`) is stored into a dynamically allocated `kthread_create_info` structure (`create->threadfn = threadfn`).

This store happens in the context of the task that is creating a new kernel thread (for example, during workqueue initialization when a new rescuer thread is requested). The `__kthread_create_on_node()` function adds this creation request to the `kthread_create_list` and wakes up the `kthreadd_task` daemon.

The execution of the stored function pointer (`threadfn`) occurs completely asynchronously in a new execution context. The `kthreadd` daemon forks a new kernel thread, and the entry point of this new kernel thread (`kthread()`) retrieves the `create` structure and directly executes `create->threadfn(create->data)`. 

Because the `rescuer_thread` function executes as the main loop of the newly spawned kernel thread, the "current" task context during its execution is the newly created thread itself, not the task that originally called `kthread_create()`. Thus, the execution is fundamentally asynchronous.
---

## Task 381: `rhashtable_jhash2` at `lib/rhashtable.c:1062`
**Verdict:** Yes

The `rhashtable_init_noprof` function initializes a new scalable hash table (`struct rhashtable`). It stores the function pointer `rhashtable_jhash2` into `ht->p.hashfn` when the hash function is not provided in parameters and the key length is aligned to a 4-byte boundary. 

The stored hash function is later invoked through `rht_key_hashfn` (and indirectly via `rht_key_get_hash`) during various hash table operations, such as element insertion, deletion, lookup, and resizing (e.g., `rhashtable_insert_fast`, `rhashtable_lookup`). Since these hash table operations are initiated by different processes or threads at a later point in time (for example, during network packet processing or by other kernel subsystems using `rhashtable`), the "current" task context will be different from the one that executed the initialization. Therefore, the function pointer is executed asynchronously.
---

## Task 382: `rht_deferred_worker` at `lib/rhashtable.c:1081`
**Verdict:** Yes

The task asks to determine if the function pointer `rht_deferred_worker` stored at `lib/rhashtable.c:1081` inside `rhashtable_init_noprof` will be executed asynchronously.

1. At `lib/rhashtable.c:1081`, inside the hash table initialization function `rhashtable_init_noprof`, the macro `INIT_WORK(&ht->run_work, rht_deferred_worker)` is used.
2. This macro initializes a `work_struct` (`ht->run_work`) and stores the function pointer `rht_deferred_worker` as the callback to be executed when the work is scheduled.
3. The `run_work` is scheduled dynamically by the rhashtable code during its operation using `schedule_work(&ht->run_work)`. This typically happens when the hash table needs to be resized (e.g., expanding because it grew above a threshold like 75%, or shrinking) and this operation must be deferred to process context.
4. When `schedule_work` is called, the work item is placed on the global system workqueue.
5. A kernel worker thread will asynchronously dequeue this work item and execute the stored callback `rht_deferred_worker()`.
6. Since the callback is executed by a separate kernel worker thread at an arbitrary later time, and not by the task that initialized the hash table or scheduled the work, the execution happens asynchronously.

Therefore, the function pointer is executed asynchronously, and the "current" task context will change.
---

## Task 383: `rtnetlink_bind` at `net/netlink/af_netlink.c:716`
**Verdict:** No

The function pointer `rtnetlink_bind` is stored into `nlk->netlink_bind` during the creation of a netlink socket inside `__netlink_create()` (at `net/netlink/af_netlink.c:716`).

This stored function pointer is executed when the user space application calls the `bind()` or `setsockopt()` system calls on the netlink socket. Specifically, it is invoked directly from `netlink_bind()` and `netlink_setsockopt()` to handle multicast group registrations.

Because the execution of the callback is performed directly inline by the process invoking these system calls, the execution is synchronous. The work is not deferred to a background thread, workqueue, timer, or softirq. Thus, the "current" task context does not inherently change (it executes in the context of whatever task invoked the system call). Verdict: No.
---

## Task 384: `scmd_eh_abort_handler` at `drivers/scsi/scsi_lib.c:1260`
**Verdict:** Yes

The store operation occurs in `scsi_init_command()` (at `drivers/scsi/scsi_lib.c:1260`), where the `scmd_eh_abort_handler` function pointer is passed to the `INIT_DELAYED_WORK` macro. This macro initializes a `delayed_work` struct (`cmd->abort_work`) and stores the function pointer in the underlying `work_struct`.

This store happens when a new SCSI command is being prepared and initialized for submission. The context is typically the process submitting the I/O request (such as a user space task performing a read/write system call, or a kernel thread originating block layer I/O).

The execution of the stored function pointer (`scmd_eh_abort_handler`) occurs only if the SCSI command takes too long and times out, prompting the delayed work timer to expire. When the timer expires, the work item is queued to a system workqueue, and it is subsequently executed by a worker thread (e.g., `kworker`). 

Because the store is performed by the I/O submitter and the execution is performed by a dedicated workqueue thread long after submission (and only in the event of a timeout), the "current" task context definitively changes between the two operations. Thus, the function is executed asynchronously.
---

## Task 385: `scsi_done` at `drivers/ata/libata-scsi.c:687`
**Verdict:** Yes

The task asks to determine if the function pointer `scsi_done` stored at `drivers/ata/libata-scsi.c:687` inside `__ata_scsi_queuecmd` (specifically within `ata_scsi_qc_new`) will be executed asynchronously.

1. At `drivers/ata/libata-scsi.c:687` within `ata_scsi_qc_new`, the SCSI completion callback function pointer `scsi_done` is stored in the `ata_queued_cmd` structure (`qc->scsidone = scsi_done;`).
2. This structure encapsulates an ATA command that is then queued to the underlying hardware controller for execution.
3. The function that stores this pointer (`__ata_scsi_queuecmd` -> `ata_scsi_qc_new`) returns, allowing the original task (which issued the disk I/O request) to continue execution or sleep while waiting for the hardware to finish the operation.
4. Once the hardware completes the disk I/O, it raises a hardware interrupt. The kernel's interrupt handler (and subsequently softirq context) processes the completion of the ATA command via `ata_qc_complete()`.
5. During this asynchronous completion path, the libata subsystem invokes the stored callback `qc->scsidone(qc->scsicmd)` to notify the higher-level SCSI layer that the command has finished.
6. Because `scsi_done` is executed from the hardware interrupt or softirq context triggered by the disk controller, it executes asynchronously relative to the task that originally queued the command.

Therefore, the function pointer is executed asynchronously, and the "current" task context definitively changes when it is called.
---

## Task 386: `seg6_genl_dumphmac` at `net/netlink/genetlink.c:272`
**Verdict:** No

The task asks to determine if the function pointer `seg6_genl_dumphmac` stored at `net/netlink/genetlink.c:272` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `dumpit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 272, it copies the `dumpit` function pointer (`op->dumpit = full->dumpit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_dumpit` and `__netlink_dump_start`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 387: `seg6_genl_dumphmac_done` at `net/netlink/genetlink.c:273`
**Verdict:** Yes

The function pointer `seg6_genl_dumphmac_done` is stored into a `struct genl_split_ops` at `net/netlink/genetlink.c:273` within `genl_cmd_full_to_split()`.
This happens when a genetlink family receives a dump request (e.g., via a `sendmsg` syscall), and `genl_family_rcv_msg()` uses `genl_get_cmd()` to initialize a local stack variable `op` of type `struct genl_split_ops`.
This stack variable is then passed to `genl_family_rcv_msg_dumpit()`, which initiates the netlink dump by calling `__netlink_dump_start()`. 
During the dump initialization in `genl_start()`, the `ops` structure (containing the function pointer) is copied to a dynamically allocated heap structure `info` (`info->op = *ops;`), which is saved in the netlink callback state (`cb->data`).
The actual execution of the stored `.done` function occurs later, when the netlink dump finishes. This typically happens during subsequent `recvmsg` system calls on the netlink socket, which invoke `netlink_dump()`, and finally `genl_done()`, executing `ops->done(cb)`.
Because the function pointer is stored during the initial request processing (e.g., `sendmsg`) and executed later during a separate event or system call (e.g., `recvmsg`), it breaks the synchronous call chain and is executed asynchronously. Additionally, it could potentially be executed by a different task if the file descriptor is shared. Thus, the execution context is asynchronous relative to the store.
---

## Task 388: `seg6_genl_dumphmac_start` at `net/netlink/genetlink.c:271`
**Verdict:** No

The function pointer `seg6_genl_dumphmac_start` is stored into `op->start` inside `genl_cmd_full_to_split()` at `net/netlink/genetlink.c:271`. This function is inlined into `genl_op_iter_next()`, where it populates the `start` field of a `struct genl_split_ops` inside a `struct genl_op_iter`. The `genl_op_iter` is used purely for iterating over the available generic netlink operations (for purposes such as dumping policy to userspace or validating operations during family registration). The function pointer stored within this iterator structure is never actually executed from the iterator. (When the command is actually executed, `genl_cmd_full_to_split()` is called from `genl_get_cmd()` to populate a different `genl_split_ops` structure, from which it is executed synchronously). Since the function pointer stored in `genl_op_iter_next()` is never executed, it is not executed asynchronously.
---

## Task 389: `seg6_genl_get_tunsrc` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task asks to determine if the function pointer `seg6_genl_get_tunsrc` stored at `net/netlink/genetlink.c:276` inside `genl_op_iter_next` (which inlines `genl_cmd_full_to_split`) will be executed asynchronously.

This is structurally identical to the situation for other `doit` generic netlink operations when iterating ops.
1. `genl_cmd_full_to_split` is a helper function that copies a generic netlink operation definition from a `struct genl_ops` to a `struct genl_split_ops`. At line 276, it copies the `doit` function pointer (`op->doit = full->doit;`).
2. When this store occurs via `genl_op_iter_next`, it is because the kernel is iterating over netlink operations (for example, during `genl_validate_ops` at registration time, or during `ctrl_fill_info` and `ctrl_dumppolicy` to report family capabilities to userspace).
3. In all of these iteration paths, the function pointers copied into the iterator's state (`iter->doit` and `iter->dumpit`) are only queried for their metadata (like command ID, flags, maxattr, and policy validation rules). They are NEVER executed from these iterator copies.
4. The only path where the copied pointer is actually executed is when `genl_cmd_full_to_split` is called from `genl_get_cmd` during the processing of an incoming netlink message (`genl_family_rcv_msg`). In that case, as established in previous tasks, the execution happens synchronously as part of the `sendmsg` syscall context (via `genl_family_rcv_msg_doit`).

Since the function pointer stored at this location is either never executed (if stored during iteration) or executed synchronously within the same task context (if stored during message processing), it is never executed asynchronously. Therefore, the `current` task context does not change when called.
---

## Task 390: `seg6_genl_set_tunsrc` at `net/netlink/genetlink.c:276`
**Verdict:** No

The function pointer `seg6_genl_set_tunsrc` is stored into `op->doit` at `net/netlink/genetlink.c:276` within the function `genl_cmd_full_to_split`. This assignment occurs when converting a full generic netlink operation definition into a split operation definition. 

This conversion happens in a couple of places:
1. During `genl_get_cmd`, which is called by `genl_family_rcv_msg` when a generic netlink message is received. In this path, the `op->doit` function is immediately invoked via `genl_family_rcv_msg_doit` within the exact same task context (the task invoking the `sendmsg` system call on the netlink socket). The execution is completely synchronous.
2. During `genl_op_iter_next`, which is used to iterate over a generic netlink family's operations (e.g., during validation in `genl_validate_ops` or when dumping policy info). In these paths, the `op->doit` function pointer is just copied and read, but never executed.

In either case, the stored function pointer is never executed asynchronously in a different task context. Therefore, the execution of the stored function pointer does not involve a change in the "current" task.
---

## Task 391: `seg6_genl_sethmac` at `net/netlink/genetlink.c:276`
**Verdict:** No

The task involves the function pointer `seg6_genl_sethmac`, which serves as a `.doit` handler for the generic netlink command `SEG6_CMD_SETHMAC`. The store happens at `net/netlink/genetlink.c:276` inside `genl_cmd_full_to_split`.

The provided context indicates this specific store was triggered from `genl_op_iter_next`. The `genl_op_iter_next` function is an iterator used during family registration (`genl_validate_ops`) or when querying family info (`ctrl_fill_info`, `ctrl_dumppolicy_put_op`). In these iterator paths, the function pointer is copied into an iterator struct (`iter->doit.doit`) purely to query operation properties (like `.policy` or `.flags`), but the function pointer itself is never invoked.

Even if we consider the execution path where the `.doit` function is actually invoked (when handling a received netlink message via `genl_rcv_msg` -> `genl_family_rcv_msg`), `genl_get_cmd` copies the operation structure onto the stack, and `genl_family_rcv_msg_doit` immediately and synchronously calls the `.doit` function pointer. Since the function is called synchronously within the same task context that received and parsed the netlink message, there is no change in task context. Thus, the function is never executed asynchronously.
---

## Task 392: `set_is_seen` at `fs/proc/proc_sysctl.c:1530`
**Verdict:** Yes

The function pointer `set_is_seen` is passed to `setup_sysctl_set` inside `setup_ipc_sysctls` (in `ipc/ipc_sysctl.c:249`) and is stored into the `is_seen` field of a `struct ctl_table_set` at `fs/proc/proc_sysctl.c:1530`.

This storage occurs when an IPC namespace is initialized (either during boot for the initial namespace or when a new IPC namespace is created via `unshare` or `clone`).

The stored `is_seen` function pointer is later invoked via `sysctl_is_seen` when performing a pathname lookup in `/proc/sys/`. Specifically, the VFS calls `proc_sys_compare` (the `d_compare` dentry operation for procfs sysctl entries), which in turn executes `set_is_seen`.

This execution happens in the context of whichever user-space task is attempting to resolve a path in `/proc/sys/` (for example, by calling `open`, `stat`, or `read`). Because this lookup can be performed by any process at any time, the execution of the stored function pointer happens asynchronously relative to the task that initialized the IPC namespace, and the "current" task context will evaluate to the process performing the VFS lookup.
---

## Task 393: `shmem_free_in_core_inode` at `fs/inode.c:315`
**Verdict:** Yes

The function pointer `shmem_free_in_core_inode` (which is passed as `ops->free_inode` for the shmem filesystem) is stored into `inode->free_inode` at `fs/inode.c:315` within `destroy_inode()` (which is inlined into `evict()`). Immediately after this store, `call_rcu(&inode->i_rcu, i_callback)` is called. `call_rcu` schedules the `i_callback` function to be executed asynchronously after an RCU grace period (typically in a softirq context). When the RCU grace period elapses, the `i_callback` function executes and calls the stored function pointer via `inode->free_inode(inode)`. Since the execution is deferred via RCU, the stored function will be executed asynchronously in a different context (RCU callback context) from the task context that stored it. Verdict: Yes.
---

## Task 394: `single_next` at `fs/seq_file.c:580`
**Verdict:** Yes

The function pointer `single_next` is stored into the `next` field of a newly allocated `struct seq_operations` at `fs/seq_file.c:580` inside the `single_open` function.

This storage occurs when a process opens a sequential file (like many files in `/proc`, `/sys`, or debugfs) that uses the `single_open` interface. This happens during the `open` system call.

The stored `next` function pointer is later invoked during the `read` system call when the user-space process reads data from the opened file descriptor. Specifically, the execution happens inside `seq_read_iter` (e.g., `m->op->next(m, p, &m->index)`).

Because the execution of the function pointer happens during a subsequent `read` system call (which may even be performed by a completely different process if the file descriptor is passed around or inherited), it is executed asynchronously relative to the task context that stored it during the `open` system call. The "current" task context will change to whatever process is performing the read.
---

## Task 395: `single_start` at `fs/seq_file.c:579`
**Verdict:** Yes

The function pointer `single_start` is stored into a dynamically allocated `struct seq_operations` (specifically the `.start` field) at `fs/seq_file.c:579` within the `single_open()` function.
This function is generally called during the `open` system call when a user opens a corresponding sequential file (e.g., in `/proc`). The `seq_operations` struct is then linked to the `seq_file` associated with the open file descriptor via `seq_open()`.
The stored `.start` function is not executed synchronously during the `open` call. Instead, its execution is deferred until a `read` or `lseek` system call is performed on that file descriptor. When a user process reads from the file, `seq_read_iter()` or `traverse()` is invoked, which executes the stored function via `m->op->start()`.
Because the function pointer is stored during the `open` system call and executed later during a subsequent `read` or `lseek` system call, it breaks the synchronous call chain and is executed asynchronously relative to the store. Furthermore, if the file descriptor is shared (e.g., across a `fork` or sent via a UNIX socket), the function may even be executed by a completely different process, definitively changing the "current" task context.
---

## Task 396: `single_stop` at `fs/seq_file.c:581`
**Verdict:** Yes

The function pointer `single_stop` is stored into `op->stop` at `fs/seq_file.c:581` within `single_open()`. This store occurs when a process invokes the `open()` system call for a specific sequence file. The stored function pointer is later executed during the `read()` system call on that file descriptor (for example, inside `seq_read_iter()`). Because the function pointer is stored during one system call (`open`) and executed during a later, separate system call (`read`), the execution is deferred. The `read()` system call can be performed by a completely different task than the one that originally opened the file (e.g., if the file descriptor was inherited by a child process after a `fork()`, or passed to another process via a Unix domain socket). Therefore, the stored function is executed asynchronously relative to the original store operation, and the 'current' task context can indeed change between the store and the execution. Verdict: Yes.
---

## Task 397: `sk_stream_write_space` at `net/ipv4/tcp.c:460`
**Verdict:** Yes

The function pointer `sk_stream_write_space` is stored in the `sk_write_space` callback field of a TCP socket (`struct sock *sk`) during socket initialization at `net/ipv4/tcp.c:460` inside the `tcp_init_sock` function.

This storage happens in the context of the user-space process that creates the socket, typically through a `socket()` system call for `AF_INET/SOCK_STREAM` or during the `accept()` system call when a new socket is being set up.

The stored `sk_write_space` callback is later executed when the socket frees up write buffer space, usually because the remote peer acknowledged received data. This execution happens in the networking bottom-half (softirq) context (e.g., `NET_RX_SOFTIRQ`), specifically during packet processing in `tcp_rcv_established` or similar input paths (e.g., `INDIRECT_CALL_1(sk->sk_write_space, ...)` in `tcp_input.c`).

Because the function pointer is executed in response to network events (interrupts/softirqs) long after the socket was created, it is executed asynchronously. The "current" task context during its execution will typically be `ksoftirqd` or an arbitrary task that was interrupted, which is completely decoupled from the task that originally stored the pointer.
---

## Task 398: `snd_info_seq_show` at `fs/seq_file.c:582`
**Verdict:** Yes

The function pointer `snd_info_seq_show` is stored into a dynamically allocated `struct seq_operations` (specifically the `.show` field) at `fs/seq_file.c:582` within the `single_open()` function.
This function is generally called during the `open` system call when a user opens a corresponding ALSA sound information sequential file. The `seq_operations` struct is then linked to the `seq_file` associated with the open file descriptor via `seq_open()`.
The stored `.show` function is not executed synchronously during the `open` call. Instead, its execution is deferred until a `read` system call is performed on that file descriptor. When a user process reads from the file, `seq_read_iter()` or `traverse()` is invoked, which executes the stored function via `m->op->show()`.
Because the function pointer is stored during the `open` system call and executed later during a subsequent `read` system call, it breaks the synchronous call chain and is executed asynchronously relative to the store. Furthermore, if the file descriptor is shared (e.g., across a `fork` or sent via a UNIX socket), the function may even be executed by a completely different process, definitively changing the "current" task context.
---

## Task 399: `sock_def_destruct` at `net/core/sock.c:3479`
**Verdict:** Yes

The function pointer `sock_def_destruct` is stored in the `sk_destruct` callback field of a network socket (`struct sock *sk`) during the socket's initialization at `net/core/sock.c:3479` inside `sock_init_data_uid` (called from `sock_init_data`).

This storage occurs in the context of the task creating the socket, typically during a `socket()` system call or when accepting a new connection.

The stored `sk_destruct` callback is later executed when the socket is being destroyed and its memory is being freed. This is triggered by `sk_destruct` (called by `sk_free` when the socket's reference count drops to zero). Depending on the socket type, it might be executed immediately in the context of the task closing the socket, or more commonly for many socket types (like TCP, which set `SOCK_RCU_FREE`), it is deferred via `call_rcu` and executed in an RCU callback (softirq or RCU kthread context).

Because the function pointer is executed upon the last reference drop (which can occur in an arbitrary task context, a softirq, or an RCU callback) long after the socket was created, it is executed asynchronously. The "current" task context will depend on whatever triggered the final `sock_put`, which is decoupled from the task that originally stored the pointer.
---

## Task 400: `sock_def_write_space` at `net/core/sock.c:3477`
**Verdict:** Yes

The `sock_init_data_uid` function initializes a new socket (`struct sock`) and stores the default write space callback function pointer `sock_def_write_space` into `sk->sk_write_space`. 

The `sk_write_space` callback is invoked to wake up processes waiting to write to the socket when buffer space becomes available. This typically happens when transmitted packets are acknowledged and their corresponding socket buffers (`sk_buff`) are freed (for example, via `sock_wfree` which is called when the network interface card finishes transmitting a packet). These events occur in the context of network interrupt handlers, softirqs (like `NET_RX_SOFTIRQ`), or NAPI polling, which are different from the process context that originally created the socket (e.g., during the `socket()` system call). Therefore, the stored function pointer will be executed asynchronously in a different task context.
---

## Task 401: `sock_diag_bind` at `net/netlink/af_netlink.c:716`
**Verdict:** Yes

The function pointer `sock_diag_bind` is stored into the `netlink_bind` field of a `netlink_sock` structure at `net/netlink/af_netlink.c:716` inside the `netlink_create()` function.
This occurs when a user space application creates a new netlink socket (e.g., of protocol `NETLINK_SOCK_DIAG`) using the `socket()` system call. During socket creation, the kernel copies the protocol-specific `bind` callback from the global `nl_table` into the new socket's private data structure (`nlk->netlink_bind = bind`).
The stored function is not executed immediately during the `socket()` system call. Instead, its execution is deferred until the application subsequently invokes a `bind()` system call on that socket (handled by `netlink_bind()`) or adds a multicast group membership via `setsockopt()` (handled by `netlink_setsockopt()`).
Because the function pointer is stored during the `socket` creation syscall and executed in response to a subsequent and distinct `bind` or `setsockopt` syscall, the execution is asynchronous relative to the store. This breaks the synchronous call chain, and if the socket is shared (e.g., via `fork` or UNIX domain sockets), the callback could even be executed by a different task context.
---

## Task 402: `sock_free_inode` at `fs/inode.c:315`
**Verdict:** Yes

The function pointer `sock_free_inode` (which is passed as `ops->free_inode` for the sockfs filesystem) is stored into `inode->free_inode` at `fs/inode.c:315` within `destroy_inode()` (which is inlined into `evict()`). Immediately after this store, `call_rcu(&inode->i_rcu, i_callback)` is called. `call_rcu` schedules the `i_callback` function to be executed asynchronously after an RCU grace period (typically in a softirq context). When the RCU grace period elapses, the `i_callback` function executes and calls the stored function pointer via `inode->free_inode(inode)`. Since the execution is deferred via RCU, the stored function will be executed asynchronously in a different context (RCU callback context) from the task context that stored it. Verdict: Yes.
---

## Task 403: `submit_bio_wait_endio` at `block/bio.c:1390`
**Verdict:** Yes

The function pointer `submit_bio_wait_endio` is stored into `bio->bi_end_io` at `block/bio.c:1390` within `submit_bio_wait()`. Immediately after this store, `submit_bio(bio)` is called to issue the block I/O request to the block layer, and the current task goes to sleep using `blk_wait_io(&done)` to wait for the I/O completion. The stored `bi_end_io` callback is invoked by the block layer when the underlying device signals that the I/O has finished. This completion process generally occurs in an asynchronous context, such as a hardware interrupt handler, a softirq (e.g., `BLOCK_SOFTIRQ`), or an I/O completion workqueue. The callback executes in this distinct context and calls `complete()` to wake up the original submitting thread. Because the execution of the callback is deferred until hardware completion and occurs in a separate context, the stored function is executed asynchronously. Verdict: Yes.
---

## Task 404: `super_cache_count` at `fs/super.c:384`
**Verdict:** Yes

The `alloc_super` function creates and initializes a new superblock (`struct super_block`), including its associated cache shrinker (`s->s_shrink`). It stores the `super_cache_count` function pointer into `s->s_shrink->count_objects`. 

This stored callback is later invoked by the kernel's memory management subsystem (e.g., via background threads like `kswapd` or by other processes during direct memory reclaim) to determine the number of items in the superblock's caches that can be freed. Because memory reclaim operations are triggered globally and generally run in entirely different task contexts (such as `kswapd` or unrelated tasks under memory pressure) than the process that originally mounted the filesystem and called `alloc_super`, the function pointer is executed asynchronously.
---

## Task 405: `super_cache_scan` at `fs/super.c:383`
**Verdict:** Yes

The function pointer `super_cache_scan` is stored in the `scan_objects` callback field of a shrinker (`struct shrinker`) during superblock allocation at `fs/super.c:382-383` inside the `alloc_super` function.

This storage occurs when a filesystem is being mounted, which happens in the context of the user-space process invoking the `mount` system call.

The stored `scan_objects` callback is later executed when the system experiences memory pressure and needs to reclaim memory by shrinking caches (like the dentry and inode caches associated with this superblock). This execution is performed by `shrink_slab` (and related functions), which is typically invoked either by the background kernel thread `kswapd` or by arbitrary tasks performing direct memory reclaim when they fail to allocate memory.

Because the function pointer is executed long after the mount operation completes and is triggered by system memory conditions rather than a direct synchronous call, it is executed asynchronously. The "current" task context will evaluate to the memory-reclaiming task (e.g., `kswapd` or any other process), which is completely decoupled from the task that originally stored the pointer.
---

## Task 406: `tcp_compressed_ack_kick` at `net/ipv4/tcp_timer.c:881`
**Verdict:** Yes

The function pointer `tcp_compressed_ack_kick` is stored into the `function` field of an `hrtimer` (`tcp_sk(sk)->compressed_ack_timer.function`) at `net/ipv4/tcp_timer.c:881` within `tcp_init_xmit_timers()`. This operation initializes the callback for a high-resolution timer used to handle compressed acknowledgments in TCP. The timer is initialized with the `HRTIMER_MODE_REL_PINNED_SOFT` flag. When the timer is subsequently armed and expires, the `hrtimer` subsystem invokes this callback. The execution of the timer callback occurs in a softirq context, which is entirely separate from the execution context (or task) that initialized or armed the timer. Because the timer subsystem defers execution until the timer expires and runs it in a different context, the stored function is executed asynchronously. Verdict: Yes.
---

## Task 407: `tcp_delack_timer` at `kernel/time/timer.c:900`
**Verdict:** Yes

The `tcp_delack_timer` function is a kernel timer callback used for TCP delayed acknowledgments. It is registered by storing its function pointer into a `struct timer_list` (via `timer_setup` or `init_timer_key`).

Once the timer is armed (e.g., when a TCP packet is received and an ACK is delayed), the kernel's timer subsystem will later execute this function when the timer expires. The execution occurs in a softirq context (typically `TIMER_SOFTIRQ`), which is completely decoupled and asynchronous from the context that originally initialized or armed the timer. Thus, the "current" task context will indeed change when the function is called.
---

## Task 408: `tcp_keepalive_timer` at `kernel/time/timer.c:900`
**Verdict:** Yes

The function pointer `tcp_keepalive_timer` is stored into a `struct timer_list` via the `init_timer_key()` function (which sets `timer->function = func`).
This occurs when a TCP connection initializes its keepalive timer. The stored callback function is executed only when the timer expires.
Timer callbacks in the Linux kernel are executed by the timer wheel infrastructure (typically in `TIMER_SOFTIRQ` context) entirely asynchronously from the task that armed or initialized the timer. Since the timer expiration happens independently of the system call or task that set it up, the "current" task context during execution will be different (i.e., it will run in interrupt/softirq context, interrupting whatever task happens to be running, or in a dedicated ksoftirqd kernel thread). Therefore, it breaks the synchronous call chain and is definitively executed asynchronously.
---

## Task 409: `tcp_pace_kick` at `net/ipv4/tcp_timer.c:877`
**Verdict:** Yes

The function pointer `tcp_pace_kick` is stored in the `function` callback field of a high-resolution timer (`struct hrtimer pacing_timer` inside `struct tcp_sock`) at `net/ipv4/tcp_timer.c:877` within the `tcp_init_xmit_timers` function.

This storage happens during TCP socket initialization (called via `tcp_init_sock`), which occurs in the context of the user-space process that creates the socket via the `socket()` or `accept()` system calls.

The stored `tcp_pace_kick` callback is later executed when the pacing timer expires. This execution occurs in the high-resolution timer interrupt or softirq context to manage TCP packet pacing (sending data at a controlled rate). 

Because the timer expires and the callback is invoked based on clock events long after the socket was initialized, it is executed asynchronously. The "current" task context at the time of execution will be whatever task happened to be running when the timer interrupt fired or the softirq thread executing the timers, which is entirely decoupled from the task that stored the pointer.
---

## Task 410: `tcp_v6_do_rcv` at `net/ipv6/af_inet6.c:219`
**Verdict:** Yes

The function pointer `tcp_v6_do_rcv` (obtained from `answer->prot->backlog_rcv` for TCPv6) is stored into `sk->sk_backlog_rcv` at `net/ipv6/af_inet6.c:219` within `inet6_create()`. This initialization occurs when an IPv6 socket is created via the `socket()` system call. The `sk_backlog_rcv` callback is invoked to process incoming network packets that arrive when the socket is currently locked by a process (e.g., during a `recvmsg` or `sendmsg` operation). When a packet arrives under these conditions (typically in a softirq context), it is added to the socket's backlog queue. Later, when the process releases the socket lock (via `release_sock()`), the queued packets are processed by calling `sk->sk_backlog_rcv`. Because packet arrival and socket locking are independent, asynchronous events relative to the initial socket creation, and because the socket may be operated on by different tasks (e.g., via `fork` or file descriptor passing), the stored function is executed asynchronously. Verdict: Yes.
---

## Task 411: `tcp_write_timer` at `kernel/time/timer.c:900`
**Verdict:** Yes

The `tcp_write_timer` function is a kernel timer callback used for handling TCP retransmissions, zero-window probes, and other write-related timeouts. It is registered by storing its function pointer into a `struct timer_list` (via `timer_setup` or `init_timer_key`).

When the armed timer expires, the kernel's timer subsystem executes this callback. This execution occurs asynchronously in a softirq context (typically `TIMER_SOFTIRQ`), which is completely independent of the task context that originally initialized or armed the timer. As a result, the "current" task context will change when the function is invoked.
---

## Task 412: `tctx_task_work` at `./include/linux/task_work.h:13`
**Verdict:** Yes

The function pointer `tctx_task_work` is stored into a `struct callback_head` via the `init_task_work()` function.
This initialization occurs in `io_uring_alloc_task_context()`, which allocates and sets up the io_uring task context for a process the first time it submits an io_uring request.
The stored callback is not executed synchronously. Instead, when an asynchronous io_uring request completes (often in an interrupt handler, softirq context, or an `io-wq` worker thread), the kernel schedules the `tctx_task_work` to run in the original submitting task's context by calling `task_work_add()`.
The function is subsequently executed when the original task returns to userspace and processes its pending task work queue via `task_work_run()`. Because the callback is stored during context initialization and executed later during the task's return-to-userspace loop (triggered by asynchronous completion events), it breaks the synchronous call chain and is definitively executed asynchronously.
---

## Task 413: `tctx_task_work` at `io_uring/tctx.c:90`
**Verdict:** No

The function pointer `tctx_task_work` is stored inside the `task_work` structure (of type `struct callback_head`) of an `io_uring_task` context at `io_uring/tctx.c:90` within the `io_uring_alloc_task_context` function.

This storage occurs when a task first interacts with an io_uring instance and its task-specific io_uring context is allocated. The task that stores the pointer is the current task interacting with io_uring.

The stored `tctx_task_work` callback is later executed when the task processes its task work queue (e.g., via `task_work_run()` upon returning to user space or in `io_run_task_work()`). The `task_work_add` function strictly queues the work onto the original task's work list (`req->task`). 

Because task work executes exclusively in the context of the task to which it was added, the `tctx_task_work` function will always be executed by the exact same task that stored it. Therefore, the "current" task context does NOT change, and the function pointer is not executed asynchronously with respect to the task context.
---

## Task 414: `udp_destruct_sock` at `net/ipv4/udp.c:1609`
**Verdict:** Yes

The function pointer `udp_destruct_sock` is stored into `sk->sk_destruct` at `net/ipv4/udp.c:1609` within `udp_init_sock()`. This initialization happens during the creation of an IPv4 UDP socket. The `sk_destruct` callback is invoked when the socket is being destroyed after its reference count drops to zero. For UDP sockets, the socket structure has the `SOCK_RCU_FREE` flag set. As a result, when the last reference to the socket is dropped and the kernel begins to free it (via `sk_destruct()` in `net/core/sock.c`), it calls `call_rcu(&sk->sk_rcu, __sk_destruct)`. This defers the execution of `__sk_destruct`, which is the function that actually invokes `sk->sk_destruct(sk)`. The deferred execution occurs in an RCU callback context (typically a softirq) after a grace period. Therefore, the stored function is executed asynchronously, changing the "current" task context from the one that dropped the last reference (or originally created the socket). Verdict: Yes.
---

## Task 415: `udpv6_destruct_sock` at `net/ipv6/udp.c:71`
**Verdict:** Yes

The `udpv6_init_sock` function initializes an IPv6 UDP socket and sets its destructor callback `sk->sk_destruct` to the function pointer `udpv6_destruct_sock`. 

The `sk_destruct` callback is invoked when the socket's reference count drops to zero and the socket is being freed. While this can happen synchronously during a `close()` system call, it very frequently happens asynchronously. For example, socket references are held by network packets (`sk_buff`) in flight. When the last packet associated with the socket is transmitted or discarded by the network interface driver, the corresponding `sk_buff` is freed, and `sock_put()` is called from a softirq context (like `NET_TX_SOFTIRQ` or `NET_RX_SOFTIRQ`). Furthermore, many network sockets are destroyed via RCU callbacks. In these cases, the destructor is executed in a completely different task context than the one that originally created the socket. Thus, the function is executed asynchronously.
---

## Task 416: `umh_keys_init` at `kernel/umh.c:378`
**Verdict:** Yes

The function pointer `umh_keys_init` is stored in the `init` callback field of a `subprocess_info` structure at `kernel/umh.c:378` within the `call_usermodehelper_setup` function.

This storage occurs when a task requests the execution of a user-mode helper (in this case, for key management via `security/keys/request_key.c:81`), which happens in the context of whatever task initiated the request.

The stored `init` callback is later executed by `call_usermodehelper_exec_async`. This execution happens inside a newly spawned kernel thread (created via `user_mode_thread` from a system workqueue) that prepares to transition into user space and execute the user-mode helper binary via `kernel_execve`.

Because the function pointer is executed by this newly created worker thread to set up credentials before execing the helper, it is executed asynchronously. The "current" task context at the time of execution will be the newly spawned `user_mode_thread`, which is distinct from the task that originally stored the pointer.
---

## Task 417: `unix_dgram_peer_wake_relay` at `./include/linux/wait.h:92`
**Verdict:** Yes

The function pointer `unix_dgram_peer_wake_relay` is stored into a waitqueue entry's `.func` field via `init_waitqueue_func_entry(&u->peer_wake, unix_dgram_peer_wake_relay)`.
This storage occurs during the initialization of a UNIX domain socket (e.g., in `unix_create1()`).
The stored callback is designed to relay wakeups from a peer socket back to this socket. It is not executed synchronously. Instead, when the socket is connected or attempts to send data to a peer and block, this waitqueue entry (`u->peer_wake`) is added to the peer socket's `peer_wait` queue.
The callback is subsequently executed when the peer socket invokes a wakeup on its `peer_wait` queue. Since this wakeup is typically triggered by an action on the peer socket (such as another process reading from it or closing it), the callback is executed in the context of the task performing that action, not the task that created the socket or added the wait queue entry.
Because the function pointer is stored during socket initialization and executed later during a waitqueue wakeup triggered by an independent event on a peer socket (typically by a different process), the execution breaks the synchronous call chain and definitively changes the "current" task context.
---

## Task 418: `unix_sock_destructor` at `net/unix/af_unix.c:974`
**Verdict:** Yes

The function pointer `unix_sock_destructor` is stored into `sk->sk_destruct` at `net/unix/af_unix.c:974` within `unix_create1()`. This initialization takes place during the creation of a Unix domain socket. The `sk_destruct` callback is invoked when the socket is being destroyed after its reference count drops to zero. The dropping of the final reference can easily happen in an asynchronous context. For example, Unix domain sockets are subject to garbage collection to break reference cycles (`net/unix/garbage.c`). This garbage collector runs asynchronously in a workqueue (`unix_gc_work`). If the GC frees in-flight SKBs and drops the last reference to the socket, the destructor will run in the workqueue context. Furthermore, even if the socket is destroyed during a standard `close()` system call, this is a separate, deferred event relative to socket creation, and it may be performed by a different task (for instance, if the file descriptor was inherited by a child process or passed to another process via `SCM_RIGHTS`). Because execution is deferred until the final reference drop and can occur in a different task or workqueue context, the stored function is executed asynchronously. Verdict: Yes.
---

## Task 419: `unix_stream_read_actor` at `net/unix/af_unix.c:2922`
**Verdict:** No

The function pointer `unix_stream_read_actor` is stored into a stack-allocated `struct unix_stream_read_state` (in the `recv_actor` field) within the `unix_stream_recvmsg` function. This state structure is then passed directly to `unix_stream_read_generic`. 

Inside `unix_stream_read_generic`, the stored function pointer is invoked synchronously to copy data from socket buffers into the user's message buffer during the `recvmsg` system call. While the thread may yield and sleep while waiting for data to arrive, the actual execution of the callback always occurs synchronously within the same task context that originally initiated the system call. Therefore, the function is never executed asynchronously.
---

## Task 420: `unix_write_space` at `net/unix/af_unix.c:972`
**Verdict:** Yes

The function pointer `unix_write_space` is stored in the `sk_write_space` callback field of a UNIX domain socket (`struct sock`) during socket creation at `net/unix/af_unix.c:972` inside the `unix_create1` function.

This storage occurs in the context of the task creating the socket, typically during a `socket()` or `socketpair()` system call.

The stored `sk_write_space` callback is later executed when the socket's write buffer space becomes available. For UNIX domain sockets, this typically happens when a packet (skb) sent by this socket is consumed and freed by the receiving peer socket. The skb's destructor (`sock_wfree`) drops the write memory accounting and invokes `sk->sk_write_space` to wake up any tasks waiting to send more data. 

Because this execution happens during the peer's `recvmsg()` system call (when it frees the skb) or during garbage collection, the callback is executed asynchronously. The "current" task context will be the task reading from the receiving socket, which is generally a completely different process or thread from the one that created the sending socket.
---

## Task 421: `update_super_work` at `fs/ext4/super.c:5276`
**Verdict:** Yes

The function pointer `update_super_work` is stored into the `func` field of the work structure `sbi->s_sb_upd_work` at `fs/ext4/super.c:5276` within `ext4_fill_super()`. This initialization is performed using the `INIT_WORK()` macro. The initialized work structure is designed to handle updates to the ext4 superblock in the background. When an event occurs that requires updating the superblock (such as recording an error state), the filesystem calls `schedule_work(&EXT4_SB(sb)->s_sb_upd_work)`. This adds the work to a kernel workqueue, which will subsequently be executed by a kernel worker thread. Because the execution of `update_super_work` is deferred to a worker thread running in a completely different context from the task that scheduled it (or the one that initialized it), the stored function is executed asynchronously. Verdict: Yes.
---

## Task 422: `vc_SAK` at `drivers/tty/vt/vt.c:1072`
**Verdict:** Yes

The function pointer `vc_SAK` is stored into a `struct work_struct` via the `INIT_WORK(&vc_cons[currcons].SAK_work, vc_SAK)` macro.
This initialization occurs during virtual console allocation (`vc_allocate()`).
The stored callback is designed to be executed by the Linux workqueue subsystem. It is not executed synchronously during allocation. Instead, the work is scheduled to run when the Secure Attention Key (SAK) combination is triggered by the keyboard driver, which calls `schedule_work(&vc_cons[fg_console].SAK_work)`.
Once scheduled, the `vc_SAK` function is executed asynchronously by a `kworker` kernel thread. Because the function is stored during VT initialization and executed later by the workqueue infrastructure in response to a keyboard interrupt, it breaks the synchronous call chain and is definitively executed in a completely different task context.
---

## Task 423: `wake_bit_function` at `fs/fs-writeback.c:1512`
**Verdict:** Yes

The macro `DEFINE_WAIT_BIT` at `fs/fs-writeback.c:1512` initializes a `wait_bit_queue` structure on the stack. During this initialization, the function pointer `wake_bit_function` is stored into the wait queue entry's callback field (`func`). 

This wait queue entry is then added to the inode's wait queue, and the current task goes to sleep waiting for the `__I_SYNC` bit to be cleared (indicating writeback completion). When the writeback finishes, a different thread (such as a kernel flusher thread or a worker thread handling IO completion) calls `wake_up_bit()`. This waker thread iterates through the wait queue and executes the stored `wake_bit_function` callback to wake up the sleeping task. Because the callback is executed by the waker thread and not the thread that initialized the wait queue entry, it is executed asynchronously in a different task context.
---

## Task 424: `wb_update_bandwidth_workfn` at `mm/backing-dev.c:540`
**Verdict:** Yes

The function pointer `wb_update_bandwidth_workfn` is stored into the `func` field of the delayed work structure `wb->bw_dwork` at `mm/backing-dev.c:540` within `wb_init()`. This is accomplished using the `INIT_DELAYED_WORK()` macro. Delayed work items allow tasks to be scheduled for future execution. When the kernel needs to update writeback bandwidth statistics, it queues this delayed work (e.g., using `queue_delayed_work()`). Once the specified delay elapses, the workqueue subsystem dispatches the callback function `wb_update_bandwidth_workfn` to be executed by a kernel worker thread. Since the function is executed in a deferred manner by a background worker thread—completely detached from the execution context that initialized or queued the work—it is executed asynchronously. Verdict: Yes.
---

## Task 425: `wb_workfn` at `mm/backing-dev.c:539`
**Verdict:** Yes

The function pointer `wb_workfn` is stored in the `dwork` field (a `struct delayed_work`) of a `bdi_writeback` structure at `mm/backing-dev.c:539` via the `INIT_DELAYED_WORK` macro inside the `wb_init` function.

This storage occurs when a backing device info (BDI) or a cgroup-specific writeback context is initialized. This typically happens during system boot, device initialization, or filesystem mount in the context of the task performing those operations.

The stored `wb_workfn` callback is later executed when writeback work is scheduled (e.g., to flush dirty pages to disk). Because it was initialized as a workqueue item, its execution is handled by a background worker thread (`kworker`) associated with the `bdi_wq` workqueue.

Since the function pointer is executed by a background worker thread rather than the task that initialized the BDI, it is executed asynchronously. The "current" task context at the time of execution evaluates to the `kworker` thread, which is completely decoupled from the task that originally stored the pointer.
---

## Task 426: `woken_wake_function` at `net/ipv4/af_inet.c:600`
**Verdict:** Yes

The function pointer `woken_wake_function` is stored into a waitqueue entry's `.func` field via the `DEFINE_WAIT_FUNC(wait, woken_wake_function)` macro in `inet_wait_for_connect()`.
This storage occurs when a task initiates a blocking stream connection (e.g., TCP connect) and must wait for the connection to be established. The waitqueue entry is then added to the socket's sleep queue (`sk_sleep(sk)`).
The stored callback is not executed synchronously by the connecting task. Instead, it is executed later when the socket receives a network event indicating a state change (such as receiving a SYN-ACK), which triggers a wakeup on the socket's waitqueue (e.g., via `sk->sk_state_change`).
This wakeup and the subsequent execution of `woken_wake_function` occur in the network receive path context (typically a software interrupt / softirq context), entirely independently of the sleeping task. Because the execution is triggered by an asynchronous network event in a different context, the synchronous call chain is broken and the execution context changes.
---

## Task 427: `wq_barrier_func` at `kernel/workqueue.c:3784`
**Verdict:** Yes

In `insert_wq_barrier` (which is called during `__flush_work`), a special barrier work item (`struct wq_barrier`) is initialized on the stack. During this initialization, the function pointer `wq_barrier_func` is stored as the callback function for the work item. 

This barrier work item is then inserted into the workqueue directly behind the target work item that is being flushed. The thread that initiated the flush subsequently goes to sleep waiting for the barrier to complete via `wait_for_completion()`.

When the workqueue worker thread finishes executing the target work item, it proceeds to execute the barrier work item. It invokes the stored `wq_barrier_func`, which signals completion and wakes up the flushing thread. Because `wq_barrier_func` is executed by the workqueue worker thread rather than the thread that stored it, it executes asynchronously in a different task context.
---

