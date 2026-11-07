import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.commande import Commande


class ModePaiement(enum.StrEnum):
    """Les moyens de paiement acceptés par l'atelier."""

    especes = "especes"
    wave = "wave"
    orange_money = "orange_money"
    virement = "virement"
    cheque = "cheque"


class Paiement(Base):
    """Un versement pour une commande : acompte ou solde."""

    __tablename__ = "paiements"
    __table_args__ = (
        CheckConstraint("montant > 0", name="montant_positif"),  # RG16
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id"), index=True)
    montant: Mapped[int]  # en FCFA
    mode: Mapped[ModePaiement] = mapped_column(Enum(ModePaiement, name="mode_paiement"))
    reference: Mapped[str | None] = mapped_column(String(100))  # n° de transaction, de chèque...
    date_paiement: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    enregistre_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commande: Mapped["Commande"] = relationship(back_populates="paiements")