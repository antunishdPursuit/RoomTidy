"""Check the bundled font and primary text contrasts independently of UI layout."""
import os
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from ui_theme import FONT_PATH, TOKENS, apply_theme


def _luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4 for channel in channels]
    return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))


def _contrast(first, second):
    bright, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (bright + .05) / (dark + .05)


def test_primary_and_body_text_contrast():
    for foreground, background in (
        ('surface', 'primary'), ('surface', 'primary_hover'), ('surface', 'primary_pressed'),
        ('text', 'surface'), ('text', 'background'), ('secondary', 'surface'),
        ('secondary', 'background'), ('disabled_text', 'disabled_surface'),
        ('warning', 'warning_surface'), ('error', 'error_surface'), ('success', 'success_surface'),
        ('primary_pressed', 'periwinkle'),
    ):
        assert _contrast(TOKENS[foreground], TOKENS[background]) >= 4.5, (foreground, background)


def test_bundled_font_loads_and_theme_applies():
    app = QApplication.instance() or QApplication([])
    assert FONT_PATH.is_file()
    family = apply_theme(app)
    assert 'Nunito Sans' in family
    assert family in QFontDatabase.families()
    assert app.font().family() == family
    assert TOKENS['primary'] in app.styleSheet()
    assert 'QPushButton:focus' in app.styleSheet()
    assert FONT_PATH.with_name('OFL.txt').is_file()


def test_original_illustration_is_valid_svg():
    path = Path(__file__).resolve().parents[1] / 'assets' / 'room-illustration.svg'
    root = ET.parse(path).getroot()
    assert root.tag == '{http://www.w3.org/2000/svg}svg'
    assert root.attrib['viewBox'] == '0 0 420 280'
