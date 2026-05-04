# Option: Add set of function pointers as new type in parallel to cover and signal

## Upsides
Can save side to side to current information.
Can eventually consider it different information from current signal

## Downsides
Possibly it involves much more changes

## PLAN

### MVP
MVP is all new function pointer cover gets registered without deflaking, and saved into the cover AND corpus.

Version 1.0 is function pointer cover gets deflaked

### first

[x] Add new coverage map to all places that keep track of it (corpus, fuzzer, items)

[ ] Mirror all (or a minimal subset of) Merge, MergeFromRaw, etc. methods from pkg/signal for the new cover

[ ] Update all constructors of the modified types to initialize (probably propagate) the new cover metric.

    * fuzzer.Cover:
        [x] addRawMaxSignal
           |x| fuzzer.triageProgCall
           | | triageJob.deflake
        [ ] CopyMaxSignal  --> won't
        [ ] GrabSignalDelta --> won't

    * fuzzer.triageCall:
        [   ] triageJob.deflake
        [   ] triageJob.stopDeflake
        [   ] triageJob.minimize
        [MVP] triageJob.handleCall

    * corpus.Corpus:
        [ ] corpus.Corpus.Save
        [ ] corpus.Corpus.NewFocusedCorpus
        [ ] corpus.Corpus.Minimize

    * corpus.Item:
        [ ] corpus.Corpus.Save
        [ ] corpus.NewFocusedCorpus

    * corpus.NewInput:
        [MVP] triageJob.handleCall
        [   ] corpus.Corpus.Save

    * corpus.NewItemEvent:
        [ ] corpus.NewMonitoredCorpus
        [ ] corpus.NewFocusedCorpus
        [ ] corpus.Corpus.Save
        [ ] syz-manager.Manager.corpusInputHandler
        [ ] syz-manager.Manager.MachineChecked

[x] Write down all use cases of the modified type and list what they are

    (output: subitems of above)

[x] Modify processResults to figure out if current function pointer cover is new cover

[x] Modify fuzzer.job representation of testcases to handle new cover

[ ] Modify triage to care about new cover

[ ] Decide if the use cases of the modified types need to be changed

[ ] Look at all other fuzzer jobs and reason about if they should care about new cover

**[ ] Make a pass through all references to signal to make find other places that should be changed**

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

