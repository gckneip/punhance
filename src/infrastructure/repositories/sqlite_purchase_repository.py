import sqlite3
from typing import List, Optional
from datetime import date
from src.domain.entities.purchase import Purchase, PaymentMethod
from src.domain.entities.purchase_item import PurchaseItem
from src.domain.repositories.purchase_repository import PurchaseRepository


class SQLitePurchaseRepository(PurchaseRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, purchase: Purchase, commit: bool = True) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO purchases
               (id, financial_event_id, total_amount, payment_method, credit_card_id, counterparty_id, invoice_date, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                purchase.id,
                purchase.financial_event_id,
                purchase.total_amount,
                purchase.payment_method.value,
                purchase.credit_card_id,
                purchase.counterparty_id,
                purchase.invoice_date.isoformat() if purchase.invoice_date else None,
                purchase.notes,
            ),
        )
        if commit:
            self._conn.commit()

    def find_by_id(self, purchase_id: str) -> Optional[Purchase]:
        cursor = self._conn.execute(
            "SELECT * FROM purchases WHERE id = ?", (purchase_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_purchase(row)

    def find_by_financial_event(self, financial_event_id: str) -> Optional[Purchase]:
        cursor = self._conn.execute(
            "SELECT * FROM purchases WHERE financial_event_id = ?",
            (financial_event_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_purchase(row)

    def find_all(self) -> List[Purchase]:
        cursor = self._conn.execute(
            "SELECT * FROM purchases ORDER BY id"
        )
        return [self._row_to_purchase(row) for row in cursor.fetchall()]

    def delete(self, purchase_id: str) -> None:
        self._conn.execute("DELETE FROM purchase_items WHERE purchase_id = ?", (purchase_id,))
        self._conn.execute("DELETE FROM installments WHERE installment_plan_id IN (SELECT id FROM installment_plans WHERE purchase_id = ?)", (purchase_id,))
        self._conn.execute("DELETE FROM installment_plans WHERE purchase_id = ?", (purchase_id,))
        self._conn.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
        self._conn.commit()

    def save_item(self, item: PurchaseItem, commit: bool = True) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO purchase_items
               (id, purchase_id, name, quantity, unit, unit_price, total_price, category_id, product_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.purchase_id, item.name, item.quantity,
             item.unit, item.unit_price, item.total_price, item.category_id, item.product_id),
        )
        if commit:
            self._conn.commit()

    def find_items_by_purchase(self, purchase_id: str) -> List[PurchaseItem]:
        cursor = self._conn.execute(
            "SELECT * FROM purchase_items WHERE purchase_id = ? ORDER BY name",
            (purchase_id,),
        )
        return [self._row_to_item(row) for row in cursor.fetchall()]

    def find_items_in_range(self, date_from=None, date_to=None) -> List[PurchaseItem]:
        query = """SELECT purchase_items.* FROM purchase_items
                   JOIN purchases ON purchase_items.purchase_id = purchases.id
                   JOIN financial_events ON purchases.financial_event_id = financial_events.id
                   WHERE 1=1"""
        params = []
        if date_from:
            query += " AND financial_events.event_date >= ?"
            params.append(date_from.isoformat())
        if date_to:
            query += " AND financial_events.event_date < ?"
            params.append(date_to.isoformat())
        cursor = self._conn.execute(query, params)
        return [self._row_to_item(row) for row in cursor.fetchall()]

    def count_items_by_product(self, product_id: str) -> int:
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM purchase_items WHERE product_id = ?", (product_id,)
        )
        return cursor.fetchone()[0]

    def delete_items_by_purchase(self, purchase_id: str, commit: bool = True) -> None:
        self._conn.execute(
            "DELETE FROM purchase_items WHERE purchase_id = ?", (purchase_id,)
        )
        if commit:
            self._conn.commit()

    def _row_to_purchase(self, row: sqlite3.Row) -> Purchase:
        inv_date = None
        if row["invoice_date"]:
            inv_date = date.fromisoformat(row["invoice_date"])
        return Purchase(
            id=row["id"],
            financial_event_id=row["financial_event_id"],
            total_amount=row["total_amount"],
            payment_method=PaymentMethod(row["payment_method"]),
            credit_card_id=row["credit_card_id"],
            counterparty_id=row["counterparty_id"],
            invoice_date=inv_date,
            notes=row["notes"],
        )

    def _row_to_item(self, row: sqlite3.Row) -> PurchaseItem:
        return PurchaseItem(
            id=row["id"],
            purchase_id=row["purchase_id"],
            name=row["name"],
            quantity=row["quantity"],
            unit=row["unit"],
            unit_price=row["unit_price"],
            total_price=row["total_price"],
            category_id=row["category_id"],
            product_id=row["product_id"],
        )
