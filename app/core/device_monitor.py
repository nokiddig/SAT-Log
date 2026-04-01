from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from app.core.adb_client import AdbError, list_devices


class DeviceMonitorWorker(QObject):
    devices_updated = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, interval_ms: int = 3000) -> None:
        super().__init__()
        self._interval_ms = interval_ms
        self._running = False
        self._last_snapshot: list[tuple[str, str, str]] | None = None

    @pyqtSlot()
    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                devices = list_devices()
                snapshot = [(device.serial, device.state, device.label) for device in devices]
                if snapshot != self._last_snapshot:
                    self._last_snapshot = snapshot
                    self.devices_updated.emit(devices)
            except AdbError as exc:
                error_snapshot = [("adb", "error", str(exc))]
                if error_snapshot != self._last_snapshot:
                    self._last_snapshot = error_snapshot
                    self.error.emit(str(exc))

            for _ in range(max(1, self._interval_ms // 100)):
                if not self._running:
                    break
                QThread.msleep(100)

        self.finished.emit()

    def stop(self) -> None:
        self._running = False
