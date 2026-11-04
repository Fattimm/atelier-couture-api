from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings

# ---------------------------------------------------------------------------
# Hachage des mots de passe (RG21)
# ---------------------------------------------------------------------------

# Outil de hachage configuré avec Argon2 (variante Argon2id)
_password_hash = PasswordHash((Argon2Hasher(),))


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Renvoie le hash Argon2 d'un mot de passe (avec un sel aléatoire inclus)."""
    return _password_hash.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    """Vérifie qu'un mot de passe en clair correspond au hash enregistré."""
    return _password_hash.verify(mot_de_passe, mot_de_passe_hash)


# ---------------------------------------------------------------------------
# Jetons d'accès JWT (RG22)
# ---------------------------------------------------------------------------


def creer_jeton_acces(utilisateur_id: int) -> tuple[str, int]:
    """Crée un jeton JWT signé pour un utilisateur.

    Renvoie le jeton et sa durée de validité en secondes (pour le champ expires_in).
    """
    duree_secondes = settings.access_token_expire_minutes * 60
    maintenant = datetime.now(timezone.utc)

    contenu = {
        "sub": str(utilisateur_id),
        "iat": maintenant,
        "exp": maintenant + timedelta(seconds=duree_secondes),
    }
    jeton = jwt.encode(contenu, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return jeton, duree_secondes


def decoder_jeton_acces(jeton: str) -> int | None:
    """Vérifie un jeton et renvoie l'id de l'utilisateur, ou None s'il est invalide ou expiré."""
    try:
        contenu = jwt.decode(
            jeton,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
        return int(contenu["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None