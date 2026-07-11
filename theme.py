ACCENT = "#00ff88"
ACCENT2 = "#818cf8"
ACCENT3 = "#f472b6"
ACCENT_DIM = "#00cc6a"
ACCENT_GLOW = "rgba(0,255,136,0.08)"
BG_DEEP = "#0a0e14"
BG_CARD = "#111827"
BG_SIDEBAR = "#0d1219"
BG_SURFACE = "#1a1f35"
TEXT_MAIN = "#e2e8f0"
TEXT_DIM = "#64748b"
TEXT_MUTED = "#475569"
SUCCESS = "#00ff88"
DANGER = "#ff4444"
WARNING = "#fbbf24"
INFO = "#818cf8"
PURPLE = "#a78bfa"
CYAN = "#22d3ee"
PINK = "#f472b6"
BORDER = "rgba(0,255,136,0.1)"
BORDER_LIGHT = "rgba(0,255,136,0.05)"
BORDER_SUBTLE = "rgba(255,255,255,0.03)"

VERSION = "1.0.0"

TABLE_QSS = """
QTableWidget {
    background: rgba(10,14,20,240);
    border: 1px solid rgba(0,255,136,0.05);
    border-radius: 12px;
    color: #e2e8f0;
    font-size: 12px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    gridline-color: transparent;
    selection-background-color: rgba(0,255,136,0.08);
    outline: none;
}
QTableWidget::item {
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid rgba(255,255,255,0.015);
    background: transparent;
}
QTableWidget::item:selected {
    background: rgba(0,255,136,0.08);
    color: #00ff88;
}
QTableWidget::item:hover {
    background: rgba(0,255,136,0.02);
}
QTableWidget::item:alternate {
    background: rgba(255,255,255,0.008);
}
QHeaderView::section {
    background: rgba(17,24,39,255);
    color: #00ff88;
    border: none;
    border-bottom: 1px solid rgba(0,255,136,0.08);
    border-right: 1px solid rgba(255,255,255,0.015);
    padding: 10px 12px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-family: 'Cascadia Code', monospace;
}
QHeaderView::section:last { border-right: none; }
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(0,255,136,0.1);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0,255,136,0.2);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""

QSS = """
/* ═══════════════════════════════════════════════════════════════════
   KUS Pro v1.0.0 — Modern Dark Theme
   ═══════════════════════════════════════════════════════════════════ */

/* ── Global ── */
QWidget {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    color: #f0f4f8;
    background: transparent;
}
QMainWindow { background: #0a0e14; }

/* ── Sidebar ── */
#sidebar {
    background: rgba(13,18,25,248);
    border-right: 1px solid rgba(0,255,136,0.04);
    min-width: 220px;
    max-width: 220px;
}
#app_title {
    font-size: 26px;
    font-weight: 900;
    color: #00ff88;
    letter-spacing: 5px;
    padding: 24px 18px 2px 18px;
    font-family: 'Cascadia Code', monospace;
}
#app_sub {
    font-size: 9px;
    color: #475569;
    letter-spacing: 3px;
    padding: 0 18px 20px 18px;
    font-weight: 600;
    font-family: 'Cascadia Code', monospace;
}
#admin_badge {
    font-size: 10px;
    color: #00ff88;
    padding: 8px 18px 14px 18px;
    font-weight: 600;
    font-family: 'Cascadia Code', monospace;
}

/* ── Navigation ── */
#nav_idle {
    text-align: left;
    padding: 12px 18px;
    border: none;
    background: transparent;
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
    border-radius: 10px;
    margin: 3px 8px;
}
#nav_idle:hover {
    background: rgba(0,255,136,0.05);
    color: #94a3b8;
    border-left: 3px solid rgba(0,255,136,0.15);
}
#nav_active {
    text-align: left;
    padding: 12px 18px;
    border: none;
    background: rgba(0,255,136,0.08);
    color: #00ff88;
    font-size: 13px;
    font-weight: 700;
    border-radius: 10px;
    margin: 3px 8px;
    border-left: 3px solid #00ff88;
}

/* ── Cards ── */
#card {
    background: rgba(17,24,39,180);
    border: 1px solid rgba(0,255,136,0.05);
    border-radius: 14px;
}
#card_title {
    font-size: 11px;
    font-weight: 700;
    color: #00ff88;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-family: 'Cascadia Code', monospace;
}
#card_sub {
    font-size: 12px;
    color: #8899aa;
    line-height: 1.5;
}

/* ── Page Header ── */
#page_title {
    font-size: 24px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 0.5px;
}
#page_sub {
    font-size: 13px;
    color: #8899aa;
    margin-bottom: 6px;
}

/* ── Buttons ── */
QPushButton {
    padding: 12px 24px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
    border: 1px solid rgba(0,255,136,0.25);
    background: rgba(15,18,25,220);
    color: #00ff88;
}
QPushButton:hover {
    background: rgba(0,255,136,0.08);
    border-color: rgba(0,255,136,0.45);
    color: #33ffaa;
}
QPushButton:pressed {
    background: rgba(0,255,136,0.15);
    border-color: rgba(0,255,136,0.6);
}
QPushButton:disabled {
    background: rgba(15,18,25,100);
    border-color: rgba(255,255,255,0.05);
    color: rgba(255,255,255,0.2);
}

#btn_danger {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(239,68,68,0.35) !important;
    color: #ef4444 !important;
}
#btn_danger:hover {
    background: rgba(239,68,68,0.1) !important;
    border-color: rgba(239,68,68,0.55) !important;
    color: #f87171 !important;
}

#btn_sec {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(0,255,136,0.25) !important;
    color: #00ff88 !important;
}
#btn_sec:hover {
    background: rgba(0,255,136,0.08) !important;
    border-color: rgba(0,255,136,0.45) !important;
    color: #33ffaa !important;
}

#btn_warn {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(251,191,36,0.35) !important;
    color: #fbbf24 !important;
    font-weight: 700;
    padding: 12px 32px;
    border-radius: 10px;
}
#btn_warn:hover {
    background: rgba(251,191,36,0.1) !important;
    border-color: rgba(251,191,36,0.55) !important;
    color: #fcd34d !important;
}

#btn_info {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(129,140,248,0.25) !important;
    color: #818cf8 !important;
}
#btn_info:hover {
    background: rgba(129,140,248,0.08) !important;
    border-color: rgba(129,140,248,0.45) !important;
    color: #a5b4fc !important;
}

#btn_success {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(0,255,136,0.25) !important;
    color: #00ff88 !important;
}

#btn_purple {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(167,139,250,0.25) !important;
    color: #a78bfa !important;
}
#btn_purple:hover {
    background: rgba(167,139,250,0.08) !important;
    border-color: rgba(167,139,250,0.45) !important;
}

#btn_cyan {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(34,211,238,0.25) !important;
    color: #22d3ee !important;
}
#btn_cyan:hover {
    background: rgba(34,211,238,0.08) !important;
    border-color: rgba(34,211,238,0.45) !important;
}

#btn_glow {
    background: rgba(15,18,25,220) !important;
    border: 1px solid rgba(0,255,136,0.4) !important;
    color: #00ff88 !important;
    font-weight: 700;
    font-size: 14px;
    padding: 14px 36px;
    border-radius: 12px;
}
#btn_glow:hover {
    background: rgba(0,255,136,0.12) !important;
    border-color: rgba(0,255,136,0.6) !important;
    color: #33ffaa !important;
}

#btn_neon {
    background: rgba(15,18,25,220) !important;
    color: #00ff88 !important;
    border: 1px solid rgba(0,255,136,0.35) !important;
    font-weight: 700;
    padding: 12px 32px;
    border-radius: 12px;
}
#btn_neon:hover {
    background: rgba(0,255,136,0.1) !important;
    border-color: rgba(0,255,136,0.55) !important;
    color: #33ffaa !important;
}

#btn_glass {
    background: rgba(15,18,25,220) !important;
    color: #f0f4f8 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    font-weight: 700;
    padding: 12px 32px;
    border-radius: 10px;
}
#btn_glass:hover {
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.2) !important;
    color: #00ff88 !important;
}

#tray_btn {
    background: rgba(15,18,25,220);
    color: #64748b;
    border: 1px solid rgba(100,116,139,0.15);
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 12px;
    font-weight: 600;
}
#tray_btn:hover {
    color: #e2e8f0;
    border-color: rgba(0,255,136,0.25);
    background: rgba(0,255,136,0.05);
}

/* ── Badges ── */
#badge_run {
    border-radius: 10px;
    padding: 5px 14px;
    background: rgba(0,255,136,0.06);
    color: #00ff88;
    border: 1px solid rgba(0,255,136,0.12);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: 'Cascadia Code', monospace;
}
#badge_stop {
    border-radius: 10px;
    padding: 5px 14px;
    background: rgba(255,68,68,0.05);
    color: #ff4444;
    border: 1px solid rgba(255,68,68,0.1);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: 'Cascadia Code', monospace;
}
#badge_info {
    border-radius: 10px;
    padding: 5px 14px;
    background: rgba(129,140,248,0.06);
    color: #818cf8;
    border: 1px solid rgba(129,140,248,0.12);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: 'Cascadia Code', monospace;
}

/* ── Log Console ── */
QPlainTextEdit {
    background: rgba(5,8,12,240);
    border: 1px solid rgba(0,255,136,0.05);
    border-radius: 12px;
    color: #00ff88;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 12px;
    selection-background-color: rgba(0,255,136,0.15);
}

/* ── Inputs ── */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background: rgba(10,14,20,220);
    border: 1px solid rgba(0,255,136,0.06);
    border-radius: 8px;
    padding: 10px 14px;
    color: #e2e8f0;
    selection-background-color: rgba(0,255,136,0.15);
    font-size: 13px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: rgba(0,255,136,0.2);
}
QLineEdit:disabled, QSpinBox:disabled {
    background: rgba(10,14,20,120);
    color: #475569;
}

/* ── ComboBox ── */
QComboBox {
    background: rgba(10,14,20,220);
    border: 1px solid rgba(0,255,136,0.06);
    border-radius: 8px;
    padding: 8px 14px;
    color: #e2e8f0;
    font-size: 13px;
    min-width: 100px;
}
QComboBox:hover { border-color: rgba(0,255,136,0.15); }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #64748b;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background: #111827;
    border: 1px solid rgba(0,255,136,0.08);
    border-radius: 8px;
    color: #e2e8f0;
    selection-background-color: rgba(0,255,136,0.08);
    padding: 4px;
}

/* ── CheckBox ── */
QCheckBox {
    color: #e2e8f0;
    spacing: 10px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
}
QCheckBox::indicator:hover { border-color: rgba(0,255,136,0.2); }
QCheckBox::indicator:checked {
    background: rgba(0,255,136,0.12);
    border-color: rgba(0,255,136,0.3);
}

/* ── ProgressBar ── */
QProgressBar {
    background: rgba(10,14,20,180);
    border: none;
    border-radius: 3px;
    height: 6px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00ff88, stop:0.5 #818cf8, stop:1 #f472b6);
    border-radius: 3px;
}

/* ── GroupBox ── */
QGroupBox {
    background: rgba(17,24,39,100);
    border: 1px solid rgba(0,255,136,0.04);
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 22px;
    font-weight: 700;
    color: #00ff88;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-family: 'Cascadia Code', monospace;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
}

/* ── TabWidget ── */
QTabWidget::pane {
    border: 1px solid rgba(0,255,136,0.04);
    border-radius: 10px;
    background: rgba(17,24,39,100);
}
QTabBar::tab {
    background: rgba(10,14,20,180);
    border: 1px solid rgba(0,255,136,0.04);
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: #64748b;
    font-weight: 600;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: rgba(0,255,136,0.05);
    color: #00ff88;
    border-bottom-color: transparent;
}
QTabBar::tab:hover:!selected {
    background: rgba(0,255,136,0.02);
    color: #94a3b8;
}

/* ── ScrollArea ── */
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }

/* ── Slider ── */
QSlider::groove:horizontal {
    background: rgba(255,255,255,0.04);
    height: 5px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00ff88;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #33ff9f; }
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00ff88, stop:0.5 #818cf8, stop:1 #f472b6);
    border-radius: 3px;
}

/* ── ToolTip ── */
QToolTip {
    background: #1e293b;
    color: #e2e8f0;
    border: 1px solid rgba(0,255,136,0.08);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Menu ── */
QMenu {
    background: #111827;
    border: 1px solid rgba(0,255,136,0.06);
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
    color: #e2e8f0;
}
QMenu::item:selected {
    background: rgba(0,255,136,0.06);
    color: #00ff88;
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.03);
    margin: 4px 8px;
}

/* ── ListWidget ── */
QListWidget {
    background: rgba(10,14,20,180);
    border: 1px solid rgba(0,255,136,0.04);
    border-radius: 10px;
    color: #e2e8f0;
    outline: none;
}
QListWidget::item {
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.015);
}
QListWidget::item:selected {
    background: rgba(0,255,136,0.06);
    color: #00ff88;
    font-weight: bold;
    border-left: 3px solid #00ff88;
}
QListWidget::item:hover {
    background: rgba(0,255,136,0.02);
}
"""

# ══════════════════════════════════════════════════════════════════════
#  Светлая тема
# ══════════════════════════════════════════════════════════════════════

LIGHT_THEME = {
    "ACCENT": "#00aa6a",
    "ACCENT2": "#6366f1",
    "ACCENT3": "#ec4899",
    "ACCENT_DIM": "#008855",
    "ACCENT_GLOW": "rgba(0,170,106,0.08)",
    "BG_DEEP": "#f8fafc",
    "BG_CARD": "#ffffff",
    "BG_SIDEBAR": "#f1f5f9",
    "BG_SURFACE": "#e2e8f0",
    "TEXT_MAIN": "#1e293b",
    "TEXT_DIM": "#64748b",
    "TEXT_MUTED": "#94a3b8",
    "SUCCESS": "#00aa6a",
    "DANGER": "#dc2626",
    "WARNING": "#d97706",
    "INFO": "#6366f1",
    "PURPLE": "#7c3aed",
    "CYAN": "#0891b2",
    "PINK": "#db2777",
    "BORDER": "rgba(0,0,0,0.08)",
    "BORDER_LIGHT": "rgba(0,0,0,0.04)",
    "BORDER_SUBTLE": "rgba(0,0,0,0.02)",
}

LIGHT_QSS = """
QMainWindow, QWidget {
    background: #f8fafc;
    color: #1e293b;
}
QPlainTextEdit, QTextEdit {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
QLineEdit {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
}
QComboBox {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 12px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #1e293b;
    selection-background-color: #e2e8f0;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QToolTip {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px;
}
QPushButton {
    padding: 10px 22px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 13px;
    border: none;
    background: rgba(0,170,106,0.08);
    color: #1e293b;
}
QPushButton:hover {
    background: rgba(0,170,106,0.15);
}
QPushButton:pressed {
    background: rgba(0,170,106,0.2);
}
QPushButton:disabled {
    background: rgba(0,170,106,0.04);
    color: rgba(30,41,59,0.3);
}
QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 700;
    color: #1e293b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
}
QTabBar::tab {
    background: #f1f5f9;
    color: #64748b;
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #00aa6a;
    border-bottom: 2px solid #00aa6a;
}
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00aa6a;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QMenu {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: rgba(0,170,106,0.1);
}
QHeaderView::section {
    background: #f1f5f9;
    color: #1e293b;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    font-weight: 600;
}
"""


class ThemeManager:
    """Менеджер переключения между тёмной и светлой темой."""

    _current_theme = "dark"

    @classmethod
    def is_dark(cls) -> bool:
        return cls._current_theme == "dark"

    @classmethod
    def is_light(cls) -> bool:
        return cls._current_theme == "light"

    @classmethod
    def get_color(cls, name: str) -> str:
        """Возвращает цвет по имени для текущей темы."""
        if cls._current_theme == "light" and name in LIGHT_THEME:
            return LIGHT_THEME[name]
        # Тёмная тема — дефолтные глобальные переменные
        return globals().get(name, "#ffffff")

    @classmethod
    def get_qss(cls) -> str:
        """Возвращает QSS для текущей темы."""
        if cls._current_theme == "light":
            return LIGHT_QSS
        return QSS

    @classmethod
    def get_table_qss(cls) -> str:
        """Возвращает QSS таблиц для текущей темы."""
        if cls._current_theme == "light":
            return """
QTableWidget {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    color: #1e293b;
    font-size: 12px;
    gridline-color: transparent;
    selection-background-color: rgba(0,170,106,0.1);
    outline: none;
}
QTableWidget::item {
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #f1f5f9;
    background: transparent;
}
QTableWidget::item:selected {
    background: rgba(0,170,106,0.1);
    color: #00aa6a;
}
QTableWidget::item:hover {
    background: #f8fafc;
}
QHeaderView::section {
    background: #f1f5f9;
    color: #1e293b;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    font-weight: 600;
}
"""
        return TABLE_QSS

    @classmethod
    def switch_to(cls, theme: str):
        """Переключает тему ('dark' или 'light')."""
        if theme not in ("dark", "light"):
            return
        cls._current_theme = theme

    @classmethod
    def toggle(cls):
        """Переключает между тёмной и светлой темой."""
        cls._current_theme = "light" if cls._current_theme == "dark" else "dark"

