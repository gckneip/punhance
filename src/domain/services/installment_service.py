import calendar
from typing import List
from datetime import date
from src.domain.entities.installment_plan import InstallmentPlan
from src.domain.entities.installment import Installment, InstallmentStatus


class InstallmentService:
    def create_installments(
        self,
        plan: InstallmentPlan,
        first_due_date: date,
    ) -> List[Installment]:
        installment_amount = round(plan.total_amount / plan.installment_count, 2)
        remainder = round(plan.total_amount - installment_amount * plan.installment_count, 2)
        target_index = 0 if plan.remainder_on_first else plan.installment_count - 1

        installments = []
        for i in range(plan.installment_count):
            amount = installment_amount
            if i == target_index:
                amount = round(amount + remainder, 2)

            total_months = first_due_date.month + i
            year_offset = (total_months - 1) // 12
            month = ((total_months - 1) % 12) + 1
            year = first_due_date.year + year_offset
            max_day = calendar.monthrange(year, month)[1]
            day = min(first_due_date.day, max_day)
            due_date = date(year, month, day)

            installments.append(Installment(
                installment_plan_id=plan.id,
                installment_number=i + 1,
                amount=amount,
                due_date=due_date,
                status=InstallmentStatus.PENDING,
            ))

        return installments

    def get_credit_card_debt(
        self,
        installments: List[Installment],
    ) -> float:
        # Installments have no "paid" concept: they're charges against the
        # card that raise its debt the moment they're generated, regardless
        # of status. Debt only goes down via an actual card payment (see
        # CreditCardService.get_status), not by flagging an installment.
        return sum(i.amount for i in installments)
