from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import CurrentUser, SessionDep
from app.core.security import creer_jeton_acces
from app.models import Utilisateur
from app.schemas.auth import Jeton
from app.schemas.utilisateur import UtilisateurRead
from app.services.auth import authentifier

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton)
def login(
    db: SessionDep,
    formulaire: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Jeton:
    """Connexion : username = e-mail, password = mot de passe. Renvoie un jeton JWT."""
    utilisateur = authentifier(db, formulaire.username, formulaire.password)
    if utilisateur is None:
        # RG23 : même message quelle que soit la cause de l'échec
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou mot de passe incorrect, ou compte désactivé",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jeton, duree = creer_jeton_acces(utilisateur.id)
    return Jeton(access_token=jeton, expires_in=duree)


@router.get("/me", response_model=UtilisateurRead)
def me(utilisateur: CurrentUser) -> Utilisateur:
    """Profil de l'utilisateur connecté (sans aucune donnée sensible)."""
    return utilisateur