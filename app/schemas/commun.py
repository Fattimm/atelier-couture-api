from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Format commun des listes paginées : {items, total, limit, offset}."""

    items: list[T]
    total: int
    limit: int
    offset: int