from __future__ import annotations

from dataclasses import dataclass


LEVEL_LABELS = {
    "V": "Verbose",
    "D": "Debug",
    "I": "Info",
    "W": "Warn",
    "E": "Error",
    "F": "Fatal",
    "A": "Assert",
}

LEVEL_PRIORITY = {
    "": 0,
    "V": 0,
    "D": 1,
    "I": 2,
    "W": 3,
    "E": 4,
    "F": 5,
    "A": 5,
}


@dataclass(slots=True)
class LogEntry:
    time: str
    pid: str
    tid: str
    package: str
    level: str
    tag: str
    message: str
    raw_line: str
    continuation: bool = False

    @property
    def level_name(self) -> str:
        return LEVEL_LABELS.get(self.level, self.level or "-")
