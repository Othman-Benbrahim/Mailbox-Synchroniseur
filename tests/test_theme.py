"""The interface must stay readable on a system in dark mode.

Regression: with the platform palette dark and only part of the widgets covered by
the stylesheet, the application showed dark text on a dark background and the user
could not read what was about to be copied.
"""
import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from mailbox_sync import theme
from mailbox_sync.ui import STYLE, Window

DARK = "#1f1f1f"


def luminance(colour: QColor) -> float:
    """WCAG relative luminance: sRGB channels must be linearised first."""
    def channel(value):
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    return (0.2126 * channel(colour.redF()) + 0.7152 * channel(colour.greenF())
            + 0.0722 * channel(colour.blueF()))


def contrast(one: QColor, two: QColor) -> float:
    first, second = sorted((luminance(one) + 0.05, luminance(two) + 0.05))
    return second / first


@pytest.fixture
def dark_system(app):
    """A dark platform palette, as Windows or GNOME in dark mode provides."""
    previous = QApplication.palette()
    dark = QPalette()
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button,
                 QPalette.ColorRole.AlternateBase):
        dark.setColor(role, QColor(DARK))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        dark.setColor(role, QColor("#f0f0f0"))
    app.setPalette(dark)
    yield app
    app.setPalette(previous)


def test_a_dark_system_palette_is_replaced(dark_system):
    assert dark_system.palette().color(QPalette.ColorRole.Window).name() == DARK
    theme.apply(dark_system)
    palette = dark_system.palette()
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
        assert luminance(palette.color(role)) > 0.7, role
    for pair in ((QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
                 (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
                 (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button)):
        assert contrast(palette.color(pair[0]), palette.color(pair[1])) >= 7


def test_disabled_text_stays_legible():
    palette = theme.palette()
    disabled = QPalette.ColorGroup.Disabled
    assert contrast(palette.color(disabled, QPalette.ColorRole.Text),
                    palette.color(disabled, QPalette.ColorRole.Base)) >= 3


def test_selected_rows_are_legible():
    palette = theme.palette()
    assert contrast(palette.color(QPalette.ColorRole.HighlightedText),
                    palette.color(QPalette.ColorRole.Highlight)) >= 4.5


def test_window_keeps_light_colours_under_a_dark_system(dark_system):
    theme.apply(dark_system)
    window = Window()
    window.show()
    palette = window.palette()
    assert luminance(palette.color(QPalette.ColorRole.Window)) > 0.7
    assert luminance(palette.color(window.source.host.backgroundRole())) > 0.7
    window.close()


@pytest.mark.parametrize("widget", ["QTabBar::tab", "QTableWidget", "QListWidget", "QHeaderView::section",
                                    "QComboBox QAbstractItemView", "QCalendarWidget QWidget",
                                    "QPushButton", "QLineEdit", "QMessageBox", "QToolTip"])
def test_every_widget_family_states_its_own_colours(widget):
    """A widget left out of the stylesheet inherits the platform background."""
    block = STYLE[STYLE.index(widget):]
    block = block[:block.index("}")]
    assert "color:" in block and "background" in block, widget
