"""Warna dan stylesheet (QSS)."""

STATE_COLORS = {
    None: "#ffffff", "work": "#ff8a80", "break": "#7ee08a",
    "off": "#9a9a9a", "paused": "#f5c542", "done": "#ff5c5c",
}

FLOATING_QSS = """
#phase { color: #cccccc; font-size: 12px; }
QLineEdit { background: #2b2c33; color: #eeeeee; border: 1px solid #444550;
            border-radius: 4px; padding: 2px 4px; font-size: 13px; }
QPushButton { background: #33343d; color: #eeeeee; border: none; border-radius: 4px;
              padding: 2px 8px; font-size: 13px; }
QPushButton:hover { background: #42434e; }
QPushButton[active="true"] { background: #c0392b; color: white; }
QToolTip { background: #2b2c33; color: #eeeeee; border: 1px solid #444550; }
"""

SETTINGS_QSS = """
QDialog, QWidget#page { background-color: #1c1d23; color: #f0f0f0; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #262731; color: #cfd0d8; padding: 8px 16px; margin-right: 2px;
               border-top-left-radius: 8px; border-top-right-radius: 8px; }
QTabBar::tab:selected { background: #33343f; color: #ffffff; }
QLabel { color: #f0f0f0; }
QLabel#section { color: #ff8a80; font-weight: bold; font-size: 13px; margin-top: 8px; }
QLabel#hint { color: #8a8d99; font-size: 11px; }
QFrame#card { background-color: #262731; border: 1px solid #33343f; border-radius: 10px; }
QLineEdit, QSpinBox, QComboBox { background: #14151a; color: #f0f0f0; border: 1px solid #33343f;
                                 border-radius: 5px; padding: 3px 6px; }
QLineEdit[error="true"] { border-color: #ff5c5c; color: #ff5c5c; }
QLineEdit:disabled, QSpinBox:disabled { color: #666874; }
QPushButton { background: #33343f; color: #f0f0f0; border: none; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background: #42434e; }
QPushButton#primary { background: #c0392b; color: white; }
QPushButton#primary:hover { background: #d44637; }
QSlider::groove:horizontal { height: 4px; background: #33343f; border-radius: 2px; }
QSlider::handle:horizontal { background: #ff8a80; width: 14px; margin: -6px 0; border-radius: 7px; }
QFrame#preview { background-color: #14151a; border-radius: 12px; }
"""


def polish(widget):
    """Paksa Qt menerapkan ulang QSS setelah properti dinamis berubah."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
