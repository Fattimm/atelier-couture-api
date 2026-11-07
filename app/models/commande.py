import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.mesure import Mesure
    from app.models.type_vetement import TypeVetement
    from app.models.paiement import Paiement


class StatutCommande(enum.StrEnum):
    """Les étapes de la vie d'une commande (workflow de la section 6)."""

    en_attente = "en_attente"
    en_coupe = "en_coupe"
    en_couture = "en_couture"
    essayage = "essayage"
    retouches = "retouches"
    terminee = "terminee"
    livree = "livree"
    annulee = "annulee"


# Un seul type PostgreSQL, partagé par les commandes et l'historique
TYPE_STATUT = Enum(StatutCommande, name="statut_commande")


class Commande(Base):
    """Une commande d'un client : le bon de commande."""

    __tablename__ = "commandes"
    __table_args__ = (
        CheckConstraint("remise >= 0", name="remise_positive"),
        CheckConstraint("montant_total >= 0", name="montant_total_positif"),
        CheckConstraint("montant_paye >= 0", name="montant_paye_positif"),
        CheckConstraint("montant_paye <= montant_total", name="paye_inferieur_total"),  # RG7
        CheckConstraint("date_livraison_prevue >= date_commande", name="livraison_apres_commande"),  # RG8
        Index("ix_commandes_client_id", "client_id"),
        Index("ix_commandes_statut", "statut"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(15), unique=True)  # CMD-AAAA-NNNNN (RG5)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))  # pas de CASCADE : RG4
    mesure_id: Mapped[int | None] = mapped_column(ForeignKey("mesures.id"))  # pas de CASCADE : RG4
    statut: Mapped[StatutCommande] = mapped_column(
        TYPE_STATUT, default=StatutCommande.en_attente, server_default=StatutCommande.en_attente.value
    )
    date_commande: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    date_livraison_prevue: Mapped[date] = mapped_column(Date)
    date_livraison_reelle: Mapped[date | None] = mapped_column(Date)
    remise: Mapped[int] = mapped_column(default=0, server_default="0")
    montant_total: Mapped[int] = mapped_column(default=0, server_default="0")
    montant_paye: Mapped[int] = mapped_column(default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    cree_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="commandes")
    mesure: Mapped["Mesure | None"] = relationship()
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="LigneCommande.id",
    )
    historique: Mapped[list["HistoriqueStatut"]] = relationship(
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="(HistoriqueStatut.date_changement, HistoriqueStatut.id)",
    )
    paiements: Mapped[list["Paiement"]] = relationship(
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="Paiement.id",  # ordre de saisie (route 33)
    )
    
    # --- Valeurs calculées (non stockées) -------------------------------
    
    @property
    def solde(self) -> int:
        """Reste à payer : total − payé (RG7)."""
        return self.montant_total - self.montant_paye

    @property
    def en_retard(self) -> bool:
        """RG11 : date prévue dépassée, et commande ni livrée ni annulée."""
        return (
            self.date_livraison_prevue < date.today()
            and self.statut not in (StatutCommande.livree, StatutCommande.annulee)
        )

    @property
    def client_nom(self) -> str:
        """Prénom et nom du client, pour les listes (route 25)."""
        return f"{self.client.prenom} {self.client.nom}"


class LigneCommande(Base):
    """Une prestation commandée : « 2 × Boubou à 35 000 F »."""

    __tablename__ = "lignes_commande"
    __table_args__ = (
        CheckConstraint("quantite > 0", name="quantite_positive"),
        CheckConstraint("prix_unitaire >= 0", name="prix_unitaire_positif"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"))
    type_vetement_id: Mapped[int] = mapped_column(ForeignKey("types_vetement.id"))
    description: Mapped[str | None] = mapped_column(Text)
    quantite: Mapped[int]
    prix_unitaire: Mapped[int]  # figé au moment de la commande (RG6)

    commande: Mapped["Commande"] = relationship(back_populates="lignes")
    type_vetement: Mapped["TypeVetement"] = relationship()

    
    @property
    def sous_total(self) -> int:
        """Quantité × prix unitaire (calculé, non stocké)."""
        return self.quantite * self.prix_unitaire

    @property
    def type_vetement_nom(self) -> str:
        """Nom de la prestation commandée (route 26)."""
        return self.type_vetement.nom

class HistoriqueStatut(Base):
    """Un changement de statut d'une commande (RG15)."""

    __tablename__ = "historique_statuts"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    ancien_statut: Mapped[StatutCommande | None] = mapped_column(TYPE_STATUT)  # vide à la création
    nouveau_statut: Mapped[StatutCommande] = mapped_column(TYPE_STATUT)
    commentaire: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    date_changement: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commande: Mapped["Commande"] = relationship(back_populates="historique")