from pydantic import BaseModel

from app.models import StatutCommande


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