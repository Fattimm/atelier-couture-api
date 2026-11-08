from typing import Any

from fastapi import APIRouter

from app.core.deps import AdminUser, LimitParam, OffsetParam, SessionDep
from app.schemas.commande import CommandeResume
from app.schemas.commun import Page
from app.schemas.statistiques import TableauDeBord
from app.services import statistiques as service

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