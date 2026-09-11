from dataclasses import dataclass
from src.domain.entities.credit_card import CreditCard
from src.domain.entities.financial_event import EventType
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.repositories.installment_repository import InstallmentRepository
from src.domain.services.installment_service import InstallmentService


@dataclass
class CreditCardStatus:
    card: CreditCard
    current_debt: float
    available_credit: float


class CreditCardService:
    def __init__(
        self,
        installment_repository: InstallmentRepository,
        installment_service: InstallmentService,
        financial_event_repository: FinancialEventRepository = None,
    ):
        self._installment_repository = installment_repository
        self._installment_service = installment_service
        self._financial_event_repository = financial_event_repository

    def get_status(self, card: CreditCard) -> CreditCardStatus:
        installments = self._installment_repository.find_by_credit_card(card.id)
        current_debt = self._installment_service.get_credit_card_debt(installments)

        if self._financial_event_repository is not None:
            # Plain expense events can also be tagged with a credit card
            # directly (via EventDialog), without going through the
            # Purchase/installment flow - those never generate an
            # Installment, so they're summed here as charges too.
            tagged_events = self._financial_event_repository.find_all(
                credit_card_id=card.id, event_type=EventType.EXPENSE,
            )
            current_debt += sum(e.amount for e in tagged_events)

            # Paying the card (see CreditCardUseCases.pay_card) is a ledger
            # entry, not a link to specific installments - it just reduces
            # the running total, like a transfer from an account to the card.
            payments = self._financial_event_repository.find_all(
                credit_card_id=card.id, event_type=EventType.CARD_PAYMENT,
            )
            current_debt -= sum(e.amount for e in payments)

        available_credit = card.credit_limit - current_debt

        return CreditCardStatus(
            card=card,
            current_debt=current_debt,
            available_credit=available_credit,
        )
