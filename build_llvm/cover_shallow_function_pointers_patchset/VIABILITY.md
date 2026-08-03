# Cases when injecting a dereference of the value written to a struct pointer variable would introduce a kernel bug.

## 1. When the struct is being assigned the literal `NULL` value, or another `CONSTANT` defined literal such as `LIST_POISON1`.
This makes it so dereferencing the variable is prohibited.

Nevertheless, NULL or ERROR POINTERS only appear at static literal assignements,
or as the result value of a helper function.

The first case can be identified via static analyis. (How?)

The second case needs to be solved the same way as `3. The stored variable needs to be checked against IS_ERR_PTR.`

## 2. When the variable is being assigned the result of `rcu_access_pointer`.
This happens about 70 times in the linux kernel.
Most of them are in contexts where the variable is not being accessed;
or the variable is safe under rcu_locks otherwise.

Can this condition be statically checked?
Alternatively, identifying llvm Users of `rcu_access_pointer` could prevent dereferencing returns of this API.
Although this would easily break when forwarding the value accross function calls.

## 3. When the variable should be checked against IS_ERR_PTR.
This happens extremely often in snippets like these:
```c
// snippet source net/wireless/nl80211.c:982
static int nl80211_prepare_wdev_dump(struct netlink_callback *cb,
				     struct cfg80211_registered_device **rdev,
				     struct wireless_dev **wdev,
				     struct nlattr **attrbuf)
{   // ...
	if (!cb->args[0]) {
        // ...
		rtnl_lock();
		*wdev = __cfg80211_wdev_from_attrs(NULL, sock_net(cb->skb->sk),  //<<--- Unsafe to dereference `*wdev` at point of Store
						   attrbuf);
		kfree(attrbuf_free);
		if (IS_ERR(*wdev)) {
			rtnl_unlock();
			return PTR_ERR(*wdev);
		}
		*rdev = wiphy_to_rdev((*wdev)->wiphy);          //<<--- Safe to dereference `*wdev` once IS_ERR returned false
    // ...
    }
}
```
Is it possible to statically check this?
It sounds feasible to inject code that dynamically guards against this.

## 4. When the variable is being assigned a pointer that lives in userspace.
It becomes imperative to identify statically the __user tag to ignore these structs.
Alternatively; structs of `sigaction` type can be blacklisted individually.

This happens often during userspace/kernel space boundaries in syscall initialization.
It almost never happens that the user space struct contains function pointers.
Nevertheless, this does happen for the signal handling kernel API.

The rt_sigaction signal receives a `sigaction __user` pointer 
```c
// snippet source kernel/signal.c:4484
SYSCALL_DEFINE4(rt_sigaction, int, sig,
		const struct sigaction __user *, act,
		struct sigaction __user *, oact,
		size_t, sigsetsize)
```
Which holds a pointer to the `sa_handler` userspace function that the user process wants to associate
with the signal specified in the syscall:
```c
// snippet source include/linux/signal_types.h:72
struct sigaction {
#ifndef __ARCH_HAS_IRIX_SIGACTION
	__sighandler_t	sa_handler;    //  <<---- culprit
	unsigned long	sa_flags;
#else
	unsigned int	sa_flags;
	__sighandler_t	sa_handler;
#endif
#ifdef __ARCH_HAS_SA_RESTORER
	__sigrestore_t sa_restorer;
#endif
	sigset_t	sa_mask;	/* mask last for extensibility */
};
```
This variable of `__sighandler_t` is defined by the architecture to be a void returning function.
```c
// snippet source include/uapi/asm-generic/signal-defs.h:82
typedef void __signalfn_t(int);
typedef __signalfn_t __user *__sighandler_t;
```
The kernel processes are (naturally) never expected to call this userspace function;
instead they manipulate the stack state of the userspace process to inject a "call" to it during signal handling.

## 5. When the variable is a parameter to the current executing function.
The assignment of this stack variable is not necessarily interesting.
