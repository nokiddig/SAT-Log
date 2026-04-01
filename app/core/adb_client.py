from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess
from typing import Iterable


ADB_EXECUTABLE = "adb"


class AdbError(RuntimeError):
    """Raised when an adb command fails or adb is not available."""


@dataclass(slots=True)
class DeviceInfo:
    serial: str
    state: str
    label: str

    @property
    def is_ready(self) -> bool:
        return self.state == "device"


def build_adb_command(args: Iterable[str], device_serial: str | None = None) -> list[str]:
    command = [ADB_EXECUTABLE]
    if device_serial:
        command.extend(["-s", device_serial])
    command.extend(args)
    return command


def _windows_creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_adb_command(
    args: Iterable[str],
    device_serial: str | None = None,
    timeout: float = 5.0,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = build_adb_command(args, device_serial=device_serial)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_windows_creation_flags(),
            check=False,
        )
    except FileNotFoundError as exc:
        raise AdbError("Khong tim thay adb trong PATH. Hay cai Android Platform Tools.") from exc
    except subprocess.TimeoutExpired as exc:
        raise AdbError(f"Lenh adb bi timeout sau {timeout:.1f}s: {' '.join(command)}") from exc

    if check and completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "adb command failed"
        raise AdbError(stderr)

    return completed


def list_devices() -> list[DeviceInfo]:
    completed = run_adb_command(["devices", "-l"], timeout=5.0)
    devices: list[DeviceInfo] = []

    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("List of devices attached") or stripped.startswith("*"):
            continue

        parts = re.split(r"\s+", stripped)
        if len(parts) < 2:
            continue

        serial = parts[0]
        state = parts[1]
        label = serial
        for token in parts[2:]:
            if token.startswith("model:"):
                label = token.split(":", 1)[1].replace("_", " ")
                break

        devices.append(DeviceInfo(serial=serial, state=state, label=label))

    return devices


def fetch_pid_package_map(device_serial: str) -> dict[str, str]:
    completed = run_adb_command(["shell", "ps", "-A"], device_serial=device_serial, timeout=6.0)
    mapping: dict[str, str] = {}

    for raw_line in completed.stdout.splitlines():
        stripped = raw_line.strip()
        if not stripped or (" PID " in f" {stripped} " and " NAME" in stripped):
            continue

        parts = re.split(r"\s+", stripped)
        if len(parts) < 2:
            continue

        pid_index = next((index for index, token in enumerate(parts) if token.isdigit()), None)
        if pid_index is None or pid_index >= len(parts) - 1:
            continue

        pid = parts[pid_index]
        process_name = parts[-1]
        if pid and process_name:
            mapping[pid] = process_name

    return mapping
