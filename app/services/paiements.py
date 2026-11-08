from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import Conflit, RessourceIntrouvable
from app.models import Commande, Paiement, StatutCommande, Utilisateur
from app.schemas.paiement import PaiementCreate
from app.services.commandes import obtenir_commande


def recalculer_montant_paye(commande: Commande) -> None:
    """RG7 / RG17 : payé = somme des paiements (recalculée entièrement, jamais par ajouts)."""
    commande.montant_paye = sum(paiement.montant for paiement in commande.paiements)


def enregistrer_paiement(
    db: Session,
    commande_id: int,
    donnees: PaiementCreate,
    auteur: Utilisateur,
) -> Paiement:
    """Encaisse un acompte ou le solde (route 32). Applique RG16."""
    commande = obtenir_commande(db, commande_id)

    if commande.statut == StatutCommande.annulee:
        raise Conflit(f"La commande {commande.numero} est annulée : aucun paiement ne peut être encaissé")

    if donnees.montant > commande.solde:
        raise Conflit(
            f"Le paiement ({donnees.montant} F) dépasse le solde restant de la commande ({commande.solde} F)"
        )

    paiement = Paiement(
        montant=donnees.montant,
        mode=donnees.mode,
        reference=donnees.reference,
        date_paiement=donnees.date_paiement or date.today(),
        enregistre_par_id=auteur.id,
    )
    commande.paiements.append(paiement)
    recalculer_montant_paye(commande)

    try:
        db.flush()  # la contrainte paye <= total protège contre deux paiements simultanés
    except IntegrityError:
        raise Conflit("Le paiement dépasse le solde restant de la commande") from None
    return paiement


def lister_paiements(db: Session, commande_id: int) -> list[Paiement]:
    """Paiements d'une commande, dans l'ordre de saisie (route 33)."""
    return obtenir_commande(db, commande_id).paiements


def annuler_paiement(db: Session, paiement_id: int) -> None:
    """Annule un paiement saisi par erreur et recalcule le solde (route 34, RG17)."""
    paiement = db.get(Paiement, paiement_id)
    if paiement is None:
        raise RessourceIntrouvable(f"Aucun paiement avec l'identifiant {paiement_id}")

    commande = paiement.commande
    commande.paiements.remove(paiement)  # delete-orphan : le paiement sera supprimé
    recalculer_montant_paye(commande)
    db.flush()