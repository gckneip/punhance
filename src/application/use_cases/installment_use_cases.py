from typing import List, Optional
from datetime import date
from src.domain.entities.installment import Installment, InstallmentStatus
from src.domain.repositories.installment_repository import InstallmentRepository
from src.domain.repositories.installment_plan_repository import InstallmentPlanRepository
from src.application.dto.installment_dto import InstallmentDTO


class InstallmentUseCases:
    def __init__(
        self,
        installment_repository: InstallmentRepository,
        installment_plan_repository: InstallmentPlanRepository,
    ):
        self._installment_repo = installment_repository
        self._plan_repo = installment_plan_repository

    def list_installments(
        self,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        credit_card_id: Optional[str] = None,
    ) -> List[InstallmentDTO]:
        if credit_card_id:
            installments = self._installment_repo.find_by_credit_card(credit_card_id)
            if status:
                status_enum = InstallmentStatus(status)
                installments = [i for i in installments if i.status == status_enum]
            if date_from:
                installments = [i for i in installments if i.due_date >= date_from]
            if date_to:
                installments = [i for i in installments if i.due_date < date_to]
        else:
            status_enum = InstallmentStatus(status) if status else None
            installments = self._installment_repo.find_all(
                status=status_enum,
                date_from=date_from,
                date_to=date_to,
            )
        return [self._to_dto(i) for i in installments]

    def mark_as_paid(self, installment_id: str) -> None:
        inst = self._installment_repo.find_by_id(installment_id)
        if inst:
            inst.status = InstallmentStatus.PAID
            self._installment_repo.save(inst)

    def _to_dto(self, inst: Installment) -> InstallmentDTO:
        return InstallmentDTO(
            id=inst.id,
            installment_plan_id=inst.installment_plan_id,
            installment_number=inst.installment_number,
            amount=inst.amount,
            due_date=inst.due_date,
            status=inst.status.value,
        )
