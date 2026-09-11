from dataclasses import dataclass


@dataclass
class CreateProductDTO:
    name: str


@dataclass
class ProductDTO:
    id: str
    name: str
