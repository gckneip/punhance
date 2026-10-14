"""One-off migration: seed initial CONTRIBUTION transactions for pre-existing
amount-based holdings (renda fixa, caixinhas, other) that were created before the
app started seeding them automatically.

Such holdings have a current_price (their total value) but no principal-in
transaction, so they report a market value with zero invested and an inflated
"gain". This backfills a CONTRIBUTION equal to current_price so the invested total
matches the value entered at creation.

Only touches holdings whose net_invested is currently 0 — so it is idempotent and
never disturbs holdings that already have real transactions.

Usage (from the project root):
    python -m scripts.seed_initial_contributions            # dry run (preview only)
    python -m scripts.seed_initial_contributions --apply    # write the changes
"""
import sys
from datetime import date

from src.infrastructure.database.connection import get_connection
from src.infrastructure.database.schema import create_tables
from src.infrastructure.repositories.sqlite_investment_repository import (
    SQLiteInvestmentRepository,
)
from src.infrastructure.repositories.sqlite_investment_transaction_repository import (
    SQLiteInvestmentTransactionRepository,
)
from src.domain.entities.investment_transaction import (
    InvestmentTransaction,
    InvestmentTxnType,
)
from src.domain.services.investment_service import InvestmentService
from src.application.use_cases.investment_use_cases import _AMOUNT_BASED_ASSET_TYPES


def _seed_date(investment) -> str:
    """When the value was recorded, if known, else today. price_updated_at is an
    ISO datetime string; we keep only the date part."""
    if investment.price_updated_at:
        return investment.price_updated_at[:10]
    return date.today().isoformat()


def main(apply: bool) -> int:
    conn = get_connection()
    create_tables(conn)
    inv_repo = SQLiteInvestmentRepository(conn)
    txn_repo = SQLiteInvestmentTransactionRepository(conn)
    service = InvestmentService()

    to_seed = []
    for inv in inv_repo.find_all():
        if inv.asset_type not in _AMOUNT_BASED_ASSET_TYPES or not inv.current_price:
            continue
        position = service.compute_position(inv, txn_repo.find_by_investment(inv.id))
        if position.net_invested == 0:
            to_seed.append(inv)

    if not to_seed:
        print("Nothing to do — no amount-based holdings with zero invested found.")
        return 0

    print(f"{'Applying' if apply else 'Would seed'} {len(to_seed)} holding(s):")
    for inv in to_seed:
        seed_date = _seed_date(inv)
        print(
            f"  - {inv.name} ({inv.asset_type.value}): "
            f"{inv.currency} {inv.current_price:.2f}  [date {seed_date}]"
        )
        if apply:
            txn_repo.save(InvestmentTransaction(
                investment_id=inv.id,
                txn_type=InvestmentTxnType.CONTRIBUTION,
                date=seed_date,
                total=inv.current_price,
                notes="Initial contribution (migration)",
            ))

    if apply:
        conn.commit()
        print("Done — initial contributions recorded.")
    else:
        print("\nDry run — no changes written. Re-run with --apply to commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv[1:]))
