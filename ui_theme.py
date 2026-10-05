"""Shared visual tokens and a local, accessible Qt application theme."""
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

TOKENS = {
    'primary': '#4565C6', 'primary_hover': '#3654AD', 'primary_pressed': '#2D4694',
    'periwinkle': '#E8EDFF', 'background': '#F7F8FC', 'surface': '#FFFFFF',
    'text': '#202944', 'secondary': '#5C667D', 'border': '#CBD3E3',
    'focus': '#30489B', 'hover': '#EFF2FA', 'disabled_surface': '#EFF2F8',
    'disabled_text': '#5C667D', 'success': '#23634C', 'success_surface': '#E9F5EF',
    'warning': '#825218', 'warning_surface': '#FFF3DB',
    'error': '#A83842', 'error_hover': '#8D2834', 'error_surface': '#FCEBED',
    'space_xs': 4, 'space_sm': 8, 'space_md': 12, 'space_lg': 16,
    'space_xl': 24, 'space_xxl': 32, 'radius_control': 8, 'radius_card': 12,
    'font_body': 14, 'font_caption': 12, 'font_heading': 20, 'font_title': 28,
}

FONT_PATH = Path(__file__).resolve().parent / 'assets' / 'fonts' / 'NunitoSans-Variable.ttf'


def apply_theme(app) -> str:
    """Load the bundled font, set the shared QSS, and return its active family."""
    font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    family = families[0] if families else 'Segoe UI'
    font = QFont(family)
    font.setPixelSize(TOKENS['font_body'])
    app.setFont(font)
    t = TOKENS
    app.setStyleSheet(f'''
        QWidget {{ color: {t['text']}; font-family: "{family}"; font-size: {t['font_body']}px; }}
        QMainWindow, QDialog {{ background: {t['background']}; }}
        QWidget#page, QWidget#pageContent {{ background: {t['background']}; }}
        QWidget#sidebar {{ background: {t['surface']}; border-right: 1px solid {t['border']}; }}
        QWidget#header {{ background: {t['background']}; }}
        QWidget#card {{ background: {t['surface']}; border: 1px solid {t['border']};
            border-radius: {t['radius_card']}px; }}
        QLabel {{ background: transparent; border: none; }}
        QLabel#title {{ font-size: {t['font_title']}px; font-weight: 600; }}
        QLabel#subtitle {{ font-size: {t['font_heading']}px; font-weight: 600; }}
        QLabel#muted, QLabel[role="muted"] {{ color: {t['secondary']}; }}
        QLabel[role="caption"] {{ color: {t['secondary']}; font-size: {t['font_caption']}px; }}
        QLabel#status {{ color: {t['primary_pressed']}; background: {t['periwinkle']};
            border-radius: {t['radius_control']}px; padding: {t['space_sm']}px {t['space_md']}px; }}
        QLabel#status[state="success"], QLabel[role="success"] {{ color: {t['success']}; background: {t['success_surface']}; }}
        QLabel#status[state="warning"], QLabel[role="warning"] {{ color: {t['warning']}; background: {t['warning_surface']}; }}
        QLabel#status[state="error"], QLabel[role="error"] {{ color: {t['error']}; background: {t['error_surface']}; }}
        QPushButton {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']};
            border-radius: {t['radius_control']}px; padding: {t['space_sm']}px {t['space_lg']}px;
            min-height: {t['space_xl']}px; font-weight: 600; }}
        QPushButton:hover {{ background: {t['hover']}; border-color: {t['primary']}; }}
        QPushButton:pressed {{ background: {t['periwinkle']}; }}
        QPushButton[role="primary"] {{ background: {t['primary']}; color: {t['surface']}; border-color: {t['primary']}; }}
        QPushButton[role="primary"]:hover {{ background: {t['primary_hover']}; border-color: {t['primary_hover']}; }}
        QPushButton[role="primary"]:pressed {{ background: {t['primary_pressed']}; }}
        QPushButton[role="nav"] {{ text-align: left; padding: {t['space_md']}px {t['space_lg']}px; border: 1px solid transparent; }}
        QPushButton[role="nav"]:checked {{ color: {t['primary_pressed']}; background: {t['periwinkle']}; font-weight: 600; }}
        QPushButton[role="danger"] {{ color: {t['error']}; border-color: {t['error']}; }}
        QPushButton[role="danger"]:hover {{ color: {t['error_hover']}; background: {t['error_surface']}; }}
        QPushButton:focus {{ border: 2px solid {t['focus']}; padding: {t['space_sm'] - 1}px {t['space_lg'] - 1}px; }}
        QPushButton[role="nav"]:focus {{ border: 2px solid {t['focus']}; padding: {t['space_md']-1}px {t['space_lg']-1}px; }}
        QPushButton:disabled {{ color: {t['disabled_text']}; background: {t['disabled_surface']}; border-color: {t['border']}; }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{ background: {t['surface']};
            border: 1px solid {t['border']}; border-radius: {t['radius_control']}px;
            padding: {t['space_sm']}px; selection-background-color: {t['primary']}; selection-color: {t['surface']}; }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 2px solid {t['focus']}; }}
        QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ background: {t['disabled_surface']}; color: {t['disabled_text']}; }}
        QComboBox QAbstractItemView {{ background: {t['surface']}; selection-background-color: {t['periwinkle']}; selection-color: {t['text']}; }}
        QListWidget {{ background: {t['surface']}; border: 1px solid {t['border']};
            border-radius: {t['radius_card']}px; padding: {t['space_sm']}px; outline: none; }}
        QListWidget::item {{ min-height: {t['space_xxl'] * 2}px; padding: {t['space_sm']}px {t['space_md']}px;
            border: 1px solid transparent; border-radius: {t['radius_control']}px; }}
        QListWidget::item:hover {{ background: {t['hover']}; }}
        QListWidget::item:selected {{ color: {t['text']}; background: {t['periwinkle']}; border-color: {t['primary']}; }}
        QListWidget::item:focus {{ border: 2px solid {t['focus']}; }}
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ background: {t['background']}; width: {t['space_md']}px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {t['secondary']}; min-height: {t['space_xxl']}px; border-radius: {t['radius_card'] // 2}px; }}
        QScrollBar::handle:vertical:hover {{ background: {t['primary']}; }}
        QScrollBar:horizontal {{ background: {t['background']}; height: {t['space_md']}px; margin: 0; }}
        QScrollBar::handle:horizontal {{ background: {t['secondary']}; min-width: {t['space_xxl']}px; border-radius: {t['radius_card'] // 2}px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QCheckBox {{ spacing: {t['space_sm']}px; }}
        QCheckBox:focus {{ color: {t['focus']}; }}
        QGroupBox {{ border: 1px solid {t['border']}; border-radius: {t['radius_card']}px;
            margin-top: {t['space_lg']}px; padding: {t['space_lg']}px; font-weight: 600; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: {t['space_lg']}px; padding: 0 {t['space_xs']}px; }}
        QLabel#cameraPreview {{ background: {t['text']}; color: {t['surface']}; border-radius: {t['radius_control']}px; }}
        QProgressBar {{ background: {t['periwinkle']}; border: none; border-radius: {t['space_xs']}px; max-height: {t['space_sm']}px; }}
        QProgressBar::chunk {{ background: {t['primary']}; border-radius: {t['space_xs']}px; }}
        QRubberBand {{ border: 2px solid {t['primary']}; background: {t['periwinkle']}; }}
        QToolTip {{ background: {t['text']}; color: {t['surface']}; border: none; padding: {t['space_sm']}px; }}
    ''')
    return family
