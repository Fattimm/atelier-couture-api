from pydantic import BaseModel

from app.models import StatutCommande
import enum
from datetime import date


class TableauDeBord(BaseModel):
    """Indicateurs du tableau de bord (route 39)."""

    # Mois courant
    chiffre_affaires_mois: int
    encaisse_mois: int
    nb_commandes_mois: int

    # Situation actuelle
    reste_a_encaisser: int
    commandes_par_statut: dict[StatutCommande, int]
    nb_commandes_en_retard: int
    commandes_pretes_a_livrer: int
    livraisons_du_jour: int


class Granularite(enum.StrEnum):
    jour = "jour"
    mois = "mois"


class PeriodeChiffreAffaires(BaseModel):
    periode: str  # "2026-11-06" par jour, "2026-11" par mois
    chiffre_affaires: int
    encaisse: int


class ChiffreAffaires(BaseModel):
    """Chiffre d'affaires et encaissements par période (route 40)."""

    granularite: Granularite
    date_debut: date
    date_fin: date
    total_chiffre_affaires: int
    total_encaisse: int
    periodes: list[PeriodeChiffreAffaires]


class VenteTypeVetement(BaseModel):
    """Ventes d'une prestation sur la période (route 41)."""

    type_vetement_id: int
    nom: str
    quantite_vendue: int
    chiffre_affaires: int  # avant remise


class TopClient(BaseModel):
    """Un client du classement (route 42)."""

    client_id: int
    client_nom: str
    nb_commandes: int
    chiffre_affaires: int
    solde_du: int