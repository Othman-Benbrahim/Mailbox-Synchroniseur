"""Readable colours whatever the system theme.

Qt follows the platform palette, so on a system in dark mode every widget the
stylesheet does not cover explicitly gets a dark background while the stylesheet
keeps a dark text colour: unreadable. The application therefore states its own
complete light palette instead of inheriting half of one.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

INK = "#192d42"          # text
MUTED = "#52687c"
PAPER = "#f3f6fa"        # window background
SURFACE = "#ffffff"      # inputs, cards, lists
BORDER = "#b8c8d9"
ACCENT = "#146f66"
DISABLED = "#7b8898"


def palette() -> QPalette:
    colours = QPalette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive,
                  QPalette.ColorGroup.Disabled):
        def put(role, value):
            colours.setColor(group, role, QColor(value))
        disabled = group == QPalette.ColorGroup.Disabled
        put(QPalette.ColorRole.Window, PAPER)
        put(QPalette.ColorRole.WindowText, DISABLED if disabled else INK)
        put(QPalette.ColorRole.Base, "#edf0f4" if disabled else SURFACE)
        put(QPalette.ColorRole.AlternateBase, PAPER)
        put(QPalette.ColorRole.Text, DISABLED if disabled else INK)
        put(QPalette.ColorRole.Button, SURFACE)
        put(QPalette.ColorRole.ButtonText, DISABLED if disabled else INK)
        put(QPalette.ColorRole.ToolTipBase, SURFACE)
        put(QPalette.ColorRole.ToolTipText, INK)
        put(QPalette.ColorRole.PlaceholderText, MUTED)
        put(QPalette.ColorRole.Highlight, "#d7e2ea" if disabled else ACCENT)
        put(QPalette.ColorRole.HighlightedText, INK if disabled else SURFACE)
        put(QPalette.ColorRole.Link, ACCENT)
        put(QPalette.ColorRole.BrightText, "#b3261e")
    return colours


def apply(app):
    """Fusion draws identically on every platform; the native styles partly ignore
    the palette on Windows, which is exactly where the dark-mode problem appears."""
    app.setStyle("Fusion")
    app.setPalette(palette())
    return app
