from __future__ import annotations

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from app.models.log_filter import LogFilter
from app.models.log_entry import LogEntry


class FilterTaskSignals(QObject):
    finished = pyqtSignal(int, int, object, object, str)


class FilterTask(QRunnable):
    def __init__(
        self,
        request_id: int,
        store_version: int,
        snapshot: list[LogEntry],
        log_filter: LogFilter,
    ) -> None:
        super().__init__()
        self.request_id = request_id
        self.store_version = store_version
        self.snapshot = snapshot
        self.log_filter = log_filter
        self.signals = FilterTaskSignals()

    def run(self) -> None:
        try:
            filtered_entries = [entry for entry in self.snapshot if self.log_filter.matches(entry)]
            self.signals.finished.emit(
                self.request_id,
                self.store_version,
                filtered_entries,
                self.log_filter.visibility_signature,
                "",
            )
        except Exception as exc:  # pragma: no cover - defensive fallback for UI apps
            self.signals.finished.emit(
                self.request_id,
                self.store_version,
                [],
                self.log_filter.visibility_signature,
                str(exc),
            )
