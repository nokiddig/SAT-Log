from __future__ import annotations

from dataclasses import dataclass
import re

from app.models.log_entry import LEVEL_PRIORITY, LogEntry


@dataclass(frozen=True, slots=True)
class LogFilterSettings:
    minimum_level: str = "V"
    target_filter: str = ""
    query: str = ""
    regex_enabled: bool = False
    mode: str = "filter"


class LogFilter:
    def __init__(self, settings: LogFilterSettings) -> None:
        self.settings = settings
        self.minimum_level = settings.minimum_level or "V"
        self.minimum_level_priority = LEVEL_PRIORITY.get(self.minimum_level, 0)
        self.target_filter = settings.target_filter.strip()
        self.target_filter_lower = self.target_filter.lower()
        self.target_is_pid = self.target_filter.isdigit()
        self.query = settings.query.strip()
        self.query_lower = self.query.lower()
        self.mode = settings.mode if settings.mode in {"filter", "highlight"} else "filter"
        self.regex_enabled = bool(settings.regex_enabled and self.mode == "filter" and self.query)
        self.regex_error: str | None = None
        self._pattern: re.Pattern[str] | None = None

        if self.regex_enabled:
            try:
                self._pattern = re.compile(self.query, re.IGNORECASE)
            except re.error as exc:
                self.regex_error = str(exc)
                self.regex_enabled = False

    @property
    def visibility_signature(self) -> tuple[str, str, str, bool]:
        effective_query = ""
        effective_regex = False
        if self.mode == "filter" and self.query and self.regex_error is None:
            effective_query = self.query
            effective_regex = self.regex_enabled

        return (
            self.minimum_level,
            self.target_filter_lower,
            effective_query,
            effective_regex,
        )

    def matches(self, entry: LogEntry) -> bool:
        if LEVEL_PRIORITY.get(entry.level, 0) < self.minimum_level_priority:
            return False

        if self.target_filter_lower:
            if self.target_is_pid:
                if entry.pid != self.target_filter:
                    return False
            else:
                if self.target_filter_lower not in entry.package.lower():
                    return False

        if self.mode != "filter" or not self.query or self.regex_error:
            return True

        if self.regex_enabled and self._pattern is not None:
            combined_text = "\n".join(
                [
                    entry.package,
                    entry.level_name,
                    entry.raw_line,
                ]
            )
            return bool(self._pattern.search(combined_text))

        if self.query_lower in entry.package.lower():
            return True
        if self.query_lower in entry.level_name.lower():
            return True
        return self.query_lower in entry.raw_line.lower()
