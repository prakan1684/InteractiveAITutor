from enum import Enum


class CheckStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNCERTAIN = "UNCERTAIN"
    NEED_MORE_CONTEXT = "NEED_MORE_CONTEXT"
    BASELINE_RESET = "BASELINE_RESET"
    STALE_DUE_TO_EDIT = "STALE_DUE_TO_EDIT"


class ChangeType(str, Enum):
    APPEND = "APPEND"
    EDIT_IN_PLACE = "EDIT_IN_PLACE"
    REWRITE = "REWRITE"
    UNKNOWN = "UNKNOWN"


class Verdict(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNCERTAIN = "UNCERTAIN"


class HighlightType(str, Enum):
    UNDERLINE = "underline"
    HIGHLIGHT = "highlight"


class ToolCallStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    SKIPPED = "SKIPPED"


class TraceEventType(str, Enum):
    DECISION = "DECISION"
    TOOL_CALL = "TOOL_CALL"
    STORE_READ = "STORE_READ"
    STORE_WRITE = "STORE_WRITE"
    FINAL = "FINAL"
