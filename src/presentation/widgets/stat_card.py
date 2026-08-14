from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


def make_stat_card(title: str, value_label: QLabel) -> QFrame:
    card = QFrame()
    card.setObjectName("statCard")
    card.setMinimumWidth(150)

    layout = QVBoxLayout(card)
    title_label = QLabel(title)
    title_label.setObjectName("statCardTitle")
    layout.addWidget(title_label)

    value_label.setObjectName("statCardValue")
    layout.addWidget(value_label)

    return card
