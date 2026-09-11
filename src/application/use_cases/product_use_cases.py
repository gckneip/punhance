from typing import List, Optional
from src.domain.entities.product import Product
from src.domain.repositories.product_repository import ProductRepository
from src.application.dto.product_dto import CreateProductDTO, ProductDTO


class ProductUseCases:
    def __init__(self, product_repository: ProductRepository):
        self._product_repository = product_repository

    def create_product(self, dto: CreateProductDTO) -> ProductDTO:
        entity = Product(name=dto.name)
        self._product_repository.save(entity)
        return self._to_dto(entity)

    def update_product(self, product_id: str, dto: CreateProductDTO) -> Optional[ProductDTO]:
        entity = self._product_repository.find_by_id(product_id)
        if entity is None:
            return None
        entity.name = dto.name
        self._product_repository.save(entity)
        return self._to_dto(entity)

    def list_products(self) -> List[ProductDTO]:
        entities = self._product_repository.find_all()
        return [self._to_dto(e) for e in entities]

    def delete_product(self, product_id: str) -> None:
        self._product_repository.delete(product_id)

    def _to_dto(self, entity: Product) -> ProductDTO:
        return ProductDTO(id=entity.id, name=entity.name)
