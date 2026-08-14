import sqlite3
from typing import List, Optional
from src.domain.entities.category import Category
from src.domain.repositories.category_repository import CategoryRepository


class SQLiteCategoryRepository(CategoryRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, category: Category) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO categories (id, name, color, parent_id) VALUES (?, ?, ?, ?)",
            (category.id, category.name, category.color, category.parent_id),
        )
        self._conn.commit()

    def find_by_id(self, category_id: str) -> Optional[Category]:
        cursor = self._conn.execute(
            "SELECT id, name, color, parent_id FROM categories WHERE id = ?",
            (category_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Category(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            parent_id=row["parent_id"],
        )

    def find_all(self) -> List[Category]:
        cursor = self._conn.execute(
            "SELECT id, name, color, parent_id FROM categories ORDER BY name"
        )
        return [
            Category(
                id=row["id"],
                name=row["name"],
                color=row["color"],
                parent_id=row["parent_id"],
            )
            for row in cursor.fetchall()
        ]

    def delete(self, category_id: str) -> None:
        self._conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self._conn.commit()
