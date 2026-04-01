from __future__ import annotations

import re

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem, QStyledItemDelegate


class HighlightDelegate(QStyledItemDelegate):
    def __init__(self) -> None:
        super().__init__()
        self._mode = "filter"
        self._query = ""
        self._compiled_pattern: re.Pattern[str] | None = None

    def set_search(self, query: str, regex_enabled: bool, mode: str) -> None:
        self._mode = mode
        self._query = query.strip()
        self._compiled_pattern = None

        if not self._query or self._mode != "highlight":
            return

        try:
            pattern = self._query if regex_enabled else re.escape(self._query)
            self._compiled_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error:
            self._compiled_pattern = None

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        if self._compiled_pattern is None or self._mode != "highlight":
            super().paint(painter, option, index)
            return

        style_option = QStyleOptionViewItem(option)
        self.initStyleOption(style_option, index)
        text = style_option.text
        if not text:
            super().paint(painter, option, index)
            return

        display_text = style_option.fontMetrics.elidedText(
            text,
            style_option.textElideMode,
            max(10, style_option.rect.width() - 8),
        )
        matches = list(self._compiled_pattern.finditer(display_text))
        if not matches:
            super().paint(painter, option, index)
            return

        widget = style_option.widget
        style = widget.style() if widget else QApplication.style()
        style_option.text = ""

        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, style_option, painter, widget)
        text_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, style_option, widget)
        text_rect = text_rect.adjusted(4, 0, -4, 0)

        painter.save()
        painter.setClipRect(text_rect)

        highlight_fill = QColor(245, 158, 11, 170)
        for match in matches:
            start, end = match.span()
            left = text_rect.x() + style_option.fontMetrics.horizontalAdvance(display_text[:start])
            width = style_option.fontMetrics.horizontalAdvance(display_text[start:end])
            highlight_rect = QRectF(left, text_rect.y() + 3, max(3, width), text_rect.height() - 6)
            painter.fillRect(highlight_rect, highlight_fill)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(style_option.palette.highlightedText().color())
        else:
            painter.setPen(style_option.palette.text().color())

        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), display_text)
        painter.restore()
