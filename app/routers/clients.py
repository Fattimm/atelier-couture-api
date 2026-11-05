from typing import Annotated, Any

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, LimitParam, OffsetParam, SessionDep
from app.models import Client, GenreClient
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.schemas.commun import Page
from app.services import clients as service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def creer_client(donnees: ClientCreate, db: SessionDep, _utilisateur: CurrentUser) -> Client:
    """Crée un client. 409 si le téléphone existe déjà (RG1) ; 422 si le numéro est invalide."""
    client = service.creer_client(db, donnees)
    db.commit()
    return client


@router.get("", response_model=Page[ClientRead])
def lister_clients(
    db: SessionDep,
    _utilisateur: CurrentUser,
    q: Annotated[
        str | None,
        Query(min_length=2, description="Recherche dans le nom, le prénom et le téléphone"),
    ] = None,
    genre: GenreClient | None = None,
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
) -> dict[str, Any]:
    """Liste paginée des clients, triée par nom puis prénom."""
    elements, total = service.lister_clients(db, q, genre, limit, offset)
    return {"items": elements, "total": total, "limit": limit, "offset": offset}


@router.get("/{client_id}", response_model=ClientRead)
def obtenir_client(client_id: int, db: SessionDep, _utilisateur: CurrentUser) -> Client:
    """Fiche d'un client. 404 si inconnu."""
    return service.obtenir_client(db, client_id)


@router.patch("/{client_id}", response_model=ClientRead)
def modifier_client(
    client_id: int,
    donnees: ClientUpdate,
    db: SessionDep,
    _utilisateur: CurrentUser,
) -> Client:
    """Modification partielle. nom, prenom et telephone ne peuvent pas être vidés (422)."""
    client = service.modifier_client(db, client_id, donnees)
    db.commit()
    return client