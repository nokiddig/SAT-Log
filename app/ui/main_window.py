from __future__ import annotations

from pathlib import Path
import re

from PyQt6.QtCore import QSettings, QThread, QThreadPool, QTimer, Qt
from PyQt6.QtGui import QCloseEvent, QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.core.adb_client import DeviceInfo
from app.core.device_monitor import DeviceMonitorWorker
from app.core.filter_task import FilterTask
from app.core.logcat_worker import LogcatWorker
from app.dialogs.log_detail_dialog import LogDetailDialog
from app.models.log_filter import LogFilter, LogFilterSettings
from app.models.log_store import LogStore
from app.models.log_table_model import LogTableModel
from app.ui.highlight_delegate import HighlightDelegate


class MainWindow(QMainWindow):
    STORAGE_WINDOWS = [
        (5_000, "5k"),
        (10_000, "10k"),
        (25_000, "25k"),
        (50_000, "50k"),
        (100_000, "100k"),
        (200_000, "200k"),
    ]
    FILTER_DEBOUNCE_MS = 220

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SAT Logcat Viewer")
        self.resize(1600, 900)

        self.settings = QSettings("SAT", "SATLogcatViewer")
        self.log_store = LogStore(max_entries=self._load_storage_window())
        self.model = LogTableModel()

        self.highlight_delegate = HighlightDelegate()
        self.log_detail_dialog = LogDetailDialog(self)

        self.log_thread: QThread | None = None
        self.log_worker: LogcatWorker | None = None
        self.device_thread: QThread | None = None
        self.device_worker: DeviceMonitorWorker | None = None

        self.filter_pool = QThreadPool(self)
        self.filter_pool.setMaxThreadCount(1)
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._start_filter_rebuild)

        self._filter_request_id = 0
        self._active_filter_request_id = 0
        self._filter_job_running = False
        self._pending_rebuild_after_current = False
        self._deferred_deltas: list[tuple[list, list]] = []

        self._user_scrolled_up = False
        self._device_error_text = ""
        self._requested_filter = LogFilter(LogFilterSettings())
        self._display_filter = self._requested_filter

        self._build_ui()
        self._bind_signals()
        self._restore_last_session()
        self._start_device_monitor()
        self._update_stats_label()

    def _build_ui(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)
        self.setCentralWidget(central)

        control_panel = QFrame()
        control_panel.setObjectName("ControlPanel")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(14, 14, 14, 14)
        control_layout.setSpacing(10)

        row_one = QHBoxLayout()
        row_one.setSpacing(10)
        row_two = QHBoxLayout()
        row_two.setSpacing(10)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(250)
        self.device_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.device_combo.addItem("Scanning adb devices...", None)

        self.level_combo = QComboBox()
        for code, label in [
            ("V", "Verbose+"),
            ("D", "Debug+"),
            ("I", "Info+"),
            ("W", "Warn+"),
            ("E", "Error+"),
            ("F", "Fatal"),
        ]:
            self.level_combo.addItem(label, code)

        self.storage_combo = QComboBox()
        for value, label in self.STORAGE_WINDOWS:
            self.storage_combo.addItem(label, value)
        storage_index = self.storage_combo.findData(self.log_store.max_entries)
        if storage_index >= 0:
            self.storage_combo.setCurrentIndex(storage_index)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("PID hoac package name")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search text or regex in all columns")

        self.regex_checkbox = QCheckBox("Regex")

        self.search_mode_combo = QComboBox()
        self.search_mode_combo.addItem("Filter", "filter")
        self.search_mode_combo.addItem("Highlight", "highlight")

        self.auto_scroll_checkbox = QCheckBox("Auto-scroll to bottom")
        self.auto_scroll_checkbox.setChecked(True)

        self.stats_label = QLabel()
        self.stats_label.setProperty("hint", True)

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("PrimaryButton")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("DangerButton")
        self.stop_button.setEnabled(False)
        self.clear_button = QPushButton("Clear Log")
        self.export_button = QPushButton("Export .txt")

        row_one.addWidget(self._wrap_field("Device Selector", self.device_combo), 2)
        row_one.addWidget(self._wrap_field("Log Level Filter", self.level_combo), 1)
        row_one.addWidget(self._wrap_field("Storage Window", self.storage_combo), 1)
        row_one.addWidget(self._wrap_field("Target Filter", self.target_input), 2)
        row_one.addWidget(self.auto_scroll_checkbox)
        row_one.addStretch(1)
        row_one.addWidget(self.start_button)
        row_one.addWidget(self.stop_button)
        row_one.addWidget(self.clear_button)
        row_one.addWidget(self.export_button)

        row_two.addWidget(self._wrap_field("Search Bar", self.search_input), 3)
        row_two.addWidget(self.regex_checkbox)
        row_two.addWidget(self._wrap_field("Search Mode", self.search_mode_combo), 1)
        row_two.addStretch(1)
        row_two.addWidget(self.stats_label)

        control_layout.addLayout(row_one)
        control_layout.addLayout(row_two)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setItemDelegate(self.highlight_delegate)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_view.setSortingEnabled(False)
        self.table_view.setWordWrap(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setShowGrid(False)
        self.table_view.setCornerButtonEnabled(False)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.setColumnWidth(0, 155)
        self.table_view.setColumnWidth(1, 85)
        self.table_view.setColumnWidth(2, 85)
        self.table_view.setColumnWidth(3, 220)
        self.table_view.setColumnWidth(4, 95)
        self.table_view.setColumnWidth(5, 220)
        self.table_view.setFont(self._monospace_font())

        control_hint = QLabel(
            "Search va package filter duoc debounce + async rebuild de khong block UI khi log rat lon."
        )
        control_hint.setProperty("hint", True)

        root_layout.addWidget(control_panel)
        root_layout.addWidget(control_hint)
        root_layout.addWidget(self.table_view, 1)

        self.statusBar().showMessage("San sang. Dang cho thiet bi Android ket noi qua adb.")

    def _bind_signals(self) -> None:
        self.level_combo.currentIndexChanged.connect(self._schedule_filter_refresh)
        self.target_input.textChanged.connect(self._schedule_filter_refresh)
        self.search_input.textChanged.connect(self._schedule_filter_refresh)
        self.regex_checkbox.toggled.connect(self._schedule_filter_refresh)
        self.search_mode_combo.currentIndexChanged.connect(self._schedule_filter_refresh)
        self.storage_combo.currentIndexChanged.connect(self._change_storage_window)
        self.start_button.clicked.connect(self.start_log_stream)
        self.stop_button.clicked.connect(self.stop_log_stream)
        self.clear_button.clicked.connect(self.clear_logs)
        self.export_button.clicked.connect(self.export_logs)
        self.table_view.doubleClicked.connect(self.show_log_detail)
        self.table_view.verticalScrollBar().valueChanged.connect(self._update_autoscroll_state)

    def _wrap_field(self, title: str, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setProperty("hint", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return container

    def _monospace_font(self) -> QFont:
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(10)
        return font

    def _load_storage_window(self) -> int:
        stored = int(self.settings.value("storage_window", 100_000))
        allowed_values = [value for value, _label in self.STORAGE_WINDOWS]
        return stored if stored in allowed_values else 100_000

    def _start_device_monitor(self) -> None:
        self.device_thread = QThread(self)
        self.device_worker = DeviceMonitorWorker(interval_ms=3000)
        self.device_worker.moveToThread(self.device_thread)
        self.device_thread.started.connect(self.device_worker.run)
        self.device_worker.devices_updated.connect(self._update_device_combo)
        self.device_worker.error.connect(self._handle_device_error)
        self.device_worker.finished.connect(self.device_thread.quit)
        self.device_worker.finished.connect(self.device_worker.deleteLater)
        self.device_thread.finished.connect(self._on_device_thread_finished)
        self.device_thread.finished.connect(self.device_thread.deleteLater)
        self.device_thread.start()

    def _restore_last_session(self) -> None:
        self.level_combo.setCurrentIndex(int(self.settings.value("level_index", 0)))
        self.target_input.setText(str(self.settings.value("target_filter", "")))
        self.search_input.setText(str(self.settings.value("search_text", "")))
        self.regex_checkbox.setChecked(self._as_bool(self.settings.value("search_regex", False)))
        mode = str(self.settings.value("search_mode", "filter"))
        mode_index = self.search_mode_combo.findData(mode)
        if mode_index >= 0:
            self.search_mode_combo.setCurrentIndex(mode_index)
        self.auto_scroll_checkbox.setChecked(self._as_bool(self.settings.value("auto_scroll", True)))
        self._schedule_filter_refresh(immediate=True)

    def _save_session_settings(self) -> None:
        self.settings.setValue("level_index", self.level_combo.currentIndex())
        self.settings.setValue("target_filter", self.target_input.text())
        self.settings.setValue("search_text", self.search_input.text())
        self.settings.setValue("search_regex", self.regex_checkbox.isChecked())
        self.settings.setValue("search_mode", self.search_mode_combo.currentData())
        self.settings.setValue("auto_scroll", self.auto_scroll_checkbox.isChecked())
        self.settings.setValue("storage_window", self.log_store.max_entries)

    def _capture_filter(self) -> LogFilter:
        return LogFilter(
            LogFilterSettings(
                minimum_level=str(self.level_combo.currentData()),
                target_filter=self.target_input.text(),
                query=self.search_input.text(),
                regex_enabled=self.regex_checkbox.isChecked(),
                mode=str(self.search_mode_combo.currentData()),
            )
        )

    def _schedule_filter_refresh(self, *_args, immediate: bool = False) -> None:
        requested_filter = self._capture_filter()
        self._requested_filter = requested_filter
        self.highlight_delegate.set_search(
            self.search_input.text(),
            self.regex_checkbox.isChecked(),
            str(self.search_mode_combo.currentData()),
        )
        self.table_view.viewport().update()

        regex_error = self._search_regex_error()
        self._apply_search_validation(regex_error)

        if (
            requested_filter.visibility_signature == self._display_filter.visibility_signature
            and not self._filter_job_running
        ):
            self._display_filter = requested_filter
            self._update_stats_label()
            return

        if immediate:
            self.filter_timer.stop()
            self._start_filter_rebuild()
        else:
            self.filter_timer.start(self.FILTER_DEBOUNCE_MS)

    def _search_regex_error(self) -> str | None:
        if not self.regex_checkbox.isChecked():
            return None

        query = self.search_input.text().strip()
        if not query:
            return None

        try:
            re.compile(query, re.IGNORECASE)
        except re.error as exc:
            return str(exc)
        return None

    def _apply_search_validation(self, regex_error: str | None) -> None:
        self.search_input.setProperty("error", bool(regex_error))
        self.search_input.style().unpolish(self.search_input)
        self.search_input.style().polish(self.search_input)
        self.search_input.update()

        if regex_error:
            self.search_input.setToolTip(regex_error)
            self.statusBar().showMessage(f"Regex khong hop le: {regex_error}")
        else:
            self.search_input.setToolTip("")

    def _start_filter_rebuild(self) -> None:
        if self._filter_job_running:
            self._pending_rebuild_after_current = True
            return

        snapshot, store_version = self.log_store.snapshot()
        if not snapshot:
            self._display_filter = self._requested_filter
            self._update_stats_label()
            return

        self._filter_request_id += 1
        self._active_filter_request_id = self._filter_request_id
        self._filter_job_running = True
        self._pending_rebuild_after_current = False
        self._deferred_deltas.clear()

        task = FilterTask(
            request_id=self._active_filter_request_id,
            store_version=store_version,
            snapshot=snapshot,
            log_filter=self._requested_filter,
        )
        task.signals.finished.connect(self._on_filter_rebuild_finished)
        self.statusBar().showMessage(f"Dang loc lai {len(snapshot):,} dong log ...")
        self.filter_pool.start(task)

    def _on_filter_rebuild_finished(
        self,
        request_id: int,
        _store_version: int,
        filtered_entries: list,
        visibility_signature: tuple,
        error_text: str,
    ) -> None:
        if request_id != self._active_filter_request_id:
            return

        self._filter_job_running = False

        if error_text:
            self.statusBar().showMessage(f"Loi khi loc log: {error_text}")
            QMessageBox.warning(self, "Filter Error", error_text)
            return

        if self._pending_rebuild_after_current or visibility_signature != self._requested_filter.visibility_signature:
            self._pending_rebuild_after_current = False
            self._start_filter_rebuild()
            return

        self.model.set_entries(filtered_entries)
        self._display_filter = self._requested_filter

        if self._deferred_deltas:
            for dropped_entries, new_entries in self._deferred_deltas:
                self._apply_incremental_delta(dropped_entries, new_entries, self._display_filter)
            self._deferred_deltas.clear()

        self._update_stats_label()
        if self.auto_scroll_checkbox.isChecked() and not self._user_scrolled_up and self.model.rowCount() > 0:
            self.table_view.scrollToBottom()
        self.statusBar().showMessage(
            f"Da loc xong. Visible {self.model.rowCount():,} / Stored {len(self.log_store):,} dong."
        )

    def _change_storage_window(self, *_args) -> None:
        max_entries = int(self.storage_combo.currentData())
        dropped_entries = self.log_store.set_max_entries(max_entries)
        self.settings.setValue("storage_window", self.log_store.max_entries)

        if self._filter_job_running:
            self._deferred_deltas.append((dropped_entries, []))
        else:
            self._apply_incremental_delta(dropped_entries, [], self._display_filter)

        self._update_stats_label()
        self.statusBar().showMessage(f"Storage window da doi sang {max_entries:,} dong.")

    def _update_device_combo(self, devices: list[DeviceInfo]) -> None:
        self._device_error_text = ""
        selected_serial = ""
        selected_device = self.device_combo.currentData()
        if isinstance(selected_device, DeviceInfo):
            selected_serial = selected_device.serial

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        ready_devices = 0
        for device in devices:
            suffix = "" if device.is_ready else f" [{device.state}]"
            self.device_combo.addItem(f"{device.label} ({device.serial}){suffix}", device)
            if device.is_ready:
                ready_devices += 1

        if not devices:
            self.device_combo.addItem("No devices detected", None)

        if selected_serial:
            for row in range(self.device_combo.count()):
                device = self.device_combo.itemData(row)
                if isinstance(device, DeviceInfo) and device.serial == selected_serial:
                    self.device_combo.setCurrentIndex(row)
                    break
        self.device_combo.blockSignals(False)

        if ready_devices:
            self.statusBar().showMessage(f"Da tim thay {ready_devices} thiet bi san sang.")
        else:
            self.statusBar().showMessage("Khong co thiet bi nao o trang thai device.")

    def _handle_device_error(self, message: str) -> None:
        self._device_error_text = message
        self.statusBar().showMessage(message)
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem("ADB unavailable", None)
        self.device_combo.blockSignals(False)

    def start_log_stream(self) -> None:
        if self.log_thread is not None:
            return

        device = self.device_combo.currentData()
        if not isinstance(device, DeviceInfo) or not device.is_ready:
            QMessageBox.warning(self, "No Device", "Hay chon mot thiet bi dang o trang thai device.")
            return

        self.log_thread = QThread(self)
        self.log_worker = LogcatWorker(device.serial)
        self.log_worker.moveToThread(self.log_thread)

        # Viec doc stdout cua adb logcat van o worker thread, UI thread chi xu ly
        # batch log ngan gon va render delta can thiet de giu giao dien muot khi log rat lon.
        self.log_thread.started.connect(self.log_worker.run)
        self.log_worker.batch_ready.connect(self._append_log_batch)
        self.log_worker.status_changed.connect(self.statusBar().showMessage)
        self.log_worker.error.connect(self._handle_log_error)
        self.log_worker.finished.connect(self.log_thread.quit)
        self.log_worker.finished.connect(self.log_worker.deleteLater)
        self.log_thread.finished.connect(self._on_log_thread_finished)
        self.log_thread.finished.connect(self.log_thread.deleteLater)

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.device_combo.setEnabled(False)
        self.statusBar().showMessage(f"Bat dau logcat tren thiet bi {device.serial} ...")
        self.log_thread.start()

    def stop_log_stream(self) -> None:
        if self.log_worker is None:
            return
        self.log_worker.stop()

    def _append_log_batch(self, entries: list) -> None:
        should_follow = self.auto_scroll_checkbox.isChecked() and not self._user_scrolled_up
        dropped_entries = self.log_store.append_entries(entries)

        if self._filter_job_running:
            self._deferred_deltas.append((dropped_entries, entries))
            self._update_stats_label()
            return

        self._apply_incremental_delta(dropped_entries, entries, self._display_filter)
        self._update_stats_label()
        if should_follow and self.model.rowCount() > 0:
            self.table_view.scrollToBottom()

    def _apply_incremental_delta(self, dropped_entries: list, new_entries: list, log_filter: LogFilter) -> None:
        if dropped_entries:
            removed_visible = sum(1 for entry in dropped_entries if log_filter.matches(entry))
            if removed_visible:
                self.model.trim_start(removed_visible)

        if new_entries:
            visible_entries = [entry for entry in new_entries if log_filter.matches(entry)]
            if visible_entries:
                self.model.append_entries(visible_entries)

    def _on_log_thread_finished(self) -> None:
        self.log_thread = None
        self.log_worker = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.statusBar().showMessage("Logcat da dung.")

    def _on_device_thread_finished(self) -> None:
        self.device_thread = None
        self.device_worker = None

    def _handle_log_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "ADB Logcat", message)

    def _update_autoscroll_state(self, value: int) -> None:
        scrollbar = self.table_view.verticalScrollBar()
        self._user_scrolled_up = value < max(0, scrollbar.maximum() - 2)

    def _update_stats_label(self) -> None:
        self.stats_label.setText(
            f"Visible {self.model.rowCount():,} / Stored {len(self.log_store):,} / Window {self.log_store.max_entries:,}"
        )

    def clear_logs(self) -> None:
        self.filter_timer.stop()
        if self._filter_job_running:
            self._filter_request_id += 1
            self._active_filter_request_id = self._filter_request_id
            self._filter_job_running = False
            self._pending_rebuild_after_current = False
        self._deferred_deltas.clear()
        self.log_store.clear()
        self.model.clear()
        self._update_stats_label()
        self.statusBar().showMessage("Da clear log hien thi.")

    def show_log_detail(self, index) -> None:
        entry = self.model.data(index, Qt.ItemDataRole.UserRole)
        if entry is None:
            return
        self.log_detail_dialog.set_entry(entry)
        self.log_detail_dialog.show()
        self.log_detail_dialog.raise_()
        self.log_detail_dialog.activateWindow()

    def export_logs(self) -> None:
        default_name = Path.cwd() / "sat-log-export.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            str(default_name),
            "Text Files (*.txt);;All Files (*.*)",
        )
        if not file_path:
            return

        lines = ["Time\tPID\tTID\tPackage\tLevel\tTag\tMessage"]
        for entry in self.model.entries():
            lines.append(
                "\t".join(
                    [
                        entry.time,
                        entry.pid,
                        entry.tid,
                        entry.package,
                        entry.level_name,
                        entry.tag,
                        entry.message.replace("\t", "    "),
                    ]
                )
            )

        try:
            Path(file_path).write_text("\n".join(lines), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Export Log", f"Khong the ghi file: {exc}")
            return

        self.statusBar().showMessage(f"Da export {len(lines) - 1} dong log ra {file_path}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_session_settings()
        self.filter_timer.stop()
        self.filter_pool.waitForDone(2000)

        if self.log_worker is not None:
            self.log_worker.stop()
        if self.device_worker is not None:
            self.device_worker.stop()

        if self.log_thread is not None:
            self.log_thread.wait(2500)
        if self.device_thread is not None:
            self.device_thread.wait(6500)

        super().closeEvent(event)

    @staticmethod
    def _as_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
