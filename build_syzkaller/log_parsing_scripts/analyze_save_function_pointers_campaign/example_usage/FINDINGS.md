# Duplicates caused by triage having an outdated copy of unflaky coverage
## In general
Running the script [check_stable_coverage.py](./check_stable_coverage.py) produces an output of how many of the triage jobs are doing unnecessary work:
* Of the 3241 saved programs, only 1598 are distinct
* Of the 5177 triaged <prog, call> pairs, 1083 identical pairs were triaged at least twice 
* And more

This means that the current approach that relies on outdated coverage for decision on whether to triage or not creates a lot of unnecessary work.

## In relation to programs saved due to function pointers ("Interesting Progs")

### How many Interesting Progs are there really, and what do they look like?
The majority of the saved programs due to function pointers are very simple pointers, such as 
```json
"prog_in_corpus": [
    [
    "request_key(&(0x7f0000000300)='asymmetric\\x00', &(0x7f0000000340)={'syz', 0x0}, 0x0, 0x0)"
    ]
]
```
This seems disheartening, since saving a majority of such simple programs is not useful.
In spite of this, we can see that this actually happens because **a majority of saved programs due to function pointers are duplicate**.

As we can see by executing the script [check_stable_coverage.py](./check_stable_coverage.py), we find that out of the 1055 programs saved due to function pointers, only 108 actual unique programs exist.
Furthermore, 75 of those account for the more than 900 repetitions of duplicate programs.
This means that a few programs account for the majority of repetitions.

If we look at [the unique programs](./saved_because_fpointer.json) we get after deduplication, most saved programs are actually of a moderately decent length. For example:
```json
"prog_in_corpus": [
    [
    "mknodat(0xffffffffffffff9c, &(0x7f00000000c0)='./file2\\x00', 0x81c0, 0x0)",
    "mknodat(0xffffffffffffff9c, 0x0, 0x61c0, 0x700)",
    "prctl$PR_SET_NO_NEW_PRIVS(0x26, 0x1)",
    "execveat(0xffffffffffffff9c, &(0x7f0000000280)='./file2\\x00', 0x0, 0x0, 0x0)",
    "openat$dir(0xffffffffffffff9c, 0x0, 0x1, 0x0)"
    ]
]
```

In fact, it is only in the [version holding the duplicates](./saved_because_fpointer_w_duplicates.json) that the small programs take hold.
This means that there is plenty of potentially interesting programs to be into the corpus.
We'd just need to modify the triage process to prevent so many uninteresting testcases to be triaged at once

### Are the Interesting Progs actually interesting, or are they desinchronized from the Signal coverage due to the flakiness lag?
This should be analyzed next.
