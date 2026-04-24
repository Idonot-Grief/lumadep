"""
Enhanced Minecraft Launcher v2.0
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_QPA_PLATFORM_THEME"] = "qt5ct"

from core.config import load_config, save_config, migrate_old_config, LAUNCHER_DIR
from core.logger import launcher_logger
from core.updates import UpdateManager
from gui.theme import apply_theme
from gui.main_window import MainWindow


class UpdateCheckThread(QThread):
    updates_available = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, update_manager: UpdateManager):
        super().__init__()
        self.update_manager = update_manager

    def run(self):
        try:
            available = self.update_manager.fetch_updates_list()
            missing = self.update_manager.get_missing_updates(available)
            if missing:
                self.updates_available.emit(missing)
        except Exception as e:
            self.error.emit(str(e))


def main():
    launcher_logger.info("=" * 60)
    launcher_logger.info("Luma Launcher v2.0 Starting")
    launcher_logger.info("=" * 60)

    migrate_old_config()

    # ONE config object — passed everywhere, never re-loaded
    config = load_config()
    launcher_logger.info(f"Loaded config from {LAUNCHER_DIR}")
    launcher_logger.info(f"Theme: {config.theme.name}")
    launcher_logger.info(f"API: {config.api_type}")
    launcher_logger.info(f"Update Server: {config.update_server}")

    app = QApplication(sys.argv)
    app.setApplicationName("Luma Launcher")
    app.setApplicationVersion(config.version)
    app.setQuitOnLastWindowClosed(True)  # ensure process exits when window closes

    launcher_logger.info("Applying theme...")
    apply_theme(app, config.theme)

    launcher_logger.info("Creating main window...")
    window = MainWindow(config=config)  # pass the single config object in

    if config.window_geometry:
        geom = config.window_geometry
        window.setGeometry(geom.get('x', 100), geom.get('y', 100),
                           geom.get('width', 1000), geom.get('height', 660))

    if config.theme.custom_icon and Path(config.theme.custom_icon).exists():
        try:
            window.setWindowIcon(QIcon(config.theme.custom_icon))
        except Exception as e:
            launcher_logger.warning(f"Failed to load custom icon: {e}")

    if config.auto_check_updates:
        launcher_logger.info("Checking for updates...")
        update_manager = UpdateManager(LAUNCHER_DIR, config.update_server)
        check_thread = UpdateCheckThread(update_manager)

        def _show_update_dialog(updates):
            launcher_logger.info(f"Found {len(updates)} update(s) — showing dialog")
            from gui.dialogs import UpdateDialog
            dlg = UpdateDialog(window, updates=updates, update_manager=update_manager)
            dlg.exec()

        check_thread.updates_available.connect(_show_update_dialog)
        check_thread.error.connect(
            lambda e: launcher_logger.warning(f"Update check failed: {e}"))
        check_thread.start()

    window.show()
    launcher_logger.info("Launcher window displayed")

    def save_state():
        # Always save window.config — it has the latest settings from dialogs
        window.config.window_geometry = {
            'x': window.geometry().x(),
            'y': window.geometry().y(),
            'width': window.geometry().width(),
            'height': window.geometry().height(),
        }
        save_config(window.config)
        launcher_logger.info("Window state saved")

    app.aboutToQuit.connect(save_state)

    launcher_logger.info("Entering main event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        launcher_logger.critical(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)