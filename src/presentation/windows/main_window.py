from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QDateEdit, QComboBox, QLineEdit, QFormLayout,
    QDialog, QDoubleSpinBox, QDialogButtonBox,
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QKeySequence, QShortcut
from datetime import date, timedelta

from src.application.use_cases.account_use_cases import AccountUseCases
from src.application.use_cases.category_use_cases import CategoryUseCases
from src.application.use_cases.counterparty_use_cases import CounterpartyUseCases
from src.application.use_cases.credit_card_use_cases import CreditCardUseCases
from src.application.use_cases.financial_event_use_cases import FinancialEventUseCases
from src.application.use_cases.purchase_use_cases import PurchaseUseCases
from src.application.use_cases.installment_use_cases import InstallmentUseCases
from src.application.dto.account_dto import CreateAccountDTO
from src.application.dto.category_dto import CreateCategoryDTO
from src.application.dto.counterparty_dto import CreateCounterpartyDTO
from src.application.dto.credit_card_dto import CreateCreditCardDTO
from src.application.dto.financial_event_dto import CreateFinancialEventDTO
from src.application.dto.purchase_dto import CreatePurchaseDTO, CreatePurchaseItemDTO
from src.domain.entities.financial_event import EventType
from src.domain.entities.purchase import PaymentMethod
from src.domain.services.monthly_summary_service import MonthlySummaryService
from src.presentation.dialogs.account_dialog import AccountDialog
from src.presentation.dialogs.category_dialog import CategoryDialog
from src.presentation.dialogs.counterparty_dialog import CounterpartyDialog
from src.presentation.dialogs.credit_card_dialog import CreditCardDialog
from src.presentation.dialogs.purchase_dialog import PurchaseDialog
from src.presentation.widgets.dashboard_widget import DashboardWidget
from src.presentation.widgets.installments_widget import InstallmentsWidget
from src.presentation.widgets.category_breakdown_widget import CategoryBreakdownWidget
from src.presentation.widgets.account_summary_widget import AccountSummaryWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        account_use_cases: AccountUseCases,
        category_use_cases: CategoryUseCases,
        counterparty_use_cases: CounterpartyUseCases,
        credit_card_use_cases: CreditCardUseCases,
        financial_event_use_cases: FinancialEventUseCases,
        purchase_use_cases: PurchaseUseCases,
        installment_use_cases: InstallmentUseCases,
        monthly_summary_service: MonthlySummaryService,
        category_breakdown_service=None,
        account_summary_service=None,
    ):
        super().__init__()
        self._account_use_cases = account_use_cases
        self._category_use_cases = category_use_cases
        self._counterparty_use_cases = counterparty_use_cases
        self._credit_card_use_cases = credit_card_use_cases
        self._financial_event_use_cases = financial_event_use_cases
        self._purchase_use_cases = purchase_use_cases
        self._installment_use_cases = installment_use_cases
        self._category_breakdown_service = category_breakdown_service
        self._account_summary_service = account_summary_service

        self.setWindowTitle("Personal Finance Manager")
        self.resize(900, 600)

        self._build_ui()

        self._dashboard = DashboardWidget(monthly_summary_service, financial_event_use_cases)
        self._dashboard.entry_added.connect(self._refresh_all)
        self._tabs.insertTab(0, self._dashboard, "Dashboard")
        self._tabs.setCurrentIndex(0)

        self._build_shortcuts()

        self._refresh_all()

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._focus_quick_add)

    def _focus_quick_add(self):
        self._tabs.setCurrentWidget(self._dashboard)
        self._dashboard.focus_quick_add()

    def _make_actions_widget(self, actions):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        for label, handler in actions:
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
        layout.addStretch()
        return widget

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._btn_add_event = QPushButton("+ Event")
        self._btn_add_event.setObjectName("primaryButton")
        self._btn_add_event.setShortcut(QKeySequence("Ctrl+N"))
        self._btn_add_event.setToolTip("Add a financial event (Ctrl+N)")
        self._btn_add_event.clicked.connect(self._add_event)
        toolbar.addWidget(self._btn_add_event)

        self._btn_add_purchase = QPushButton("+ Purchase")
        self._btn_add_purchase.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self._btn_add_purchase.setToolTip("Add a detailed purchase with items/installments (Ctrl+Shift+N)")
        self._btn_add_purchase.clicked.connect(self._add_purchase)
        toolbar.addWidget(self._btn_add_purchase)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_events_tab()
        self._build_accounts_tab()
        self._build_categories_tab()
        self._build_counterparties_tab()
        self._build_credit_cards_tab()
        self._build_installments_tab()
        self._build_category_breakdown_tab()
        self._build_account_summary_tab()

    def _build_events_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        filter_row = QHBoxLayout()

        self._filter_date_from = QDateEdit()
        self._filter_date_from.setCalendarPopup(True)
        self._filter_date_from.setDate(date(date.today().year, date.today().month, 1))
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self._filter_date_from)

        self._filter_date_to = QDateEdit()
        self._filter_date_to.setCalendarPopup(True)
        self._filter_date_to.setDate(date.today())
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self._filter_date_to)

        self._filter_description = QLineEdit()
        self._filter_description.setPlaceholderText("Search description...")
        filter_row.addWidget(QLabel("Desc:"))
        filter_row.addWidget(self._filter_description)

        self._filter_category = QComboBox()
        self._filter_category.addItem("All Categories", None)
        filter_row.addWidget(QLabel("Category:"))
        filter_row.addWidget(self._filter_category)

        self._filter_account = QComboBox()
        self._filter_account.addItem("All Accounts", None)
        filter_row.addWidget(QLabel("Account:"))
        filter_row.addWidget(self._filter_account)

        self._btn_filter = QPushButton("Search")
        self._btn_filter.clicked.connect(self._refresh_events)
        filter_row.addWidget(self._btn_filter)

        layout.addLayout(filter_row)

        self._events_table = QTableWidget()
        self._events_table.setColumnCount(10)
        self._events_table.setHorizontalHeaderLabels(
            ["Date", "Type", "Description", "Amount", "Currency", "Category", "Account", "Counterparty", "Notes", "ID"]
        )
        self._events_table.horizontalHeader().setStretchLastSection(True)
        self._events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._events_table.setAlternatingRowColors(True)
        layout.addWidget(self._events_table)

        self._tabs.addTab(tab, "Events")

    def _build_accounts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Account")
        btn.clicked.connect(self._add_account)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._accounts_table = QTableWidget()
        self._accounts_table.setColumnCount(5)
        self._accounts_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Initial Balance", "ID", "Actions"]
        )
        self._accounts_table.horizontalHeader().setStretchLastSection(True)
        self._accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._accounts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._accounts_table.setAlternatingRowColors(True)
        layout.addWidget(self._accounts_table)

        self._tabs.addTab(tab, "Accounts")

    def _build_categories_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Category")
        btn.clicked.connect(self._add_category)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._categories_table = QTableWidget()
        self._categories_table.setColumnCount(4)
        self._categories_table.setHorizontalHeaderLabels(
            ["Name", "Color", "Parent", "Actions"]
        )
        self._categories_table.horizontalHeader().setStretchLastSection(True)
        self._categories_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._categories_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._categories_table.setAlternatingRowColors(True)
        layout.addWidget(self._categories_table)

        self._tabs.addTab(tab, "Categories")

    def _build_counterparties_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Counterparty")
        btn.clicked.connect(self._add_counterparty)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._counterparties_table = QTableWidget()
        self._counterparties_table.setColumnCount(3)
        self._counterparties_table.setHorizontalHeaderLabels(["Name", "ID", "Actions"])
        self._counterparties_table.horizontalHeader().setStretchLastSection(True)
        self._counterparties_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._counterparties_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._counterparties_table.setAlternatingRowColors(True)
        layout.addWidget(self._counterparties_table)

        self._tabs.addTab(tab, "Counterparties")

    def _build_credit_cards_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Credit Card")
        btn.clicked.connect(self._add_credit_card)
        btn_row.addWidget(btn)

        self._btn_pay_card = QPushButton("Pay Card")
        self._btn_pay_card.clicked.connect(self._pay_card)
        btn_row.addWidget(self._btn_pay_card)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._credit_cards_table = QTableWidget()
        self._credit_cards_table.setColumnCount(9)
        self._credit_cards_table.setHorizontalHeaderLabels(
            ["Name", "Issuer", "Credit Limit", "Closing Day", "Due Day", "Active", "Current Debt", "Available Credit", "Actions"]
        )
        self._credit_cards_table.horizontalHeader().setStretchLastSection(True)
        self._credit_cards_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._credit_cards_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._credit_cards_table.setAlternatingRowColors(True)
        layout.addWidget(self._credit_cards_table)

        self._tabs.addTab(tab, "Credit Cards")

    def _build_installments_tab(self):
        self._installments_widget = InstallmentsWidget(
            self._installment_use_cases,
        )
        self._tabs.addTab(self._installments_widget, "Installments")

    def _build_category_breakdown_tab(self):
        if self._category_breakdown_service:
            self._category_breakdown_widget = CategoryBreakdownWidget(
                self._category_breakdown_service,
                self._category_use_cases,
            )
            self._tabs.addTab(self._category_breakdown_widget, "Category Breakdown")

    def _build_account_summary_tab(self):
        if self._account_summary_service:
            self._account_summary_widget = AccountSummaryWidget(
                self._account_summary_service,
            )
            self._tabs.addTab(self._account_summary_widget, "Account Summary")

    def _add_account(self):
        dialog = AccountDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateAccountDTO(
                name=data["name"],
                type=data["type"],
                initial_balance=data["initial_balance"],
            )
            self._account_use_cases.create_account(dto)
            self._refresh_all()

    def _edit_account(self, account_id):
        accounts = {a.id: a for a in self._account_use_cases.list_accounts()}
        account = accounts.get(account_id)
        if account is None:
            return

        dialog = AccountDialog(self, account=account)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateAccountDTO(
                name=data["name"],
                type=data["type"],
                initial_balance=data["initial_balance"],
            )
            self._account_use_cases.update_account(account_id, dto)
            self._refresh_all()

    def _add_category(self):
        categories = self._category_use_cases.list_categories()
        dialog = CategoryDialog(categories, self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateCategoryDTO(
                name=data["name"],
                color=data["color"],
                parent_id=data["parent_id"],
            )
            self._category_use_cases.create_category(dto)
            self._refresh_all()

    def _edit_category(self, category_id):
        categories = self._category_use_cases.list_categories()
        category = next((c for c in categories if c.id == category_id), None)
        if category is None:
            return

        dialog = CategoryDialog(categories, self, category=category)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateCategoryDTO(
                name=data["name"],
                color=data["color"],
                parent_id=data["parent_id"],
            )
            self._category_use_cases.update_category(category_id, dto)
            self._refresh_all()

    def _add_counterparty(self):
        dialog = CounterpartyDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateCounterpartyDTO(name=data["name"])
            self._counterparty_use_cases.create_counterparty(dto)
            self._refresh_all()

    def _edit_counterparty(self, counterparty_id):
        counterparties = {c.id: c for c in self._counterparty_use_cases.list_counterparties()}
        counterparty = counterparties.get(counterparty_id)
        if counterparty is None:
            return

        dialog = CounterpartyDialog(self, counterparty=counterparty)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateCounterpartyDTO(name=data["name"])
            self._counterparty_use_cases.update_counterparty(counterparty_id, dto)
            self._refresh_all()

    def _add_credit_card(self):
        dialog = CreditCardDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateCreditCardDTO(
                name=data["name"],
                issuer=data["issuer"],
                credit_limit=data["credit_limit"],
                closing_day=data["closing_day"],
                due_day=data["due_day"],
                is_active=data["is_active"],
            )
            self._credit_card_use_cases.create_card(dto)
            self._refresh_all()

    def _edit_credit_card(self, card_id):
        cards = {c.id: c for c in self._credit_card_use_cases.list_cards()}
        card = cards.get(card_id)
        if card is None:
            return

        dialog = CreditCardDialog(self, card=card)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateCreditCardDTO(
                name=data["name"],
                issuer=data["issuer"],
                credit_limit=data["credit_limit"],
                closing_day=data["closing_day"],
                due_day=data["due_day"],
                is_active=data["is_active"],
            )
            self._credit_card_use_cases.update_card(card_id, dto)
            self._refresh_all()

    def _pay_card(self):
        rows = self._credit_cards_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a credit card to pay.")
            return

        row = rows[0].row()
        cards = self._credit_card_use_cases.list_cards()
        if row >= len(cards):
            return

        card = cards[row]
        status = self._credit_card_use_cases.get_status(card.id)
        if status is None:
            return

        if status.current_debt <= 0:
            QMessageBox.information(self, "Info", "No outstanding debt on this card.")
            return

        from src.application.dto.card_payment_dto import CreateCardPaymentDTO
        from src.presentation.dialogs.card_payment_dialog import CardPaymentDialog

        accounts = self._account_use_cases.list_accounts()
        installments = self._installment_use_cases.list_installments(
            credit_card_id=card.id,
        )
        pending = [i for i in installments if i.status in ("pending", "overdue")]

        dialog = CardPaymentDialog(
            accounts, pending, status.current_debt, card.name, self
        )
        if dialog.exec():
            data = dialog.get_data()
            confirm = QMessageBox.question(
                self,
                "Confirm Payment",
                f"Pay R$ {data['amount']:.2f} for {card.name}?\n"
                "This will debit the selected account and mark the chosen "
                "installments as paid.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
            dto = CreateCardPaymentDTO(
                event_date=data["event_date"],
                description=data["description"],
                amount=data["amount"],
                account_id=data["account_id"],
                credit_card_id=card.id,
                installment_ids=data["installment_ids"],
                notes=data["notes"],
            )
            result = self._credit_card_use_cases.pay_card(dto)
            if "error" in result:
                QMessageBox.warning(self, "Error", result["error"])
            else:
                self._refresh_all()

    def _add_event(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()

        dialog = QDialog(self)
        dialog.setWindowTitle("Create Financial Event")
        dialog.setModal(True)
        dialog.resize(400, 350)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        form.addRow("Date:", date_edit)

        type_combo = QComboBox()
        type_combo.addItems(["expense", "income", "transfer"])
        form.addRow("Type:", type_combo)

        amount_row = QHBoxLayout()
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(-999999, 999999)
        amount_row.addWidget(amount_spin)

        currency_combo = QComboBox()
        currency_combo.addItems(["BRL", "USD", "EUR", "GBP", "JPY", "ARS", "CAD", "AUD"])
        currency_combo.setCurrentText("BRL")
        amount_row.addWidget(currency_combo)
        form.addRow("Amount:", amount_row)

        description_edit = QLineEdit()
        form.addRow("Description:", description_edit)

        category_combo = QComboBox()
        category_combo.addItem("None", None)
        for cat in categories:
            category_combo.addItem(f"{cat.name}", cat.id)
        form.addRow("Category:", category_combo)

        account_combo = QComboBox()
        account_combo.addItem("None", None)
        for acc in accounts:
            account_combo.addItem(f"{acc.name} ({acc.type})", acc.id)
        form.addRow("Account (Source):", account_combo)

        dest_account_combo = QComboBox()
        dest_account_combo.addItem("None", None)
        for acc in accounts:
            dest_account_combo.addItem(f"{acc.name} ({acc.type})", acc.id)
        dest_account_combo.setVisible(False)
        dest_label = QLabel("Destination Account:")
        dest_label.setVisible(False)
        form.addRow(dest_label, dest_account_combo)

        def _on_type_changed(text):
            is_transfer = (text == "transfer")
            dest_account_combo.setVisible(is_transfer)
            dest_label.setVisible(is_transfer)
        type_combo.currentTextChanged.connect(_on_type_changed)

        counterparty_combo = QComboBox()
        counterparty_combo.addItem("None", None)
        for cp in counterparties:
            counterparty_combo.addItem(cp.name, cp.id)
        form.addRow("Counterparty:", counterparty_combo)

        notes_edit = QLineEdit()
        form.addRow("Notes:", notes_edit)

        layout.addLayout(form)

        def _validate_and_accept():
            if not description_edit.text().strip():
                QMessageBox.warning(dialog, "Validation", "Description is required.")
                return
            if amount_spin.value() == 0:
                QMessageBox.warning(dialog, "Validation", "Amount cannot be zero.")
                return
            if type_combo.currentText() == "transfer":
                if dest_account_combo.currentData() is None:
                    QMessageBox.warning(dialog, "Validation", "Destination account is required for transfers.")
                    return
                if dest_account_combo.currentData() == account_combo.currentData():
                    QMessageBox.warning(dialog, "Validation", "Source and destination accounts must differ.")
                    return
            dialog.accept()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(_validate_and_accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            type_map = {
                "expense": EventType.EXPENSE,
                "income": EventType.INCOME,
                "transfer": EventType.TRANSFER,
            }
            dto = CreateFinancialEventDTO(
                event_type=type_map[type_combo.currentText()],
                event_date=date_edit.date().toPython(),
                description=description_edit.text().strip(),
                amount=amount_spin.value(),
                category_id=category_combo.currentData(),
                account_id=account_combo.currentData(),
                destination_account_id=dest_account_combo.currentData(),
                counterparty_id=counterparty_combo.currentData(),
                currency=currency_combo.currentText(),
                notes=notes_edit.text().strip() or None,
            )
            self._financial_event_use_cases.create_event(dto)
            self._refresh_all()

    def _add_purchase(self):
        categories = self._category_use_cases.list_categories()
        credit_cards = self._credit_card_use_cases.list_cards()
        counterparties = self._counterparty_use_cases.list_counterparties()

        dialog = PurchaseDialog(categories, credit_cards, counterparties, self)
        if dialog.exec():
            data = dialog.get_data()
            items = []
            for i in data["items"]:
                items.append(CreatePurchaseItemDTO(
                    name=i["name"],
                    quantity=i["quantity"],
                    unit=i["unit"],
                    unit_price=i["unit_price"],
                    total_price=i["total_price"],
                    category_id=i["category_id"],
                ))

            dto = CreatePurchaseDTO(
                event_date=data["event_date"],
                description=data["description"],
                total_amount=data["total_amount"],
                payment_method=PaymentMethod(data["payment_method"]),
                credit_card_id=data["credit_card_id"],
                notes=data["notes"],
                installment_count=data["installment_count"],
                counterparty_id=data["counterparty_id"],
                items=items,
            )
            result = self._purchase_use_cases.create_purchase(dto)
            if result.get("warnings"):
                QMessageBox.warning(self, "Purchase Warning", "\n".join(result["warnings"]))
            self._refresh_all()

    def _refresh_all(self):
        self._refresh_events()
        self._refresh_accounts()
        self._refresh_categories()
        self._refresh_counterparties()
        self._refresh_credit_cards()
        self._refresh_installments()
        self._refresh_dashboard()
        if hasattr(self, '_category_breakdown_widget'):
            self._category_breakdown_widget.refresh()
        if hasattr(self, '_account_summary_widget'):
            self._account_summary_widget.refresh()

    def _populate_filter_combos(self):
        self._filter_category.blockSignals(True)
        self._filter_account.blockSignals(True)

        prev_cat = self._filter_category.currentData()
        prev_acc = self._filter_account.currentData()

        self._filter_category.clear()
        self._filter_category.addItem("All Categories", None)
        for cat in self._category_use_cases.list_categories():
            self._filter_category.addItem(cat.name, cat.id)

        self._filter_account.clear()
        self._filter_account.addItem("All Accounts", None)
        for acc in self._account_use_cases.list_accounts():
            self._filter_account.addItem(acc.name, acc.id)

        if prev_cat is not None:
            idx = self._filter_category.findData(prev_cat)
            if idx >= 0:
                self._filter_category.setCurrentIndex(idx)
        if prev_acc is not None:
            idx = self._filter_account.findData(prev_acc)
            if idx >= 0:
                self._filter_account.setCurrentIndex(idx)

        self._filter_category.blockSignals(False)
        self._filter_account.blockSignals(False)

    def _refresh_events(self):
        self._populate_filter_combos()

        date_from = self._filter_date_from.date().toPython()
        date_to = self._filter_date_to.date().toPython()
        description = self._filter_description.text().strip() or None
        category_id = self._filter_category.currentData()
        account_id = self._filter_account.currentData()

        events = self._financial_event_use_cases.list_events(
            date_from=date_from,
            # date_to is an exclusive upper bound in the repository, but the "To"
            # date picker is meant to be inclusive of that whole day.
            date_to=date_to + timedelta(days=1),
            description=description,
            category_id=category_id,
            account_id=account_id,
        )

        accounts_map = {a.id: a.name for a in self._account_use_cases.list_accounts()}
        categories_map = {c.id: c.name for c in self._category_use_cases.list_categories()}
        counterparties_map = {c.id: c.name for c in self._counterparty_use_cases.list_counterparties()}

        self._events_table.setRowCount(len(events))
        for i, e in enumerate(events):
            self._events_table.setItem(i, 0, QTableWidgetItem(e.event_date.isoformat()))
            self._events_table.setItem(i, 1, QTableWidgetItem(e.event_type))
            self._events_table.setItem(i, 2, QTableWidgetItem(e.description))
            self._events_table.setItem(i, 3, QTableWidgetItem(f"{e.currency} {e.amount:.2f}"))
            self._events_table.setItem(i, 4, QTableWidgetItem(e.currency))
            cat_name = categories_map.get(e.category_id, str(e.category_id or ""))
            self._events_table.setItem(i, 5, QTableWidgetItem(cat_name))
            if e.event_type == "transfer" and e.destination_account_id:
                src = accounts_map.get(e.account_id, str(e.account_id or ""))
                dst = accounts_map.get(e.destination_account_id, str(e.destination_account_id or ""))
                acc_display = f"{src} → {dst}"
            else:
                acc_display = accounts_map.get(e.account_id, str(e.account_id or ""))
            self._events_table.setItem(i, 6, QTableWidgetItem(acc_display))
            cp_name = counterparties_map.get(e.counterparty_id, str(e.counterparty_id or ""))
            self._events_table.setItem(i, 7, QTableWidgetItem(cp_name))
            self._events_table.setItem(i, 8, QTableWidgetItem(e.notes or ""))
            self._events_table.setItem(i, 9, QTableWidgetItem(e.id))

        self._events_table.resizeColumnsToContents()

    def _refresh_accounts(self):
        accounts = self._account_use_cases.list_accounts()
        self._accounts_table.setRowCount(len(accounts))
        for i, a in enumerate(accounts):
            self._accounts_table.setItem(i, 0, QTableWidgetItem(a.name))
            self._accounts_table.setItem(i, 1, QTableWidgetItem(a.type))
            self._accounts_table.setItem(i, 2, QTableWidgetItem(f"R$ {a.initial_balance:.2f}"))
            self._accounts_table.setItem(i, 3, QTableWidgetItem(a.id))
            self._accounts_table.setCellWidget(i, 4, self._make_actions_widget([
                ("Edit", lambda _, acc_id=a.id: self._edit_account(acc_id)),
            ]))
        self._accounts_table.resizeColumnsToContents()

    def _refresh_categories(self):
        categories = self._category_use_cases.list_categories()
        categories_map = {c.id: c.name for c in categories}
        self._categories_table.setRowCount(len(categories))
        for i, c in enumerate(categories):
            self._categories_table.setItem(i, 0, QTableWidgetItem(c.name))
            self._categories_table.setItem(i, 1, QTableWidgetItem(c.color or ""))
            parent_name = categories_map.get(c.parent_id, "") if c.parent_id else ""
            self._categories_table.setItem(i, 2, QTableWidgetItem(parent_name))
            self._categories_table.setCellWidget(i, 3, self._make_actions_widget([
                ("Edit", lambda _, cat_id=c.id: self._edit_category(cat_id)),
            ]))
        self._categories_table.resizeColumnsToContents()

    def _refresh_counterparties(self):
        counterparties = self._counterparty_use_cases.list_counterparties()
        self._counterparties_table.setRowCount(len(counterparties))
        for i, c in enumerate(counterparties):
            self._counterparties_table.setItem(i, 0, QTableWidgetItem(c.name))
            self._counterparties_table.setItem(i, 1, QTableWidgetItem(c.id))
            self._counterparties_table.setCellWidget(i, 2, self._make_actions_widget([
                ("Edit", lambda _, cp_id=c.id: self._edit_counterparty(cp_id)),
            ]))
        self._counterparties_table.resizeColumnsToContents()

    def _refresh_credit_cards(self):
        cards = self._credit_card_use_cases.list_cards()
        self._credit_cards_table.setRowCount(len(cards))
        for i, c in enumerate(cards):
            self._credit_cards_table.setItem(i, 0, QTableWidgetItem(c.name))
            self._credit_cards_table.setItem(i, 1, QTableWidgetItem(c.issuer))
            self._credit_cards_table.setItem(i, 2, QTableWidgetItem(f"R$ {c.credit_limit:.2f}"))
            self._credit_cards_table.setItem(i, 3, QTableWidgetItem(str(c.closing_day)))
            self._credit_cards_table.setItem(i, 4, QTableWidgetItem(str(c.due_day)))
            self._credit_cards_table.setItem(i, 5, QTableWidgetItem("Yes" if c.is_active else "No"))

            status = self._credit_card_use_cases.get_status(c.id)
            if status:
                self._credit_cards_table.setItem(i, 6, QTableWidgetItem(f"R$ {status.current_debt:.2f}"))
                self._credit_cards_table.setItem(i, 7, QTableWidgetItem(f"R$ {status.available_credit:.2f}"))
            else:
                self._credit_cards_table.setItem(i, 6, QTableWidgetItem("R$ 0.00"))
                self._credit_cards_table.setItem(i, 7, QTableWidgetItem(f"R$ {c.credit_limit:.2f}"))

            self._credit_cards_table.setCellWidget(i, 8, self._make_actions_widget([
                ("Edit", lambda _, card_id=c.id: self._edit_credit_card(card_id)),
            ]))

        self._credit_cards_table.resizeColumnsToContents()

    def _refresh_installments(self):
        credit_cards = self._credit_card_use_cases.list_cards()
        self._installments_widget.refresh(credit_cards=credit_cards)

    def _refresh_dashboard(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        events = self._financial_event_use_cases.list_events()
        self._dashboard.refresh(events, accounts, categories, counterparties)
