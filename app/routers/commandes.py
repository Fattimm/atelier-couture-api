from fastapi import APIRouter, status

from app.services import commandes as service
from datetime import date
from typing import Any

from app.core.deps import AccueilUser, CurrentUser, LimitParam, OffsetParam, SessionDep
from app.models import Commande, HistoriqueStatut, StatutCommande
from app.schemas.commande import CommandeCreate, CommandeDetail, CommandeResume, CommandeUpdate, LigneCreate, HistoriqueRead, StatutChangement
from app.schemas.commun import Page

router = APIRouter(prefix="/commandes", tags=["Commandes"])


@router.post("", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED)
def creer_commande(donnees: CommandeCreate, db: SessionDep, accueil: AccueilUser) -> Commande:
    """Crée une commande (accueil). Statut initial en_attente ; numéro et montants calculés par le serveur."""
    commande = service.creer_commande(db, donnees, accueil)
    db.commit()
    return commande


@router.get("", response_model=Page[CommandeResume])
def lister_commandes(
    db: SessionDep,
    _utilisateur: CurrentUser,
    statut: StatutCommande | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    numero: str | None = None,
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
) -> dict[str, Any]:
    """Liste paginée des commandes, la plus récente d'abord, avec filtres."""
    elements, total = service.lister_commandes(
        db,
        statut=statut,
        client_id=client_id,
        en_retard=en_retard,
        date_min=date_min,
        date_max=date_max,
        numero=numero,
        limit=limit,
        offset=offset,
    )
    return {"items": elements, "total": total, "limit": limit, "offset": offset}


@router.get("/{commande_id}", response_model=CommandeDetail)
def obtenir_commande(commande_id: int, db: SessionDep, _utilisateur: CurrentUser) -> Commande:
    """Détail d'une commande : lignes (avec nom de prestation et sous-total), solde, retard."""
    return service.obtenir_commande(db, commande_id)


@router.patch("/{commande_id}", response_model=CommandeDetail)
def modifier_commande(
    commande_id: int,
    donnees: CommandeUpdate,
    db: SessionDep,
    _accueil: AccueilUser,
) -> Commande:
    """Modifie mesures, date prévue, remise ou notes ; recalcule les montants. 409 si livrée ou annulée."""
    commande = service.modifier_commande(db, commande_id, donnees)
    db.commit()
    return commande


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


@router.post("/{commande_id}/lignes", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED)
def ajouter_ligne(
    commande_id: int,
    donnees: LigneCreate,
    db: SessionDep,
    _accueil: AccueilUser,
) -> Commande:
    """Ajoute une prestation (RG10) ; renvoie la commande avec les montants recalculés."""
    commande = service.ajouter_ligne(db, commande_id, donnees)
    db.commit()
    return commande


@router.delete("/{commande_id}/lignes/{ligne_id}", response_model=CommandeDetail)
def retirer_ligne(
    commande_id: int,
    ligne_id: int,
    db: SessionDep,
    _accueil: AccueilUser,
) -> Commande:
    """Retire une prestation (RG10) ; renvoie la commande mise à jour. 404 si la ligne n'existe pas."""
    commande = service.retirer_ligne(db, commande_id, ligne_id)
    db.commit()
    return commande