from __future__ import annotations

import re
from typing import Mapping

from app.models.log_entry import LogEntry


THREADTIME_PATTERNS = (
    re.compile(
        r"^(?P<time>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3,6})\s+"
        r"(?P<pid>\d+)\s+"
        r"(?P<tid>\S+)\s+"
        r"(?P<level>[VDIWEFA])\s+"
        r"(?P<tag>[^:]+?)\s*:\s(?P<message>.*)$"
    ),
    re.compile(
        r"^(?P<time>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3,6})\s+"
        r"(?P<pid>\d+)\s+"
        r"(?P<tid>\S+)\s+"
        r"(?P<level>[VDIWEFA])\s+"
        r"(?P<tag>\S+)\s+(?P<message>.*)$"
    ),
)


class LogcatParser:
    def __init__(self) -> None:
        self._last_entry: LogEntry | None = None
        self._known_packages: dict[str, str] = {}

    def parse_line(
        self,
        raw_line: str,
        pid_package_map: Mapping[str, str] | None = None,
    ) -> LogEntry | None:
        if not raw_line:
            return None

        if pid_package_map:
            self._known_packages.update(pid_package_map)

        stripped = raw_line.rstrip("\r\n")

        # logcat format is not perfectly identical across AOSP/Samsung/vendor builds,
        # so we try a strict threadtime parser first and then a looser fallback.
        for pattern in THREADTIME_PATTERNS:
            match = pattern.match(stripped)
            if not match:
                continue

            groups = match.groupdict()
            pid = groups["pid"]
            package = self._known_packages.get(pid, "")
            entry = LogEntry(
                time=groups["time"],
                pid=pid,
                tid=groups["tid"],
                package=package,
                level=groups["level"],
                tag=groups["tag"].strip(),
                message=groups["message"],
                raw_line=stripped,
            )
            self._last_entry = entry
            return entry

        if self._last_entry is None:
            return LogEntry(
                time="",
                pid="",
                tid="",
                package="",
                level="",
                tag="",
                message=stripped,
                raw_line=stripped,
                continuation=True,
            )

        continuation = LogEntry(
            time=self._last_entry.time,
            pid=self._last_entry.pid,
            tid=self._last_entry.tid,
            package=self._last_entry.package,
            level=self._last_entry.level,
            tag=self._last_entry.tag,
            message=stripped,
            raw_line=stripped,
            continuation=True,
        )
        self._last_entry = continuation
        return continuation
