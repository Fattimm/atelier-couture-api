from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import Conflit, DonneesInvalides, RessourceIntrouvable
from app.models import TypeVetement
from app.schemas.type_vetement import TypeVetementCreate, TypeVetementUpdate
from app.services.commun import verifier_champs_non_vides

MESSAGE_NOM_PRIS = "Une prestation porte déjà ce nom dans le catalogue"

# Seule colonne facultative : on peut l'effacer en envoyant null
CHAMPS_EFFACABLES = {"description"}


def _nom_deja_pris(db: Session, nom: str, sauf_id: int | None = None) -> bool:
    """Vrai si une autre prestation porte ce nom (sans tenir compte des majuscules)."""
    requete = select(TypeVetement.id).where(func.lower(TypeVetement.nom) == nom.lower())
    if sauf_id is not None:
        requete = requete.where(TypeVetement.id != sauf_id)
    return db.scalar(requete) is not None


def creer_type_vetement(db: Session, donnees: TypeVetementCreate) -> TypeVetement:
    """Ajoute une prestation au catalogue. Lève Conflit si le nom existe déjà."""
    if _nom_deja_pris(db, donnees.nom):
        raise Conflit(MESSAGE_NOM_PRIS)

    type_vetement = TypeVetement(**donnees.model_dump())
    db.add(type_vetement)
    try:
        db.flush()
    except IntegrityError:
        raise Conflit(MESSAGE_NOM_PRIS) from None
    return type_vetement


def lister_types_vetement(db: Session, actifs_seulement: bool = True) -> list[TypeVetement]:
    """Liste du catalogue, triée par nom. Par défaut, seulement les prestations actives."""
    requete = select(TypeVetement).order_by(TypeVetement.nom, TypeVetement.id)
    if actifs_seulement:
        requete = requete.where(TypeVetement.actif.is_(True))
    return list(db.scalars(requete))


def obtenir_type_vetement(db: Session, type_vetement_id: int) -> TypeVetement:
    """Renvoie une prestation. Lève RessourceIntrouvable si elle n'existe pas."""
    type_vetement = db.get(TypeVetement, type_vetement_id)
    if type_vetement is None:
        raise RessourceIntrouvable(f"Aucune prestation avec l'identifiant {type_vetement_id}")
    return type_vetement


def modifier_type_vetement(
    db: Session,
    type_vetement_id: int,
    donnees: TypeVetementUpdate,
) -> TypeVetement:
    """Modifie seulement les champs envoyés. actif=false retire la prestation du catalogue."""
    type_vetement = obtenir_type_vetement(db, type_vetement_id)
    changements = donnees.model_dump(exclude_unset=True)

    verifier_champs_non_vides(changements, effacables=CHAMPS_EFFACABLES)

    if "nom" in changements and _nom_deja_pris(db, changements["nom"], sauf_id=type_vetement.id):
        raise Conflit(MESSAGE_NOM_PRIS)

    for champ, valeur in changements.items():
        setattr(type_vetement, champ, valeur)

    try:
        db.flush()
    except IntegrityError:
        raise Conflit(MESSAGE_NOM_PRIS) from None
    return type_vetement