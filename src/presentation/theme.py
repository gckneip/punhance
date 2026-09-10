BG_APP = "#f4f6fb"
SURFACE = "#ffffff"
BORDER = "#e1e4eb"
TEXT_PRIMARY = "#1f2430"
TEXT_SECONDARY = "#6b7280"
PRIMARY = "#3462eb"
PRIMARY_HOVER = "#2c53c9"
PRIMARY_PRESSED = "#2445a8"
INCOME = "#1d9a6c"
EXPENSE = "#e5484d"
SELECTION = "#dbe4ff"

# Fixed-order categorical palette for open-ended chart breakdowns (by category,
# counterparty, credit card, account, ...). Order is the CVD-safety mechanism -
# never cycle or reorder it. Series 9+ should fold into "Other" rather than
# reusing a slot. Income-vs-expenses charts should keep using INCOME/EXPENSE
# above instead of these slots, since that pairing is a reserved semantic, not
# an open-ended category.
CHART_CATEGORICAL = [
    "#2a78d6",  # blue
    "#008300",  # green
    "#e87ba4",  # magenta
    "#eda100",  # yellow
    "#1baf7a",  # aqua
    "#eb6834",  # orange
    "#4a3aa7",  # violet
    "#e34948",  # red
]


def load_palette(palette) -> None:
    """Mutate this module's color globals from a ThemePalette.

    Restart-only theming: call this exactly once, in main()/driver.py, after
    AppSettingsUseCases/ThemeUseCases exist but before app.setStyleSheet(),
    configure_pyqtgraph_theme(), or any widget/icon is constructed. Every
    theme.* read-site in src/presentation/ does `from src.presentation import
    theme` (module import) and reads theme.X inside a function/method body,
    so it naturally picks up these new values with zero per-file changes.
    """
    global BG_APP, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY
    global PRIMARY, PRIMARY_HOVER, PRIMARY_PRESSED, INCOME, EXPENSE, SELECTION
    global CHART_CATEGORICAL
    BG_APP = palette.bg_app
    SURFACE = palette.surface
    BORDER = palette.border
    TEXT_PRIMARY = palette.text_primary
    TEXT_SECONDARY = palette.text_secondary
    PRIMARY = palette.primary
    PRIMARY_HOVER = palette.primary_hover
    PRIMARY_PRESSED = palette.primary_pressed
    INCOME = palette.income
    EXPENSE = palette.expense
    SELECTION = palette.selection
    CHART_CATEGORICAL = list(palette.chart_categorical)


def _hex_to_rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _mix(hex_a: str, hex_b: str, amount: float) -> str:
    """Blend hex_a toward hex_b by `amount` (0..1). Used to derive
    hover/pressed/disabled/alternate-row shades from the active palette
    instead of hardcoding light-mode-tuned grays that would look wrong
    (e.g. a near-white hover flash) on a dark theme."""
    a, b = _hex_to_rgb(hex_a), _hex_to_rgb(hex_b)
    mixed = tuple(round(ca + (cb - ca) * amount) for ca, cb in zip(a, b))
    return "#%02x%02x%02x" % mixed


def build_stylesheet() -> str:
    """Was a frozen module-level f-string (STYLESHEET). Now a function so it
    re-interpolates the current module globals at call time - necessary
    because an f-string bakes its values in at construction time, which
    would happen once at import, before load_palette() could ever run."""
    hover_bg = _mix(SURFACE, BORDER, 0.5)
    pressed_bg = _mix(SURFACE, BORDER, 0.8)
    disabled_bg = _mix(SURFACE, BORDER, 0.35)
    alt_row_bg = _mix(SURFACE, BORDER, 0.15)
    header_bg = _mix(SURFACE, BORDER, 0.3)

    return f"""
* {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QMainWindow, QWidget {{
    background: {BG_APP};
}}

QDialog {{
    background: {SURFACE};
}}

QLabel {{
    background: transparent;
}}

QToolTip {{
    background: {TEXT_PRIMARY};
    color: {SURFACE};
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: {SURFACE};
    top: -1px;
}}

QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background: {SURFACE};
    color: {TEXT_PRIMARY};
    font-weight: 600;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
}}

QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    color: {TEXT_PRIMARY};
}}

QPushButton:hover {{
    background: {hover_bg};
    border-color: {PRIMARY};
}}

QPushButton:pressed {{
    background: {pressed_bg};
}}

QPushButton:disabled {{
    color: {TEXT_SECONDARY};
    background: {disabled_bg};
}}

QPushButton#primaryButton {{
    background: {PRIMARY};
    border: 1px solid {PRIMARY};
    color: white;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background: {PRIMARY_HOVER};
    border-color: {PRIMARY_HOVER};
}}

QPushButton#primaryButton:pressed {{
    background: {PRIMARY_PRESSED};
}}

QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {SELECTION};
}}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1px solid {PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QTableWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
    selection-background-color: {SELECTION};
    selection-color: {TEXT_PRIMARY};
    alternate-background-color: {alt_row_bg};
}}

QHeaderView::section {{
    background: {header_bg};
    color: {TEXT_SECONDARY};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
}}

QTableWidget::item {{
    padding: 4px;
}}

QCheckBox, QRadioButton {{
    spacing: 6px;
}}

QFrame#statCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QLabel#statCardTitle {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
}}

QLabel#statCardValue {{
    font-size: 20px;
    font-weight: 700;
}}

QFrame#quickAddBar {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#previewDrawer {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px;
}}

QListWidget#sidebarNav {{
    background: {SURFACE};
    border: none;
    border-right: 1px solid {BORDER};
    outline: none;
}}

QListWidget#sidebarNav::item {{
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 6px;
    color: {TEXT_SECONDARY};
}}

QListWidget#sidebarNav::item:selected {{
    background: {SELECTION};
    color: {PRIMARY};
    font-weight: 600;
}}

QListWidget#sidebarNav::item:hover:!selected {{
    background: {hover_bg};
    color: {TEXT_PRIMARY};
}}
"""
