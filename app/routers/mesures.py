from fastapi import APIRouter, status

from app.core.deps import CurrentUser, SessionDep, TailleurUser
from app.models import Mesure
from app.schemas.mesure import MesureCreate, MesureRead, MesureUpdate
from app.services import mesures as service

# Pas de préfixe : les routes sont réparties entre /clients/{id}/mesures et /mesures/{id}
router = APIRouter(tags=["Mesures"])


# --- Dans le contexte d'un client -------------------------------------------


@router.post(
    "/clients/{client_id}/mesures",
    response_model=MesureRead,
    status_code=status.HTTP_201_CREATED,
)
def prendre_mesures(client_id: int, donnees: MesureCreate, db: SessionDep, tailleur: TailleurUser) -> Mesure:
    """Nouvelle prise de mesures (tailleur). date_prise vaut aujourd'hui par défaut."""
    mesure = service.creer_mesure(db, client_id, donnees, tailleur)
    db.commit()
    return mesure


@router.get("/clients/{client_id}/mesures", response_model=list[MesureRead])
def historique_mesures(client_id: int, db: SessionDep, _utilisateur: CurrentUser) -> list[Mesure]:
    """Historique complet des prises du client, la plus récente d'abord."""
    return service.lister_mesures_client(db, client_id)


@router.get("/clients/{client_id}/mesures/derniere", response_model=MesureRead)
def dernieres_mesures(client_id: int, db: SessionDep, _utilisateur: CurrentUser) -> Mesure:
    """Dernières mesures du client. 404 s'il n'en a aucune."""
    return service.obtenir_derniere_mesure(db, client_id)


# --- Sur une prise de mesures précise ---------------------------------------


@router.get("/mesures/{mesure_id}", response_model=MesureRead)
def obtenir_mesure(mesure_id: int, db: SessionDep, _utilisateur: CurrentUser) -> Mesure:
    """Une prise de mesures."""
    return service.obtenir_mesure(db, mesure_id)


@router.patch("/mesures/{mesure_id}", response_model=MesureRead)
def corriger_mesure(mesure_id: int, donnees: MesureUpdate, db: SessionDep, _tailleur: TailleurUser) -> Mesure:
    """Corrige une erreur de saisie (tailleur). 422 si plus aucune mesure ne resterait."""
    mesure = service.modifier_mesure(db, mesure_id, donnees)
    db.commit()
    return mesure


@router.delete("/mesures/{mesure_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_mesure(mesure_id: int, db: SessionDep, _tailleur: TailleurUser) -> None:
    """Supprime une prise de mesures (tailleur). 409 si une commande l'utilise."""
    service.supprimer_mesure(db, mesure_id)
    db.commit()