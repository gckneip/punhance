from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMenu,
    QTableWidget, QTableWidgetItem, QFileDialog,
    QLabel, QMessageBox, QDateEdit, QComboBox, QLineEdit, QAbstractItemView,
)
from datetime import date, timedelta

from src.application.use_cases.account_use_cases import AccountUseCases
from src.application.use_cases.category_use_cases import CategoryUseCases
from src.application.use_cases.counterparty_use_cases import CounterpartyUseCases
from src.application.use_cases.credit_card_use_cases import CreditCardUseCases
from src.application.use_cases.financial_event_use_cases import FinancialEventUseCases
from src.application.use_cases.purchase_use_cases import PurchaseUseCases
from src.application.use_cases.installment_use_cases import InstallmentUseCases
from src.application.use_cases.recurring_event_use_cases import RecurringEventUseCases
from src.application.dto.account_dto import CreateAccountDTO
from src.application.dto.category_dto import CreateCategoryDTO
from src.application.dto.counterparty_dto import CreateCounterpartyDTO
from src.application.dto.credit_card_dto import CreateCreditCardDTO
from src.application.dto.financial_event_dto import CreateFinancialEventDTO
from src.application.dto.purchase_dto import CreatePurchaseDTO, CreatePurchaseItemDTO
from src.application.dto.recurring_event_dto import CreateRecurringEventDTO
from src.domain.entities.purchase import PaymentMethod
from src.domain.entities.app_settings import NavigationStyle
from src.application.use_cases.dashboard_layout_use_cases import DashboardLayoutUseCases
from src.application.use_cases.app_settings_use_cases import AppSettingsUseCases
from src.domain.services.chart_data_service import ChartDataService
from src.presentation.dialogs.account_dialog import AccountDialog
from src.presentation.dialogs.category_dialog import CategoryDialog
from src.presentation.dialogs.counterparty_dialog import CounterpartyDialog
from src.presentation.dialogs.credit_card_dialog import CreditCardDialog
from src.presentation.dialogs.purchase_dialog import PurchaseDialog
from src.presentation.dialogs.event_dialog import EventDialog
from src.presentation.dialogs.recurring_event_dialog import RecurringEventDialog
from src.presentation.dialogs.settings_dialog import SettingsDialog
from src.presentation.dialogs.homebank_import_dialog import HomeBankImportPreviewDialog
from src.presentation.dialogs.homebank_export_dialog import HomeBankExportDialog
from src.infrastructure.homebank.xhb_reader import XhbParseError
from src.application.dto.homebank_dto import HomeBankExportOptionsDTO
from src.application.use_cases.theme_use_cases import ThemeUseCases
from src.infrastructure.theming.theme_parser import ThemeParseError
from src.presentation.app_restart import restart_app
from src.presentation.widgets.dashboard.dashboard_grid_widget import DashboardGridWidget
from src.presentation.widgets.installments_widget import InstallmentsWidget
from src.presentation.widgets.category_breakdown_widget import CategoryBreakdownWidget
from src.presentation.widgets.account_summary_widget import AccountSummaryWidget
from src.presentation.widgets.nav_host import TabNavHost, SidebarNavHost
from src.presentation import icons, theme


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
        recurring_event_use_cases: RecurringEventUseCases,
        dashboard_layout_use_cases: DashboardLayoutUseCases,
        app_settings_use_cases: AppSettingsUseCases,
        chart_data_service: ChartDataService,
        category_breakdown_service=None,
        account_summary_service=None,
        homebank_import_use_cases=None,
        homebank_export_use_cases=None,
        theme_use_cases: ThemeUseCases = None,
    ):
        super().__init__()
        self._account_use_cases = account_use_cases
        self._category_use_cases = category_use_cases
        self._counterparty_use_cases = counterparty_use_cases
        self._credit_card_use_cases = credit_card_use_cases
        self._financial_event_use_cases = financial_event_use_cases
        self._purchase_use_cases = purchase_use_cases
        self._installment_use_cases = installment_use_cases
        self._recurring_event_use_cases = recurring_event_use_cases
        self._app_settings_use_cases = app_settings_use_cases
        self._category_breakdown_service = category_breakdown_service
        self._account_summary_service = account_summary_service
        self._homebank_import_use_cases = homebank_import_use_cases
        self._homebank_export_use_cases = homebank_export_use_cases
        self._theme_use_cases = theme_use_cases

        self.setWindowTitle("Personal Finance Manager")
        self.setWindowIcon(icons.icon("fa6s.sack-dollar", color=theme.PRIMARY))
        self.resize(900, 600)

        self._navigation_style = app_settings_use_cases.get_navigation_style()
        self._build_ui()

        self._dashboard = DashboardGridWidget(
            dashboard_layout_use_cases, chart_data_service, financial_event_use_cases, purchase_use_cases
        )
        self._dashboard.entry_added.connect(self._refresh_all)
        self._dashboard.edit_event_requested.connect(self._edit_event)
        self._tabs.insertTab(0, self._dashboard, icons.icon("fa6s.gauge-high"), "Dashboard")
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
        for action in actions:
            label, icon_name, handler = action[:3]
            color = action[3] if len(action) > 3 else None
            btn = QPushButton()
            btn.setIcon(icons.icon(icon_name, color=color))
            btn.setToolTip(label)
            btn.setFixedWidth(32)
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

        self._btn_add = QPushButton("+ Add")
        self._btn_add.setObjectName("primaryButton")
        self._btn_add.setIcon(icons.icon("fa6s.circle-plus", color="white"))
        self._btn_add.setToolTip("Create a new event, purchase, recurring event, or bank transfer")
        toolbar.addWidget(self._btn_add)
        self._build_add_menu()

        toolbar.addStretch()

        self._btn_data = QPushButton()
        self._btn_data.setIcon(icons.icon("fa6s.file-import"))
        self._btn_data.setToolTip("Import / Export")
        self._btn_data.setFixedWidth(36)
        toolbar.addWidget(self._btn_data)
        self._build_data_menu()

        self._btn_settings = QPushButton()
        self._btn_settings.setIcon(icons.icon("fa6s.gear"))
        self._btn_settings.setToolTip("Settings")
        self._btn_settings.setFixedWidth(36)
        self._btn_settings.clicked.connect(self._open_settings)
        toolbar.addWidget(self._btn_settings)

        layout.addLayout(toolbar)

        self._tabs = TabNavHost() if self._navigation_style == NavigationStyle.TABS else SidebarNavHost()
        layout.addWidget(self._tabs)

        self._build_events_tab()
        self._build_accounts_tab()
        self._build_categories_tab()
        self._build_counterparties_tab()
        self._build_credit_cards_tab()
        self._build_installments_tab()
        self._build_recurring_events_tab()
        self._build_category_breakdown_tab()
        self._build_account_summary_tab()

    def _build_add_menu(self):
        menu = QMenu(self)

        action_event = menu.addAction(icons.icon("fa6s.circle-plus"), "Create Event")
        action_event.setShortcut(QKeySequence("Ctrl+N"))
        action_event.triggered.connect(self._add_event)

        action_purchase = menu.addAction(icons.icon("fa6s.cart-shopping"), "Create Purchase")
        action_purchase.setShortcut(QKeySequence("Ctrl+Shift+N"))
        action_purchase.triggered.connect(self._add_purchase)

        action_recurring = menu.addAction(icons.icon("fa6s.arrows-rotate"), "Create Recurring Event")
        action_recurring.triggered.connect(self._add_recurring_event)

        action_transfer = menu.addAction(icons.icon("fa6s.right-left"), "Create Bank Transfer")
        action_transfer.triggered.connect(self._add_transfer)

        self._btn_add.setMenu(menu)

    def _build_data_menu(self):
        menu = QMenu(self)

        action_import = menu.addAction(icons.icon("fa6s.file-import"), "Import from HomeBank...")
        action_import.triggered.connect(self._import_homebank)

        action_export = menu.addAction(icons.icon("fa6s.file-export"), "Export to HomeBank...")
        action_export.triggered.connect(self._export_homebank)

        self._btn_data.setMenu(menu)

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
        self._btn_filter.setIcon(icons.icon("fa6s.magnifying-glass"))
        self._btn_filter.clicked.connect(self._refresh_events)
        filter_row.addWidget(self._btn_filter)

        filter_row.addStretch()

        self._btn_delete_selected_events = QPushButton("Delete Selected")
        self._btn_delete_selected_events.setIcon(icons.icon("fa6s.trash", color=theme.EXPENSE))
        self._btn_delete_selected_events.clicked.connect(self._delete_selected_events)
        filter_row.addWidget(self._btn_delete_selected_events)

        layout.addLayout(filter_row)

        self._events_table = QTableWidget()
        self._events_table.setColumnCount(11)
        self._events_table.setHorizontalHeaderLabels(
            ["Date", "Type", "Description", "Amount", "Currency", "Category", "Account", "Counterparty", "Notes", "ID", "Actions"]
        )
        self._events_table.horizontalHeader().setStretchLastSection(True)
        self._events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._events_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._events_table.setAlternatingRowColors(True)
        layout.addWidget(self._events_table)

        self._tabs.addTab(tab, icons.icon("fa6s.list"), "Events")

    def _build_accounts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Account")
        btn.setIcon(icons.icon("fa6s.wallet"))
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

        self._tabs.addTab(tab, icons.icon("fa6s.wallet"), "Accounts")

    def _build_categories_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Category")
        btn.setIcon(icons.icon("fa6s.tag"))
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

        self._tabs.addTab(tab, icons.icon("fa6s.tag"), "Categories")

    def _build_counterparties_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Counterparty")
        btn.setIcon(icons.icon("fa6s.user-group"))
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

        self._tabs.addTab(tab, icons.icon("fa6s.user-group"), "Counterparties")

    def _build_credit_cards_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Credit Card")
        btn.setIcon(icons.icon("fa6s.credit-card"))
        btn.clicked.connect(self._add_credit_card)
        btn_row.addWidget(btn)

        self._btn_pay_card = QPushButton("Pay Card")
        self._btn_pay_card.setIcon(icons.icon("fa6s.money-bill-wave"))
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

        self._tabs.addTab(tab, icons.icon("fa6s.credit-card"), "Credit Cards")

    def _build_installments_tab(self):
        self._installments_widget = InstallmentsWidget(
            self._installment_use_cases,
        )
        self._tabs.addTab(self._installments_widget, icons.icon("fa6s.calendar-days"), "Installments")

    def _build_recurring_events_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton("+ Recurring Event")
        btn.setIcon(icons.icon("fa6s.arrows-rotate"))
        btn.clicked.connect(self._add_recurring_event)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._recurring_events_table = QTableWidget()
        self._recurring_events_table.setColumnCount(9)
        self._recurring_events_table.setHorizontalHeaderLabels(
            ["Description", "Amount", "Frequency", "Anchor", "Start", "End", "Active", "ID", "Actions"]
        )
        self._recurring_events_table.horizontalHeader().setStretchLastSection(True)
        self._recurring_events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._recurring_events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._recurring_events_table.setAlternatingRowColors(True)
        layout.addWidget(self._recurring_events_table)

        self._tabs.addTab(tab, icons.icon("fa6s.arrows-rotate"), "Recurring Events")

    def _build_category_breakdown_tab(self):
        if self._category_breakdown_service:
            self._category_breakdown_widget = CategoryBreakdownWidget(
                self._category_breakdown_service,
                self._category_use_cases,
            )
            self._tabs.addTab(self._category_breakdown_widget, icons.icon("fa6s.chart-pie"), "Category Breakdown")

    def _build_account_summary_tab(self):
        if self._account_summary_service:
            self._account_summary_widget = AccountSummaryWidget(
                self._account_summary_service,
            )
            self._tabs.addTab(self._account_summary_widget, icons.icon("fa6s.chart-line"), "Account Summary")

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

    def _add_recurring_event(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        credit_cards = self._credit_card_use_cases.list_cards()

        dialog = RecurringEventDialog(accounts, categories, counterparties, credit_cards, self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateRecurringEventDTO(**data)
            self._recurring_event_use_cases.create_recurring_event(dto)
            self._refresh_all()

    def _edit_recurring_event(self, recurring_event_id):
        templates = {r.id: r for r in self._recurring_event_use_cases.list_recurring_events()}
        template = templates.get(recurring_event_id)
        if template is None:
            return

        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        credit_cards = self._credit_card_use_cases.list_cards()

        dialog = RecurringEventDialog(
            accounts, categories, counterparties, credit_cards, self, recurring_event=template
        )
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateRecurringEventDTO(**data)
            self._recurring_event_use_cases.update_recurring_event(recurring_event_id, dto)
            self._refresh_all()

    def _delete_recurring_event(self, recurring_event_id):
        reply = QMessageBox.question(
            self,
            "Delete Recurring Event",
            "Delete this recurring event? Already-confirmed events are kept; "
            "any pending (unconfirmed) occurrences will disappear.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._recurring_event_use_cases.delete_recurring_event(recurring_event_id)
        self._refresh_all()

    def _recurring_anchor_label(self, r) -> str:
        if r.frequency == "weekly" and r.weekday is not None:
            names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            return names[r.weekday]
        if r.frequency == "monthly" and r.day_of_month is not None:
            return f"Day {r.day_of_month}"
        if r.frequency == "yearly" and r.month is not None and r.day_of_month is not None:
            return f"{r.month:02d}/{r.day_of_month:02d}"
        return ""

    def _confirm_occurrence(self, occurrence):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()

        dialog = EventDialog(accounts, categories, counterparties, self, event=occurrence)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(credit_card_id=occurrence.credit_card_id, **data)
            self._recurring_event_use_cases.confirm_occurrence(
                occurrence.recurring_event_id, occurrence.occurrence_date, dto
            )
            self._refresh_all()

    def _skip_occurrence(self, recurring_event_id, occurrence_date):
        reply = QMessageBox.question(
            self,
            "Skip Occurrence",
            "Skip this occurrence? It won't be shown again.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._recurring_event_use_cases.skip_occurrence(recurring_event_id, occurrence_date)
        self._refresh_all()

    def _add_event(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()

        dialog = EventDialog(accounts, categories, counterparties, self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(**data)
            self._financial_event_use_cases.create_event(dto)
            self._refresh_all()

    def _add_transfer(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()

        dialog = EventDialog(accounts, categories, counterparties, self)
        index = dialog.type_combo.findText("transfer")
        if index >= 0:
            dialog.type_combo.setCurrentIndex(index)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(**data)
            self._financial_event_use_cases.create_event(dto)
            self._refresh_all()

    def _import_homebank(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import HomeBank File", "", "HomeBank Files (*.xhb);;All Files (*)"
        )
        if not path:
            return

        try:
            plan = self._homebank_import_use_cases.build_import_plan(path)
        except XhbParseError as exc:
            QMessageBox.critical(self, "Import Error", f"Could not read this HomeBank file:\n{exc}")
            return

        dialog = HomeBankImportPreviewDialog(plan.to_preview_dto(), self)
        if not dialog.exec():
            return

        result = self._homebank_import_use_cases.commit_import_plan(plan)
        self._refresh_all()

        summary = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in result.created_counts.items() if v)
        message = f"Import complete: {summary or 'nothing to import'}."
        if result.warnings:
            message += f"\n\n{len(result.warnings)} item(s) had issues during import."
        QMessageBox.information(self, "Import from HomeBank", message)

    def _export_homebank(self):
        options_dialog = HomeBankExportDialog(self)
        if not options_dialog.exec():
            return
        options_data = options_dialog.get_data()

        path, _ = QFileDialog.getSaveFileName(
            self, "Export to HomeBank File", "export.xhb", "HomeBank Files (*.xhb)"
        )
        if not path:
            return
        if not path.lower().endswith(".xhb"):
            path += ".xhb"

        options = HomeBankExportOptionsDTO(**options_data)
        result = self._homebank_export_use_cases.export(path, options)

        summary = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in result.counts.items() if v)
        message = f"Exported to {result.path}\n\n{summary or 'nothing to export'}."
        if result.warnings:
            message += f"\n\n{len(result.warnings)} item(s) had issues during export."
        QMessageBox.information(self, "Export to HomeBank", message)

    def _open_settings(self):
        current_style = self._app_settings_use_cases.get_navigation_style()
        current_theme_id = self._app_settings_use_cases.get_current_theme_id()
        available_themes = self._theme_use_cases.list_available_themes() if self._theme_use_cases else []

        dialog = SettingsDialog(current_style, current_theme_id, available_themes, self)
        dialog.import_theme_requested.connect(lambda: self._handle_theme_import(dialog))
        if dialog.exec():
            data = dialog.get_data()
            changes = []
            if data["navigation_style"] != current_style:
                changes.append("navigation style")
            if data["theme_id"] and data["theme_id"] != current_theme_id:
                changes.append("theme")

            if not changes:
                return

            box = QMessageBox(self)
            box.setWindowTitle("Restart Required")
            box.setText(
                f"Restart Finance Manager for the new {' and '.join(changes)} to take effect."
            )
            restart_button = box.addButton("Restart Now", QMessageBox.AcceptRole)
            box.addButton("Discard Changes", QMessageBox.RejectRole)
            box.setDefaultButton(restart_button)
            box.exec()

            if box.clickedButton() is not restart_button:
                return

            if data["navigation_style"] != current_style:
                self._app_settings_use_cases.set_navigation_style(data["navigation_style"])
            if data["theme_id"] and data["theme_id"] != current_theme_id:
                self._app_settings_use_cases.set_current_theme_id(data["theme_id"])
            restart_app()

    def _handle_theme_import(self, dialog):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Theme", "", "Theme Files (*.json);;All Files (*)"
        )
        if not path:
            return

        try:
            result = self._theme_use_cases.import_theme_file(path)
        except ThemeParseError as exc:
            QMessageBox.critical(self, "Import Error", f"Could not read this theme file:\n{exc}")
            return

        all_themes = self._theme_use_cases.list_available_themes()
        dialog.select_theme(result.theme_id, result.name, all_themes)

        message = f"Imported theme '{result.name}'."
        if result.warnings:
            message += (
                f"\n\n{len(result.warnings)} color(s) were defaulted or ignored:\n"
                + "\n".join(f"- {w}" for w in result.warnings)
            )
        QMessageBox.information(self, "Import Theme", message)

    def _edit_event(self, event_id):
        events = {e.id: e for e in self._financial_event_use_cases.list_events()}
        event = events.get(event_id)
        if event is None:
            return

        if event.event_type == "purchase":
            self._edit_purchase(event_id)
            return

        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()

        dialog = EventDialog(accounts, categories, counterparties, self, event=event)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(credit_card_id=event.credit_card_id, **data)
            self._financial_event_use_cases.update_event(event_id, dto)
            self._refresh_all()

    def _edit_purchase(self, event_id):
        purchase_data = self._purchase_use_cases.get_purchase_by_event(event_id)
        if purchase_data is None:
            return

        categories = self._category_use_cases.list_categories()
        credit_cards = self._credit_card_use_cases.list_cards()
        counterparties = self._counterparty_use_cases.list_counterparties()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        dialog = PurchaseDialog(
            categories, credit_cards, counterparties, create_counterparty, self,
            purchase_data=purchase_data,
        )
        if dialog.exec():
            data = dialog.get_data()
            items = [
                CreatePurchaseItemDTO(
                    name=i["name"],
                    quantity=i["quantity"],
                    unit=i["unit"],
                    unit_price=i["unit_price"],
                    total_price=i["total_price"],
                    category_id=i["category_id"],
                )
                for i in data["items"]
            ]

            dto = CreatePurchaseDTO(
                event_date=data["event_date"],
                description=data["description"],
                total_amount=data["total_amount"],
                payment_method=PaymentMethod(data["payment_method"]),
                credit_card_id=data["credit_card_id"],
                notes=data["notes"],
                installment_count=data["installment_count"],
                remainder_on_first=data["remainder_on_first"],
                counterparty_id=data["counterparty_id"],
                category_id=data["category_id"],
                items=items,
            )
            result = self._purchase_use_cases.update_purchase(purchase_data["purchase"].id, dto)
            if result and result.get("warnings"):
                QMessageBox.warning(self, "Purchase Warning", "\n".join(result["warnings"]))
            self._refresh_all()

    def _delete_event_cascade(self, event_id):
        self._purchase_use_cases.delete_purchase_by_event(event_id)
        self._financial_event_use_cases.delete_event(event_id)

    def _delete_event(self, event_id):
        reply = QMessageBox.question(
            self,
            "Delete Event",
            "Are you sure you want to delete this event?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._delete_event_cascade(event_id)
        self._refresh_all()

    def _delete_selected_events(self):
        rows = sorted({idx.row() for idx in self._events_table.selectionModel().selectedRows()})
        event_ids = [
            self._events_table.item(r, 9).text()
            for r in rows
            if self._events_table.item(r, 9) is not None
            and not self._events_table.item(r, 9).text().startswith("virtual:")
        ]
        if not event_ids:
            return
        reply = QMessageBox.question(
            self,
            "Delete Events",
            f"Are you sure you want to delete {len(event_ids)} selected event(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for event_id in event_ids:
            self._delete_event_cascade(event_id)
        self._refresh_all()

    def _add_purchase(self):
        categories = self._category_use_cases.list_categories()
        credit_cards = self._credit_card_use_cases.list_cards()
        counterparties = self._counterparty_use_cases.list_counterparties()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        dialog = PurchaseDialog(categories, credit_cards, counterparties, create_counterparty, self)
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
                remainder_on_first=data["remainder_on_first"],
                counterparty_id=data["counterparty_id"],
                category_id=data["category_id"],
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
        self._refresh_recurring_events()
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
        # date_to is an exclusive upper bound in the repository/service layer, but
        # the "To" date picker is meant to be inclusive of that whole day.
        date_to_exclusive = date_to + timedelta(days=1)

        events = self._financial_event_use_cases.list_events(
            date_from=date_from,
            date_to=date_to_exclusive,
            description=description,
            category_id=category_id,
            account_id=account_id,
        )
        occurrences = self._recurring_event_use_cases.get_pending_occurrences(
            date_from, date_to_exclusive,
            category_id=category_id, account_id=account_id, description=description,
        )

        accounts_map = {a.id: a.name for a in self._account_use_cases.list_accounts()}
        categories_map = {c.id: c.name for c in self._category_use_cases.list_categories()}
        counterparties_map = {c.id: c.name for c in self._counterparty_use_cases.list_counterparties()}
        multi_category_event_ids = self._purchase_use_cases.get_multi_category_event_ids()

        rows = [(e.event_date, False, e) for e in events]
        rows += [(o.occurrence_date, True, o) for o in occurrences]
        rows.sort(key=lambda r: r[0], reverse=True)

        self._events_table.setRowCount(len(rows))
        for i, (_, is_virtual, payload) in enumerate(rows):
            if is_virtual:
                self._populate_virtual_event_row(i, payload, categories_map, accounts_map, counterparties_map)
            else:
                self._populate_real_event_row(
                    i, payload, categories_map, accounts_map, counterparties_map, multi_category_event_ids
                )

        self._events_table.resizeColumnsToContents()

    def _populate_real_event_row(self, i, e, categories_map, accounts_map, counterparties_map, multi_category_event_ids):
        self._events_table.setItem(i, 0, QTableWidgetItem(e.event_date.isoformat()))
        self._events_table.setItem(i, 1, QTableWidgetItem(e.event_type))
        self._events_table.setItem(i, 2, QTableWidgetItem(e.description))
        self._events_table.setItem(i, 3, QTableWidgetItem(f"{e.currency} {e.amount:.2f}"))
        self._events_table.setItem(i, 4, QTableWidgetItem(e.currency))
        if e.category_id is None and e.id in multi_category_event_ids:
            cat_name = "Multiple"
        else:
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
        self._events_table.setCellWidget(i, 10, self._make_actions_widget([
            ("Edit", "fa6s.pen", lambda _, event_id=e.id: self._edit_event(event_id)),
            ("Delete", "fa6s.trash", lambda _, event_id=e.id: self._delete_event(event_id), theme.EXPENSE),
        ]))

    def _populate_virtual_event_row(self, i, o, categories_map, accounts_map, counterparties_map):
        italic_font = QFont()
        italic_font.setItalic(True)

        def _item(text):
            item = QTableWidgetItem(text)
            item.setFont(italic_font)
            return item

        self._events_table.setItem(i, 0, _item(o.occurrence_date.isoformat()))
        self._events_table.setItem(i, 1, _item(f"{o.event_type} (recurring)"))
        self._events_table.setItem(i, 2, _item(o.description))
        self._events_table.setItem(i, 3, _item(f"{o.currency} {o.amount:.2f}"))
        self._events_table.setItem(i, 4, _item(o.currency))
        self._events_table.setItem(i, 5, _item(categories_map.get(o.category_id, str(o.category_id or ""))))
        self._events_table.setItem(i, 6, _item(accounts_map.get(o.account_id, str(o.account_id or ""))))
        self._events_table.setItem(i, 7, _item(counterparties_map.get(o.counterparty_id, str(o.counterparty_id or ""))))
        self._events_table.setItem(i, 8, _item(o.notes or ""))
        self._events_table.setItem(
            i, 9, _item(f"virtual:{o.recurring_event_id}:{o.occurrence_date.isoformat()}")
        )
        self._events_table.setCellWidget(i, 10, self._make_actions_widget([
            ("Confirm", "fa6s.check", lambda _, occ=o: self._confirm_occurrence(occ), theme.INCOME),
            (
                "Skip", "fa6s.forward-step",
                lambda _, rid=o.recurring_event_id, od=o.occurrence_date: self._skip_occurrence(rid, od),
                theme.EXPENSE,
            ),
        ]))

    def _refresh_recurring_events(self):
        templates = self._recurring_event_use_cases.list_recurring_events()
        self._recurring_events_table.setRowCount(len(templates))
        for i, r in enumerate(templates):
            self._recurring_events_table.setItem(i, 0, QTableWidgetItem(r.description))
            self._recurring_events_table.setItem(i, 1, QTableWidgetItem(f"{r.currency} {r.amount:.2f}"))
            freq_label = r.frequency.capitalize() if r.interval == 1 else f"Every {r.interval} {r.frequency}s"
            self._recurring_events_table.setItem(i, 2, QTableWidgetItem(freq_label))
            self._recurring_events_table.setItem(i, 3, QTableWidgetItem(self._recurring_anchor_label(r)))
            self._recurring_events_table.setItem(i, 4, QTableWidgetItem(r.start_date.isoformat()))
            self._recurring_events_table.setItem(
                i, 5, QTableWidgetItem(r.end_date.isoformat() if r.end_date else "")
            )
            self._recurring_events_table.setItem(i, 6, QTableWidgetItem("Yes" if r.is_active else "No"))
            self._recurring_events_table.setItem(i, 7, QTableWidgetItem(r.id))
            self._recurring_events_table.setCellWidget(i, 8, self._make_actions_widget([
                ("Edit", "fa6s.pen", lambda _, rid=r.id: self._edit_recurring_event(rid)),
                ("Delete", "fa6s.trash", lambda _, rid=r.id: self._delete_recurring_event(rid), theme.EXPENSE),
            ]))
        self._recurring_events_table.resizeColumnsToContents()

    def _refresh_accounts(self):
        accounts = self._account_use_cases.list_accounts()
        self._accounts_table.setRowCount(len(accounts))
        for i, a in enumerate(accounts):
            self._accounts_table.setItem(i, 0, QTableWidgetItem(a.name))
            self._accounts_table.setItem(i, 1, QTableWidgetItem(a.type))
            self._accounts_table.setItem(i, 2, QTableWidgetItem(f"R$ {a.initial_balance:.2f}"))
            self._accounts_table.setItem(i, 3, QTableWidgetItem(a.id))
            self._accounts_table.setCellWidget(i, 4, self._make_actions_widget([
                ("Edit", "fa6s.pen", lambda _, acc_id=a.id: self._edit_account(acc_id)),
            ]))
        self._accounts_table.resizeColumnsToContents()
        self._accounts_table.resizeRowsToContents()

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
                ("Edit", "fa6s.pen", lambda _, cat_id=c.id: self._edit_category(cat_id)),
            ]))
        self._categories_table.resizeColumnsToContents()
        self._categories_table.resizeRowsToContents()

    def _refresh_counterparties(self):
        counterparties = self._counterparty_use_cases.list_counterparties()
        self._counterparties_table.setRowCount(len(counterparties))
        for i, c in enumerate(counterparties):
            self._counterparties_table.setItem(i, 0, QTableWidgetItem(c.name))
            self._counterparties_table.setItem(i, 1, QTableWidgetItem(c.id))
            self._counterparties_table.setCellWidget(i, 2, self._make_actions_widget([
                ("Edit", "fa6s.pen", lambda _, cp_id=c.id: self._edit_counterparty(cp_id)),
            ]))
        self._counterparties_table.resizeColumnsToContents()
        self._counterparties_table.resizeRowsToContents()

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
                ("Edit", "fa6s.pen", lambda _, card_id=c.id: self._edit_credit_card(card_id)),
            ]))

        self._credit_cards_table.resizeColumnsToContents()
        self._credit_cards_table.resizeRowsToContents()

    def _refresh_installments(self):
        credit_cards = self._credit_card_use_cases.list_cards()
        self._installments_widget.refresh(credit_cards=credit_cards)

    def _refresh_dashboard(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        events = self._financial_event_use_cases.list_events()
        purchases = self._purchase_use_cases.list_purchases()
        multi_category_event_ids = self._purchase_use_cases.get_multi_category_event_ids()
        credit_cards = self._credit_card_use_cases.list_cards()
        installments_by_event = self._purchase_use_cases.get_multi_installment_map()
        self._dashboard.refresh(
            events, accounts, categories, counterparties, purchases, multi_category_event_ids, credit_cards,
            installments_by_event,
        )
