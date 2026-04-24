"""
Widgets — MultiMC-style UI components.

InstanceGridWidget  — icon grid with right-click context menu
SidebarPanel        — right side action buttons (like MultiMC)
ConsoleWidget       — log output panel with colour coding + copy/upload
NewsWidget          — placeholder news panel
"""
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QFrame, QAbstractItemView, QTextEdit, QMenu,
    QApplication, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QAction
from gui.icons import make_instance_icon, instance_qicon


# ── Instance Grid ─────────────────────────────────────────────────────────────

class InstanceGridWidget(QListWidget):
    """
    MultiMC-style icon grid.  Supports left-click select, double-click launch,
    and a right-click context menu with all instance actions.
    """
    instance_selected        = pyqtSignal(str)
    instance_double_clicked  = pyqtSignal(str)

    # context menu signals
    launch_requested         = pyqtSignal(str)
    launch_offline_requested = pyqtSignal(str)
    edit_requested           = pyqtSignal(str)
    view_mods_requested      = pyqtSignal(str)
    view_worlds_requested    = pyqtSignal(str)
    open_folder_requested    = pyqtSignal(str)
    delete_requested         = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(48, 48))
        self.setGridSize(QSize(92, 82))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setWordWrap(True)
        self.setSpacing(4)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setUniformItemSizes(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemClicked.connect(lambda i: self.instance_selected.emit(i.text()))
        self.itemDoubleClicked.connect(lambda i: self.instance_double_clicked.emit(i.text()))

    def add_instance(self, name: str):
        item = QListWidgetItem(name)
        item.setIcon(instance_qicon(name, 48))
        item.setSizeHint(QSize(88, 78))
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        item.setToolTip(name)
        self.addItem(item)

    def remove_instance(self, name: str):
        for i in range(self.count()):
            if self.item(i).text() == name:
                self.takeItem(i)
                return

    def _show_context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        if not item:
            return
        name = item.text()
        self.setCurrentItem(item)
        self.instance_selected.emit(name)

        menu = QMenu(self)
        menu.addAction("▶  Launch",          lambda: self.launch_requested.emit(name))
        menu.addAction("Launch Offline",     lambda: self.launch_offline_requested.emit(name))
        menu.addSeparator()
        menu.addAction("Edit Instance…",     lambda: self.edit_requested.emit(name))
        menu.addSeparator()
        menu.addAction("View Mods",          lambda: self.view_mods_requested.emit(name))
        menu.addAction("View Worlds",        lambda: self.view_worlds_requested.emit(name))
        menu.addAction("Instance Folder",    lambda: self.open_folder_requested.emit(name))
        menu.addSeparator()
        act_del = menu.addAction("Delete Instance", lambda: self.delete_requested.emit(name))
        act_del.setObjectName("danger")
        menu.exec(self.mapToGlobal(pos))


# ── Sidebar Panel ─────────────────────────────────────────────────────────────

class SidebarPanel(QFrame):
    """
    Right-side panel — matches MultiMC's sidebar layout exactly:
    instance name, Launch / Launch Offline, separator, Edit / Mods / Worlds /
    Folder, separator, Delete.
    """
    launch_requested         = pyqtSignal()
    launch_offline_requested = pyqtSignal()
    edit_instance_requested  = pyqtSignal()
    delete_instance_requested= pyqtSignal()
    view_mods_requested      = pyqtSignal()
    view_worlds_requested    = pyqtSignal()
    open_folder_requested    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(156)
        self.setMaximumWidth(172)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(3)

        # ── Instance name ──
        self.instance_label = QLabel("No instance\nselected")
        self.instance_label.setObjectName("heading")
        self.instance_label.setWordWrap(True)
        self.instance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instance_label.setMinimumHeight(36)
        layout.addWidget(self.instance_label)

        layout.addSpacing(4)

        # ── Launch buttons ──
        self.launch_btn = self._btn("▶  Launch", "launch")
        self.launch_btn.clicked.connect(self.launch_requested)
        layout.addWidget(self.launch_btn)

        self.launch_offline_btn = self._btn("Launch Offline")
        self.launch_offline_btn.clicked.connect(self.launch_offline_requested)
        layout.addWidget(self.launch_offline_btn)

        layout.addWidget(self._sep())

        # ── Instance management ──
        for label, sig in [
            ("Edit Instance",   self.edit_instance_requested),
            ("View Mods",       self.view_mods_requested),
            ("View Worlds",     self.view_worlds_requested),
            ("Instance Folder", self.open_folder_requested),
        ]:
            btn = self._btn(label)
            btn.clicked.connect(sig)
            layout.addWidget(btn)

        layout.addWidget(self._sep())

        self.delete_btn = self._btn("Delete Instance", "danger")
        self.delete_btn.clicked.connect(self.delete_instance_requested)
        layout.addWidget(self.delete_btn)

        layout.addStretch(1)

        # Playtime label at bottom
        self.playtime_label = QLabel("")
        self.playtime_label.setObjectName("playtime")
        self.playtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.playtime_label.setWordWrap(True)
        layout.addWidget(self.playtime_label)

        self._set_enabled(False)

    def _btn(self, text: str, obj_name: str = "") -> QPushButton:
        b = QPushButton(text)
        b.setMinimumHeight(26)
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if obj_name:
            b.setObjectName(obj_name)
        return b

    def _sep(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setFixedHeight(1)
        return line

    def _set_enabled(self, enabled: bool):
        for w in [self.launch_btn, self.launch_offline_btn, self.delete_btn]:
            w.setEnabled(enabled)

    def set_instance(self, name: str | None, playtime: str = ""):
        if name:
            self.instance_label.setText(name)
            self._set_enabled(True)
        else:
            self.instance_label.setText("No instance\nselected")
            self._set_enabled(False)
        self.playtime_label.setText(playtime)


# ── Console Widget ────────────────────────────────────────────────────────────

class ConsoleWidget(QWidget):
    """
    Log output panel — MultiMC console style.
    Header row: title + Keep Updating checkbox + Copy / Upload / Clear buttons.
    Body: colour-coded text output.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ──
        header = QFrame()
        header.setObjectName("consoleHeader")
        header.setStyleSheet(
            "QFrame#consoleHeader { background:#252525; border-top:1px solid #1a1a1a; }"
        )
        header.setFixedHeight(28)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(6, 0, 4, 0)
        hlay.setSpacing(4)

        title = QLabel("Minecraft Log")
        title.setObjectName("subheading")
        hlay.addWidget(title)
        hlay.addStretch(1)

        for label, slot in [("Copy", self._copy_all), ("Clear", self._clear)]:
            btn = QPushButton(label)
            btn.setFixedHeight(20)
            btn.setFixedWidth(46)
            btn.clicked.connect(slot)
            hlay.addWidget(btn)

        root.addWidget(header)

        # ── Log text area ──
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #d4d4d4;
                border: none;
                padding: 4px 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 8pt;
            }
        """)
        font = QFont("Consolas" if sys.platform == "win32" else "Courier New", 9)
        self.text.setFont(font)
        self.text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self._context_menu)
        root.addWidget(self.text)

    _COLORS = {
        "info":  "#a8d8a8",
        "warn":  "#e8d060",
        "error": "#f07070",
        "debug": "#8888cc",
        "game":  "#aaaaaa",
    }

    def append(self, msg: str, level: str = "info"):
        color = self._COLORS.get(level, self._COLORS["info"])
        # Escape HTML special chars
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.text.append(f'<span style="color:{color}; white-space:pre;">{safe}</span>')
        sb = self.text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear(self):
        self.text.clear()

    def _copy_all(self):
        QApplication.clipboard().setText(self.text.toPlainText())

    def _context_menu(self, pos):
        menu = QMenu(self)
        if self.text.textCursor().hasSelection():
            menu.addAction("Copy Selected",
                           lambda: QApplication.clipboard().setText(
                               self.text.textCursor().selectedText()))
        menu.addAction("Copy All",   self._copy_all)
        menu.addAction("Clear",      self._clear)
        menu.addSeparator()
        menu.addAction("Select All", self.text.selectAll)
        menu.exec(self.text.mapToGlobal(pos))


# ── News Widget ───────────────────────────────────────────────────────────────

class NewsWidget(QWidget):
    """Welcome / news panel shown at the bottom of the main window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QTextBrowser
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet(
            "QTextBrowser { background:#252525; border:none; color:#cccccc; }"
        )
        self.browser.setHtml("""
        <div style='font-family:Segoe UI,sans-serif;color:#cccccc;padding:4px;'>
        <span style='color:#4a90d9;font-weight:bold;'>MC Launcher</span>
        &nbsp;·&nbsp; Create instances · Manage mods · Auto-install Java
        </div>
        """)
        layout.addWidget(self.browser)