from datetime import date

from fastapi import APIRouter

from app.core.deps import AccueilUser, CurrentUser, SessionDep
from app.models import Commande, Livraison, StatutLivraison
from app.schemas.commande import CommandeDetail
from app.schemas.livraison import LivraisonConfirmation, LivraisonPlanification, LivraisonRead, LivraisonTournee
from app.services import livraisons as service

# Pas de préfixe : routes réparties entre /commandes/{id}/livraison et /livraisons
router = APIRouter(tags=["Livraisons"])


@router.put("/commandes/{commande_id}/livraison", response_model=LivraisonRead)
def planifier_livraison(
    commande_id: int,
    donnees: LivraisonPlanification,
    db: SessionDep,
    _accueil: AccueilUser,
) -> Livraison:
    """Planifie ou replanifie la livraison (accueil). Voir RG18. 409 si la commande est livrée ou annulée."""
    livraison = service.planifier_livraison(db, commande_id, donnees)
    db.commit()
    return livraison


@router.get("/commandes/{commande_id}/livraison", response_model=LivraisonRead)
def obtenir_livraison(commande_id: int, db: SessionDep, _utilisateur: CurrentUser) -> Livraison:
    """Livraison de la commande. 404 si aucune n'est planifiée."""
    return service.obtenir_livraison(db, commande_id)


@router.post("/commandes/{commande_id}/livraison/confirmer", response_model=CommandeDetail)
def confirmer_livraison(
    commande_id: int,
    db: SessionDep,
    accueil: AccueilUser,
    donnees: LivraisonConfirmation | None = None,
) -> Commande:
    """Remise du vêtement au client (accueil). Corps facultatif. Voir RG19 et RG20."""
    commande = service.confirmer_livraison(db, commande_id, donnees or LivraisonConfirmation(), accueil)
    db.commit()
    return commande


@router.get("/livraisons", response_model=list[LivraisonTournee])
def liste_de_tournee(
    db: SessionDep,
    _utilisateur: CurrentUser,
    statut: StatutLivraison | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
) -> list[Livraison]:
    """Liste de tournée, triée par date prévue."""
    return service.lister_livraisons(db, statut=statut, date_min=date_min, date_max=date_max)