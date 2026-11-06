import re
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints

from app.models import GenreClient

_CARACTERES_A_SUPPRIMER = re.compile(r"[\s.\-()]")
_FORME_VALIDE = re.compile(r"\+?\d{6,20}")


def nettoyer_telephone(valeur: str) -> str:
    """Supprime espaces, points, tirets et parenthèses (sans rien vérifier)."""
    return _CARACTERES_A_SUPPRIMER.sub("", valeur)


def normaliser_telephone(valeur: str) -> str:
    """RG1 : nettoie le numéro, puis vérifie sa forme.

    "77 123 45 67" et "771234567" donnent tous deux "771234567".
    """
    normalise = nettoyer_telephone(valeur)
    if not _FORME_VALIDE.fullmatch(normalise):
        raise ValueError(
            "numéro invalide : il doit contenir de 6 à 20 chiffres, avec un + initial facultatif"
        )
    return normalise


Telephone = Annotated[str, AfterValidator(normaliser_telephone)]
NomPersonne = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TexteLibre = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class ClientCreate(BaseModel):
    """Données attendues pour créer un client (POST /clients)."""

    model_config = ConfigDict(extra="forbid")

    nom: NomPersonne
    prenom: NomPersonne
    telephone: Telephone
    email: EmailStr | None = None
    adresse: TexteLibre | None = None
    genre: GenreClient | None = None
    notes: TexteLibre | None = None


class ClientUpdate(BaseModel):
    """Modification partielle d'un client (PATCH /clients/{id})."""

    model_config = ConfigDict(extra="forbid")

    nom: NomPersonne | None = None
    prenom: NomPersonne | None = None
    telephone: Telephone | None = None
    email: EmailStr | None = None
    adresse: TexteLibre | None = None
    genre: GenreClient | None = None
    notes: TexteLibre | None = None


class ClientRead(BaseModel):
    """Fiche client renvoyée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    adresse: str | None
    genre: GenreClient | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ClientResume(BaseModel):
    """Résumé financier d'un client (route 13). Les commandes annulées sont exclues."""

    nb_commandes: int
    chiffre_affaires: int
    total_paye: int
    solde_du: int
    derniere_commande: date | None  # date de la dernière commande non annulée
    a_des_mesures: bool