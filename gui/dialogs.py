# -*- coding: utf-8 -*-
"""
Dialogs for the launcher: NewInstance, EditInstance (MultiMC-style),
Settings, Updates.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox, QPushButton,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QProgressBar,
    QGroupBox, QFormLayout, QScrollArea, QSplitter, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QColor
from pathlib import Path
from core.config import LauncherConfig, save_config
from core.updates import UpdateManager, UpdateInfo
from core.logger import launcher_logger


# -------------------------------------------------------------------
# New Instance Dialog
# -------------------------------------------------------------------
class NewInstanceDialog(QDialog):
    def __init__(self, parent, versions=None):
        super().__init__(parent)
        self.versions = versions or []
        self.setWindowTitle("Create New Instance")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Instance")
        form.addRow("Instance Name:", self.name_edit)

        self.version_combo = QComboBox()
        version_ids = [v["id"] for v in self.versions] if self.versions else []
        self.version_combo.addItems(version_ids)
        if version_ids:
            self.version_combo.setCurrentIndex(0)
        form.addRow("Minecraft Version:", self.version_combo)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("(default)")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        form.addRow("Custom Path (optional):", path_layout)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = QPushButton("Create")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Instance Folder")
        if path:
            self.path_edit.setText(path)

    def _on_create(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a name for the instance.")
            return
        self.accept()

    def get_values(self):
        version_id = self.version_combo.currentText() if self.version_combo.count() > 0 else ""
        return {
            "name":       self.name_edit.text().strip(),
            "version_id": version_id,
            "path":       self.path_edit.text().strip() or None,
        }


# -------------------------------------------------------------------
# MultiMC-style Edit Instance Dialog
# -------------------------------------------------------------------
class EditInstanceDialog(QDialog):
    """
    MultiMC-style instance editor with a left nav panel and tabbed content.
    Panels: Version, Loader mods, Resource packs, Shader packs, Notes,
            Worlds, Servers, Screenshots, Settings, Other logs
    """

    PANELS = [
        "Version",
        "Loader mods",
        "Resource packs",
        "Shader packs",
        "Notes",
        "Worlds",
        "Servers",
        "Screenshots",
        "Settings",
        "Other logs",
    ]

    def __init__(self, parent, instance):
        super().__init__(parent)
        self.instance = instance
        self.setWindowTitle("Edit Instance -- " + instance.name)
        self.setMinimumWidth(780)
        self.setMinimumHeight(520)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # --- Left nav list ---
        self.nav = QListWidget()
        self.nav.setFixedWidth(140)
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        self.nav.setStyleSheet(
            "QListWidget { background: #1a1a2e; color: #ccc; border-right: 1px solid #333; }"
            "QListWidget::item { padding: 10px 14px; font-size: 13px; }"
            "QListWidget::item:selected { background: #2d5a8e; color: #fff; }"
            "QListWidget::item:hover:!selected { background: #252540; }"
        )
        for panel in self.PANELS:
            item = QListWidgetItem(panel)
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._switch_panel)
        root.addWidget(self.nav)

        # --- Right content stack ---
        self.stack = QTabWidget()
        self.stack.tabBar().hide()
        self.stack.setDocumentMode(True)

        self.stack.addTab(self._build_version_panel(),       "Version")
        self.stack.addTab(self._build_mods_panel(),          "Loader mods")
        self.stack.addTab(self._build_respacks_panel(),      "Resource packs")
        self.stack.addTab(self._build_shaderpacks_panel(),   "Shader packs")
        self.stack.addTab(self._build_notes_panel(),         "Notes")
        self.stack.addTab(self._build_worlds_panel(),        "Worlds")
        self.stack.addTab(self._build_servers_panel(),       "Servers")
        self.stack.addTab(self._build_screenshots_panel(),   "Screenshots")
        self.stack.addTab(self._build_settings_panel(),      "Settings")
        self.stack.addTab(self._build_otherlogs_panel(),     "Other logs")

        content_wrap = QWidget()
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.stack)

        # Bottom buttons
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_bar.addWidget(close_btn)
        content_layout.addLayout(btn_bar)

        root.addWidget(content_wrap)

    def _switch_panel(self, idx):
        self.stack.setCurrentIndex(idx)

    # ---- Version panel ------------------------------------------------
    def _build_version_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Version list (mimics MultiMC component list)
        self.version_tree = QTreeWidget()
        self.version_tree.setHeaderLabels(["Name", "Version"])
        self.version_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.version_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.version_tree.setRootIsDecorated(False)
        self.version_tree.setAlternatingRowColors(True)
        self._refresh_version_tree()
        layout.addWidget(self.version_tree)

        # Right-side action buttons (MultiMC style)
        btn_layout = QHBoxLayout()
        for label, slot in [
            ("Change version",    self._change_version),
            ("Move up",           lambda: None),
            ("Move down",         lambda: None),
            ("Remove",            lambda: None),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            btn_layout.addWidget(b)
        btn_layout.addStretch()

        install_layout = QHBoxLayout()
        for label, slot in [
            ("Install Forge",     lambda: self._install_loader("forge")),
            ("Install NeoForge",  lambda: self._install_loader("neoforge")),
            ("Install Fabric",    lambda: self._install_loader("fabric")),
            ("Install Quilt",     lambda: self._install_loader("quilt")),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            install_layout.addWidget(b)
        install_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addLayout(install_layout)
        return w

    def _refresh_version_tree(self):
        self.version_tree.clear()
        mc_ver = self.instance.data.get("version", "Unknown")

        rows = [("Minecraft", mc_ver, True)]

        fabric = self.instance.data.get("fabric_loader", "")
        if fabric:
            rows.append(("Intermediary Mappings", mc_ver, True))
            rows.append(("Fabric Loader", fabric, True))

        forge = self.instance.data.get("forge_version", "")
        if forge:
            rows.append(("Forge", forge, True))

        quilt = self.instance.data.get("quilt_version", "")
        if quilt:
            rows.append(("Quilt Loader", quilt, True))

        for name, ver, enabled in rows:
            item = QTreeWidgetItem([name, ver])
            item.setCheckState(0, Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            green = QColor("#4caf50")
            item.setForeground(1, green)
            self.version_tree.addTopLevelItem(item)

    def _change_version(self):
        sel = self.version_tree.currentItem()
        if not sel:
            return
        component = sel.text(0)
        if component == "Minecraft":
            new_ver, ok = _input_dialog(self, "Change Minecraft Version",
                                        "New version ID:", self.instance.data.get("version", ""))
            if ok and new_ver.strip():
                self.instance.data["version"] = new_ver.strip()
                self.instance.save()
                self._refresh_version_tree()
        elif "Fabric" in component:
            new_ver, ok = _input_dialog(self, "Change Fabric Version",
                                        "Fabric loader version:", self.instance.data.get("fabric_loader", ""))
            if ok and new_ver.strip():
                self.instance.data["fabric_loader"] = new_ver.strip()
                self.instance.save()
                self._refresh_version_tree()

    def _install_loader(self, loader):
        loaders = {
            "fabric":   ("fabric_loader",   "Fabric loader version (e.g. 0.15.11):"),
            "forge":    ("forge_version",   "Forge version (e.g. 43.3.0):"),
            "neoforge": ("neoforge_version","NeoForge version (e.g. 21.0.0):"),
            "quilt":    ("quilt_version",   "Quilt loader version (e.g. 0.24.0):"),
        }
        key, prompt = loaders[loader]
        current = self.instance.data.get(key, "")
        new_ver, ok = _input_dialog(self, "Install " + loader.capitalize(), prompt, current)
        if ok:
            if new_ver.strip():
                self.instance.data[key] = new_ver.strip()
            else:
                self.instance.data.pop(key, None)
            self.instance.save()
            self._refresh_version_tree()

    # ---- Mods panel ---------------------------------------------------
    def _build_mods_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        label = QLabel("Loader mods folder:")
        layout.addWidget(label)

        self.mods_list = QListWidget()
        self._populate_file_list(self.mods_list, self.instance.path / ".minecraft" / "mods")
        layout.addWidget(self.mods_list)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open mods folder")
        open_btn.clicked.connect(lambda: _open_dir(self.instance.path / ".minecraft" / "mods"))
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    # ---- Resource packs panel -----------------------------------------
    def _build_respacks_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Resource packs:"))
        lst = QListWidget()
        self._populate_file_list(lst, self.instance.path / ".minecraft" / "resourcepacks")
        layout.addWidget(lst)
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open resourcepacks folder")
        open_btn.clicked.connect(lambda: _open_dir(self.instance.path / ".minecraft" / "resourcepacks"))
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    # ---- Shader packs panel -------------------------------------------
    def _build_shaderpacks_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Shader packs:"))
        lst = QListWidget()
        self._populate_file_list(lst, self.instance.path / ".minecraft" / "shaderpacks")
        layout.addWidget(lst)
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open shaderpacks folder")
        open_btn.clicked.connect(lambda: _open_dir(self.instance.path / ".minecraft" / "shaderpacks"))
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    # ---- Notes panel --------------------------------------------------
    def _build_notes_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Notes (saved with instance):"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(self.instance.data.get("notes", ""))
        self.notes_edit.textChanged.connect(self._save_notes)
        layout.addWidget(self.notes_edit)
        return w

    def _save_notes(self):
        self.instance.data["notes"] = self.notes_edit.toPlainText()
        self.instance.save()

    # ---- Worlds panel -------------------------------------------------
    def _build_worlds_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Worlds:"))
        lst = QListWidget()
        saves = self.instance.path / ".minecraft" / "saves"
        if saves.exists():
            for d in sorted(saves.iterdir()):
                if d.is_dir():
                    lst.addItem(d.name)
        else:
            lst.addItem("(no worlds found)")
        layout.addWidget(lst)
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open saves folder")
        open_btn.clicked.connect(lambda: _open_dir(saves))
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    # ---- Servers panel ------------------------------------------------
    def _build_servers_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Servers (servers.dat parsed):"))
        self.servers_list = QListWidget()
        self._load_servers()
        layout.addWidget(self.servers_list)
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open .minecraft folder")
        open_btn.clicked.connect(lambda: _open_dir(self.instance.path / ".minecraft"))
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    def _load_servers(self):
        self.servers_list.clear()
        try:
            import struct
            dat = self.instance.path / ".minecraft" / "servers.dat"
            if dat.exists():
                # Simple NBT text-search for server names
                raw = dat.read_bytes()
                text = raw.decode("utf-8", errors="ignore")
                # find "ip" tag values as rough heuristic
                import re
                names = re.findall(r"[\x00-\x20]{1,4}(.{3,64}?)[\x00-\x20]", text)
                for n in names[:20]:
                    n2 = "".join(c for c in n if 32 <= ord(c) < 127)
                    if n2:
                        self.servers_list.addItem(n2)
        except Exception:
            pass
        if self.servers_list.count() == 0:
            self.servers_list.addItem("(no servers found -- launch the game first)")

    # ---- Screenshots panel --------------------------------------------
    def _build_screenshots_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Screenshots:"))
        lst = QListWidget()
        shots = self.instance.path / ".minecraft" / "screenshots"
        if shots.exists():
            for f in sorted(shots.iterdir()):
                if f.is_file():
                    lst.addItem(f.name)
        if lst.count() == 0:
            lst.addItem("(no screenshots)")
        layout.addWidget(lst)
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open screenshots folder")
        open_btn.clicked.connect(lambda: _open_dir(shots))
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    # ---- Settings panel -----------------------------------------------
    def _build_settings_panel(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.name_edit = QLineEdit(self.instance.name)
        layout.addRow("Instance Name:", self.name_edit)
        self.name_edit.editingFinished.connect(self._save_settings)

        self.ram_min = QSpinBox()
        self.ram_min.setRange(512, 32768)
        self.ram_min.setSuffix(" MB")
        self.ram_min.setValue(int(self.instance.data.get("ram_min", 2048)))
        self.ram_min.valueChanged.connect(self._save_settings)
        layout.addRow("Minimum RAM:", self.ram_min)

        self.ram_max = QSpinBox()
        self.ram_max.setRange(512, 32768)
        self.ram_max.setSuffix(" MB")
        self.ram_max.setValue(int(self.instance.data.get("ram_max", 4096)))
        self.ram_max.valueChanged.connect(self._save_settings)
        layout.addRow("Maximum RAM:", self.ram_max)

        self.jvm_args = QLineEdit(self.instance.data.get("jvm_args", ""))
        self.jvm_args.setPlaceholderText("-XX:+UseG1GC ...")
        self.jvm_args.editingFinished.connect(self._save_settings)
        layout.addRow("Extra JVM Args:", self.jvm_args)

        self.java_path = QLineEdit(self.instance.data.get("java_path", ""))
        self.java_path.setPlaceholderText("(use launcher default)")
        java_browse = QPushButton("Browse...")
        java_browse.clicked.connect(self._browse_java)
        java_row = QHBoxLayout()
        java_row.addWidget(self.java_path)
        java_row.addWidget(java_browse)
        layout.addRow("Java executable:", java_row)

        return w

    def _browse_java(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Java Executable",
            filter="Java (java.exe java);;All Files (*)"
        )
        if path:
            self.java_path.setText(path)
            self._save_settings()

    def _save_settings(self):
        name = self.name_edit.text().strip()
        if name:
            self.instance.name = name
        self.instance.data["ram_min"] = self.ram_min.value()
        self.instance.data["ram_max"] = self.ram_max.value()
        self.instance.data["jvm_args"] = self.jvm_args.text().strip()
        self.instance.data["java_path"] = self.java_path.text().strip()
        self.instance.save()

    # ---- Other logs panel ---------------------------------------------
    def _build_otherlogs_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Log files in .minecraft/logs/:"))
        lst = QListWidget()
        logs = self.instance.path / ".minecraft" / "logs"
        if logs.exists():
            for f in sorted(logs.iterdir(), reverse=True):
                if f.is_file():
                    lst.addItem(f.name)
        if lst.count() == 0:
            lst.addItem("(no log files -- launch the game first)")
        lst.itemDoubleClicked.connect(lambda item: self._open_log(logs / item.text()))
        layout.addWidget(lst)
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open logs folder")
        open_btn.clicked.connect(lambda: _open_dir(logs))
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    def _open_log(self, path):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(path.name)
        dlg.resize(800, 500)
        v = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(text)
        te.setFont(QFont("Courier New", 9))
        v.addWidget(te)
        dlg.exec()

    # ---- Helpers ------------------------------------------------------
    def _populate_file_list(self, lst, folder):
        folder = Path(folder)
        if folder.exists():
            for f in sorted(folder.iterdir()):
                if f.is_file():
                    lst.addItem(f.name)
        if lst.count() == 0:
            lst.addItem("(folder is empty)")

    def get_values(self):
        # kept for compatibility -- settings are auto-saved in the panel
        return {
            "name":     self.instance.name,
            "ram_min":  int(self.instance.data.get("ram_min", 2048)),
            "ram_max":  int(self.instance.data.get("ram_max", 4096)),
            "jvm_args": self.instance.data.get("jvm_args", ""),
        }


# -------------------------------------------------------------------
# Settings Dialog
# -------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent, config: LauncherConfig):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(),    "General")
        tabs.addTab(self._build_java_tab(),       "Java")
        tabs.addTab(self._build_auth_tab(),       "Authentication")
        tabs.addTab(self._build_appearance_tab(), "Appearance")
        tabs.addTab(self._build_advanced_tab(),   "Advanced")
        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _build_general_tab(self):
        widget = QWidget()
        self._tab_general = widget
        layout = QFormLayout(widget)

        self.auto_check = QCheckBox("Auto-check for updates on startup")
        self.auto_check.setChecked(self.config.auto_check_updates)
        layout.addRow("Updates", self.auto_check)

        self.keep_open = QCheckBox("Keep launcher open after starting game")
        self.keep_open.setChecked(self.config.keep_launcher_open)
        layout.addRow("Launcher", self.keep_open)

        self.show_console = QCheckBox("Show console when launching")
        self.show_console.setChecked(self.config.show_console)
        layout.addRow("Console", self.show_console)

        return widget

    def _build_java_tab(self):
        widget = QWidget()
        self._tab_java = widget
        layout = QFormLayout(widget)

        java_layout = QHBoxLayout()
        self.java_path = QLineEdit(self.config.java.java_path)
        java_btn = QPushButton("Browse...")
        java_btn.clicked.connect(self._browse_java)
        java_layout.addWidget(self.java_path)
        java_layout.addWidget(java_btn)
        layout.addRow("Java Path", java_layout)

        self.min_ram = QSpinBox()
        self.min_ram.setMinimum(512)
        self.min_ram.setMaximum(32768)
        self.min_ram.setValue(self.config.java.min_ram)
        self.min_ram.setSuffix(" MB")
        layout.addRow("Minimum RAM", self.min_ram)

        self.max_ram = QSpinBox()
        self.max_ram.setMinimum(512)
        self.max_ram.setMaximum(32768)
        self.max_ram.setValue(self.config.java.max_ram)
        self.max_ram.setSuffix(" MB")
        layout.addRow("Maximum RAM", self.max_ram)

        self.jvm_args = QLineEdit(self.config.java.extra_jvm_args)
        layout.addRow("Extra JVM Args", self.jvm_args)

        return widget

    def _build_auth_tab(self):
        widget = QWidget()
        self._tab_auth = widget
        layout = QFormLayout(widget)

        self.username_edit = QLineEdit(self.config.auth.default_offline_name)
        layout.addRow("Offline Username", self.username_edit)

        self.offline_mode = QCheckBox("Use offline mode by default")
        self.offline_mode.setChecked(self.config.auth.offline_mode)
        layout.addRow("Offline Mode", self.offline_mode)

        self.login_btn = QPushButton("Sign in with Microsoft...")
        layout.addRow("Microsoft Account", self.login_btn)

        self.offline_btn = QPushButton("Set Offline Username")
        layout.addRow("", self.offline_btn)

        return widget

    def _build_appearance_tab(self):
        widget = QWidget()
        self._tab_appearance = widget
        layout = QFormLayout(widget)

        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light", "Auto"])
        self.theme.setCurrentText(self.config.theme.name)
        layout.addRow("Theme", self.theme)

        icon_layout = QHBoxLayout()
        self.icon_path = QLineEdit(self.config.theme.custom_icon)
        icon_btn = QPushButton("Browse...")
        icon_btn.clicked.connect(self._browse_icon)
        icon_layout.addWidget(self.icon_path)
        icon_layout.addWidget(icon_btn)
        layout.addRow("Custom Icon", icon_layout)

        return widget

    def _build_advanced_tab(self):
        widget = QWidget()
        self._tab_advanced = widget
        layout = QFormLayout(widget)

        self.api_type = QComboBox()
        self.api_type.addItems(["mojang", "fabric", "custom"])
        self.api_type.setCurrentText(self.config.api_type)
        layout.addRow("API Type", self.api_type)

        self.api_url = QLineEdit(self.config.custom_api_url)
        layout.addRow("Custom API URL", self.api_url)

        self.update_server = QLineEdit(self.config.update_server)
        layout.addRow("Update Server", self.update_server)

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText(self.config.logging_level)
        layout.addRow("Logging Level", self.log_level)

        return widget

    def _browse_java(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Java Executable",
            filter="Java Executable (java.exe java);;All Files (*)"
        )
        if path:
            self.java_path.setText(path)

    def _browse_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon Image",
            filter="Image Files (*.png *.ico *.jpg)"
        )
        if path:
            self.icon_path.setText(path)

    def get_values(self):
        return {
            "java": {
                "java_path":      self.java_path.text(),
                "min_ram":        self.min_ram.value(),
                "max_ram":        self.max_ram.value(),
                "extra_jvm_args": self.jvm_args.text(),
            },
            "auth": {
                "default_offline_name": self.username_edit.text(),
                "offline_mode":         self.offline_mode.isChecked(),
            },
            "theme": {
                "name":        self.theme.currentText(),
                "custom_icon": self.icon_path.text(),
            },
            "api_type":           self.api_type.currentText(),
            "custom_api_url":     self.api_url.text(),
            "update_server":      self.update_server.text(),
            "logging_level":      self.log_level.currentText(),
            "auto_check_updates": self.auto_check.isChecked(),
            "keep_launcher_open": self.keep_open.isChecked(),
            "show_console":       self.show_console.isChecked(),
        }


# -------------------------------------------------------------------
# Update Dialog
# -------------------------------------------------------------------
class UpdateDialog(QDialog):
    def __init__(self, parent, updates, update_manager):
        super().__init__(parent)
        self.updates = updates
        self.update_manager = update_manager
        self.setWindowTitle("Updates Available")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        info = QLabel("{n} update(s) available for the launcher".format(n=len(self.updates)))
        layout.addWidget(info)

        self.list = QListWidget()
        for update in self.updates:
            item_text = "{id} - v{ver}\n{desc}".format(id=update.id, ver=update.version, desc=update.description)
            self.list.addItem(item_text)
        layout.addWidget(self.list)

        btn_layout = QHBoxLayout()
        skip_btn = QPushButton("Skip")
        skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(skip_btn)
        apply_btn = QPushButton("Install Updates")
        apply_btn.clicked.connect(self._apply_updates)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _apply_updates(self):
        self.setEnabled(False)
        launcher_logger.info("Starting update download and installation...")

        patch_paths = []
        for update in self.updates:
            patch_path = self.update_manager.download_patch(update)
            if patch_path:
                patch_paths.append(patch_path)

        if not patch_paths:
            QMessageBox.critical(self, "Error", "Failed to download patches")
            self.setEnabled(True)
            return

        success = True
        for patch_path in patch_paths:
            if not self.update_manager.apply_patch(patch_path):
                success = False

        if success:
            QMessageBox.information(self, "Success", "Updates installed!\nThe launcher will restart.")
            launcher_logger.info("Updates applied successfully")
            import subprocess, sys
            if getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable])
            else:
                main_py = Path(__file__).resolve().parent.parent / "main.py"
                subprocess.Popen([sys.executable, str(main_py)])
            sys.exit(0)
        else:
            QMessageBox.critical(self, "Error", "Some patches failed to apply")
            launcher_logger.error("Update installation failed")
            self.setEnabled(True)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _input_dialog(parent, title, label, current=""):
    """Thin wrapper around QInputDialog.getText."""
    from PyQt6.QtWidgets import QInputDialog
    return QInputDialog.getText(parent, title, label, text=current)


def _open_dir(path):
    """Open a folder in the OS file manager, creating it if needed."""
    import os, platform, subprocess
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    s = platform.system()
    if s == "Windows":
        os.startfile(str(path))
    elif s == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])