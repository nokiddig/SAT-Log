from __future__ import annotations

import subprocess
import time

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from app.core.adb_client import AdbError, build_adb_command, fetch_pid_package_map
from app.core.logcat_parser import LogcatParser
from app.models.log_entry import LogEntry


class LogcatWorker(QObject):
    batch_ready = pyqtSignal(list)
    status_changed = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    BATCH_SIZE = 150
    FLUSH_INTERVAL_SECONDS = 0.15
    PID_REFRESH_SECONDS = 5.0

    def __init__(self, device_serial: str) -> None:
        super().__init__()
        self._device_serial = device_serial
        self._running = False
        self._stop_requested = False
        self._process: subprocess.Popen[str] | None = None
        self._parser = LogcatParser()
        self._pid_package_map: dict[str, str] = {}

    @pyqtSlot()
    def run(self) -> None:
        self._running = True
        self._stop_requested = False
        buffered_entries: list[LogEntry] = []
        last_flush = time.monotonic()
        last_pid_refresh = 0.0

        try:
            self._refresh_pid_package_map()
            command = build_adb_command(["logcat", "-v", "threadtime", "*:V"], self._device_serial)
            self.status_changed.emit(f"Dang doc logcat tu thiet bi {self._device_serial} ...")
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            if self._process.stdout is None:
                raise AdbError("Khong the mo stdout cua tien trinh adb logcat.")

            while self._running:
                if time.monotonic() - last_pid_refresh >= self.PID_REFRESH_SECONDS:
                    self._refresh_pid_package_map(silent=True)
                    last_pid_refresh = time.monotonic()

                line = self._process.stdout.readline()
                if not line:
                    if self._process.poll() is not None:
                        break
                    time.sleep(0.03)
                    self._flush_if_needed(buffered_entries, force=True)
                    continue

                entry = self._parser.parse_line(line, self._pid_package_map)
                if entry is not None:
                    buffered_entries.append(entry)

                now = time.monotonic()
                if len(buffered_entries) >= self.BATCH_SIZE or now - last_flush >= self.FLUSH_INTERVAL_SECONDS:
                    self.batch_ready.emit(buffered_entries[:])
                    buffered_entries.clear()
                    last_flush = now

            self._flush_if_needed(buffered_entries, force=True)

            if not self._stop_requested and self._process and self._process.returncode not in (None, 0):
                raise AdbError(f"adb logcat da dung voi ma loi {self._process.returncode}.")
        except AdbError as exc:
            self.error.emit(str(exc))
        except FileNotFoundError:
            self.error.emit("Khong tim thay adb trong PATH. Hay cai Android Platform Tools.")
        except Exception as exc:  # pragma: no cover - defensive fallback for UI apps
            self.error.emit(f"Loi khong mong doi khi doc logcat: {exc}")
        finally:
            self._terminate_process()
            self._running = False
            self.finished.emit()

    def stop(self) -> None:
        self._stop_requested = True
        self._running = False
        self.status_changed.emit("Dang dung logcat ...")
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def _flush_if_needed(self, buffered_entries: list[LogEntry], force: bool = False) -> None:
        if buffered_entries and force:
            self.batch_ready.emit(buffered_entries[:])
            buffered_entries.clear()

    def _refresh_pid_package_map(self, silent: bool = False) -> None:
        try:
            self._pid_package_map = fetch_pid_package_map(self._device_serial)
            if not silent:
                self.status_changed.emit(
                    f"Da nap {len(self._pid_package_map)} tien trinh de map PID -> package."
                )
        except AdbError as exc:
            if not silent:
                self.status_changed.emit(str(exc))

    def _terminate_process(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1.0)
        self._process = None
