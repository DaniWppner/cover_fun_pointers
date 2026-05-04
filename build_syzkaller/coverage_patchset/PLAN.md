# Option: Add set of function pointers as new type in parallel to cover and signal

## Upsides
Can save side to side to current information.
Can eventually consider it different information from current signal

## Downsides
Possibly it involves much more changes

## PLAN

### MVP
MVP is all new function pointer cover gets registered without minimizing, and saved into the cover AND corpus.

Version 1.0 is function pointer cover gets deflaked and minimization takes it into account.

Version 2.0 is corpus.ProgramsList gets refactored to include function pointer coverage information (which gets used in random corpus choice).

### first

[x] Add new coverage map to all places that keep track of it (corpus, fuzzer, items)

[ ] Mirror all (or a minimal subset of) Merge, MergeFromRaw, etc. methods from pkg/signal for the new cover

[ ] Update all constructors of the modified types to initialize (probably propagate) the new cover metric.

    * fuzzer.Cover:
        [x] addRawMaxSignal
           |x| fuzzer.triageProgCall
           |x| triageJob.deflake
        [ ] CopyMaxSignal  --> won't
        [ ] GrabSignalDelta --> won't

    * fuzzer.triageCall:
        [MVP] triageJob.deflake
        [MVP] triageJob.stopDeflake
        [   ] triageJob.minimize
        [MVP] triageJob.handleCall

    * corpus.Corpus:
        [ x ] corpus.Corpus.Save
        [ x ] corpus.Corpus.NewFocusedCorpus
        [   ] corpus.Corpus.Minimize

    * corpus.Item:
        [ x ] corpus.Corpus.Save
        [ x ] corpus.NewFocusedCorpus

    * corpus.NewInput:
        [MVP] triageJob.handleCall
        [ x ] corpus.Corpus.Save

[x] Write down all use cases of the modified type and list what they are

    (output: subitems of above)

[x] Modify processResults to figure out if current function pointer cover is new cover

[x] Modify fuzzer.job representation of testcases to handle new cover

[WIP] Modify triage to care about new cover

[??] Decide if the use cases of the modified types need to be changed

[ ] Look at all other fuzzer jobs and reason about if they should care about new cover

**[x] Make a pass through all references to signal to find other places that should be changed**

### afterwards

[ ] Figure out how corpus.prio works


# Option: Modify Signal type to include new infomation

## Upsides
Only involves changing the signal type itself and all the places where it is handled.

## Downsides
This might involve a lot of methods that are not of the signal type itself and know its inner workings

## PLAN

### first

[ ] Figure out feasability

[ ] Update Signal Type

[ ] Update Constructor methods

[ ] Check what other methods would need changing

