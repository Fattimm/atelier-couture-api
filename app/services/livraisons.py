from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import Conflit, DonneesInvalides, RessourceIntrouvable
from app.models import Commande, Livraison, ModeLivraison, StatutCommande, StatutLivraison, Utilisateur
from app.schemas.livraison import LivraisonConfirmation, LivraisonPlanification
from app.services.commandes import STATUTS_FINAUX, enregistrer_changement_statut, obtenir_commande



def planifier_livraison(db: Session, commande_id: int, donnees: LivraisonPlanification) -> Livraison:
    """Planifie ou replanifie la livraison d'une commande (route 35, RG18)."""
    commande = obtenir_commande(db, commande_id)

    if commande.statut in STATUTS_FINAUX:
        raise Conflit(f"La commande {commande.numero} est {commande.statut.value} : sa livraison ne peut plus être planifiée")

    # RG18 : une livraison à domicile exige une adresse
    if donnees.mode == ModeLivraison.domicile and not donnees.adresse:
        raise DonneesInvalides("Une livraison à domicile exige une adresse")

    if donnees.date_prevue < commande.date_commande:
        raise DonneesInvalides("La date de livraison prévue ne peut pas précéder la date de commande")

    if commande.livraison is None:
        commande.livraison = Livraison(statut=StatutLivraison.planifiee)  # planifier

    # Planifier ou replanifier : PUT remplace toute la planification
    livraison = commande.livraison
    livraison.mode = donnees.mode
    livraison.date_prevue = donnees.date_prevue
    livraison.adresse = donnees.adresse
    livraison.livreur = donnees.livreur
    livraison.notes = donnees.notes

    # RG18 : la date prévue de la commande suit celle de la livraison
    commande.date_livraison_prevue = donnees.date_prevue

    db.flush()
    return livraison


def obtenir_livraison(db: Session, commande_id: int) -> Livraison:
    """Livraison d'une commande (route 36). 404 si aucune n'est planifiée."""
    commande = obtenir_commande(db, commande_id)
    if commande.livraison is None:
        raise RessourceIntrouvable(f"Aucune livraison n'est planifiée pour la commande {commande.numero}")
    return commande.livraison


def confirmer_livraison(
    db: Session,
    commande_id: int,
    donnees: LivraisonConfirmation,
    auteur: Utilisateur,
) -> Commande:
    """Remise du vêtement au client (route 37). Applique RG19 et RG20."""
    commande = obtenir_commande(db, commande_id)

    # RG19 : seule une commande terminée peut être livrée
    if commande.statut != StatutCommande.terminee:
        raise Conflit(
            f"Seule une commande terminee peut être livrée (statut actuel de {commande.numero} : {commande.statut.value})"
        )

    # RG19 : la commande doit être soldée, sauf autorisation explicite
    impaye = commande.solde
    if impaye > 0 and not donnees.autoriser_solde_impaye:
        raise Conflit(
            f"La commande n'est pas soldée : il reste {impaye} F à payer. "
            "Encaissez le solde, ou confirmez avec autoriser_solde_impaye à true."
        )

    date_effective = donnees.date_effective or date.today()
    if date_effective < commande.date_commande or date_effective > date.today():
        raise DonneesInvalides("La date de remise doit être comprise entre la date de commande et aujourd'hui")

    # RG20 : sans planification préalable, un retrait à l'atelier est créé
    if commande.livraison is None:
        commande.livraison = Livraison(
            mode=ModeLivraison.retrait_atelier,
            date_prevue=commande.date_livraison_prevue,
        )

    # RG20 : la livraison et la commande sont marquées livrées, avec leurs dates réelles
    commande.livraison.statut = StatutLivraison.livree
    commande.livraison.date_effective = date_effective
    commande.date_livraison_reelle = date_effective

    # RG15 / RG19 : inscription dans l'historique, avec la mention d'impayé éventuelle
    commentaire = "Livraison confirmée"
    if impaye > 0:
        commentaire += f" avec un solde impayé de {impaye} F (autorisé)"
    enregistrer_changement_statut(commande, StatutCommande.livree, auteur, commentaire)

    db.flush()
    return commande


def lister_livraisons(
    db: Session,
    *,
    statut: StatutLivraison | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
) -> list[Livraison]:
    """Liste de tournée, triée par date prévue (route 38)."""
    if date_min is not None and date_max is not None and date_min > date_max:
        raise DonneesInvalides("date_min ne peut pas être postérieure à date_max")

    requete = (
        select(Livraison)
        .options(joinedload(Livraison.commande).joinedload(Commande.client))
        .order_by(Livraison.date_prevue, Livraison.id)
    )
    if statut is not None:
        requete = requete.where(Livraison.statut == statut)
    if date_min is not None:
        requete = requete.where(Livraison.date_prevue >= date_min)
    if date_max is not None:
        requete = requete.where(Livraison.date_prevue <= date_max)

    return list(db.scalars(requete))