from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateCategoryDTO:
    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None


@dataclass
class CategoryDTO:
    id: str
    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None
