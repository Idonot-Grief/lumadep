"""
Icon helpers — generate simple colored block icons for instances
(MultiMC uses icon packs; we generate them programmatically for portability).
"""
import hashlib
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QFont, QIcon, QLinearGradient
from PyQt6.QtCore import Qt, QRect, QPoint

# A palette of colors for auto-assigning instance icons
_PALETTE = [
    ("#2ecc71", "#27ae60"),
    ("#3498db", "#2980b9"),
    ("#9b59b6", "#8e44ad"),
    ("#e67e22", "#d35400"),
    ("#e74c3c", "#c0392b"),
    ("#1abc9c", "#16a085"),
    ("#f39c12", "#e67e22"),
    ("#34495e", "#2c3e50"),
]

def _color_for_name(name: str):
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(_PALETTE)
    return _PALETTE[idx]

def make_instance_icon(name: str, size: int = 48) -> QPixmap:
    """Create a colored block icon with the first letter of the instance name."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    top_color, bot_color = _color_for_name(name)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, QColor(top_color))
    grad.setColorAt(1, QColor(bot_color))

    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(QColor(bot_color).darker(120), 1.5))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 6, 6)

    # Shine overlay
    shine = QLinearGradient(0, 2, 0, size // 2)
    shine.setColorAt(0, QColor(255, 255, 255, 60))
    shine.setColorAt(1, QColor(255, 255, 255, 0))
    painter.setBrush(QBrush(shine))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, size - 4, (size - 4) // 2, 6, 6)

    # Letter
    font = QFont("Arial", int(size * 0.40), QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255, 220))
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, name[0].upper())

    painter.end()
    return pm

def instance_qicon(name: str, size: int = 48) -> QIcon:
    return QIcon(make_instance_icon(name, size))
