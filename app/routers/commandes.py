from fastapi import APIRouter, status

from app.core.deps import AccueilUser, CurrentUser, SessionDep
from app.models import Commande
from app.schemas.commande import CommandeCreate, CommandeDetail
from app.services import commandes as service

router = APIRouter(prefix="/commandes", tags=["Commandes"])


@router.post("", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED)
def creer_commande(donnees: CommandeCreate, db: SessionDep, accueil: AccueilUser) -> Commande:
    """Crée une commande (accueil). Statut initial en_attente ; numéro et montants calculés par le serveur."""
    commande = service.creer_commande(db, donnees, accueil)
    db.commit()
    return commande


@router.get("/{commande_id}", response_model=CommandeDetail)
def obtenir_commande(commande_id: int, db: SessionDep, _utilisateur: CurrentUser) -> Commande:
    """Détail d'une commande : lignes (avec nom de prestation et sous-total), solde, retard."""
    return service.obtenir_commande(db, commande_id)