from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout

from app.models.log_entry import LogEntry


class LogDetailDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Log Detail")
        self.resize(960, 560)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        metadata_layout = QFormLayout()
        metadata_layout.setContentsMargins(0, 0, 0, 0)
        metadata_layout.setHorizontalSpacing(16)
        metadata_layout.setVerticalSpacing(8)

        self.time_label = QLabel("-")
        self.pid_label = QLabel("-")
        self.tid_label = QLabel("-")
        self.package_label = QLabel("-")
        self.level_label = QLabel("-")
        self.tag_label = QLabel("-")

        metadata_layout.addRow("Time", self.time_label)
        metadata_layout.addRow("PID", self.pid_label)
        metadata_layout.addRow("TID", self.tid_label)
        metadata_layout.addRow("Package", self.package_label)
        metadata_layout.addRow("Level", self.level_label)
        metadata_layout.addRow("Tag", self.tag_label)

        self.message_view = QPlainTextEdit()
        self.message_view.setReadOnly(True)
        self.message_view.setPlaceholderText("No message")

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)

        root_layout.addLayout(metadata_layout)
        root_layout.addWidget(self.message_view, 1)
        root_layout.addLayout(close_row)

    def set_entry(self, entry: LogEntry) -> None:
        self.time_label.setText(entry.time or "-")
        self.pid_label.setText(entry.pid or "-")
        self.tid_label.setText(entry.tid or "-")
        self.package_label.setText(entry.package or "-")
        self.level_label.setText(entry.level_name)
        self.tag_label.setText(entry.tag or "-")
        self.message_view.setPlainText(entry.message)
