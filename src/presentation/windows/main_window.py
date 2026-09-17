from PySide6.QtCore import Qt, QSize
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
from src.application.dto.product_dto import CreateProductDTO
from src.application.dto.recurring_event_dto import CreateRecurringEventDTO
from src.domain.entities.purchase import PaymentMethod
from src.domain.entities.app_settings import NavigationStyle
from src.application.use_cases.dashboard_layout_use_cases import DashboardLayoutUseCases
from src.application.use_cases.dashboard_report_use_cases import DashboardReportUseCases
from src.application.use_cases.app_settings_use_cases import AppSettingsUseCases
from src.domain.services.chart_data_service import ChartDataService
from src.presentation.dialogs.account_dialog import AccountDialog
from src.presentation.dialogs.category_dialog import CategoryDialog
from src.presentation.dialogs.counterparty_dialog import CounterpartyDialog
from src.presentation.dialogs.product_dialog import ProductDialog
from src.presentation.dialogs.product_detail_dialog import ProductDetailDialog
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
from src.presentation.widgets.dashboard.dashboard_tabs_widget import DashboardTabsWidget
from src.presentation.widgets.dashboard.chart_widget import PieChartWidget
from src.presentation.widgets.date_range_selector import DateRangeSelector
from src.presentation.widgets.installments_widget import InstallmentsWidget
from src.presentation.widgets.calendar_widget import CalendarWidget
from src.presentation.widgets.category_breakdown_widget import CategoryBreakdownWidget
from src.presentation.widgets.account_summary_widget import AccountSummaryWidget
from src.presentation.widgets.nav_host import TabNavHost, SidebarNavHost
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from src.presentation import icons, theme, i18n
from src.presentation.i18n import t, format_currency, format_date
from src.presentation.labels import (
    event_type_label, account_type_label, recurrence_frequency_label,
)


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
        dashboard_report_use_cases: DashboardReportUseCases,
        app_settings_use_cases: AppSettingsUseCases,
        chart_data_service: ChartDataService,
        category_breakdown_service=None,
        account_summary_service=None,
        homebank_import_use_cases=None,
        homebank_export_use_cases=None,
        theme_use_cases: ThemeUseCases = None,
        product_use_cases=None,
        dashboard_widget_template_use_cases=None,
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
        self._product_use_cases = product_use_cases
        self._dashboard_widget_template_use_cases = dashboard_widget_template_use_cases

        self.setWindowTitle(t("app.title"))
        self.setWindowIcon(icons.icon("fa6s.sack-dollar", color=theme.PRIMARY))
        self.resize(900, 600)

        self._navigation_style = app_settings_use_cases.get_navigation_style()
        self._build_ui()

        self._dashboard = DashboardTabsWidget(
            dashboard_report_use_cases, dashboard_layout_use_cases, chart_data_service,
            financial_event_use_cases, purchase_use_cases,
            dashboard_widget_template_use_cases=dashboard_widget_template_use_cases,
        )
        self._dashboard.entry_added.connect(self._refresh_all)
        self._dashboard.edit_event_requested.connect(self._edit_event)
        self._tabs.insertTab(0, self._dashboard, icons.icon("fa6s.gauge-high"), t("mainwindow.tab.dashboard"))
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
            btn.setIconSize(QSize(18, 18))
            btn.setToolTip(label)
            btn.setFixedSize(36, 36)
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

        self._btn_add = QPushButton(t("mainwindow.btn.add"))
        self._btn_add.setObjectName("primaryButton")
        self._btn_add.setIcon(icons.icon("fa6s.circle-plus", color="white"))
        self._btn_add.setToolTip(t("mainwindow.tooltip.add"))
        toolbar.addWidget(self._btn_add)
        self._build_add_menu()

        toolbar.addStretch()

        self._btn_data = QPushButton()
        self._btn_data.setIcon(icons.icon("fa6s.file-import"))
        self._btn_data.setToolTip(t("mainwindow.tooltip.data"))
        self._btn_data.setFixedWidth(36)
        toolbar.addWidget(self._btn_data)
        self._build_data_menu()

        self._btn_settings = QPushButton()
        self._btn_settings.setIcon(icons.icon("fa6s.gear"))
        self._btn_settings.setToolTip(t("mainwindow.tooltip.settings"))
        self._btn_settings.setFixedWidth(36)
        self._btn_settings.clicked.connect(self._open_settings)
        toolbar.addWidget(self._btn_settings)

        layout.addLayout(toolbar)

        if self._navigation_style == NavigationStyle.TABS:
            self._tabs = TabNavHost()
        else:
            self._tabs = SidebarNavHost(mode=self._app_settings_use_cases.get_sidebar_mode())
            self._tabs.mode_changed.connect(self._app_settings_use_cases.set_sidebar_mode)
        layout.addWidget(self._tabs)

        self._build_events_tab()
        self._build_calendar_tab()
        self._build_accounts_tab()
        self._build_categories_tab()
        self._build_counterparties_tab()
        self._build_products_tab()
        self._build_credit_cards_tab()
        self._build_installments_tab()
        self._build_recurring_events_tab()
        self._build_category_breakdown_tab()
        self._build_account_summary_tab()

    def _build_add_menu(self):
        menu = QMenu(self)

        action_event = menu.addAction(icons.icon("fa6s.circle-plus"), t("mainwindow.menu.create_event"))
        action_event.setShortcut(QKeySequence("Ctrl+N"))
        action_event.triggered.connect(self._add_event)

        action_purchase = menu.addAction(icons.icon("fa6s.cart-shopping"), t("mainwindow.menu.create_purchase"))
        action_purchase.setShortcut(QKeySequence("Ctrl+Shift+N"))
        action_purchase.triggered.connect(self._add_purchase)

        action_recurring = menu.addAction(icons.icon("fa6s.arrows-rotate"), t("mainwindow.menu.create_recurring_event"))
        action_recurring.triggered.connect(self._add_recurring_event)

        action_transfer = menu.addAction(icons.icon("fa6s.right-left"), t("mainwindow.menu.create_transfer"))
        action_transfer.triggered.connect(self._add_transfer)

        self._btn_add.setMenu(menu)

    def _build_data_menu(self):
        menu = QMenu(self)

        action_import = menu.addAction(icons.icon("fa6s.file-import"), t("mainwindow.menu.import_homebank"))
        action_import.triggered.connect(self._import_homebank)

        action_export = menu.addAction(icons.icon("fa6s.file-export"), t("mainwindow.menu.export_homebank"))
        action_export.triggered.connect(self._export_homebank)

        self._btn_data.setMenu(menu)

    def _build_events_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        filter_row = QHBoxLayout()

        self._filter_date_from = QDateEdit()
        self._filter_date_from.setCalendarPopup(True)
        self._filter_date_from.setDate(date(date.today().year, date.today().month, 1))
        filter_row.addWidget(QLabel(t("mainwindow.filter.from")))
        filter_row.addWidget(self._filter_date_from)

        self._filter_date_to = QDateEdit()
        self._filter_date_to.setCalendarPopup(True)
        self._filter_date_to.setDate(date.today())
        filter_row.addWidget(QLabel(t("mainwindow.filter.to")))
        filter_row.addWidget(self._filter_date_to)

        self._filter_description = QLineEdit()
        self._filter_description.setPlaceholderText(t("mainwindow.filter.search_description_placeholder"))
        filter_row.addWidget(QLabel(t("mainwindow.filter.desc")))
        filter_row.addWidget(self._filter_description)

        self._filter_category = QComboBox()
        self._filter_category.addItem(t("mainwindow.filter.all_categories"), None)
        filter_row.addWidget(QLabel(t("mainwindow.filter.category")))
        filter_row.addWidget(self._filter_category)

        self._filter_account = QComboBox()
        self._filter_account.addItem(t("mainwindow.filter.all_accounts"), None)
        filter_row.addWidget(QLabel(t("mainwindow.filter.account")))
        filter_row.addWidget(self._filter_account)

        self._btn_filter = QPushButton(t("common.search"))
        self._btn_filter.setIcon(icons.icon("fa6s.magnifying-glass"))
        self._btn_filter.clicked.connect(self._refresh_events)
        filter_row.addWidget(self._btn_filter)

        filter_row.addStretch()

        self._btn_delete_selected_events = QPushButton(t("common.delete_selected"))
        self._btn_delete_selected_events.setIcon(icons.icon("fa6s.trash", color=theme.EXPENSE))
        self._btn_delete_selected_events.clicked.connect(self._delete_selected_events)
        filter_row.addWidget(self._btn_delete_selected_events)

        layout.addLayout(filter_row)

        self._events_table = EvenColumnsTableWidget()
        self._events_table.setColumnCount(10)
        self._events_table.setHorizontalHeaderLabels([
            t("common.date"), t("common.type"), t("common.description"), t("common.amount"),
            t("mainwindow.table.events.header.currency"), t("common.category"), t("common.account"),
            t("mainwindow.table.events.header.counterparty"), t("mainwindow.table.events.header.notes"),
            t("common.actions"),
        ])
        self._events_table.setObjectName("mainTabTable")
        self._events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._events_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._events_table.setAlternatingRowColors(True)
        layout.addWidget(self._events_table)

        self._tabs.addTab(tab, icons.icon("fa6s.list"), t("mainwindow.tab.events"))

    def _build_accounts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton(t("mainwindow.btn.add_account"))
        btn.setIcon(icons.icon("fa6s.wallet"))
        btn.clicked.connect(self._add_account)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._accounts_table = EvenColumnsTableWidget()
        self._accounts_table.setColumnCount(5)
        self._accounts_table.setHorizontalHeaderLabels([
            t("common.name"), t("common.type"), t("mainwindow.table.accounts.header.initial_balance"),
            t("mainwindow.table.header.id"), t("common.actions"),
        ])
        self._accounts_table.setObjectName("mainTabTable")
        self._accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._accounts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._accounts_table.setAlternatingRowColors(True)
        layout.addWidget(self._accounts_table)

        self._tabs.addTab(tab, icons.icon("fa6s.wallet"), t("mainwindow.tab.accounts"))

    def _build_categories_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton(t("mainwindow.btn.add_category"))
        btn.setIcon(icons.icon("fa6s.tag"))
        btn.clicked.connect(self._add_category)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._categories_table = EvenColumnsTableWidget()
        self._categories_table.setColumnCount(4)
        self._categories_table.setHorizontalHeaderLabels([
            t("common.name"), t("mainwindow.table.categories.header.color"),
            t("mainwindow.table.categories.header.parent"), t("common.actions"),
        ])
        self._categories_table.setObjectName("mainTabTable")
        self._categories_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._categories_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._categories_table.setAlternatingRowColors(True)
        layout.addWidget(self._categories_table)

        self._tabs.addTab(tab, icons.icon("fa6s.tag"), t("mainwindow.tab.categories"))

    def _build_counterparties_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton(t("mainwindow.btn.add_counterparty"))
        btn.setIcon(icons.icon("fa6s.user-group"))
        btn.clicked.connect(self._add_counterparty)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._counterparties_table = EvenColumnsTableWidget()
        self._counterparties_table.setColumnCount(3)
        self._counterparties_table.setHorizontalHeaderLabels([
            t("common.name"), t("mainwindow.table.header.id"), t("common.actions"),
        ])
        self._counterparties_table.setObjectName("mainTabTable")
        self._counterparties_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._counterparties_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._counterparties_table.setAlternatingRowColors(True)
        layout.addWidget(self._counterparties_table)

        self._tabs.addTab(tab, icons.icon("fa6s.user-group"), t("mainwindow.tab.counterparties"))

    def _build_products_tab(self):
        tab = QWidget()
        outer_layout = QHBoxLayout(tab)

        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        btn = QPushButton(t("mainwindow.btn.add_product"))
        btn.setIcon(icons.icon("fa6s.box"))
        btn.clicked.connect(self._add_product)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._product_search = QLineEdit()
        self._product_search.setPlaceholderText(t("mainwindow.filter.search_products_placeholder"))
        self._product_search.textChanged.connect(self._refresh_products)
        layout.addWidget(self._product_search)

        self._products_table = EvenColumnsTableWidget()
        self._products_table.setColumnCount(4)
        self._products_table.setHorizontalHeaderLabels([
            t("common.name"),
            t("mainwindow.table.products.header.avg_price"),
            t("mainwindow.table.products.header.best_price"),
            t("common.actions"),
        ])
        self._products_table.setObjectName("mainTabTable")
        self._products_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._products_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._products_table.setAlternatingRowColors(True)
        layout.addWidget(self._products_table)

        outer_layout.addWidget(left, 2)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        chart_header = QHBoxLayout()
        chart_header.addWidget(QLabel(t("mainwindow.products.chart_title")))
        chart_header.addStretch()
        self._product_chart_range = DateRangeSelector(default_label="All Time")
        self._product_chart_range.range_changed.connect(lambda _d: self._refresh_products())
        chart_header.addWidget(self._product_chart_range)
        right_layout.addLayout(chart_header)

        self._product_pie_chart = PieChartWidget()
        right_layout.addWidget(self._product_pie_chart, 1)

        outer_layout.addWidget(right, 1)

        self._tabs.addTab(tab, icons.icon("fa6s.box"), t("mainwindow.tab.products"))

    def _build_credit_cards_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton(t("mainwindow.btn.add_credit_card"))
        btn.setIcon(icons.icon("fa6s.credit-card"))
        btn.clicked.connect(self._add_credit_card)
        btn_row.addWidget(btn)

        self._btn_pay_card = QPushButton(t("mainwindow.btn.pay_card"))
        self._btn_pay_card.setIcon(icons.icon("fa6s.money-bill-wave"))
        self._btn_pay_card.clicked.connect(self._pay_card)
        btn_row.addWidget(self._btn_pay_card)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._credit_cards_table = EvenColumnsTableWidget()
        self._credit_cards_table.setColumnCount(9)
        self._credit_cards_table.setHorizontalHeaderLabels([
            t("common.name"), t("mainwindow.table.cards.header.issuer"),
            t("mainwindow.table.cards.header.credit_limit"), t("mainwindow.table.cards.header.closing_day"),
            t("mainwindow.table.cards.header.due_day"), t("mainwindow.table.header.active"),
            t("mainwindow.table.cards.header.current_debt"), t("mainwindow.table.cards.header.available_credit"),
            t("common.actions"),
        ])
        self._credit_cards_table.setObjectName("mainTabTable")
        self._credit_cards_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._credit_cards_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._credit_cards_table.setAlternatingRowColors(True)
        layout.addWidget(self._credit_cards_table)

        self._tabs.addTab(tab, icons.icon("fa6s.credit-card"), t("mainwindow.tab.credit_cards"))

    def _build_calendar_tab(self):
        self._calendar_widget = CalendarWidget(
            self._financial_event_use_cases,
            self._recurring_event_use_cases,
            self._installment_use_cases,
            self._category_use_cases,
            self._account_use_cases,
            self._account_summary_service,
        )
        self._calendar_widget.edit_event_requested.connect(self._edit_event)
        self._calendar_widget.confirm_occurrence_requested.connect(self._confirm_occurrence)
        self._calendar_widget.skip_occurrence_requested.connect(
            lambda rid, od: self._skip_occurrence(rid, od)
        )
        self._tabs.addTab(self._calendar_widget, icons.icon("fa6s.calendar"), t("mainwindow.tab.calendar"))

    def _build_installments_tab(self):
        self._installments_widget = InstallmentsWidget(
            self._installment_use_cases,
        )
        self._tabs.addTab(self._installments_widget, icons.icon("fa6s.calendar-days"), t("mainwindow.tab.installments"))

    def _build_recurring_events_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        btn = QPushButton(t("mainwindow.btn.add_recurring_event"))
        btn.setIcon(icons.icon("fa6s.arrows-rotate"))
        btn.clicked.connect(self._add_recurring_event)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._recurring_events_table = EvenColumnsTableWidget()
        self._recurring_events_table.setColumnCount(9)
        self._recurring_events_table.setHorizontalHeaderLabels([
            t("common.description"), t("common.amount"), t("mainwindow.table.recurring.header.frequency"),
            t("mainwindow.table.recurring.header.anchor"), t("mainwindow.table.recurring.header.start"),
            t("mainwindow.table.recurring.header.end"), t("mainwindow.table.header.active"),
            t("mainwindow.table.header.id"), t("common.actions"),
        ])
        self._recurring_events_table.setObjectName("mainTabTable")
        self._recurring_events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._recurring_events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._recurring_events_table.setAlternatingRowColors(True)
        layout.addWidget(self._recurring_events_table)

        self._tabs.addTab(tab, icons.icon("fa6s.arrows-rotate"), t("mainwindow.tab.recurring_events"))

    def _build_category_breakdown_tab(self):
        if self._category_breakdown_service:
            self._category_breakdown_widget = CategoryBreakdownWidget(
                self._category_breakdown_service,
                self._category_use_cases,
            )
            self._tabs.addTab(self._category_breakdown_widget, icons.icon("fa6s.chart-pie"), t("mainwindow.tab.category_breakdown"))

    def _build_account_summary_tab(self):
        if self._account_summary_service:
            self._account_summary_widget = AccountSummaryWidget(
                self._account_summary_service,
            )
            self._tabs.addTab(self._account_summary_widget, icons.icon("fa6s.chart-line"), t("mainwindow.tab.account_summary"))

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

    def _add_product(self):
        dialog = ProductDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateProductDTO(name=data["name"])
            self._product_use_cases.create_product(dto)
            self._refresh_all()

    def _edit_product(self, product_id):
        products = {p.id: p for p in self._product_use_cases.list_products()}
        product = products.get(product_id)
        if product is None:
            return

        dialog = ProductDialog(self, product=product)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateProductDTO(name=data["name"])
            self._product_use_cases.update_product(product_id, dto)
            self._refresh_all()

    def _view_product_events(self, product_id):
        products = {p.id: p for p in self._product_use_cases.list_products()}
        product = products.get(product_id)
        if product is None:
            return

        events = self._purchase_use_cases.get_recent_events_for_product(product_id, limit=20)
        average_price = self._purchase_use_cases.get_average_price_by_product().get(product_id)
        dialog = ProductDetailDialog(self, product=product, events=events, average_price=average_price)
        dialog.exec()

    def _delete_product(self, product_id):
        products = {p.id: p for p in self._product_use_cases.list_products()}
        product = products.get(product_id)
        if product is None:
            return

        usage_count = self._purchase_use_cases.count_items_using_product(product_id)
        if usage_count > 0:
            QMessageBox.warning(
                self,
                t("mainwindow.msg.product_in_use.title"),
                t("mainwindow.msg.product_in_use.body", name=product.name, count=usage_count),
            )
            return

        reply = QMessageBox.question(
            self,
            t("mainwindow.msg.delete_product.title"),
            t("mainwindow.msg.delete_product.body", name=product.name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._product_use_cases.delete_product(product_id)
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
            QMessageBox.information(self, t("common.info"), t("mainwindow.msg.select_card.body"))
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
            QMessageBox.information(self, t("common.info"), t("mainwindow.msg.no_debt.body"))
            return

        from src.application.dto.card_payment_dto import CreateCardPaymentDTO
        from src.presentation.dialogs.card_payment_dialog import CardPaymentDialog

        accounts = self._account_use_cases.list_accounts()

        dialog = CardPaymentDialog(accounts, status.current_debt, card.name, self)
        if dialog.exec():
            data = dialog.get_data()
            confirm = QMessageBox.question(
                self,
                t("mainwindow.msg.confirm_payment.title"),
                t(
                    "mainwindow.msg.confirm_payment.body",
                    amount=format_currency(data['amount'], "BRL"),
                    card=card.name,
                ),
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
                notes=data["notes"],
            )
            result = self._credit_card_use_cases.pay_card(dto)
            if "error" in result:
                QMessageBox.warning(self, t("common.error"), result["error"])
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
            t("mainwindow.msg.delete_recurring.title"),
            t("mainwindow.msg.delete_recurring.body"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._recurring_event_use_cases.delete_recurring_event(recurring_event_id)
        self._refresh_all()

    def _recurring_anchor_label(self, r) -> str:
        if r.frequency == "weekly" and r.weekday is not None:
            names = [
                t("mainwindow.weekday.short.mon"), t("mainwindow.weekday.short.tue"),
                t("mainwindow.weekday.short.wed"), t("mainwindow.weekday.short.thu"),
                t("mainwindow.weekday.short.fri"), t("mainwindow.weekday.short.sat"),
                t("mainwindow.weekday.short.sun"),
            ]
            return names[r.weekday]
        if r.frequency == "monthly" and r.day_of_month is not None:
            return t("mainwindow.recurring.anchor.day", day=r.day_of_month)
        if r.frequency == "yearly" and r.month is not None and r.day_of_month is not None:
            return f"{r.month:02d}/{r.day_of_month:02d}"
        return ""

    def _confirm_occurrence(self, occurrence):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        credit_cards = self._credit_card_use_cases.list_cards()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        dialog = EventDialog(accounts, categories, counterparties, credit_cards, create_counterparty, self, event=occurrence)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(**data)
            self._recurring_event_use_cases.confirm_occurrence(
                occurrence.recurring_event_id, occurrence.occurrence_date, dto
            )
            self._refresh_all()

    def _skip_occurrence(self, recurring_event_id, occurrence_date):
        reply = QMessageBox.question(
            self,
            t("mainwindow.msg.skip_occurrence.title"),
            t("mainwindow.msg.skip_occurrence.body"),
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
        credit_cards = self._credit_card_use_cases.list_cards()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        dialog = EventDialog(accounts, categories, counterparties, credit_cards, create_counterparty, self)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(**data)
            self._financial_event_use_cases.create_event(dto)
            self._refresh_all()

    def _add_transfer(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        credit_cards = self._credit_card_use_cases.list_cards()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        dialog = EventDialog(accounts, categories, counterparties, credit_cards, create_counterparty, self)
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
            self, t("mainwindow.dialog.import_homebank.title"), "",
            t("mainwindow.dialog.import_homebank.filter"),
        )
        if not path:
            return

        try:
            plan = self._homebank_import_use_cases.build_import_plan(path)
        except XhbParseError as exc:
            QMessageBox.critical(
                self, t("mainwindow.msg.import_error.title"),
                t("mainwindow.msg.import_error.body", error=exc),
            )
            return

        dialog = HomeBankImportPreviewDialog(plan.to_preview_dto(), self)
        if not dialog.exec():
            return

        result = self._homebank_import_use_cases.commit_import_plan(plan)
        self._refresh_all()

        summary = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in result.created_counts.items() if v)
        message = t(
            "mainwindow.msg.import_complete.body",
            summary=summary or t("mainwindow.msg.nothing_to_import"),
        )
        if result.warnings:
            message += "\n\n" + t("mainwindow.msg.import_warnings", count=len(result.warnings))
        QMessageBox.information(self, t("mainwindow.msg.import_result.title"), message)

    def _export_homebank(self):
        options_dialog = HomeBankExportDialog(self)
        if not options_dialog.exec():
            return
        options_data = options_dialog.get_data()

        path, _ = QFileDialog.getSaveFileName(
            self, t("mainwindow.dialog.export_homebank.title"), "export.xhb",
            t("mainwindow.dialog.export_homebank.filter"),
        )
        if not path:
            return
        if not path.lower().endswith(".xhb"):
            path += ".xhb"

        options = HomeBankExportOptionsDTO(**options_data)
        result = self._homebank_export_use_cases.export(path, options)

        summary = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in result.counts.items() if v)
        message = t(
            "mainwindow.msg.export_complete.body",
            path=result.path,
            summary=summary or t("mainwindow.msg.nothing_to_export"),
        )
        if result.warnings:
            message += "\n\n" + t("mainwindow.msg.export_warnings", count=len(result.warnings))
        QMessageBox.information(self, t("mainwindow.msg.export_result.title"), message)

    def _open_settings(self):
        current_style = self._app_settings_use_cases.get_navigation_style()
        current_theme_id = self._app_settings_use_cases.get_current_theme_id()
        current_font_size = self._app_settings_use_cases.get_base_font_size()
        current_language = i18n.current_language()
        available_themes = self._theme_use_cases.list_available_themes() if self._theme_use_cases else []

        dialog = SettingsDialog(
            current_style, current_theme_id, available_themes, current_font_size,
            current_language=current_language, parent=self,
        )
        dialog.import_theme_requested.connect(lambda: self._handle_theme_import(dialog))
        if dialog.exec():
            data = dialog.get_data()
            changes = []
            if data.get("language") and data["language"] != current_language:
                changes.append(t("settings.change.language"))
            if data["navigation_style"] != current_style:
                changes.append(t("settings.change.navigation"))
            if data["theme_id"] and data["theme_id"] != current_theme_id:
                changes.append(t("settings.change.theme"))
            if data["base_font_size"] != current_font_size:
                changes.append(t("settings.change.font"))

            if not changes:
                return

            box = QMessageBox(self)
            box.setWindowTitle(t("settings.restart.title"))
            box.setText(t("settings.restart.body", changes=", ".join(changes)))
            restart_button = box.addButton(t("settings.restart.restart_now"), QMessageBox.AcceptRole)
            box.addButton(t("settings.restart.discard"), QMessageBox.RejectRole)
            box.setDefaultButton(restart_button)
            box.exec()

            if box.clickedButton() is not restart_button:
                return

            if data.get("language") and data["language"] != current_language:
                self._app_settings_use_cases.set_language(data["language"])
            if data["navigation_style"] != current_style:
                self._app_settings_use_cases.set_navigation_style(data["navigation_style"])
            if data["theme_id"] and data["theme_id"] != current_theme_id:
                self._app_settings_use_cases.set_current_theme_id(data["theme_id"])
            if data["base_font_size"] != current_font_size:
                self._app_settings_use_cases.set_base_font_size(data["base_font_size"])
            restart_app()

    def _handle_theme_import(self, dialog):
        path, _ = QFileDialog.getOpenFileName(
            self, t("mainwindow.dialog.import_theme.title"), "",
            t("mainwindow.dialog.import_theme.filter"),
        )
        if not path:
            return

        try:
            result = self._theme_use_cases.import_theme_file(path)
        except ThemeParseError as exc:
            QMessageBox.critical(
                self, t("mainwindow.msg.import_error.title"),
                t("mainwindow.msg.theme_import_error.body", error=exc),
            )
            return

        all_themes = self._theme_use_cases.list_available_themes()
        dialog.select_theme(result.theme_id, result.name, all_themes)

        message = t("mainwindow.msg.theme_imported.body", name=result.name)
        if result.warnings:
            message += (
                "\n\n" + t("mainwindow.msg.theme_imported.warnings", count=len(result.warnings)) + "\n"
                + "\n".join(f"- {w}" for w in result.warnings)
            )
        QMessageBox.information(self, t("mainwindow.msg.theme_import.title"), message)

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
        credit_cards = self._credit_card_use_cases.list_cards()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        dialog = EventDialog(accounts, categories, counterparties, credit_cards, create_counterparty, self, event=event)
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(**data)
            self._financial_event_use_cases.update_event(event_id, dto)
            self._refresh_all()

    def _edit_purchase(self, event_id):
        purchase_data = self._purchase_use_cases.get_purchase_by_event(event_id)
        if purchase_data is None:
            return

        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        credit_cards = self._credit_card_use_cases.list_cards()
        counterparties = self._counterparty_use_cases.list_counterparties()
        products = self._product_use_cases.list_products()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        def create_product(name):
            return self._product_use_cases.create_product(CreateProductDTO(name=name))

        dialog = PurchaseDialog(
            categories, credit_cards, counterparties, create_counterparty, self,
            purchase_data=purchase_data, accounts=accounts,
            products=products, on_create_product=create_product,
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
                    product_id=i["product_id"],
                )
                for i in data["items"]
            ]

            dto = CreatePurchaseDTO(
                event_date=data["event_date"],
                description=data["description"],
                total_amount=data["total_amount"],
                payment_method=PaymentMethod(data["payment_method"]),
                credit_card_id=data["credit_card_id"],
                account_id=data["account_id"],
                notes=data["notes"],
                installment_count=data["installment_count"],
                remainder_on_first=data["remainder_on_first"],
                counterparty_id=data["counterparty_id"],
                category_id=data["category_id"],
                items=items,
            )
            result = self._purchase_use_cases.update_purchase(purchase_data["purchase"].id, dto)
            if result and result.get("warnings"):
                QMessageBox.warning(self, t("mainwindow.msg.purchase_warning.title"), "\n".join(result["warnings"]))
            self._refresh_all()

    def _delete_event_cascade(self, event_id):
        self._purchase_use_cases.delete_purchase_by_event(event_id)
        self._financial_event_use_cases.delete_event(event_id)

    def _delete_event(self, event_id):
        reply = QMessageBox.question(
            self,
            t("mainwindow.msg.delete_event.title"),
            t("mainwindow.msg.delete_event.body"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._delete_event_cascade(event_id)
        self._refresh_all()

    def _delete_selected_events(self):
        rows = sorted({idx.row() for idx in self._events_table.selectionModel().selectedRows()})
        row_ids = [self._events_table.item(r, 0).data(Qt.UserRole) for r in rows if self._events_table.item(r, 0) is not None]
        event_ids = [row_id for row_id in row_ids if row_id and not row_id.startswith("virtual:")]
        if not event_ids:
            return
        reply = QMessageBox.question(
            self,
            t("mainwindow.msg.delete_events.title"),
            t("mainwindow.msg.delete_events.body", count=len(event_ids)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for event_id in event_ids:
            self._delete_event_cascade(event_id)
        self._refresh_all()

    def _duplicate_event(self, event_id):
        events = {e.id: e for e in self._financial_event_use_cases.list_events()}
        event = events.get(event_id)
        if event is None:
            return

        if event.event_type == "purchase":
            self._duplicate_purchase(event_id)
            return

        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        credit_cards = self._credit_card_use_cases.list_cards()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        dialog = EventDialog(
            accounts, categories, counterparties, credit_cards, create_counterparty, self,
            event=event, duplicate=True,
        )
        if dialog.exec():
            data = dialog.get_data()
            dto = CreateFinancialEventDTO(**data)
            self._financial_event_use_cases.create_event(dto)
            self._refresh_all()

    def _duplicate_purchase(self, event_id):
        purchase_data = self._purchase_use_cases.get_purchase_by_event(event_id)
        if purchase_data is None:
            return

        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        credit_cards = self._credit_card_use_cases.list_cards()
        counterparties = self._counterparty_use_cases.list_counterparties()
        products = self._product_use_cases.list_products()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        def create_product(name):
            return self._product_use_cases.create_product(CreateProductDTO(name=name))

        dialog = PurchaseDialog(
            categories, credit_cards, counterparties, create_counterparty, self,
            purchase_data=purchase_data, duplicate=True, accounts=accounts,
            products=products, on_create_product=create_product,
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
                    product_id=i["product_id"],
                )
                for i in data["items"]
            ]

            dto = CreatePurchaseDTO(
                event_date=data["event_date"],
                description=data["description"],
                total_amount=data["total_amount"],
                payment_method=PaymentMethod(data["payment_method"]),
                credit_card_id=data["credit_card_id"],
                account_id=data["account_id"],
                notes=data["notes"],
                installment_count=data["installment_count"],
                remainder_on_first=data["remainder_on_first"],
                counterparty_id=data["counterparty_id"],
                category_id=data["category_id"],
                items=items,
            )
            result = self._purchase_use_cases.create_purchase(dto)
            if result.get("warnings"):
                QMessageBox.warning(self, t("mainwindow.msg.purchase_warning.title"), "\n".join(result["warnings"]))
            self._refresh_all()

    def _add_purchase(self):
        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        credit_cards = self._credit_card_use_cases.list_cards()
        counterparties = self._counterparty_use_cases.list_counterparties()
        products = self._product_use_cases.list_products()

        def create_counterparty(name):
            dto = self._counterparty_use_cases.create_counterparty(CreateCounterpartyDTO(name=name))
            self._refresh_counterparties()
            return dto

        def create_product(name):
            return self._product_use_cases.create_product(CreateProductDTO(name=name))

        dialog = PurchaseDialog(
            categories, credit_cards, counterparties, create_counterparty, self,
            accounts=accounts, products=products, on_create_product=create_product,
        )
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
                    product_id=i["product_id"],
                ))

            dto = CreatePurchaseDTO(
                event_date=data["event_date"],
                description=data["description"],
                total_amount=data["total_amount"],
                payment_method=PaymentMethod(data["payment_method"]),
                credit_card_id=data["credit_card_id"],
                account_id=data["account_id"],
                notes=data["notes"],
                installment_count=data["installment_count"],
                remainder_on_first=data["remainder_on_first"],
                counterparty_id=data["counterparty_id"],
                category_id=data["category_id"],
                items=items,
            )
            result = self._purchase_use_cases.create_purchase(dto)
            if result.get("warnings"):
                QMessageBox.warning(self, t("mainwindow.msg.purchase_warning.title"), "\n".join(result["warnings"]))
            self._refresh_all()

    def _refresh_all(self):
        self._refresh_events()
        self._refresh_accounts()
        self._refresh_categories()
        self._refresh_counterparties()
        self._refresh_products()
        self._refresh_credit_cards()
        self._refresh_installments()
        self._refresh_recurring_events()
        self._refresh_dashboard()
        if hasattr(self, '_calendar_widget'):
            self._calendar_widget.refresh()
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
        self._filter_category.addItem(t("mainwindow.filter.all_categories"), None)
        for cat in self._category_use_cases.list_categories():
            self._filter_category.addItem(cat.name, cat.id)

        self._filter_account.clear()
        self._filter_account.addItem(t("mainwindow.filter.all_accounts"), None)
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
        self._events_table.resizeRowsToContents()

    def _populate_real_event_row(self, i, e, categories_map, accounts_map, counterparties_map, multi_category_event_ids):
        self._events_table.setItem(i, 0, QTableWidgetItem(format_date(e.event_date)))
        self._events_table.setItem(i, 1, QTableWidgetItem(event_type_label(e.event_type)))
        self._events_table.setItem(i, 2, QTableWidgetItem(e.description))
        self._events_table.setItem(i, 3, QTableWidgetItem(format_currency(e.amount, e.currency)))
        self._events_table.setItem(i, 4, QTableWidgetItem(e.currency))
        if e.category_id is None and e.id in multi_category_event_ids:
            cat_name = t("mainwindow.events.multiple_categories")
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
        self._events_table.item(i, 0).setData(Qt.UserRole, e.id)
        self._events_table.setCellWidget(i, 9, self._make_actions_widget([
            (t("common.edit"), "fa6s.pen", lambda _, event_id=e.id: self._edit_event(event_id)),
            (t("mainwindow.action.duplicate"), "fa6s.copy", lambda _, event_id=e.id: self._duplicate_event(event_id)),
            (t("common.delete"), "fa6s.trash", lambda _, event_id=e.id: self._delete_event(event_id), theme.EXPENSE),
        ]))

    def _populate_virtual_event_row(self, i, o, categories_map, accounts_map, counterparties_map):
        italic_font = QFont()
        italic_font.setItalic(True)

        def _item(text):
            item = QTableWidgetItem(text)
            item.setFont(italic_font)
            return item

        self._events_table.setItem(i, 0, _item(format_date(o.occurrence_date)))
        self._events_table.setItem(i, 1, _item(t("mainwindow.events.recurring_suffix", type=event_type_label(o.event_type))))
        self._events_table.setItem(i, 2, _item(o.description))
        self._events_table.setItem(i, 3, _item(format_currency(o.amount, o.currency)))
        self._events_table.setItem(i, 4, _item(o.currency))
        self._events_table.setItem(i, 5, _item(categories_map.get(o.category_id, str(o.category_id or ""))))
        self._events_table.setItem(i, 6, _item(accounts_map.get(o.account_id, str(o.account_id or ""))))
        self._events_table.setItem(i, 7, _item(counterparties_map.get(o.counterparty_id, str(o.counterparty_id or ""))))
        self._events_table.setItem(i, 8, _item(o.notes or ""))
        self._events_table.item(i, 0).setData(
            Qt.UserRole, f"virtual:{o.recurring_event_id}:{o.occurrence_date.isoformat()}"
        )
        self._events_table.setCellWidget(i, 9, self._make_actions_widget([
            (t("mainwindow.action.confirm"), "fa6s.check", lambda _, occ=o: self._confirm_occurrence(occ), theme.INCOME),
            (
                t("mainwindow.action.skip"), "fa6s.forward-step",
                lambda _, rid=o.recurring_event_id, od=o.occurrence_date: self._skip_occurrence(rid, od),
                theme.EXPENSE,
            ),
        ]))

    def _refresh_recurring_events(self):
        templates = self._recurring_event_use_cases.list_recurring_events()
        self._recurring_events_table.setRowCount(len(templates))
        for i, r in enumerate(templates):
            self._recurring_events_table.setItem(i, 0, QTableWidgetItem(r.description))
            self._recurring_events_table.setItem(i, 1, QTableWidgetItem(format_currency(r.amount, r.currency)))
            if r.interval == 1:
                freq_label = recurrence_frequency_label(r.frequency)
            else:
                freq_label = t(f"mainwindow.recurring.every.{r.frequency}", count=r.interval)
            self._recurring_events_table.setItem(i, 2, QTableWidgetItem(freq_label))
            self._recurring_events_table.setItem(i, 3, QTableWidgetItem(self._recurring_anchor_label(r)))
            self._recurring_events_table.setItem(i, 4, QTableWidgetItem(format_date(r.start_date)))
            self._recurring_events_table.setItem(
                i, 5, QTableWidgetItem(format_date(r.end_date) if r.end_date else "")
            )
            self._recurring_events_table.setItem(i, 6, QTableWidgetItem(t("common.yes") if r.is_active else t("common.no")))
            self._recurring_events_table.setItem(i, 7, QTableWidgetItem(r.id))
            self._recurring_events_table.setCellWidget(i, 8, self._make_actions_widget([
                (t("common.edit"), "fa6s.pen", lambda _, rid=r.id: self._edit_recurring_event(rid)),
                (t("common.delete"), "fa6s.trash", lambda _, rid=r.id: self._delete_recurring_event(rid), theme.EXPENSE),
            ]))
        self._recurring_events_table.resizeColumnsToContents()
        self._recurring_events_table.resizeRowsToContents()

    def _refresh_accounts(self):
        accounts = self._account_use_cases.list_accounts()
        self._accounts_table.setRowCount(len(accounts))
        for i, a in enumerate(accounts):
            self._accounts_table.setItem(i, 0, QTableWidgetItem(a.name))
            self._accounts_table.setItem(i, 1, QTableWidgetItem(account_type_label(a.type)))
            self._accounts_table.setItem(i, 2, QTableWidgetItem(format_currency(a.initial_balance, "BRL")))
            self._accounts_table.setItem(i, 3, QTableWidgetItem(a.id))
            self._accounts_table.setCellWidget(i, 4, self._make_actions_widget([
                (t("common.edit"), "fa6s.pen", lambda _, acc_id=a.id: self._edit_account(acc_id)),
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
                (t("common.edit"), "fa6s.pen", lambda _, cat_id=c.id: self._edit_category(cat_id)),
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
                (t("common.edit"), "fa6s.pen", lambda _, cp_id=c.id: self._edit_counterparty(cp_id)),
            ]))
        self._counterparties_table.resizeColumnsToContents()
        self._counterparties_table.resizeRowsToContents()

    def _refresh_products(self):
        products = self._product_use_cases.list_products()
        self._refresh_product_chart(products)

        search = self._product_search.text().strip().lower()
        if search:
            products = [p for p in products if search in p.name.lower()]

        avg_price_by_id = self._purchase_use_cases.get_average_price_by_product()
        best_price_by_id = self._purchase_use_cases.get_lowest_price_counterparty_by_product()
        counterparties_map = {c.id: c.name for c in self._counterparty_use_cases.list_counterparties()}

        self._products_table.setRowCount(len(products))
        for i, p in enumerate(products):
            self._products_table.setItem(i, 0, QTableWidgetItem(p.name))
            avg_price = avg_price_by_id.get(p.id)
            avg_price_text = format_currency(avg_price, "BRL") if avg_price is not None else "-"
            self._products_table.setItem(i, 1, QTableWidgetItem(avg_price_text))
            best = best_price_by_id.get(p.id)
            if best is not None:
                counterparty_id, best_price = best
                counterparty_name = counterparties_map.get(counterparty_id, "-") if counterparty_id else "-"
                best_price_text = f"{counterparty_name} ({format_currency(best_price, 'BRL')})"
            else:
                best_price_text = "-"
            self._products_table.setItem(i, 2, QTableWidgetItem(best_price_text))
            self._products_table.setCellWidget(i, 3, self._make_actions_widget([
                (t("mainwindow.action.view_events"), "fa6s.eye", lambda _, p_id=p.id: self._view_product_events(p_id)),
                (t("common.edit"), "fa6s.pen", lambda _, p_id=p.id: self._edit_product(p_id)),
                (t("common.delete"), "fa6s.trash", lambda _, p_id=p.id: self._delete_product(p_id), theme.EXPENSE),
            ]))
        self._products_table.resizeColumnsToContents()
        self._products_table.resizeRowsToContents()

    def _refresh_product_chart(self, products):
        date_from, date_to = self._product_chart_range.resolved_range()
        totals = self._purchase_use_cases.get_spending_by_product(date_from, date_to)
        name_by_id = {p.id: p.name for p in products}
        entries = sorted(
            ((name_by_id.get(pid, pid), total) for pid, total in totals.items() if total > 0),
            key=lambda entry: entry[1],
            reverse=True,
        )
        if not entries:
            self._product_pie_chart.set_empty_state(t("mainwindow.products.no_data"))
            return
        self._product_pie_chart.set_series(
            [name for name, _ in entries],
            {t("mainwindow.products.total_spent"): [total for _, total in entries]},
        )

    def _refresh_credit_cards(self):
        cards = self._credit_card_use_cases.list_cards()
        self._credit_cards_table.setRowCount(len(cards))
        for i, c in enumerate(cards):
            self._credit_cards_table.setItem(i, 0, QTableWidgetItem(c.name))
            self._credit_cards_table.setItem(i, 1, QTableWidgetItem(c.issuer))
            self._credit_cards_table.setItem(i, 2, QTableWidgetItem(format_currency(c.credit_limit, "BRL")))
            self._credit_cards_table.setItem(i, 3, QTableWidgetItem(str(c.closing_day)))
            self._credit_cards_table.setItem(i, 4, QTableWidgetItem(str(c.due_day)))
            self._credit_cards_table.setItem(i, 5, QTableWidgetItem(t("common.yes") if c.is_active else t("common.no")))

            status = self._credit_card_use_cases.get_status(c.id)
            if status:
                self._credit_cards_table.setItem(i, 6, QTableWidgetItem(format_currency(status.current_debt, "BRL")))
                self._credit_cards_table.setItem(i, 7, QTableWidgetItem(format_currency(status.available_credit, "BRL")))
            else:
                self._credit_cards_table.setItem(i, 6, QTableWidgetItem(format_currency(0, "BRL")))
                self._credit_cards_table.setItem(i, 7, QTableWidgetItem(format_currency(c.credit_limit, "BRL")))

            self._credit_cards_table.setCellWidget(i, 8, self._make_actions_widget([
                (t("common.edit"), "fa6s.pen", lambda _, card_id=c.id: self._edit_credit_card(card_id)),
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
