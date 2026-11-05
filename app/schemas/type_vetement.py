from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NomPrestation = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
PrixFCFA = Annotated[int, Field(ge=0, description="Prix de base en FCFA")]
DelaiJours = Annotated[int, Field(ge=0, le=365, description="Délai de fabrication en jours")]


class TypeVetementCreate(BaseModel):
    """Données attendues pour ajouter une prestation (POST /catalogue)."""

    model_config = ConfigDict(extra="forbid")

    nom: NomPrestation
    description: Description | None = None
    prix_base: PrixFCFA
    delai_jours: DelaiJours


class TypeVetementUpdate(BaseModel):
    """Modification partielle d'une prestation (PATCH /catalogue/{id})."""

    model_config = ConfigDict(extra="forbid")

    nom: NomPrestation | None = None
    description: Description | None = None
    prix_base: PrixFCFA | None = None
    delai_jours: DelaiJours | None = None
    actif: bool | None = None


class TypeVetementRead(BaseModel):
    """Une prestation telle que renvoyée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    description: str | None
    prix_base: int
    delai_jours: int
    actif: bool