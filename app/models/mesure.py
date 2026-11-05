from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.client import Client

# Les 18 mesures facultatives, en centimètres (noms imposés par l'énoncé)
CHAMPS_MESURES = (
    "taille_cm", "tour_cou", "carrure_dos", "longueur_epaule", "tour_poitrine",
    "tour_taille", "tour_bassin", "longueur_manche", "tour_bras", "tour_poignet",
    "longueur_dos", "longueur_haut", "longueur_pantalon", "tour_cuisse", "tour_genou",
    "bas_pantalon", "entrejambe", "longueur_robe",
)


class Mesure(Base):
    """Une prise de mesures d'un client. Chaque prise est conservée (RG3)."""

    __tablename__ = "mesures"
    __table_args__ = (
        # RG2 : au moins une mesure renseignée
        CheckConstraint(f"num_nonnulls({', '.join(CHAMPS_MESURES)}) >= 1", name="au_moins_une_mesure"),
        # RG2 : chaque mesure strictement positive et au plus 300 cm
        *(CheckConstraint(f"{champ} > 0 AND {champ} <= 300", name=f"{champ}_valide") for champ in CHAMPS_MESURES),
        # Accélère la recherche des dernières mesures d'un client
        Index("ix_mesures_client_date", "client_id", "date_prise"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    date_prise: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    prise_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    taille_cm: Mapped[float | None]
    tour_cou: Mapped[float | None]
    carrure_dos: Mapped[float | None]
    longueur_epaule: Mapped[float | None]
    tour_poitrine: Mapped[float | None]
    tour_taille: Mapped[float | None]
    tour_bassin: Mapped[float | None]
    longueur_manche: Mapped[float | None]
    tour_bras: Mapped[float | None]
    tour_poignet: Mapped[float | None]
    longueur_dos: Mapped[float | None]
    longueur_haut: Mapped[float | None]
    longueur_pantalon: Mapped[float | None]
    tour_cuisse: Mapped[float | None]
    tour_genou: Mapped[float | None]
    bas_pantalon: Mapped[float | None]
    entrejambe: Mapped[float | None]
    longueur_robe: Mapped[float | None]

    client: Mapped["Client"] = relationship(back_populates="mesures")