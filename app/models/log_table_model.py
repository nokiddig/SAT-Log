from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor, QBrush

from app.models.log_entry import LogEntry


LEVEL_FOREGROUNDS = {
    "V": QColor("#cbd5e1"),
    "D": QColor("#7dd3fc"),
    "I": QColor("#86efac"),
    "W": QColor("#fde68a"),
    "E": QColor("#fca5a5"),
    "F": QColor("#fda4af"),
    "A": QColor("#fda4af"),
}

LEVEL_BACKGROUNDS = {
    "D": QColor(31, 64, 112, 45),
    "I": QColor(22, 101, 52, 45),
    "W": QColor(133, 77, 14, 50),
    "E": QColor(127, 29, 29, 65),
    "F": QColor(136, 19, 55, 75),
    "A": QColor(136, 19, 55, 75),
}


class LogTableModel(QAbstractTableModel):
    HEADERS = ["Time", "PID", "TID", "Package", "Level", "Tag", "Message"]

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[LogEntry] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        entry = self._entries[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._value_for_column(entry, column)
        if role == Qt.ItemDataRole.TextAlignmentRole and column in {1, 2, 4}:
            return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            return QBrush(LEVEL_FOREGROUNDS.get(entry.level, QColor("#e2e8f0")))
        if role == Qt.ItemDataRole.BackgroundRole:
            color = LEVEL_BACKGROUNDS.get(entry.level)
            return QBrush(color) if color else None
        if role == Qt.ItemDataRole.ToolTipRole:
            return entry.message
        if role == Qt.ItemDataRole.UserRole:
            return entry
        return None

    def append_entries(self, entries: list[LogEntry]) -> None:
        if not entries:
            return

        start_row = len(self._entries)
        end_row = start_row + len(entries) - 1
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        self._entries.extend(entries)
        self.endInsertRows()

    def set_entries(self, entries: list[LogEntry]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def trim_start(self, count: int) -> None:
        if count <= 0 or not self._entries:
            return

        count = min(count, len(self._entries))
        self.beginRemoveRows(QModelIndex(), 0, count - 1)
        del self._entries[:count]
        self.endRemoveRows()

    def clear(self) -> None:
        if not self._entries:
            return
        self.beginResetModel()
        self._entries.clear()
        self.endResetModel()

    def entry_at(self, row: int) -> LogEntry:
        return self._entries[row]

    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def _value_for_column(self, entry: LogEntry, column: int) -> str:
        if column == 0:
            return entry.time
        if column == 1:
            return entry.pid
        if column == 2:
            return entry.tid
        if column == 3:
            return entry.package
        if column == 4:
            return entry.level_name
        if column == 5:
            return entry.tag
        if column == 6:
            return entry.message
        return ""
