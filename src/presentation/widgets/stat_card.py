from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QLabel


def make_stat_card(title: str, value_label: QLabel) -> QFrame:
    card = QFrame()
    card.setObjectName("statCard")
    # No minimum width here on purpose: the dashboard grid's column width is
    # meant to be the single source of truth for sizing (see
    # dashboard_grid_widget.py) - a hardcoded floor here would fight it and
    # force whichever column/row this card lands in to grow past the grid's
    # fixed unit size whenever its span is narrower than 150px.
    # Caps the card's height so it stays a compact tile instead of stretching
    # to fill whatever container it's placed in (e.g. the widget preview drawer).
    card.setMaximumHeight(96)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(4)
    layout.addStretch()

    title_label = QLabel(title)
    title_label.setObjectName("statCardTitle")
    # QLabel's default size policy (Preferred) still makes Qt's layout use
    # minimumSizeHint() - i.e. "wide enough to show this text unclipped" -
    # as a hard floor; setMinimumWidth(0) does NOT override that (0 is
    # already the default, so it's a no-op). Ignored is what actually makes
    # the layout disregard the text's natural width, so different titles/
    # values ("Monthly Expenses" vs "Net") don't each impose a different
    # floor on their card, unevenly distorting the grid's column widths
    # (see dashboard_grid_widget.py). Text still shows in full when there's
    # room; it just clips instead of pushing the grid around when there isn't.
    # Horizontal only - Ignored on the vertical axis too collapses these to
    # zero height, since they'd then compete for space with the addStretch()
    # calls below/above them instead of getting their natural single-line
    # height reserved. Row height varying a bit by content is an acceptable
    # trade-off; invisible text is not.
    title_label.setSizePolicy(QSizePolicy.Ignored, title_label.sizePolicy().verticalPolicy())
    layout.addWidget(title_label)

    value_label.setObjectName("statCardValue")
    value_label.setSizePolicy(QSizePolicy.Ignored, value_label.sizePolicy().verticalPolicy())
    layout.addWidget(value_label)

    layout.addStretch()

    return card
