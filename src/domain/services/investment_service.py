from dataclasses import dataclass
from typing import Dict, List

from src.domain.entities.investment import Investment
from src.domain.entities.investment_transaction import (
    InvestmentTransaction,
    PRINCIPAL_IN_TYPES,
    PRINCIPAL_OUT_TYPES,
    INCOME_TYPES,
    COST_TYPES,
)


@dataclass
class PositionSummary:
    quantity: float
    net_invested: float
    avg_unit_price: float
    market_value: float
    income_total: float
    unrealized_gain: float
    total_return: float
    return_pct: float
    # For savings-box holdings with a goal: market_value / goal_amount, in %.
    goal_progress_pct: float = 0.0


@dataclass
class PortfolioSummary:
    total_invested: float
    total_market_value: float
    total_gain: float
    total_income: float
    return_pct: float


class InvestmentService:
    """Derives positions from an investment's transaction history.

    The math is intentionally pragmatic (weighted-average cost, not per-lot
    FIFO/tax accounting):
      - quantity      = principal-in qty minus principal-out qty
      - net_invested  = principal-in cash minus principal-out cash (proceeds)
      - market_value  = current_price x quantity, but for amount-based holdings
                        (renda fixa with no per-unit quantity) quantity is 0 so we
                        treat it as 1 and use current_price as the current total.
      - income_total  = dividends + interest, minus fees + taxes
      - unrealized_gain = market_value - net_invested
      - total_return    = unrealized_gain + income_total
    """

    def compute_position(
        self, investment: Investment, transactions: List[InvestmentTransaction]
    ) -> PositionSummary:
        quantity = 0.0
        net_invested = 0.0
        income_total = 0.0

        for txn in transactions:
            if txn.txn_type in PRINCIPAL_IN_TYPES:
                quantity += txn.quantity
                net_invested += txn.total
            elif txn.txn_type in PRINCIPAL_OUT_TYPES:
                quantity -= txn.quantity
                net_invested -= txn.total
            elif txn.txn_type in INCOME_TYPES:
                income_total += txn.total
            elif txn.txn_type in COST_TYPES:
                income_total -= txn.total

        avg_unit_price = net_invested / quantity if quantity > 0 else 0.0

        effective_quantity = quantity if quantity else 1.0
        market_value = investment.current_price * effective_quantity

        unrealized_gain = market_value - net_invested
        total_return = unrealized_gain + income_total
        return_pct = (total_return / net_invested * 100.0) if net_invested > 0 else 0.0

        goal_progress_pct = (
            (market_value / investment.goal_amount * 100.0)
            if investment.goal_amount
            else 0.0
        )

        return PositionSummary(
            quantity=quantity,
            net_invested=net_invested,
            avg_unit_price=avg_unit_price,
            market_value=market_value,
            income_total=income_total,
            unrealized_gain=unrealized_gain,
            total_return=total_return,
            return_pct=return_pct,
            goal_progress_pct=goal_progress_pct,
        )

    def compute_portfolio(
        self,
        investments: List[Investment],
        txns_by_investment: Dict[str, List[InvestmentTransaction]],
    ) -> PortfolioSummary:
        total_invested = 0.0
        total_market_value = 0.0
        total_income = 0.0

        for investment in investments:
            position = self.compute_position(
                investment, txns_by_investment.get(investment.id, [])
            )
            total_invested += position.net_invested
            total_market_value += position.market_value
            total_income += position.income_total

        total_gain = total_market_value - total_invested + total_income
        return_pct = (
            (total_gain / total_invested * 100.0) if total_invested > 0 else 0.0
        )

        return PortfolioSummary(
            total_invested=total_invested,
            total_market_value=total_market_value,
            total_gain=total_gain,
            total_income=total_income,
            return_pct=return_pct,
        )
