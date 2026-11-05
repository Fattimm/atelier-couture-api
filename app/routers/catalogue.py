from fastapi import APIRouter, status

from app.core.deps import AdminUser, CurrentUser, SessionDep
from app.models import TypeVetement
from app.schemas.type_vetement import TypeVetementCreate, TypeVetementRead, TypeVetementUpdate
from app.services import catalogue as service

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


@router.post("", response_model=TypeVetementRead, status_code=status.HTTP_201_CREATED)
def creer_prestation(donnees: TypeVetementCreate, db: SessionDep, _admin: AdminUser) -> TypeVetement:
    """Ajoute une prestation (admin). 409 si le nom existe déjà."""
    type_vetement = service.creer_type_vetement(db, donnees)
    db.commit()
    return type_vetement


@router.get("", response_model=list[TypeVetementRead])
def lister_prestations(
    db: SessionDep,
    _utilisateur: CurrentUser,
    actifs_seulement: bool = True,
) -> list[TypeVetement]:
    """Liste triée par nom. Seules les prestations actives, sauf si actifs_seulement=false."""
    return service.lister_types_vetement(db, actifs_seulement)


@router.get("/{type_vetement_id}", response_model=TypeVetementRead)
def obtenir_prestation(type_vetement_id: int, db: SessionDep, _utilisateur: CurrentUser) -> TypeVetement:
    """Détail d'une prestation. 404 si elle n'existe pas."""
    return service.obtenir_type_vetement(db, type_vetement_id)


@router.patch("/{type_vetement_id}", response_model=TypeVetementRead)
def modifier_prestation(
    type_vetement_id: int,
    donnees: TypeVetementUpdate,
    db: SessionDep,
    _admin: AdminUser,
) -> TypeVetement:
    """Modifie prix, délai, nom ou description (admin). actif=false retire la prestation."""
    type_vetement = service.modifier_type_vetement(db, type_vetement_id, donnees)
    db.commit()
    return type_vetement