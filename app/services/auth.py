from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hacher_mot_de_passe, verifier_mot_de_passe
from app.models import Utilisateur

# Hash d'un mot de passe fictif, calculé une seule fois au démarrage.
# Il sert à garder un temps de réponse identique quand l'e-mail est inconnu
# (protection contre les attaques temporelles, RG23).
_HASH_FICTIF = hacher_mot_de_passe("mot-de-passe-fictif-jamais-utilise")


def authentifier(db: Session, email: str, mot_de_passe: str) -> Utilisateur | None:
    """Renvoie l'utilisateur si les identifiants sont corrects et le compte actif, sinon None.

    Aucune distinction n'est faite entre les causes d'échec (RG23).
    """
    email = email.strip().lower()
    utilisateur = db.scalar(select(Utilisateur).where(Utilisateur.email == email))

    if utilisateur is None:
        verifier_mot_de_passe(mot_de_passe, _HASH_FICTIF)
        return None

    if not verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe_hash):
        return None

    # RG22 / route 1 : un compte désactivé ne peut pas se connecter
    if not utilisateur.actif:
        return None

    return utilisateur