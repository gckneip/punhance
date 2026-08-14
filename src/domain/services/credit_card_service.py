from dataclasses import dataclass
from src.domain.entities.credit_card import CreditCard
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
    ):
        self._installment_repository = installment_repository
        self._installment_service = installment_service

    def get_status(self, card: CreditCard) -> CreditCardStatus:
        installments = self._installment_repository.find_by_credit_card(card.id)
        current_debt = self._installment_service.get_credit_card_debt(installments)
        available_credit = card.credit_limit - current_debt

        return CreditCardStatus(
            card=card,
            current_debt=current_debt,
            available_credit=available_credit,
        )
