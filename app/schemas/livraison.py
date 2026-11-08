from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models import ModeLivraison, StatutLivraison

Texte = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
NomLivreur = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


class LivraisonPlanification(BaseModel):
    """Planification complète d'une livraison (PUT /commandes/{id}/livraison).

    PUT remplace toute la planification : un champ facultatif non envoyé est effacé.
    """

    model_config = ConfigDict(extra="forbid")

    mode: ModeLivraison
    date_prevue: date
    adresse: Texte | None = None  # obligatoire si mode = domicile (RG18, vérifié par le service)
    livreur: NomLivreur | None = None
    notes: Texte | None = None


class LivraisonConfirmation(BaseModel):
    """Remise du vêtement au client (POST /commandes/{id}/livraison/confirmer). Corps facultatif."""

    model_config = ConfigDict(extra="forbid")

    date_effective: date | None = None  # aujourd'hui par défaut
    autoriser_solde_impaye: bool = False  # RG19


class LivraisonRead(BaseModel):
    """Une livraison telle que renvoyée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    mode: ModeLivraison
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: StatutLivraison
    notes: str | None


class LivraisonTournee(LivraisonRead):
    """Une livraison dans la liste de tournée (route 38)."""

    numero_commande: str
    client_nom: str
    client_telephone: str
    solde_commande: int