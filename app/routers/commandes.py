from fastapi import APIRouter, status

from app.core.deps import AccueilUser, CurrentUser, SessionDep
from app.services import commandes as service
from app.models import Commande, HistoriqueStatut
from app.schemas.commande import CommandeCreate, CommandeDetail, HistoriqueRead, StatutChangement

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


@router.post("/{commande_id}/statut", response_model=CommandeDetail)
def changer_statut(
    commande_id: int,
    donnees: StatutChangement,
    db: SessionDep,
    utilisateur: CurrentUser,
) -> Commande:
    """Fait évoluer le statut selon le workflow. Voir RG12 à RG15."""
    commande = service.changer_statut(db, commande_id, donnees, utilisateur)
    db.commit()
    return commande


@router.get("/{commande_id}/historique", response_model=list[HistoriqueRead])
def historique_commande(commande_id: int, db: SessionDep, _utilisateur: CurrentUser) -> list[HistoriqueStatut]:
    """Liste chronologique des changements de statut."""
    return service.lister_historique(db, commande_id)