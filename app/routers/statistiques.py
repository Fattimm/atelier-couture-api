from typing import Any, Annotated

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, LimitParam, OffsetParam, SessionDep
from app.schemas.commande import CommandeResume
from app.schemas.commun import Page
from app.services import statistiques as service
from datetime import date
from app.schemas.statistiques import ChiffreAffaires, Granularite, TableauDeBord, TopClient, VenteTypeVetement



router = APIRouter(prefix="/statistiques", tags=["Statistiques"])


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def tableau_de_bord(db: SessionDep, _admin: AdminUser) -> TableauDeBord:
    """Indicateurs du mois courant et de la situation actuelle (admin)."""
    return service.tableau_de_bord(db)


@router.get("/impayes", response_model=Page[CommandeResume])
def impayes(
    db: SessionDep,
    _admin: AdminUser,
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
) -> dict[str, Any]:
    """Commandes non annulées non soldées, les plus urgentes d'abord (admin)."""
    elements, total = service.lister_impayes(db, limit, offset)
    return {"items": elements, "total": total, "limit": limit, "offset": offset}


@router.get("/chiffre-affaires", response_model=ChiffreAffaires)
def chiffre_affaires(
    db: SessionDep,
    _admin: AdminUser,
    granularite: Granularite = Granularite.jour,
    date_debut: date | None = None,
    date_fin: date | None = None,
) -> ChiffreAffaires:
    """Chiffre d'affaires et encaissements par jour ou par mois (admin). Par défaut : du 1er du mois à aujourd'hui."""
    return service.chiffre_affaires(db, granularite, date_debut, date_fin)


@router.get("/types-vetement", response_model=list[VenteTypeVetement])
def ventes_par_type_vetement(
    db: SessionDep,
    _admin: AdminUser,
    date_debut: date | None = None,
    date_fin: date | None = None,
) -> list[VenteTypeVetement]:
    """Quantité vendue et chiffre d'affaires avant remise, par prestation (admin)."""
    return service.ventes_par_type_vetement(db, date_debut, date_fin)


@router.get("/top-clients", response_model=list[TopClient])
def top_clients(
    db: SessionDep,
    _admin: AdminUser,
    limite: Annotated[int, Query(ge=1, le=100)] = 10,
    date_debut: date | None = None,
    date_fin: date | None = None,
) -> list[TopClient]:
    """Meilleurs clients de la période (admin)."""
    return service.top_clients(db, limite, date_debut, date_fin)