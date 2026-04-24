"""
Enhanced logging system that follows Minecraft game log format.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

class MinecraftLogFormatter(logging.Formatter):
    """Formatter that mimics Minecraft's log format: [HH:MM:SS] [ThreadName/LEVEL]: Message"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime('%H:%M:%S')
        thread_name = threading.current_thread().name
        level = record.levelname
        
        # Color output for console
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(level, '')
            return f"{color}[{timestamp}] [{thread_name}/{level}]: {record.getMessage()}{self.RESET}"
        else:
            return f"[{timestamp}] [{thread_name}/{level}]: {record.getMessage()}"


class LauncherLogger:
    """Unified logger for the launcher and game."""
    
    _instance: Optional['LauncherLogger'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger('MinecraftLauncher')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(MinecraftLogFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler
        log_dir = Path.home() / '.minecraft_launcher' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"launcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(MinecraftLogFormatter())
        self.logger.addHandler(file_handler)
        
        self.log_file = log_file
        self.callbacks = []  # For GUI integration
    
    def add_callback(self, callback):
        """Add callback for log messages (for GUI display)."""
        self.callbacks.append(callback)
    
    def _emit_callback(self, level: str, message: str):
        """Emit message to all registered callbacks."""
        for callback in self.callbacks:
            try:
                callback(message, level.lower())
            except Exception:
                pass
    
    def debug(self, msg: str):
        self.logger.debug(msg)
        self._emit_callback('DEBUG', msg)
    
    def info(self, msg: str):
        self.logger.info(msg)
        self._emit_callback('INFO', msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
        self._emit_callback('WARNING', msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
        self._emit_callback('ERROR', msg)
    
    def critical(self, msg: str):
        self.logger.critical(msg)
        self._emit_callback('CRITICAL', msg)


# Global logger instance
launcher_logger = LauncherLogger()
