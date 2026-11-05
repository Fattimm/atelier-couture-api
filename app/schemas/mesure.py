from datetime import date
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import CHAMPS_MESURES

ValeurCm = Annotated[
    float,
    Field(gt=0, le=300, description="En centimètres : strictement positive, 300 au plus (RG2)"),
]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


def _pas_dans_le_futur(valeur: date) -> date:
    if valeur > date.today():
        raise ValueError("la date de prise ne peut pas être dans le futur")
    return valeur


DatePrise = Annotated[date, AfterValidator(_pas_dans_le_futur)]


class ValeursMesures(BaseModel):
    """Les 18 mesures facultatives, en centimètres (base commune des schémas)."""

    taille_cm: ValeurCm | None = None
    tour_cou: ValeurCm | None = None
    carrure_dos: ValeurCm | None = None
    longueur_epaule: ValeurCm | None = None
    tour_poitrine: ValeurCm | None = None
    tour_taille: ValeurCm | None = None
    tour_bassin: ValeurCm | None = None
    longueur_manche: ValeurCm | None = None
    tour_bras: ValeurCm | None = None
    tour_poignet: ValeurCm | None = None
    longueur_dos: ValeurCm | None = None
    longueur_haut: ValeurCm | None = None
    longueur_pantalon: ValeurCm | None = None
    tour_cuisse: ValeurCm | None = None
    tour_genou: ValeurCm | None = None
    bas_pantalon: ValeurCm | None = None
    entrejambe: ValeurCm | None = None
    longueur_robe: ValeurCm | None = None

    def mesures_renseignees(self) -> dict[str, float]:
        """Les mesures qui ont une valeur, sous forme {nom: valeur}."""
        return {champ: getattr(self, champ) for champ in CHAMPS_MESURES if getattr(self, champ) is not None}


class MesureCreate(ValeursMesures):
    """Nouvelle prise de mesures (POST /clients/{id}/mesures)."""

    model_config = ConfigDict(extra="forbid")

    date_prise: DatePrise | None = None  # aujourd'hui par défaut (appliqué par le service)
    notes: Notes | None = None

    @model_validator(mode="after")
    def au_moins_une_mesure(self) -> Self:
        """RG2 : une prise doit contenir au moins une mesure."""
        if not self.mesures_renseignees():
            raise ValueError("une prise de mesures doit contenir au moins une mesure")
        return self


class MesureUpdate(ValeursMesures):
    """Correction d'une erreur de saisie (PATCH /mesures/{id}).

    La règle « il doit rester au moins une mesure » dépend de l'état actuel :
    elle est vérifiée par le service.
    """

    model_config = ConfigDict(extra="forbid")

    date_prise: DatePrise | None = None
    notes: Notes | None = None


class MesureRead(ValeursMesures):
    """Une prise de mesures telle que renvoyée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    date_prise: date
    prise_par_id: int
    notes: str | None