from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Commande, Livraison, Paiement, StatutCommande, StatutLivraison
from app.schemas.statistiques import TableauDeBord
from app.services.commandes import condition_en_retard
from app.services.commun import paginer

NON_ANNULEE = Commande.statut != StatutCommande.annulee


def _bornes_mois(jour: date) -> tuple[date, date]:
    """Premier jour du mois de `jour`, et premier jour du mois suivant (borne exclue)."""
    debut = jour.replace(day=1)
    if debut.month == 12:
        fin = debut.replace(year=debut.year + 1, month=1)
    else:
        fin = debut.replace(month=debut.month + 1)
    return debut, fin


def tableau_de_bord(db: Session) -> TableauDeBord:
    """Indicateurs du mois courant et de la situation actuelle (route 39)."""
    aujourd_hui = date.today()
    debut_mois, debut_mois_suivant = _bornes_mois(aujourd_hui)

    # --- Mois courant ---
    commandes_du_mois = (
        NON_ANNULEE,
        Commande.date_commande >= debut_mois,
        Commande.date_commande < debut_mois_suivant,
    )
    chiffre_affaires_mois = db.scalar(
        select(func.coalesce(func.sum(Commande.montant_total), 0)).where(*commandes_du_mois)
    )
    nb_commandes_mois = db.scalar(select(func.count(Commande.id)).where(*commandes_du_mois))
    encaisse_mois = db.scalar(
        select(func.coalesce(func.sum(Paiement.montant), 0)).where(
            Paiement.date_paiement >= debut_mois,
            Paiement.date_paiement < debut_mois_suivant,
        )
    )

    # --- Situation actuelle ---
    reste_a_encaisser = db.scalar(
        select(func.coalesce(func.sum(Commande.montant_total - Commande.montant_paye), 0)).where(NON_ANNULEE)
    )

    # Tous les statuts, même à 0, complétés par un GROUP BY
    commandes_par_statut = {statut: 0 for statut in StatutCommande}
    for statut, nombre in db.execute(
        select(Commande.statut, func.count(Commande.id)).group_by(Commande.statut)
    ):
        commandes_par_statut[statut] = nombre

    nb_commandes_en_retard = db.scalar(select(func.count(Commande.id)).where(condition_en_retard()))
    livraisons_du_jour = db.scalar(
        select(func.count(Livraison.id)).where(
            Livraison.date_prevue == aujourd_hui,
            Livraison.statut == StatutLivraison.planifiee,
        )
    )

    return TableauDeBord(
        chiffre_affaires_mois=chiffre_affaires_mois,
        encaisse_mois=encaisse_mois,
        nb_commandes_mois=nb_commandes_mois,
        reste_a_encaisser=reste_a_encaisser,
        commandes_par_statut=commandes_par_statut,
        nb_commandes_en_retard=nb_commandes_en_retard,
        commandes_pretes_a_livrer=commandes_par_statut[StatutCommande.terminee],
        livraisons_du_jour=livraisons_du_jour,
    )


def lister_impayes(db: Session, limit: int, offset: int) -> tuple[list[Commande], int]:
    """Commandes non annulées non soldées, les plus urgentes d'abord (route 43)."""
    requete = (
        select(Commande)
        .options(selectinload(Commande.client))
        .where(NON_ANNULEE, Commande.montant_paye < Commande.montant_total)
        .order_by(Commande.date_livraison_prevue, Commande.id)
    )
    return paginer(db, requete, limit, offset)