from typing import Optional

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget


class AccountCreditCardSelector(QWidget):
    """Every event/purchase must be tied to exactly one funding source: an
    account or a credit card - never both, never neither. This widget owns
    that pairing so the rule only needs to be implemented once and every
    dialog that creates/edits an event, purchase, or recurring event stays
    consistent."""

    MODE_EITHER = "either"              # exactly one of the two, mutually exclusive
    MODE_BOTH = "both"                  # both required (e.g. a card payment: from an
                                         # account, paying down a card)
    MODE_ACCOUNT_ONLY = "account_only"  # credit card side hidden (e.g. transfers)
    MODE_CARD_ONLY = "card_only"        # account side hidden (e.g. a credit-card purchase)

    def __init__(self, accounts=None, credit_cards=None, parent=None):
        super().__init__(parent)
        self._mode = self.MODE_EITHER

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.account_combo = QComboBox()
        layout.addWidget(self.account_combo)

        self.credit_card_combo = QComboBox()
        layout.addWidget(self.credit_card_combo)

        self.set_data(accounts, credit_cards)

        self.account_combo.currentIndexChanged.connect(self._on_account_changed)
        self.credit_card_combo.currentIndexChanged.connect(self._on_card_changed)

    def set_data(self, accounts=None, credit_cards=None):
        """(Re)populates both combos, preserving the current selection where
        possible - for widgets like the dashboard's Quick Add bar that get
        fresh account/card lists pushed in on every refresh."""
        prev_account = self.account_combo.currentData()
        prev_card = self.credit_card_combo.currentData()

        self.account_combo.blockSignals(True)
        self.credit_card_combo.blockSignals(True)

        self.account_combo.clear()
        self.account_combo.addItem("None", None)
        for acc in accounts or []:
            self.account_combo.addItem(f"{acc.name} ({acc.type})", acc.id)

        self.credit_card_combo.clear()
        self.credit_card_combo.addItem("None", None)
        for card in credit_cards or []:
            self.credit_card_combo.addItem(card.name, card.id)

        if prev_account is not None:
            idx = self.account_combo.findData(prev_account)
            if idx >= 0:
                self.account_combo.setCurrentIndex(idx)
        if prev_card is not None:
            idx = self.credit_card_combo.findData(prev_card)
            if idx >= 0:
                self.credit_card_combo.setCurrentIndex(idx)

        self.account_combo.blockSignals(False)
        self.credit_card_combo.blockSignals(False)

    def _on_account_changed(self, _index):
        if self._mode == self.MODE_EITHER and self.account_combo.currentData() is not None:
            self._clear(self.credit_card_combo)

    def _on_card_changed(self, _index):
        if self._mode == self.MODE_EITHER and self.credit_card_combo.currentData() is not None:
            self._clear(self.account_combo)

    def _clear(self, combo: QComboBox):
        combo.blockSignals(True)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def set_mode(self, mode: str):
        self._mode = mode
        show_account = mode in (self.MODE_EITHER, self.MODE_BOTH, self.MODE_ACCOUNT_ONLY)
        show_card = mode in (self.MODE_EITHER, self.MODE_BOTH, self.MODE_CARD_ONLY)
        self.account_combo.setVisible(show_account)
        self.credit_card_combo.setVisible(show_card)
        if not show_account:
            self._clear(self.account_combo)
        if not show_card:
            self._clear(self.credit_card_combo)

    def set_selection(self, account_id: Optional[str], credit_card_id: Optional[str]):
        acc_idx = self.account_combo.findData(account_id)
        if acc_idx >= 0:
            self.account_combo.setCurrentIndex(acc_idx)
        card_idx = self.credit_card_combo.findData(credit_card_id)
        if card_idx >= 0:
            self.credit_card_combo.setCurrentIndex(card_idx)

    def account_id(self) -> Optional[str]:
        return self.account_combo.currentData()

    def credit_card_id(self) -> Optional[str]:
        return self.credit_card_combo.currentData()

    def validation_error(self) -> Optional[str]:
        account_id, credit_card_id = self.account_id(), self.credit_card_id()
        if self._mode == self.MODE_BOTH:
            if account_id is None or credit_card_id is None:
                return "Both an account and a credit card are required."
        elif self._mode == self.MODE_ACCOUNT_ONLY:
            if account_id is None:
                return "Account is required."
        elif self._mode == self.MODE_CARD_ONLY:
            if credit_card_id is None:
                return "Credit card is required."
        else:
            if account_id is None and credit_card_id is None:
                return "Select an account or a credit card."
        return None
