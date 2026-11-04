from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decoder_jeton_acces
from app.models import RoleUtilisateur, Utilisateur

# Lit le jeton dans l'en-tête "Authorization: Bearer ..." et active le bouton
# "Authorize" de Swagger. auto_error=False : on gère nous-mêmes l'absence de
# jeton, pour renvoyer un message en français.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Raccourci : une session de base de données
SessionDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: SessionDep,
    jeton: Annotated[str | None, Depends(oauth2_scheme)],
) -> Utilisateur:
    """Renvoie l'utilisateur connecté, ou lève une erreur 401."""
    if jeton is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise : aucun jeton fourni",
            headers={"WWW-Authenticate": "Bearer"},
        )

    utilisateur_id = decoder_jeton_acces(jeton)
    utilisateur = db.get(Utilisateur, utilisateur_id) if utilisateur_id is not None else None
    if utilisateur is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide ou expiré : reconnectez-vous",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # RG22 : un compte désactivé est refusé immédiatement, même avec un jeton valide
    if not utilisateur.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ce compte est désactivé",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return utilisateur


# Raccourci : l'utilisateur connecté (n'importe quel rôle)
CurrentUser = Annotated[Utilisateur, Depends(get_current_user)]


def require_roles(*roles: RoleUtilisateur) -> Callable[[Utilisateur], Utilisateur]:
    """Crée une dépendance qui n'accepte que les rôles donnés (l'admin passe toujours)."""

    def verifier_role(utilisateur: CurrentUser) -> Utilisateur:
        if utilisateur.role == RoleUtilisateur.admin or utilisateur.role in roles:
            return utilisateur
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : votre rôle ne permet pas cette action",
        )

    return verifier_role


# Raccourcis par rôle, à utiliser dans les routeurs
AdminUser = Annotated[Utilisateur, Depends(require_roles())]
AccueilUser = Annotated[Utilisateur, Depends(require_roles(RoleUtilisateur.accueil))]
TailleurUser = Annotated[Utilisateur, Depends(require_roles(RoleUtilisateur.tailleur))]