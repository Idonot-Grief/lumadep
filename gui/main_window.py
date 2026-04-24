"""
Main Window — MultiMC-style layout.

Layout:
  ┌──────────────────────────────────────────────────────┐
  │  Menu Bar                                             │
  ├──────────────────────────────────────────────────────┤
  │  Toolbar: [Add Instance] [Folders▾] [Settings] …     │
  ├────────────────────────────────┬─────────────────────┤
  │  Instance Grid (icon mode)     │ Sidebar actions      │
  │                                │  [Launch]            │
  │                                │  [Launch Offline]    │
  │                                │  ──────────────      │
  │                                │  [Edit Instance]     │
  │                                │  [View Mods]         │
  │                                │  [View Worlds]       │
  │                                │  [Open Folder]       │
  │                                │  ──────────────      │
  │                                │  [Delete Instance]   │
  ├────────────────────────────────┴─────────────────────┤
  │  Progress bar (hidden when idle)                      │
  ├──────────────────────────────────────────────────────┤
  │  Console (collapsible)                               │
  ├──────────────────────────────────────────────────────┤
  │  Status Bar                                          │
  └──────────────────────────────────────────────────────┘
"""
import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QToolBar, QStatusBar, QProgressBar,
    QMessageBox, QInputDialog, QLabel, QPushButton,
    QSizePolicy, QMenu, QMenuBar, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QColor

from core.config import load_config, save_config, INSTANCES_DIR
from core.net import fetch_manifest
from core.instance import Instance
from gui.widgets import InstanceGridWidget, SidebarPanel, ConsoleWidget, NewsWidget
from gui.dialogs import NewInstanceDialog, EditInstanceDialog, SettingsDialog


# ──────────────────────────────────────────────────────────
# Background worker thread
# ──────────────────────────────────────────────────────────
class WorkerThread(QThread):
    progress = pyqtSignal(float)
    message  = pyqtSignal(str, str)   # (text, level)
    finished = pyqtSignal(bool, str)  # (success, error_msg)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.func(
                *self.args,
                progress_cb=self.progress.emit,
                msg_cb=self.message.emit,
                **self.kwargs,
            )
            self.finished.emit(True, "")
        except Exception as e:
            import traceback
            self.finished.emit(False, traceback.format_exc())


# ──────────────────────────────────────────────────────────
# Game log reader thread
# ──────────────────────────────────────────────────────────
class GameLogThread(QThread):
    """
    Reads stdout AND stderr from the game process on two separate daemon
    threads and emits each line as a Qt signal to the main thread.

    Windows note: we never use selectors on pipes — on Windows,
    selectors only works on sockets, not pipe handles.  Instead we spin
    up one Python thread per stream (stdout / stderr) using blocking
    readline(), which is safe because the game process owns the write
    end of the pipes and will eventually close them.
    """
    log_line    = pyqtSignal(str, str)  # (message, level)
    game_exited = pyqtSignal(int)       # exit-code

    def __init__(self, proc):
        super().__init__()
        self.proc = proc

    def _drain(self, stream):
        from gui.console import GameLogCapture
        try:
            for raw in stream:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    level, msg = GameLogCapture.parse_game_log(line)
                    self.log_line.emit(msg, level)
        except Exception:
            pass

    def run(self):
        import threading
        threads = []
        for stream in (self.proc.stdout, self.proc.stderr):
            if stream:
                t = threading.Thread(target=self._drain, args=(stream,), daemon=True)
                t.start()
                threads.append(t)
        for t in threads:
            t.join()
        rc = self.proc.wait()
        self.game_exited.emit(rc)


# ──────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, config=None):
        super().__init__()
        self.setWindowTitle("Luma Launcher")
        self.setMinimumSize(900, 560)
        self.resize(1000, 660)

        self.config = config if config is not None else load_config()
        self.instances: list[Instance] = []
        self.current_instance: Instance | None = None
        self._version_manifest = None   # cached lazily
        self._worker: WorkerThread | None = None
        self._game_log_thread: GameLogThread | None = None
        self._game_proc = None
        self._pending_proc = None  # set by worker thread, consumed on main thread

        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

        self.load_instances()

    # ── Menu ──────────────────────────────────────────────
    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "New Instance…",   "Ctrl+N", self.new_instance)
        file_menu.addSeparator()
        self._add_action(file_menu, "Settings…",        "Ctrl+,", self.open_settings)
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit",             "Ctrl+Q", self.close)

        # Instances
        inst_menu = mb.addMenu("&Instances")
        self._add_action(inst_menu, "Launch",           "Ctrl+Return", self.launch)
        self._add_action(inst_menu, "Edit Instance…",   None, self.edit_instance)
        inst_menu.addSeparator()
        self._add_action(inst_menu, "Open Instance Folder", None, self.open_folder)
        self._add_action(inst_menu, "Delete Instance",  None, self.delete_instance)

        # Folders
        folders_menu = mb.addMenu("F&olders")
        self._add_action(folders_menu, "Instances Folder", None,
                         lambda: self._open_dir(INSTANCES_DIR))
        from core.config import LAUNCHER_DIR
        self._add_action(folders_menu, "Launcher Data Folder", None,
                         lambda: self._open_dir(LAUNCHER_DIR))

        # Help
        help_menu = mb.addMenu("&Help")
        self._add_action(help_menu, "About", None, self._about)
        help_menu.addSeparator()
        self._add_action(help_menu, "Import Patch File (.upt)...", None, self.import_patch)

    def _add_action(self, menu, text, shortcut, slot):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    # ── Toolbar ───────────────────────────────────────────
    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        def tbtn(text, tip, slot):
            btn = tb.addAction(text)
            btn.setToolTip(tip)
            btn.triggered.connect(slot)
            return btn

        tbtn("➕  Add Instance", "Create a new Minecraft instance", self.new_instance)
        tb.addSeparator()
        tbtn("📁  Folders",      "Open launcher folders",           self._folders_menu)
        tb.addSeparator()
        tbtn("⚙️  Settings",     "Open global settings",            self.open_settings)
        tb.addSeparator()
        tbtn("🔄  Refresh",      "Refresh instance list",           self.load_instances)

    # ── Central widget ────────────────────────────────────
    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top: instance grid + sidebar ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        self.grid = InstanceGridWidget()
        self.grid.instance_selected.connect(self._on_instance_selected)
        self.grid.instance_double_clicked.connect(self.launch)
        splitter.addWidget(self.grid)

        self.sidebar = SidebarPanel()
        self.sidebar.launch_requested.connect(self.launch)
        self.sidebar.launch_offline_requested.connect(self.launch_offline)
        self.sidebar.edit_instance_requested.connect(self.edit_instance)
        self.sidebar.delete_instance_requested.connect(self.delete_instance)
        self.sidebar.view_mods_requested.connect(self._view_mods)
        self.sidebar.view_worlds_requested.connect(self._view_worlds)
        self.sidebar.open_folder_requested.connect(self.open_folder)
        splitter.addWidget(self.sidebar)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        root.addWidget(splitter, stretch=3)

        # ── Progress bar ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%  %v / %m")
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        # ── Console (bottom, collapsible) ──
        self.console = ConsoleWidget()
        self.console.setFixedHeight(160)
        root.addWidget(self.console, stretch=0)

    # ── Status bar ────────────────────────────────────────
    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_bar_label")
        sb.addWidget(self.status_label)

    # ── Instance management ───────────────────────────────
    def load_instances(self):
        self.instances.clear()
        self.grid.clear()
        if INSTANCES_DIR.exists():
            for d in sorted(INSTANCES_DIR.iterdir()):
                if d.is_dir():
                    ins = Instance(d.name, d)
                    self.instances.append(ins)
                    self.grid.add_instance(ins.name)
        count = len(self.instances)
        self.status_label.setText(
            f"{count} instance{'s' if count != 1 else ''} loaded"
        )

    def _on_instance_selected(self, name: str):
        self.current_instance = next((i for i in self.instances if i.name == name), None)
        self.sidebar.set_instance(name if self.current_instance else None)

    def new_instance(self, _=None):
        """Open the New Instance dialog, fetch versions, create instance."""
        try:
            manifest = self._get_manifest()
            versions = manifest.get("versions", [])
        except Exception:
            versions = []

        dlg = NewInstanceDialog(self, versions=versions)
        if dlg.exec():
            vals = dlg.get_values()
            name = vals["name"]
            # Check for duplicate names
            if any(i.name == name for i in self.instances):
                QMessageBox.warning(self, "Duplicate", f"An instance named '{name}' already exists.")
                return
            ins = Instance(name, Path(vals["path"]) if vals["path"] else None)
            if vals.get("version_id"):
                ins.data["version"] = vals["version_id"]
            ins.save()
            self.load_instances()
            # Select the new instance
            for i in range(self.grid.count()):
                if self.grid.item(i).text() == name:
                    self.grid.setCurrentRow(i)
                    self._on_instance_selected(name)
                    break
            self.console.append(f"Created instance '{name}' (v{vals['version_id']})", "info")

    def edit_instance(self, _=None):
        if not self.current_instance:
            QMessageBox.information(self, "No Selection", "Select an instance first.")
            return
        dlg = EditInstanceDialog(self, instance=self.current_instance)
        if dlg.exec():
            vals = dlg.get_values()
            old_name = self.current_instance.name
            self.current_instance.data.update({
                "ram_min": vals["ram_min"],
                "ram_max": vals["ram_max"],
                "jvm_args": vals["jvm_args"],
            })
            if vals["name"] and vals["name"] != old_name:
                # Rename: move folder
                new_path = INSTANCES_DIR / vals["name"]
                try:
                    self.current_instance.path.rename(new_path)
                    self.current_instance.name = vals["name"]
                    self.current_instance.path = new_path
                    self.current_instance.config_file = new_path / "instance.json"
                except Exception as e:
                    QMessageBox.critical(self, "Rename Failed", str(e))
                    return
            self.current_instance.save()
            self.load_instances()
            self.console.append(f"Updated instance '{self.current_instance.name}'", "info")

    def delete_instance(self, _=None):
        if not self.current_instance:
            QMessageBox.information(self, "No Selection", "Select an instance first.")
            return
        name = self.current_instance.name
        reply = QMessageBox.question(
            self, "Delete Instance",
            f"Are you sure you want to delete '{name}'?\n\nThis will remove all instance files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            import shutil
            try:
                shutil.rmtree(self.current_instance.path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            self.current_instance = None
            self.sidebar.set_instance(None)
            self.load_instances()
            self.console.append(f"Deleted instance '{name}'", "warn")

    def open_folder(self, _=None):
        if not self.current_instance:
            return
        self._open_dir(self.current_instance.path)

    def _view_mods(self):
        if not self.current_instance:
            return
        mods_dir = self.current_instance.path / "mods"
        mods_dir.mkdir(exist_ok=True)
        self._open_dir(mods_dir)

    def _view_worlds(self):
        if not self.current_instance:
            return
        saves_dir = self.current_instance.path / ".minecraft" / "saves"
        saves_dir.mkdir(parents=True, exist_ok=True)
        self._open_dir(saves_dir)

    # ── Launch ────────────────────────────────────────────
    def launch(self, name_or_bool=None):
        self._launch_inner(offline_override=False)

    def launch_offline(self):
        self._launch_inner(offline_override=True)

    def _launch_inner(self, offline_override=False):
        if not self.current_instance:
            QMessageBox.information(self, "No Selection", "Select an instance to launch.")
            return
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "A task is already running.")
            return

        ins = self.current_instance
        version_id = ins.data.get("version", "")
        if not version_id:
            QMessageBox.warning(self, "No Version", "This instance has no version set.\nEdit it first.")
            return

        self.console.append(f"Preparing to launch '{ins.name}' ({version_id})…", "info")
        self._set_busy(True)

        def task(progress_cb, msg_cb):
            from core.net import fetch_version_meta, fetch_manifest
            from core.java import get_java_version_required, install_java, find_java_executable
            from core.downloader import download_version_client, download_libraries

            msg_cb("Fetching version manifest…", "debug")
            manifest = fetch_manifest()
            version_entry = next((v for v in manifest["versions"] if v["id"] == version_id), None)
            if not version_entry:
                raise Exception(f"Version '{version_id}' not found in manifest.")

            msg_cb(f"Fetching version metadata for {version_id}…", "debug")
            meta = fetch_version_meta(version_id, version_entry["url"])

            msg_cb("Checking Java requirement…", "debug")
            java_ver = get_java_version_required(meta)
            java_path = install_java(java_ver, callback=progress_cb)
            java_exe  = find_java_executable(java_path)
            if not java_exe:
                raise Exception("Java executable not found after installation.")
            msg_cb(f"Java {java_ver} ready at {java_exe}", "info")

            msg_cb("Downloading game client…", "info")
            download_version_client(meta, callback=progress_cb)

            msg_cb("Downloading libraries…", "info")
            download_libraries(meta, callback=progress_cb)

            # Fabric
            fabric_loader = ins.data.get("fabric_loader", "")
            if fabric_loader:
                msg_cb(f"Installing Fabric {fabric_loader}…", "info")
                from core.fabric import install_fabric
                install_fabric(meta, fabric_loader)

            # Save java path
            ins.set_java(str(java_exe))

            # Build and run launch command
            ram_min   = int(ins.data.get("ram_min",   self.config.java.min_ram))
            ram_max   = int(ins.data.get("ram_max",   self.config.java.max_ram))
            jvm_extra = ins.data.get("jvm_args", "") or ""

            from core.config import LIBRARIES_DIR, ASSETS_DIR
            from core.arguments import build_launch_command

            client_jar  = LIBRARIES_DIR / "client" / version_id / f"{version_id}.jar"
            natives_dir = LIBRARIES_DIR / "natives" / version_id
            natives_dir.mkdir(parents=True, exist_ok=True)
            game_dir    = ins.path / ".minecraft"
            game_dir.mkdir(parents=True, exist_ok=True)

            # Determine auth
            config = self.config
            if offline_override or config.auth.offline_mode:
                auth_player  = config.auth.default_offline_name or "Player"
                auth_uuid    = "00000000-0000-0000-0000-000000000000"
                access_token = "0"
                user_type    = "offline"
            else:
                from core.auth import get_minecraft_token
                access_token = get_minecraft_token() or "0"
                auth_player  = config.auth.username or "Player"
                auth_uuid    = config.auth.uuid or "00000000-0000-0000-0000-000000000000"
                user_type    = "msa"

            # Collect library classpath
            import platform as _platform
            sep  = ";" if _platform.system() == "Windows" else ":"
            libs = []
            for lib in meta.get("libraries", []):
                if "downloads" in lib and "artifact" in lib["downloads"]:
                    p = LIBRARIES_DIR / lib["downloads"]["artifact"]["path"]
                    if p.exists():
                        libs.append(str(p))
                elif "name" in lib and "downloads" not in lib:
                    # Very old format — libs shipped locally (rd-*, classic)
                    parts = lib["name"].split(":")
                    if len(parts) == 3:
                        group, artifact_id, version = parts
                        rel = (group.replace(".", "/") + "/" +
                               artifact_id + "/" + version + "/" +
                               artifact_id + "-" + version + ".jar")
                        p = LIBRARIES_DIR / rel
                        if p.exists():
                            libs.append(str(p))
            if client_jar.exists():
                libs.append(str(client_jar))

            classpath = sep.join(libs)

            # Also add the local libraries folder for classic versions
            # that shipped native JARs without a proper manifest
            local_libs_dir = LIBRARIES_DIR
            if not libs:
                msg_cb("WARNING: classpath is empty — game may not launch", "warning")

            cmd = build_launch_command(
                meta,
                java_exe     = java_exe,
                classpath    = classpath,
                natives_dir  = natives_dir,
                game_dir     = game_dir,
                assets_dir   = ASSETS_DIR,
                auth_player  = auth_player,
                auth_uuid    = auth_uuid,
                access_token = access_token,
                user_type    = user_type,
                ram_min      = ram_min,
                ram_max      = ram_max,
                extra_jvm_args = jvm_extra,
            )

            # Force java.exe (console) not javaw.exe (windowless, no stdout)
            final_cmd = [str(x) for x in cmd]
            if final_cmd and final_cmd[0].lower().endswith("javaw.exe"):
                final_cmd[0] = final_cmd[0][:-1]  # javaw.exe → java.exe
                if not Path(final_cmd[0]).exists():
                    final_cmd[0] = final_cmd[0] + "w.exe"  # revert if java.exe missing

            msg_cb(f"Launching: {' '.join(final_cmd[:5])} …", "info")
            msg_cb(f"Natives dir: {natives_dir}", "debug")
            msg_cb(f"Classpath entries: {len(libs)}", "debug")

            import platform as _plat
            _popen_kwargs = dict(
                cwd=str(game_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # On Windows, suppress the console window for the java process
            # but keep stdout/stderr piped — CREATE_NO_WINDOW = 0x08000000
            if _plat.system() == "Windows":
                _popen_kwargs["creationflags"] = 0x08000000

            proc = subprocess.Popen(final_cmd, **_popen_kwargs)

            # Store the process handle so _on_task_done (main thread) can
            # pick it up and start the log thread safely.
            self._pending_proc = proc

        self._worker = WorkerThread(task)
        self._worker.progress.connect(lambda v: self.progress_bar.setValue(int(v * 100)))
        self._worker.message.connect(lambda msg, lvl: self.console.append(msg, lvl))
        self._worker.finished.connect(self._on_task_done)
        self._worker.start()

    # ── Settings ──────────────────────────────────────────
    def import_patch(self, _=None):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from core.updates import UpdateManager
        from core.config import LAUNCHER_DIR
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Patch File", "",
            "Update Patch Files (*.upt);;All Files (*)"
        )
        if not path:
            return
        from pathlib import Path as _Path
        patch_path = _Path(path)
        mgr = UpdateManager(LAUNCHER_DIR, self.config.update_server)
        mgr.import_patch_file(patch_path)
        dest = mgr.updates_dir / patch_path.name
        if mgr.apply_patch(dest):
            QMessageBox.information(self, "Patch Applied",
                f"Patch '{patch_path.name}' applied.\nRestart for changes to take effect.")
        else:
            QMessageBox.critical(self, "Patch Failed",
                f"Failed to apply '{patch_path.name}'. Check the console.")

    def open_settings(self, _=None):
        dlg = SettingsDialog(self, config=self.config)
        dlg.login_btn.clicked.connect(self._ms_login)
        dlg.offline_btn.clicked.connect(lambda: self._set_offline(dlg))
        if dlg.exec():
            vals = dlg.get_values()
            # Update LauncherConfig dataclass fields from dialog values
            from core.config import JavaConfig, AuthConfig, ThemeConfig
            j = vals.get('java', {})
            self.config.java.java_path = j.get('java_path', self.config.java.java_path)
            self.config.java.min_ram = j.get('min_ram', self.config.java.min_ram)
            self.config.java.max_ram = j.get('max_ram', self.config.java.max_ram)
            self.config.java.extra_jvm_args = j.get('extra_jvm_args', self.config.java.extra_jvm_args)
            a = vals.get('auth', {})
            self.config.auth.default_offline_name = a.get('default_offline_name', self.config.auth.default_offline_name)
            self.config.auth.offline_mode = a.get('offline_mode', self.config.auth.offline_mode)
            t = vals.get('theme', {})
            self.config.theme.name = t.get('name', self.config.theme.name)
            self.config.theme.custom_icon = t.get('custom_icon', self.config.theme.custom_icon)
            self.config.api_type = vals.get('api_type', self.config.api_type)
            self.config.custom_api_url = vals.get('custom_api_url', self.config.custom_api_url)
            self.config.update_server = vals.get('update_server', self.config.update_server)
            self.config.logging_level = vals.get('logging_level', self.config.logging_level)
            self.config.auto_check_updates = vals.get('auto_check_updates', self.config.auto_check_updates)
            self.config.keep_launcher_open = vals.get('keep_launcher_open', self.config.keep_launcher_open)
            self.config.show_console = vals.get('show_console', self.config.show_console)
            save_config(self.config)
            QMessageBox.information(self, "Saved", "Settings saved.")

    def _ms_login(self):
        try:
            from core.auth import microsoft_login
            username = microsoft_login()
            self.config = load_config()
            QMessageBox.information(self, "Logged In", f"Signed in as {username}")
        except Exception as e:
            QMessageBox.critical(self, "Login Error", str(e))

    def _set_offline(self, dlg):
        name = dlg.username_edit.text().strip()
        if not name:
            QMessageBox.warning(dlg, "Username Required", "Enter a username for offline play.")
            return
        self.config.auth.offline_mode = True
        self.config.auth.default_offline_name = name
        self.config.auth.username = name
        save_config(self.config)
        QMessageBox.information(dlg, "Offline Mode", f"Will play offline as '{name}'.")

    # ── Helpers ───────────────────────────────────────────
    def _get_manifest(self):
        if self._version_manifest is None:
            self._version_manifest = fetch_manifest()
        return self._version_manifest

    def _set_busy(self, busy: bool):
        self.progress_bar.setVisible(busy)
        if busy:
            self.progress_bar.setValue(0)

    def _on_task_done(self, success: bool, err: str):
        self._set_busy(False)
        if success:
            self.console.append("Done!", "info")
            self.status_label.setText("Ready")
            # Start game log thread on the main thread (safe for Qt signals)
            proc = self._pending_proc
            self._pending_proc = None
            if proc is not None:
                log_thread = GameLogThread(proc)
                log_thread.log_line.connect(
                    lambda msg, lvl: self.console.append(f"[GAME] {msg}", lvl))
                log_thread.game_exited.connect(
                    lambda rc: self.console.append(
                        f"[GAME] Process exited (code {rc})",
                        "info" if rc == 0 else "warning"))
                self._game_log_thread = log_thread
                self._game_proc = proc
                log_thread.start()
        else:
            self._pending_proc = None
            self.console.append(f"ERROR:\n{err}", "error")
            self.status_label.setText("Error — see console")
            QMessageBox.critical(self, "Error", err[:600])

    def _open_dir(self, path: Path):
        import platform, subprocess
        path.mkdir(parents=True, exist_ok=True)
        s = platform.system()
        if s == "Windows":
            os.startfile(str(path))
        elif s == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _folders_menu(self, _=None):
        menu = QMenu(self)
        from core.config import LAUNCHER_DIR
        menu.addAction("Instances Folder",   lambda: self._open_dir(INSTANCES_DIR))
        menu.addAction("Launcher Data",      lambda: self._open_dir(LAUNCHER_DIR))
        if self.current_instance:
            menu.addSeparator()
            menu.addAction("Instance Folder", self.open_folder)
        # show near toolbar
        tb = self.findChild(QToolBar)
        if tb:
            menu.exec(tb.mapToGlobal(tb.rect().bottomLeft()))
        else:
            menu.exec(self.mapToGlobal(self.rect().center()))

    # ── Window close ──────────────────────────────────────────
    def closeEvent(self, event):
        """Ensure the process exits when the window is closed."""
        event.accept()
        # Save config before exiting
        try:
            from core.config import save_config
            self.config.window_geometry = {
                'x': self.geometry().x(), 'y': self.geometry().y(),
                'width': self.geometry().width(), 'height': self.geometry().height(),
            }
            save_config(self.config)
        except Exception:
            pass
        # Kill the Qt event loop — this also terminates daemon drain threads
        import sys
        sys.exit(0)

    def _about(self):
        QMessageBox.about(self, "About Luma Launcher",
            "<b>Luma Launcher</b><br>"
            "Version 2.0<br><br>"
            "A custom Minecraft instance manager.")
