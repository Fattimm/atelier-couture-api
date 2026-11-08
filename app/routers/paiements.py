from fastapi import APIRouter, status

from app.core.deps import AccueilUser, AdminUser, CurrentUser, SessionDep
from app.models import Paiement
from app.schemas.paiement import PaiementCreate, PaiementRead
from app.services import paiements as service

# Pas de préfixe : routes réparties entre /commandes/{id}/paiements et /paiements/{id}
router = APIRouter(tags=["Paiements"])


@router.post(
    "/commandes/{commande_id}/paiements",
    response_model=PaiementRead,
    status_code=status.HTTP_201_CREATED,
)
def encaisser(commande_id: int, donnees: PaiementCreate, db: SessionDep, accueil: AccueilUser) -> Paiement:
    """Encaisse un acompte ou le solde (accueil). Voir RG16."""
    paiement = service.enregistrer_paiement(db, commande_id, donnees, accueil)
    db.commit()
    return paiement


@router.get("/commandes/{commande_id}/paiements", response_model=list[PaiementRead])
def paiements_de_la_commande(commande_id: int, db: SessionDep, _utilisateur: CurrentUser) -> list[Paiement]:
    """Paiements de la commande, dans l'ordre de saisie."""
    return service.lister_paiements(db, commande_id)


@router.delete("/paiements/{paiement_id}", status_code=status.HTTP_204_NO_CONTENT)
def annuler_paiement(paiement_id: int, db: SessionDep, _admin: AdminUser) -> None:
    """Annule un paiement saisi par erreur (admin) et recalcule le solde (RG17)."""
    service.annuler_paiement(db, paiement_id)
    db.commit()