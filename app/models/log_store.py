from __future__ import annotations

from app.models.log_entry import LogEntry


class LogStore:
    def __init__(self, max_entries: int = 100_000) -> None:
        self._max_entries = max(1_000, int(max_entries))
        self._entries: list[LogEntry] = []
        self._version = 0

    @property
    def max_entries(self) -> int:
        return self._max_entries

    @property
    def version(self) -> int:
        return self._version

    def __len__(self) -> int:
        return len(self._entries)

    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def snapshot(self) -> tuple[list[LogEntry], int]:
        return list(self._entries), self._version

    def clear(self) -> None:
        if not self._entries:
            return
        self._entries.clear()
        self._version += 1

    def set_max_entries(self, max_entries: int) -> list[LogEntry]:
        self._max_entries = max(1_000, int(max_entries))
        return self._trim_if_needed()

    def append_entries(self, entries: list[LogEntry]) -> list[LogEntry]:
        if not entries:
            return []

        self._entries.extend(entries)
        self._version += 1
        return self._trim_if_needed()

    def _trim_if_needed(self) -> list[LogEntry]:
        overflow = len(self._entries) - self._max_entries
        if overflow <= 0:
            return []

        dropped_entries = self._entries[:overflow]
        del self._entries[:overflow]
        self._version += 1
        return dropped_entries
