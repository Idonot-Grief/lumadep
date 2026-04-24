"""
Enhanced console widget with proper Minecraft log display and copy functionality.
"""
from PyQt6.QtWidgets import QTextEdit, QMenu, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from datetime import datetime
import pyperclip


class ConsoleWidget(QTextEdit):
    """Enhanced console widget for game and launcher logs."""
    
    # Log level colors
    LOG_COLORS = {
        'debug': QColor(100, 200, 255),      # Light Blue
        'info': QColor(100, 255, 100),       # Green
        'warning': QColor(255, 200, 50),     # Orange
        'error': QColor(255, 100, 100),      # Red
        'critical': QColor(255, 50, 150),    # Pink
        'game': QColor(150, 150, 150),       # Gray
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
                border: none;
                padding: 5px;
            }
        """)
        
        # Setup font
        font = QFont("Courier New", 9)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.setFont(font)
        
        self.max_lines = 1000  # Limit log size
        self.line_count = 0
    
    def append(self, message: str, level: str = "info"):
        """
        Append a message with color coding.
        
        Args:
            message: Log message
            level: Log level (debug, info, warning, error, critical, game)
        """
        # Format: [HH:MM:SS] [Level]: Message
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] [{level.upper()}]: {message}"
        
        # Setup text format
        fmt = QTextCharFormat()
        color = self.LOG_COLORS.get(level, self.LOG_COLORS['info'])
        fmt.setForeground(color)
        fmt.setFont(self.font())
        
        # Move cursor to end and insert text
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(formatted_message + "\n", fmt)
        
        # Keep scrollbar at bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        
        # Limit log size
        self.line_count += 1
        if self.line_count > self.max_lines:
            # Remove oldest lines
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            self.line_count -= 1
    
    def clear_log(self):
        """Clear all log messages."""
        self.clear()
        self.line_count = 0
    
    def copy_selected(self):
        """Copy selected text to clipboard."""
        try:
            pyperclip.copy(self.textCursor().selectedText())
        except Exception:
            # Fallback to Qt clipboard
            QApplication.clipboard().setText(self.textCursor().selectedText())
    
    def copy_all(self):
        """Copy all log text to clipboard."""
        try:
            pyperclip.copy(self.toPlainText())
        except Exception:
            QApplication.clipboard().setText(self.toPlainText())
    
    def contextMenuEvent(self, event):
        """Custom context menu with copy options."""
        menu = QMenu(self)
        
        if self.textCursor().hasSelection():
            menu.addAction("Copy Selected", self.copy_selected)
            menu.addSeparator()
        
        menu.addAction("Copy All", self.copy_all)
        menu.addAction("Clear", self.clear_log)
        menu.addSeparator()
        menu.addAction("Select All", self.selectAll)
        
        menu.exec(event.globalPos())


class GameLogCapture:
    """Capture and parse Minecraft game log output."""
    
    @staticmethod
    def parse_game_log(line: str) -> tuple[str, str]:
        """
        Parse Minecraft game log line.
        Format: [HH:MM:SS] [Thread/Level]: Message
        
        Returns: (level, message)
        """
        line = line.strip()
        
        # Try to extract level from Minecraft log format
        if '[' in line and ']' in line:
            # Find the last bracket pair that contains level info
            parts = line.split(']')
            if len(parts) >= 2:
                last_bracket = parts[-2].split('[')[-1]
                if '/' in last_bracket:
                    level = last_bracket.split('/')[-1].lower()
                    message = ']'.join(parts[2:]).strip() if len(parts) > 2 else parts[-1].strip()
                    
                    # Map Minecraft levels to our levels
                    level_map = {
                        'debug': 'debug',
                        'info': 'info',
                        'warn': 'warning',
                        'error': 'error',
                        'fatal': 'critical',
                    }
                    return (level_map.get(level, 'game'), message)
        
        return ('game', line)
