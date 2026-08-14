from typing import List
from src.domain.entities.category import Category
from src.domain.repositories.category_repository import CategoryRepository
from src.application.dto.category_dto import CreateCategoryDTO, CategoryDTO


class CategoryUseCases:
    def __init__(self, category_repository: CategoryRepository):
        self._category_repository = category_repository

    def create_category(self, dto: CreateCategoryDTO) -> CategoryDTO:
        category = Category(
            name=dto.name,
            color=dto.color,
            parent_id=dto.parent_id,
        )
        self._category_repository.save(category)
        return self._to_dto(category)

    def list_categories(self) -> List[CategoryDTO]:
        categories = self._category_repository.find_all()
        return [self._to_dto(c) for c in categories]

    def delete_category(self, category_id: str) -> None:
        self._category_repository.delete(category_id)

    def _to_dto(self, category: Category) -> CategoryDTO:
        return CategoryDTO(
            id=category.id,
            name=category.name,
            color=category.color,
            parent_id=category.parent_id,
        )
