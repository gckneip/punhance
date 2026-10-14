import sqlite3
from typing import List, Optional, Set
from src.domain.entities.category import Category
from src.domain.repositories.category_repository import CategoryRepository


class SQLiteCategoryRepository(CategoryRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, category: Category) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO categories (id, name, color, parent_id, is_investment) "
            "VALUES (?, ?, ?, ?, ?)",
            (category.id, category.name, category.color, category.parent_id,
             1 if category.is_investment else 0),
        )
        self._conn.commit()

    def find_by_id(self, category_id: str) -> Optional[Category]:
        cursor = self._conn.execute(
            "SELECT id, name, color, parent_id, is_investment FROM categories WHERE id = ?",
            (category_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_category(row)

    def find_all(self) -> List[Category]:
        cursor = self._conn.execute(
            "SELECT id, name, color, parent_id, is_investment FROM categories ORDER BY name"
        )
        return [self._row_to_category(row) for row in cursor.fetchall()]

    def find_investment_ids(self) -> Set[str]:
        """Ids of every category flagged as investment, plus all of their
        descendants (a flagged parent excludes its whole sub-tree)."""
        categories = self.find_all()
        children: dict = {}
        for c in categories:
            children.setdefault(c.parent_id, []).append(c.id)
        result: Set[str] = set()
        stack = [c.id for c in categories if c.is_investment]
        while stack:
            cid = stack.pop()
            if cid in result:
                continue
            result.add(cid)
            stack.extend(children.get(cid, []))
        return result

    def delete(self, category_id: str) -> None:
        self._conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self._conn.commit()

    @staticmethod
    def _row_to_category(row) -> Category:
        return Category(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            parent_id=row["parent_id"],
            is_investment=bool(row["is_investment"]) if "is_investment" in row.keys() else False,
        )
