from sqlalchemy import CheckConstraint, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TypeVetement(Base):
    """Une prestation du catalogue : boubou, robe, retouche..."""

    __tablename__ = "types_vetement"
    __table_args__ = (
        CheckConstraint("prix_base >= 0", name="prix_base_positif"),
        CheckConstraint("delai_jours >= 0", name="delai_jours_positif"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    prix_base: Mapped[int]  # en FCFA
    delai_jours: Mapped[int]
    actif: Mapped[bool] = mapped_column(default=True, server_default=true())