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

STYLESHEET = f"""
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
    background: #eef1f8;
    border-color: {PRIMARY};
}}

QPushButton:pressed {{
    background: #e3e7f2;
}}

QPushButton:disabled {{
    color: {TEXT_SECONDARY};
    background: #f0f1f5;
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
    alternate-background-color: #fafbfe;
}}

QHeaderView::section {{
    background: #f0f2f8;
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
"""
