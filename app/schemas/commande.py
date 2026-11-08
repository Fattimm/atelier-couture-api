from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import StatutCommande
from app.schemas.paiement import PaiementRead
from app.schemas.livraison import LivraisonRead

Montant = Annotated[int, Field(ge=0, description="Montant en FCFA")]
Quantite = Annotated[int, Field(gt=0, le=100)]
Texte = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


# --- Entrées -----------------------------------------------------------------


class LigneCreate(BaseModel):
    """Une prestation à ajouter à une commande."""

    model_config = ConfigDict(extra="forbid")

    type_vetement_id: int
    quantite: Quantite = 1
    prix_unitaire: Montant | None = None  # par défaut : prix de base du catalogue (RG6)
    description: Texte | None = None


class CommandeCreate(BaseModel):
    """Nouvelle commande (POST /commandes)."""

    model_config = ConfigDict(extra="forbid")

    client_id: int
    mesure_id: int | None = None  # par défaut : dernières mesures du client (RG9)
    lignes: Annotated[list[LigneCreate], Field(min_length=1)]
    remise: Montant = 0
    date_livraison_prevue: date | None = None  # par défaut : calculée (RG8)
    notes: Texte | None = None


class CommandeUpdate(BaseModel):
    """Modification d'une commande (PATCH /commandes/{id})."""

    model_config = ConfigDict(extra="forbid")

    mesure_id: int | None = None
    date_livraison_prevue: date | None = None
    remise: Montant | None = None
    notes: Texte | None = None


class StatutChangement(BaseModel):
    """Demande de changement de statut (POST /commandes/{id}/statut)."""

    model_config = ConfigDict(extra="forbid")

    statut: StatutCommande
    commentaire: Texte | None = None


# --- Sorties -----------------------------------------------------------------


class LigneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type_vetement_id: int
    type_vetement_nom: str
    description: str | None
    quantite: int
    prix_unitaire: int
    sous_total: int


class HistoriqueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ancien_statut: StatutCommande | None
    nouveau_statut: StatutCommande
    commentaire: str | None
    utilisateur_id: int
    date_changement: datetime


class CommandeResume(BaseModel):
    """Une commande dans une liste (route 25)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: StatutCommande
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool


class CommandeDetail(CommandeResume):
    """Le détail complet d'une commande (routes 24, 26, 27...)."""

    mesure_id: int | None
    date_livraison_reelle: date | None
    remise: int
    notes: str | None
    cree_par_id: int
    created_at: datetime
    updated_at: datetime
    lignes: list[LigneRead]
    paiements: list[PaiementRead]
    livraison: LivraisonRead | None
