from enum import StrEnum

class LOGENTRY_KEYS(StrEnum):
    NEW_FPOINTERS = "new_fpointers"
    NEW_SIGNAL = "new_signal"
    NEW_FPOINTERS_PAYLOAD = "new_fpointers_json"
    STABLE_FPOINTERS = "stable_fpointers"
    STABLE_SIGNAL = "stable_signal"
    STABLE_FPOINTERS_PAYLOAD = "new_stable_fpointers_json"
    SAVED_ITEM = "saved_item"
    MINIMIZATION_REPORT_NO_DIFF = "minimization_result_equal"
    MINIMIZATION_REPORT_SAVE_FPOINTERS = "minimization_result_no_signal"
    MINIMIZATION_REPORT_SAVE_SIGNAL = "minimization_result_no_fpointer"
    MINIMIZATION_WHOLE_SKIP = "minimization_skip"
    MINIMIZATION_FPOINTER_SKIP = "minimization_skip_fpointer"
    MINIMIZATION_SIGNAL_SKIP = "minimization_skip_signal"
    


class RESULT_KEYS(StrEnum):
    NEW_FPOINTERS = "new_fpointers"
    NEW_SIGNAL = "new_signal"
    NEW_FPOINTERS_PAYLOAD = "new_fpointers_json"
    STABLE_FPOINTERS = "stable_fpointers"
    NEW_STABLE_FPOINTERS = "new_stable_fpointers"
    STABLE_FPOINTERS_PAYLOAD = "new_stable_fpointers_json"
    STABLE_SIGNAL = "stable_signal"
    NEW_STABLE_SIGNAL = "new_stable_signal"
    CALL_NAME = "call"
    SAVED_PROG = "prog_in_corpus"
    MINIMIZATION_RESULT = "minimization_result"
    MINIMIZATION_RES_PROG = "result_prog"
    MINIMIZATION_RES_TYPE = "type"
    PROGID = "prog_id"
    TRIAGEID = "triage_id"
    ORIGINAL_PROG = "original_prog"
    COUNT = "count"


class RESULT_VALUES(StrEnum):
    MINIMIZATION_RES_NODIFF = "signal_fpointer_equal"
    MINIMIZATION_RES_SAVE_SIGNAL = "save_signal_no_fpointer"
    MINIMIZATION_RES_SAVE_FPOINTER = "save_fpointer_no_signal"
    MINIMIZATION_RES_FPOINTER_SKIP = "skip_fpointer"
    MINIMIZATION_RES_SIGNAL_SKIP = "skip_signal"
    MINIMIZATION_SKIP = "minimization_skip"
