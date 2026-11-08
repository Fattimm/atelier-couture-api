from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.models import ModePaiement


def _pas_dans_le_futur(valeur: date) -> date:
    """RG16 : un paiement ne peut pas porter une date future."""
    if valeur > date.today():
        raise ValueError("un paiement ne peut pas porter une date future")
    return valeur


DatePaiement = Annotated[date, AfterValidator(_pas_dans_le_futur)]
Reference = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


class PaiementCreate(BaseModel):
    """Encaissement d'un acompte ou du solde (POST /commandes/{id}/paiements)."""

    model_config = ConfigDict(extra="forbid")

    montant: Annotated[int, Field(gt=0, description="Montant en FCFA, strictement positif")]
    mode: ModePaiement
    reference: Reference | None = None
    date_paiement: DatePaiement | None = None  # aujourd'hui par défaut


class PaiementRead(BaseModel):
    """Un paiement tel que renvoyé par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    montant: int
    mode: ModePaiement
    reference: str | None
    date_paiement: date
    enregistre_par_id: int
    created_at: datetime