import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.commande import Commande


class ModeLivraison(enum.StrEnum):
    retrait_atelier = "retrait_atelier"
    domicile = "domicile"


class StatutLivraison(enum.StrEnum):
    planifiee = "planifiee"
    livree = "livree"


class Livraison(Base):
    """La livraison d'une commande : une seule par commande."""

    __tablename__ = "livraisons"
    __table_args__ = (
        # RG18 : une livraison à domicile exige une adresse (si domicile, alors adresse)
        CheckConstraint("mode != 'domicile' OR adresse IS NOT NULL", name="adresse_si_domicile"),
        # Une livraison livrée a une date effective, une livraison planifiée n'en a pas
        CheckConstraint("(statut = 'livree') = (date_effective IS NOT NULL)", name="date_effective_si_livree"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id"), unique=True)  # une seule par commande
    mode: Mapped[ModeLivraison] = mapped_column(Enum(ModeLivraison, name="mode_livraison"))
    adresse: Mapped[str | None] = mapped_column(Text)
    livreur: Mapped[str | None] = mapped_column(String(100))
    date_prevue: Mapped[date] = mapped_column(Date)
    date_effective: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[StatutLivraison] = mapped_column(
        Enum(StatutLivraison, name="statut_livraison"),
        default=StatutLivraison.planifiee,
        server_default=StatutLivraison.planifiee.value,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    commande: Mapped["Commande"] = relationship(back_populates="livraison")