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
from src.infrastructure.repositories.sqlite_installment_plan_repository import SQLiteInstallmentPlanRepository
from src.infrastructure.repositories.sqlite_installment_repository import SQLiteInstallmentRepository
from src.application.use_cases.account_use_cases import AccountUseCases
from src.application.use_cases.category_use_cases import CategoryUseCases
from src.application.use_cases.counterparty_use_cases import CounterpartyUseCases
from src.application.use_cases.credit_card_use_cases import CreditCardUseCases
from src.application.use_cases.financial_event_use_cases import FinancialEventUseCases
from src.application.use_cases.purchase_use_cases import PurchaseUseCases
from src.application.use_cases.installment_use_cases import InstallmentUseCases
from src.domain.services.credit_card_service import CreditCardService
from src.domain.services.installment_service import InstallmentService
from src.domain.services.monthly_summary_service import MonthlySummaryService
from src.domain.services.category_breakdown_service import CategoryBreakdownService
from src.domain.services.account_summary_service import AccountSummaryService
from src.presentation.windows.main_window import MainWindow
from src.presentation import theme


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLESHEET)

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

    account_repo = SQLiteAccountRepository(conn)
    category_repo = SQLiteCategoryRepository(conn)
    counterparty_repo = SQLiteCounterpartyRepository(conn)
    credit_card_repo = SQLiteCreditCardRepository(conn)
    financial_event_repo = SQLiteFinancialEventRepository(conn)
    purchase_repo = SQLitePurchaseRepository(conn)
    installment_plan_repo = SQLiteInstallmentPlanRepository(conn)
    installment_repo = SQLiteInstallmentRepository(conn)

    account_use_cases = AccountUseCases(account_repo)
    category_use_cases = CategoryUseCases(category_repo)
    counterparty_use_cases = CounterpartyUseCases(counterparty_repo)
    credit_card_service = CreditCardService(installment_repo, InstallmentService())
    credit_card_use_cases = CreditCardUseCases(
        credit_card_repo,
        credit_card_service,
        financial_event_repo,
        installment_repo,
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
    monthly_summary_service = MonthlySummaryService(financial_event_repo)
    category_breakdown_service = CategoryBreakdownService(financial_event_repo, purchase_repo)
    account_summary_service = AccountSummaryService(financial_event_repo, account_repo)

    window = MainWindow(
        account_use_cases,
        category_use_cases,
        counterparty_use_cases,
        credit_card_use_cases,
        financial_event_use_cases,
        purchase_use_cases,
        installment_use_cases,
        monthly_summary_service,
        category_breakdown_service,
        account_summary_service,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
