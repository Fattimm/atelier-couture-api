from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models import RoleUtilisateur

# Types réutilisables, avec leurs contraintes
NomComplet = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
MotDePasse = Annotated[str, Field(min_length=8, max_length=128)]  # RG21 : 8 caractères minimum


class UtilisateurCreate(BaseModel):
    """Données attendues pour créer un compte (POST /utilisateurs)."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    nom_complet: NomComplet
    mot_de_passe: MotDePasse
    role: RoleUtilisateur

    @field_validator("email")
    @classmethod
    def normaliser_email(cls, valeur: str) -> str:
        return valeur.strip().lower()


class UtilisateurUpdate(BaseModel):
    """Données acceptées pour modifier un compte (PATCH /utilisateurs/{id}).

    Tous les champs sont facultatifs : seuls ceux envoyés seront modifiés.
    """

    model_config = ConfigDict(extra="forbid")

    nom_complet: NomComplet | None = None
    role: RoleUtilisateur | None = None
    actif: bool | None = None
    mot_de_passe: MotDePasse | None = None


class UtilisateurRead(BaseModel):
    """Données renvoyées par l'API : jamais le hash du mot de passe."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom_complet: str
    role: RoleUtilisateur
    actif: bool
    created_at: datetime