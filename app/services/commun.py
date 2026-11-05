from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import DonneesInvalides

T = TypeVar("T")


def paginer(db: Session, requete: Select[tuple[T]], limit: int, offset: int) -> tuple[list[T], int]:
    """Exécute une requête par page. Renvoie (éléments de la page, nombre total)."""
    requete_comptage = select(func.count()).select_from(requete.order_by(None).subquery())
    total = db.scalar(requete_comptage) or 0
    elements = list(db.scalars(requete.limit(limit).offset(offset)))
    return elements, total


def verifier_champs_non_vides(changements: dict[str, Any], effacables: set[str] = frozenset()) -> None:
    """Lève DonneesInvalides si un champ obligatoire est envoyé à null dans un PATCH."""
    champs_vides = [
        champ for champ, valeur in changements.items()
        if valeur is None and champ not in effacables
    ]
    if champs_vides:
        raise DonneesInvalides(f"Ces champs ne peuvent pas être vides : {', '.join(champs_vides)}")