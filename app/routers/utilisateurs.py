from fastapi import APIRouter, status

from app.core.deps import AdminUser, SessionDep
from app.models import Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurRead, UtilisateurUpdate
from app.services import utilisateurs as service

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])


@router.post("", response_model=UtilisateurRead, status_code=status.HTTP_201_CREATED)
def creer_utilisateur(donnees: UtilisateurCreate, db: SessionDep, _admin: AdminUser) -> Utilisateur:
    """Crée un compte (admin). 409 si l'e-mail existe déjà."""
    utilisateur = service.creer_utilisateur(db, donnees)
    db.commit()
    return utilisateur


@router.get("", response_model=list[UtilisateurRead])
def lister_utilisateurs(db: SessionDep, _admin: AdminUser) -> list[Utilisateur]:
    """Liste des comptes, triés par nom (admin)."""
    return service.lister_utilisateurs(db)


@router.get("/{utilisateur_id}", response_model=UtilisateurRead)
def obtenir_utilisateur(utilisateur_id: int, db: SessionDep, _admin: AdminUser) -> Utilisateur:
    """Détail d'un compte (admin). 404 s'il n'existe pas."""
    return service.obtenir_utilisateur(db, utilisateur_id)


@router.patch("/{utilisateur_id}", response_model=UtilisateurRead)
def modifier_utilisateur(
    utilisateur_id: int,
    donnees: UtilisateurUpdate,
    db: SessionDep,
    admin: AdminUser,
) -> Utilisateur:
    """Modifie nom, rôle, état actif ou mot de passe (admin). Voir RG24."""
    utilisateur = service.modifier_utilisateur(db, utilisateur_id, donnees, admin)
    db.commit()
    return utilisateur