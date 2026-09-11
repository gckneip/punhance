import sqlite3
from typing import List, Optional
from src.domain.entities.product import Product
from src.domain.repositories.product_repository import ProductRepository


class SQLiteProductRepository(ProductRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, product: Product) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO products (id, name) VALUES (?, ?)",
            (product.id, product.name),
        )
        self._conn.commit()

    def find_by_id(self, product_id: str) -> Optional[Product]:
        cursor = self._conn.execute(
            "SELECT id, name FROM products WHERE id = ?", (product_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Product(id=row["id"], name=row["name"])

    def find_all(self) -> List[Product]:
        cursor = self._conn.execute("SELECT id, name FROM products ORDER BY name")
        return [Product(id=row["id"], name=row["name"]) for row in cursor.fetchall()]

    def delete(self, product_id: str) -> None:
        self._conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self._conn.commit()
