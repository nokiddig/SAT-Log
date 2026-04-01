from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0b1220"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#172033"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0f766e"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#f8fafc"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#fecaca"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#64748b"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            color: #e2e8f0;
            background-color: #0b1220;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        QMainWindow, QDialog {
            background-color: #0b1220;
        }
        QFrame#ControlPanel {
            background-color: #101827;
            border: 1px solid #1f2937;
            border-radius: 10px;
        }
        QLabel[hint="true"] {
            color: #94a3b8;
            font-size: 9pt;
        }
        QLineEdit, QComboBox, QPlainTextEdit, QTableView {
            background-color: #111827;
            color: #e2e8f0;
            border: 1px solid #263143;
            border-radius: 8px;
            padding: 6px 8px;
            selection-background-color: #115e59;
        }
        QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTableView:focus {
            border: 1px solid #14b8a6;
        }
        QLineEdit[error="true"] {
            border: 1px solid #ef4444;
        }
        QPushButton, QToolButton {
            background-color: #162134;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 7px 12px;
        }
        QPushButton:hover, QToolButton:hover {
            background-color: #1c2a40;
        }
        QPushButton#PrimaryButton {
            background-color: #0f766e;
            border: 1px solid #14b8a6;
            font-weight: 600;
        }
        QPushButton#PrimaryButton:hover {
            background-color: #0d9488;
        }
        QPushButton#DangerButton {
            background-color: #7f1d1d;
            border: 1px solid #ef4444;
        }
        QHeaderView::section {
            background-color: #0f172a;
            color: #cbd5e1;
            border: none;
            border-bottom: 1px solid #1e293b;
            padding: 8px;
            font-weight: 600;
        }
        QTableView {
            gridline-color: #1e293b;
            alternate-background-color: #0e1728;
        }
        QStatusBar {
            background-color: #101827;
            color: #cbd5e1;
            border-top: 1px solid #1f2937;
        }
        QScrollBar:vertical {
            background: #0f172a;
            width: 12px;
            margin: 4px;
        }
        QScrollBar::handle:vertical {
            background: #334155;
            min-height: 24px;
            border-radius: 6px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """
    )
