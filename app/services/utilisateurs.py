from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import Conflit, DonneesInvalides, RessourceIntrouvable
from app.core.security import hacher_mot_de_passe
from app.models import RoleUtilisateur, Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurUpdate

MESSAGE_EMAIL_PRIS = "Un compte existe déjà avec cet e-mail"


def creer_utilisateur(db: Session, donnees: UtilisateurCreate) -> Utilisateur:
    """Crée un compte. Lève Conflit si l'e-mail est déjà utilisé."""
    deja_pris = db.scalar(select(Utilisateur.id).where(Utilisateur.email == donnees.email))
    if deja_pris is not None:
        raise Conflit(MESSAGE_EMAIL_PRIS)

    utilisateur = Utilisateur(
        email=donnees.email,
        nom_complet=donnees.nom_complet,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
        role=donnees.role,
    )
    db.add(utilisateur)
    try:
        db.flush()  # envoie l'INSERT : génère l'id et vérifie la contrainte d'unicité
    except IntegrityError:
        raise Conflit(MESSAGE_EMAIL_PRIS) from None
    return utilisateur


def lister_utilisateurs(db: Session) -> list[Utilisateur]:
    """Renvoie tous les comptes, triés par nom."""
    requete = select(Utilisateur).order_by(Utilisateur.nom_complet, Utilisateur.id)
    return list(db.scalars(requete))


def obtenir_utilisateur(db: Session, utilisateur_id: int) -> Utilisateur:
    """Renvoie un compte. Lève RessourceIntrouvable s'il n'existe pas."""
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise RessourceIntrouvable(f"Aucun utilisateur avec l'identifiant {utilisateur_id}")
    return utilisateur


def modifier_utilisateur(
    db: Session,
    utilisateur_id: int,
    donnees: UtilisateurUpdate,
    auteur: Utilisateur,
) -> Utilisateur:
    """Modifie seulement les champs envoyés. Applique RG24."""
    utilisateur = obtenir_utilisateur(db, utilisateur_id)
    changements = donnees.model_dump(exclude_unset=True)

    # Un champ envoyé explicitement à null ne peut pas vider une colonne obligatoire
    champs_vides = [champ for champ, valeur in changements.items() if valeur is None]
    if champs_vides:
        raise DonneesInvalides(f"Ces champs ne peuvent pas être vides : {', '.join(champs_vides)}")

    # RG24 : un administrateur ne peut ni se désactiver, ni retirer son propre rôle d'admin
    if utilisateur.id == auteur.id:
        if changements.get("actif") is False:
            raise Conflit("Vous ne pouvez pas désactiver votre propre compte")
        if "role" in changements and changements["role"] != RoleUtilisateur.admin:
            raise Conflit("Vous ne pouvez pas retirer votre propre rôle d'administrateur")

    # Le mot de passe n'est jamais stocké en clair : on le hache
    if "mot_de_passe" in changements:
        utilisateur.mot_de_passe_hash = hacher_mot_de_passe(changements.pop("mot_de_passe"))

    for champ, valeur in changements.items():
        setattr(utilisateur, champ, valeur)

    return utilisateur