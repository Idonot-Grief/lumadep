"""
Windows Aero glass theme — faithful MultiMC 5 dark appearance.
Adds true Aero glass title bar on Windows via DWM API calls,
and a complete MultiMC-matching stylesheet.
"""
import sys
import ctypes
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt
from core.config import ThemeConfig


# ── Windows Aero DWM glass helper ────────────────────────────────────────────

def enable_aero_glass(hwnd: int):
    """Enable DWM Aero glass on Win32 HWND. No-ops on non-Windows."""
    if sys.platform != "win32":
        return
    try:
        dwmapi = ctypes.windll.dwmapi

        class MARGINS(ctypes.Structure):
            _fields_ = [("left", ctypes.c_int), ("right", ctypes.c_int),
                        ("top",  ctypes.c_int), ("bottom", ctypes.c_int)]
        m = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))

        # Windows 11: rounded corners
        try:
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            val = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                         ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

        # Windows 11 22H2+: Mica backdrop
        try:
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            DWMSBT_MAINWINDOW = 2
            val = ctypes.c_int(DWMSBT_MAINWINDOW)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
                                         ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass
    except Exception:
        pass


def apply_dark_titlebar(hwnd: int):
    """Force dark mode title bar (Windows 10 build 17763+)."""
    if sys.platform != "win32":
        return
    try:
        dwmapi = ctypes.windll.dwmapi
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        val = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                     ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def setup_window_aero(window: QMainWindow):
    """Call after window.show() to wire up Aero glass + dark title bar."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        apply_dark_titlebar(hwnd)
        enable_aero_glass(hwnd)
    except Exception:
        pass


# ── Aero Dark stylesheet — matches MultiMC 5 ─────────────────────────────────
AERO_DARK = """
QMainWindow, QDialog {
    background-color: #2b2b2b;
    color: #eeeeee;
}
QWidget {
    background-color: #2b2b2b;
    color: #eeeeee;
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 9pt;
}
QMenuBar {
    background-color: #383838;
    color: #eeeeee;
    border-bottom: 1px solid #1c1c1c;
    padding: 1px 0;
}
QMenuBar::item { padding: 4px 10px; }
QMenuBar::item:selected { background-color: #4a90d9; color: #ffffff; }
QMenu {
    background-color: #2b2b2b;
    color: #eeeeee;
    border: 1px solid #1c1c1c;
    padding: 2px 0;
}
QMenu::item { padding: 5px 24px 5px 10px; }
QMenu::item:selected { background-color: #4a90d9; color: #ffffff; }
QMenu::item:disabled { color: #666666; }
QMenu::separator { height: 1px; background: #444444; margin: 3px 6px; }
QToolBar {
    background-color: #383838;
    border: none;
    border-bottom: 1px solid #1c1c1c;
    spacing: 1px;
    padding: 2px 4px;
}
QToolBar::separator { width: 1px; background: #505050; margin: 3px 2px; }
QToolButton {
    color: #eeeeee;
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 2px;
    padding: 4px 8px;
}
QToolButton:hover   { background-color: #4a4a4a; border-color: #5a5a5a; }
QToolButton:pressed { background-color: #2e6fad; border-color: #4a90d9; }
QToolButton:checked { background-color: #2e6fad; border-color: #4a90d9; }
QToolButton::menu-indicator { image: none; width: 0; }
QFrame#sidebar {
    background-color: #2b2b2b;
    border-left: 1px solid #1c1c1c;
}
QPushButton {
    background-color: #3c3f41;
    color: #bbbbbb;
    border: 1px solid #555555;
    border-radius: 2px;
    padding: 4px 14px;
    min-height: 23px;
}
QPushButton:hover   { background-color: #4c5052; border-color: #6a6a6a; color: #eeeeee; }
QPushButton:pressed { background-color: #2e6fad; border-color: #4a90d9; color: #ffffff; }
QPushButton:disabled { background-color: #313335; color: #666666; border-color: #444444; }
QPushButton#primary {
    background-color: #365880;
    border-color: #4a90d9;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#primary:hover   { background-color: #4169a0; }
QPushButton#primary:pressed { background-color: #1d5a90; }
QPushButton#danger {
    background-color: #5c2c2c;
    border-color: #803030;
    color: #ff9090;
}
QPushButton#danger:hover { background-color: #6d3333; }
QPushButton#launch {
    background-color: #2d6a2d;
    border-color: #3a8c3a;
    color: #ffffff;
    font-weight: bold;
    font-size: 10pt;
    min-height: 28px;
}
QPushButton#launch:hover    { background-color: #3a7d3a; }
QPushButton#launch:disabled { background-color: #253025; color: #557755; border-color: #334433; }
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1e1f22;
    color: #eeeeee;
    border: 1px solid #555555;
    border-radius: 1px;
    padding: 3px 5px;
    selection-background-color: #4a90d9;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border-color: #4a90d9; }
QLineEdit:read-only { background-color: #2b2b2b; color: #aaaaaa; }
QComboBox {
    background-color: #3c3f41;
    color: #bbbbbb;
    border: 1px solid #555555;
    border-radius: 2px;
    padding: 3px 5px;
    min-height: 23px;
}
QComboBox:hover { border-color: #6a6a6a; color: #eeeeee; }
QComboBox:focus { border-color: #4a90d9; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #555555;
}
QComboBox QAbstractItemView {
    background-color: #2b2b2b;
    color: #eeeeee;
    border: 1px solid #1c1c1c;
    selection-background-color: #4a90d9;
    outline: none;
}
QSpinBox, QDoubleSpinBox {
    background-color: #1e1f22;
    color: #eeeeee;
    border: 1px solid #555555;
    border-radius: 1px;
    padding: 3px 24px 3px 5px;
    min-height: 23px;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #4a90d9; }
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #3c3f41;
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #4c5052;
}
QCheckBox, QRadioButton { color: #bbbbbb; spacing: 6px; }
QCheckBox:hover, QRadioButton:hover { color: #eeeeee; }
QCheckBox::indicator, QRadioButton::indicator { width: 13px; height: 13px; }
QCheckBox::indicator:unchecked {
    background-color: #1e1f22;
    border: 1px solid #606060;
    border-radius: 2px;
}
QCheckBox::indicator:checked {
    background-color: #4a90d9;
    border: 1px solid #4a90d9;
    border-radius: 2px;
}
QCheckBox::indicator:hover { border-color: #4a90d9; }
QRadioButton::indicator:unchecked {
    background-color: #1e1f22;
    border: 1px solid #606060;
    border-radius: 7px;
}
QRadioButton::indicator:checked {
    background-color: #4a90d9;
    border: 2px solid #1e1f22;
    border-radius: 7px;
    outline: 1px solid #4a90d9;
}
QTabWidget::pane {
    border: 1px solid #1c1c1c;
    background-color: #2b2b2b;
    top: -1px;
}
QTabBar { background-color: transparent; }
QTabBar::tab {
    background-color: #3c3f41;
    color: #aaaaaa;
    border: 1px solid #1c1c1c;
    border-bottom: none;
    padding: 5px 14px;
    margin-right: 2px;
    border-radius: 3px 3px 0 0;
}
QTabBar::tab:selected  { background-color: #2b2b2b; color: #ffffff; }
QTabBar::tab:hover:!selected { background-color: #4a4d50; color: #dddddd; }
QListWidget, QListView, QTreeView, QTreeWidget {
    background-color: #252526;
    alternate-background-color: #2d2d2e;
    color: #eeeeee;
    border: 1px solid #1c1c1c;
    outline: none;
}
QListWidget::item, QListView::item { padding: 2px 4px; border-radius: 2px; }
QListWidget::item:selected, QListView::item:selected,
QTreeView::item:selected { background-color: #2e6fad; color: #ffffff; }
QListWidget::item:hover:!selected, QListView::item:hover:!selected,
QTreeView::item:hover:!selected { background-color: #383838; }
QScrollBar:vertical   { background-color: #252526; width: 11px; border: none; }
QScrollBar::handle:vertical {
    background-color: #555555; border-radius: 5px;
    min-height: 20px; margin: 2px 2px;
}
QScrollBar::handle:vertical:hover { background-color: #6a6a6a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background-color: #252526; height: 11px; border: none; }
QScrollBar::handle:horizontal {
    background-color: #555555; border-radius: 5px;
    min-width: 20px; margin: 2px 2px;
}
QScrollBar::handle:horizontal:hover { background-color: #6a6a6a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QProgressBar {
    background-color: #1e1f22;
    border: 1px solid #1c1c1c;
    border-radius: 2px;
    color: #eeeeee;
    text-align: center;
    font-size: 8pt;
    max-height: 18px;
}
QProgressBar::chunk { background-color: #2e6fad; border-radius: 1px; }
QGroupBox {
    color: #eeeeee;
    border: 1px solid #505050;
    border-radius: 3px;
    margin-top: 12px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
    color: #aaaaaa;
    font-weight: bold;
    font-size: 8pt;
}
QStatusBar {
    background-color: #3c3f41;
    color: #aaaaaa;
    border-top: 1px solid #1c1c1c;
    font-size: 8pt;
    min-height: 22px;
}
QStatusBar::item { border: none; }
QSplitter::handle         { background-color: #1c1c1c; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical   { height: 1px; }
QMessageBox { background-color: #2b2b2b; }
QMessageBox QLabel { color: #eeeeee; }
QLabel { color: #eeeeee; background: transparent; }
QLabel#heading    { font-weight: bold; font-size: 10pt; color: #ffffff; }
QLabel#subheading { font-weight: bold; color: #aaaaaa; font-size: 8pt; }
QLabel#playtime   { color: #888888; font-size: 8pt; }
QLabel#section    { color: #6699cc; font-size: 8pt; font-weight: bold; }
QToolTip {
    background-color: #1e1f22;
    color: #eeeeee;
    border: 1px solid #4a90d9;
    padding: 4px 7px;
    border-radius: 2px;
    font-size: 8pt;
}
QSlider::groove:horizontal {
    background-color: #1e1f22;
    border: 1px solid #555555;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #4a90d9;
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { background-color: #5aa5f0; }
QSlider::sub-page:horizontal { background-color: #2e6fad; border-radius: 2px; }
"""

AERO_LIGHT = """
QMainWindow, QDialog { background-color: #f2f2f2; color: #1a1a1a; }
QWidget { background-color: #f2f2f2; color: #1a1a1a; font-family: "Segoe UI", "Ubuntu", sans-serif; font-size: 9pt; }
QMenuBar { background-color: #e8e8e8; color: #1a1a1a; border-bottom: 1px solid #cccccc; }
QMenuBar::item:selected { background-color: #4a90d9; color: #ffffff; }
QMenu { background-color: #ffffff; color: #1a1a1a; border: 1px solid #cccccc; }
QMenu::item { padding: 5px 24px 5px 10px; }
QMenu::item:selected { background-color: #4a90d9; color: #ffffff; }
QMenu::separator { height: 1px; background: #cccccc; margin: 3px 6px; }
QToolBar { background-color: #e8e8e8; border-bottom: 1px solid #cccccc; padding: 2px 4px; }
QToolButton { color: #1a1a1a; background-color: transparent; border: 1px solid transparent; border-radius: 2px; padding: 4px 8px; }
QToolButton:hover { background-color: #d8d8d8; border-color: #bbbbbb; }
QToolButton:pressed { background-color: #4a90d9; color: #ffffff; }
QPushButton { background-color: #e0e0e0; color: #1a1a1a; border: 1px solid #bbbbbb; border-radius: 2px; padding: 4px 14px; min-height: 23px; }
QPushButton:hover { background-color: #d0d0d0; border-color: #999999; }
QPushButton:pressed { background-color: #4a90d9; color: #ffffff; }
QPushButton:disabled { background-color: #ececec; color: #aaaaaa; }
QPushButton#primary { background-color: #4a90d9; color: #ffffff; border-color: #3a80c9; font-weight: bold; }
QPushButton#primary:hover { background-color: #3a80c9; }
QPushButton#launch { background-color: #388e3c; color: #ffffff; border-color: #2e7d32; font-weight: bold; font-size: 10pt; min-height: 28px; }
QPushButton#danger { background-color: #c62828; color: #ffffff; border-color: #a01010; }
QLineEdit, QTextEdit, QPlainTextEdit { background-color: #ffffff; color: #1a1a1a; border: 1px solid #bbbbbb; border-radius: 1px; padding: 3px 5px; }
QLineEdit:focus, QTextEdit:focus { border-color: #4a90d9; }
QComboBox { background-color: #ffffff; color: #1a1a1a; border: 1px solid #bbbbbb; border-radius: 2px; padding: 3px 5px; min-height: 23px; }
QComboBox:focus { border-color: #4a90d9; }
QSpinBox, QDoubleSpinBox { background-color: #ffffff; color: #1a1a1a; border: 1px solid #bbbbbb; border-radius: 1px; padding: 3px 5px; }
QCheckBox, QRadioButton { color: #1a1a1a; spacing: 6px; }
QTabWidget::pane { border: 1px solid #cccccc; background-color: #f8f8f8; }
QTabBar::tab { background-color: #e0e0e0; color: #555555; border: 1px solid #cccccc; border-bottom: none; padding: 5px 14px; border-radius: 3px 3px 0 0; }
QTabBar::tab:selected { background-color: #f8f8f8; color: #1a1a1a; }
QListWidget, QListView, QTreeView { background-color: #ffffff; color: #1a1a1a; border: 1px solid #cccccc; }
QListWidget::item:selected, QListView::item:selected, QTreeView::item:selected { background-color: #4a90d9; color: #ffffff; }
QProgressBar { background-color: #e0e0e0; border: 1px solid #cccccc; border-radius: 2px; text-align: center; max-height: 18px; }
QProgressBar::chunk { background-color: #4a90d9; }
QStatusBar { background-color: #e8e8e8; color: #555555; border-top: 1px solid #cccccc; }
QGroupBox { color: #1a1a1a; border: 1px solid #cccccc; border-radius: 3px; margin-top: 12px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #555555; }
QLabel { color: #1a1a1a; background: transparent; }
QScrollBar:vertical { background-color: #e8e8e8; width: 11px; border: none; }
QScrollBar::handle:vertical { background-color: #bbbbbb; border-radius: 5px; min-height: 20px; margin: 2px; }
QScrollBar::handle:vertical:hover { background-color: #999999; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background-color: #e8e8e8; height: 11px; border: none; }
QScrollBar::handle:horizontal { background-color: #bbbbbb; border-radius: 5px; min-width: 20px; margin: 2px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip { background-color: #ffffcc; color: #1a1a1a; border: 1px solid #888888; padding: 3px 6px; }
"""


def apply_theme(app: QApplication, theme_config: ThemeConfig):
    """Apply Windows Aero / MultiMC-style theme."""
    is_light = theme_config.name.lower() == "light"
    app.setStyle("Fusion")
    app.setStyleSheet(AERO_LIGHT if is_light else AERO_DARK)
    font_family = "Segoe UI" if sys.platform == "win32" else "Ubuntu"
    font = QFont(font_family, 9)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
    pal = QPalette()
    if is_light:
        pal.setColor(QPalette.ColorRole.Window,          QColor("#f2f2f2"))
        pal.setColor(QPalette.ColorRole.WindowText,      QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.Base,            QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase,   QColor("#f5f5f5"))
        pal.setColor(QPalette.ColorRole.Text,            QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.Button,          QColor("#e0e0e0"))
        pal.setColor(QPalette.ColorRole.ButtonText,      QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.Highlight,       QColor("#4a90d9"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#ffffcc"))
        pal.setColor(QPalette.ColorRole.ToolTipText,     QColor("#1a1a1a"))
    else:
        pal.setColor(QPalette.ColorRole.Window,          QColor("#2b2b2b"))
        pal.setColor(QPalette.ColorRole.WindowText,      QColor("#eeeeee"))
        pal.setColor(QPalette.ColorRole.Base,            QColor("#1e1f22"))
        pal.setColor(QPalette.ColorRole.AlternateBase,   QColor("#2d2d2e"))
        pal.setColor(QPalette.ColorRole.Text,            QColor("#eeeeee"))
        pal.setColor(QPalette.ColorRole.Button,          QColor("#3c3f41"))
        pal.setColor(QPalette.ColorRole.ButtonText,      QColor("#bbbbbb"))
        pal.setColor(QPalette.ColorRole.Highlight,       QColor("#2e6fad"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#1e1f22"))
        pal.setColor(QPalette.ColorRole.ToolTipText,     QColor("#eeeeee"))
        pal.setColor(QPalette.ColorRole.Mid,             QColor("#444444"))
        pal.setColor(QPalette.ColorRole.Dark,            QColor("#1c1c1c"))
        pal.setColor(QPalette.ColorRole.Shadow,          QColor("#111111"))
    app.setPalette(pal)
