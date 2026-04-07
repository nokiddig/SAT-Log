from __future__ import annotations

import subprocess
import time

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from PyQt6.QtCore import QThread

from app.core.adb_client import AdbError, build_adb_command, fetch_pid_package_map
from app.core.logcat_parser import LogcatParser
from app.models.log_entry import LogEntry


class LogcatWorker(QObject):
    batch_ready = pyqtSignal(list)
    status_changed = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    pid_map_updated = pyqtSignal(dict)

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
        self._pid_thread: QThread | None = None
        self._pid_worker: PIDRefreshWorker | None = None

    @pyqtSlot()
    def run(self) -> None:
        self._running = True
        self._stop_requested = False
        buffered_entries: list[LogEntry] = []
        last_flush = time.monotonic()

        try:
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

            self._start_pid_refresher()

            while self._running:
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
            self._stop_pid_refresher()
            self._running = False
            self.finished.emit()

    def _start_pid_refresher(self) -> None:
        self._pid_thread = QThread(self)
        self._pid_worker = PIDRefreshWorker(self._device_serial, self.PID_REFRESH_SECONDS)
        self._pid_worker.moveToThread(self._pid_thread)
        self._pid_thread.started.connect(self._pid_worker.run)
        self._pid_worker.pid_map_updated.connect(self._update_pid_map)
        self._pid_worker.error.connect(self.error.emit)
        self._pid_worker.finished.connect(self._pid_thread.quit)
        self._pid_worker.finished.connect(self._pid_worker.deleteLater)
        self._pid_thread.finished.connect(self._pid_thread.deleteLater)
        self._pid_thread.start()

    def _stop_pid_refresher(self) -> None:
        if self._pid_worker:
            self._pid_worker.stop()
        if self._pid_thread:
            self._pid_thread.wait(2000)
            self._pid_thread = None
            self._pid_worker = None

    def _update_pid_map(self, pid_map: dict[str, str]) -> None:
        self._pid_package_map = pid_map
        self.pid_map_updated.emit(pid_map)

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


class PIDRefreshWorker(QObject):
    pid_map_updated = pyqtSignal(dict)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, device_serial: str, interval_seconds: float) -> None:
        super().__init__()
        self._device_serial = device_serial
        self._interval_seconds = interval_seconds
        self._running = False
        self._stop_requested = False

    @pyqtSlot()
    def run(self) -> None:
        self._running = True
        self._stop_requested = False

        while self._running and not self._stop_requested:
            try:
                pid_map = fetch_pid_package_map(self._device_serial)
                self.pid_map_updated.emit(pid_map)
            except AdbError as exc:
                self.error.emit(str(exc))
            time.sleep(self._interval_seconds)

        self.finished.emit()

    def stop(self) -> None:
        self._stop_requested = True
        self._running = False
