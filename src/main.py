import sys
from PySide6.QtWidgets import QApplication, QMessageBox

from src.infrastructure.database.connection import get_connection
from src.infrastructure.database.schema import create_tables
from src.infrastructure.repositories.sqlite_account_repository import SQLiteAccountRepository
from src.infrastructure.repositories.sqlite_category_repository import SQLiteCategoryRepository
from src.infrastructure.repositories.sqlite_counterparty_repository import SQLiteCounterpartyRepository
from src.infrastructure.repositories.sqlite_credit_card_repository import SQLiteCreditCardRepository
from src.infrastructure.repositories.sqlite_financial_event_repository import SQLiteFinancialEventRepository
from src.infrastructure.repositories.sqlite_purchase_repository import SQLitePurchaseRepository
from src.infrastructure.repositories.sqlite_product_repository import SQLiteProductRepository
from src.infrastructure.repositories.sqlite_installment_plan_repository import SQLiteInstallmentPlanRepository
from src.infrastructure.repositories.sqlite_installment_repository import SQLiteInstallmentRepository
from src.infrastructure.repositories.sqlite_dashboard_widget_repository import SQLiteDashboardWidgetRepository
from src.infrastructure.repositories.sqlite_dashboard_report_repository import SQLiteDashboardReportRepository
from src.infrastructure.repositories.sqlite_dashboard_widget_template_repository import (
    SQLiteDashboardWidgetTemplateRepository,
)
from src.infrastructure.repositories.sqlite_recurring_event_repository import SQLiteRecurringEventRepository
from src.infrastructure.repositories.sqlite_app_settings_repository import SQLiteAppSettingsRepository
from src.infrastructure.homebank.xhb_reader import XhbReader
from src.infrastructure.homebank.xhb_writer import XhbWriter
from src.infrastructure.theming.theme_file_repository import FileThemeRepository
from src.infrastructure.config.settings import THEMES_DIR
from src.application.use_cases.account_use_cases import AccountUseCases
from src.application.use_cases.category_use_cases import CategoryUseCases
from src.application.use_cases.counterparty_use_cases import CounterpartyUseCases
from src.application.use_cases.credit_card_use_cases import CreditCardUseCases
from src.application.use_cases.financial_event_use_cases import FinancialEventUseCases
from src.application.use_cases.purchase_use_cases import PurchaseUseCases
from src.application.use_cases.product_use_cases import ProductUseCases
from src.application.use_cases.installment_use_cases import InstallmentUseCases
from src.application.use_cases.recurring_event_use_cases import RecurringEventUseCases
from src.application.use_cases.dashboard_layout_use_cases import DashboardLayoutUseCases
from src.application.use_cases.dashboard_report_use_cases import DashboardReportUseCases
from src.application.use_cases.dashboard_widget_template_use_cases import DashboardWidgetTemplateUseCases
from src.application.use_cases.app_settings_use_cases import AppSettingsUseCases
from src.application.use_cases.homebank_import_use_cases import HomeBankImportUseCases
from src.application.use_cases.homebank_export_use_cases import HomeBankExportUseCases
from src.application.use_cases.theme_use_cases import ThemeUseCases
from src.domain.entities.theme import LIGHT_PALETTE
from src.domain.services.credit_card_service import CreditCardService
from src.domain.services.installment_service import InstallmentService
from src.domain.services.monthly_summary_service import MonthlySummaryService
from src.domain.services.category_breakdown_service import CategoryBreakdownService
from src.domain.services.account_summary_service import AccountSummaryService
from src.domain.services.recurring_event_service import RecurringEventService
from src.domain.services.chart_data_service import ChartDataService
from src.presentation.windows.main_window import MainWindow
from src.presentation.widgets.dashboard.chart_widget import configure_pyqtgraph_theme
from src.presentation import theme


def main():
    app = QApplication(sys.argv)

    try:
        conn = get_connection()
        create_tables(conn)
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Database Error",
            f"Failed to initialize the database:\n{exc}",
        )
        sys.exit(1)

    app_settings_repo = SQLiteAppSettingsRepository(conn)
    app_settings_use_cases = AppSettingsUseCases(app_settings_repo)
    theme_repo = FileThemeRepository(THEMES_DIR)
    theme_use_cases = ThemeUseCases(theme_repo)

    theme_id = app_settings_use_cases.get_current_theme_id()
    palette = theme_use_cases.resolve_palette(theme_id)
    fallback_notice = None
    if palette is None:
        fallback_notice = f"Your theme ({theme_id}) could not be found; reset to Light."
        palette = LIGHT_PALETTE
        app_settings_use_cases.set_current_theme_id("builtin:light")
    theme.load_palette(palette)
    theme.load_font_size(app_settings_use_cases.get_base_font_size())
    app.setStyleSheet(theme.build_stylesheet())
    configure_pyqtgraph_theme()
    if fallback_notice:
        QMessageBox.warning(None, "Theme Not Found", fallback_notice)

    account_repo = SQLiteAccountRepository(conn)
    category_repo = SQLiteCategoryRepository(conn)
    counterparty_repo = SQLiteCounterpartyRepository(conn)
    credit_card_repo = SQLiteCreditCardRepository(conn)
    financial_event_repo = SQLiteFinancialEventRepository(conn)
    purchase_repo = SQLitePurchaseRepository(conn)
    product_repo = SQLiteProductRepository(conn)
    installment_plan_repo = SQLiteInstallmentPlanRepository(conn)
    installment_repo = SQLiteInstallmentRepository(conn)
    dashboard_widget_repo = SQLiteDashboardWidgetRepository(conn)
    dashboard_report_repo = SQLiteDashboardReportRepository(conn)
    dashboard_widget_template_repo = SQLiteDashboardWidgetTemplateRepository(conn)
    recurring_event_repo = SQLiteRecurringEventRepository(conn)

    account_use_cases = AccountUseCases(account_repo)
    category_use_cases = CategoryUseCases(category_repo)
    counterparty_use_cases = CounterpartyUseCases(counterparty_repo)
    credit_card_service = CreditCardService(installment_repo, InstallmentService(), financial_event_repo)
    credit_card_use_cases = CreditCardUseCases(
        credit_card_repo,
        credit_card_service,
        financial_event_repo,
    )
    financial_event_use_cases = FinancialEventUseCases(financial_event_repo)
    installment_service = InstallmentService()
    purchase_use_cases = PurchaseUseCases(
        financial_event_repo,
        purchase_repo,
        installment_plan_repo,
        installment_repo,
        installment_service,
        conn,
    )
    installment_use_cases = InstallmentUseCases(installment_repo, installment_plan_repo)
    product_use_cases = ProductUseCases(product_repo)
    monthly_summary_service = MonthlySummaryService(financial_event_repo)
    category_breakdown_service = CategoryBreakdownService(financial_event_repo, purchase_repo)
    account_summary_service = AccountSummaryService(financial_event_repo, account_repo)
    recurring_event_service = RecurringEventService()
    recurring_event_use_cases = RecurringEventUseCases(
        recurring_event_repo, financial_event_repo, recurring_event_service
    )

    homebank_import_use_cases = HomeBankImportUseCases(
        account_repo, category_repo, counterparty_repo, credit_card_repo,
        financial_event_repo, purchase_use_cases, recurring_event_use_cases,
        XhbReader(), conn,
    )
    homebank_export_use_cases = HomeBankExportUseCases(
        account_use_cases, category_use_cases, counterparty_use_cases, credit_card_use_cases,
        financial_event_use_cases, purchase_use_cases, recurring_event_use_cases,
        XhbWriter(),
    )

    chart_data_service = ChartDataService(
        financial_event_repository=financial_event_repo,
        account_repository=account_repo,
        category_repository=category_repo,
        counterparty_repository=counterparty_repo,
        credit_card_repository=credit_card_repo,
        installment_repository=installment_repo,
        installment_plan_repository=installment_plan_repo,
        purchase_repository=purchase_repo,
        product_repository=product_repo,
        recurring_event_repository=recurring_event_repo,
        monthly_summary_service=monthly_summary_service,
        category_breakdown_service=category_breakdown_service,
        account_summary_service=account_summary_service,
        credit_card_service=credit_card_service,
        recurring_event_service=recurring_event_service,
    )
    dashboard_layout_use_cases = DashboardLayoutUseCases(dashboard_widget_repo)
    dashboard_layout_use_cases.seed_default_layout_if_empty()
    dashboard_report_use_cases = DashboardReportUseCases(dashboard_report_repo, dashboard_widget_repo)
    dashboard_report_use_cases.seed_default_if_empty()
    dashboard_widget_template_use_cases = DashboardWidgetTemplateUseCases(dashboard_widget_template_repo)

    window = MainWindow(
        account_use_cases,
        category_use_cases,
        counterparty_use_cases,
        credit_card_use_cases,
        financial_event_use_cases,
        purchase_use_cases,
        installment_use_cases,
        recurring_event_use_cases,
        dashboard_layout_use_cases,
        dashboard_report_use_cases,
        app_settings_use_cases,
        chart_data_service,
        category_breakdown_service,
        account_summary_service,
        homebank_import_use_cases=homebank_import_use_cases,
        homebank_export_use_cases=homebank_export_use_cases,
        theme_use_cases=theme_use_cases,
        product_use_cases=product_use_cases,
        dashboard_widget_template_use_cases=dashboard_widget_template_use_cases,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
