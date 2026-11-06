from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DonneesInvalides, RessourceIntrouvable
from app.models import CHAMPS_MESURES, Mesure, Utilisateur
from app.schemas.mesure import MesureCreate, MesureUpdate
from app.services.clients import obtenir_client
from app.services.commun import verifier_champs_non_vides
from app.core.exceptions import Conflit, DonneesInvalides, RessourceIntrouvable
from app.models import CHAMPS_MESURES, Commande, Mesure, Utilisateur

# Les mesures et les notes sont facultatives : on peut les effacer avec null.
# date_prise, elle, est obligatoire.
CHAMPS_EFFACABLES = set(CHAMPS_MESURES) | {"notes"}


def creer_mesure(db: Session, client_id: int, donnees: MesureCreate, auteur: Utilisateur) -> Mesure:
    """Enregistre une nouvelle prise de mesures pour un client (route 18)."""
    obtenir_client(db, client_id)  # 404 si le client n'existe pas

    mesure = Mesure(
        client_id=client_id,
        prise_par_id=auteur.id,
        date_prise=donnees.date_prise or date.today(),
        notes=donnees.notes,
        **donnees.mesures_renseignees(),
    )
    db.add(mesure)
    db.flush()
    return mesure


def lister_mesures_client(db: Session, client_id: int) -> list[Mesure]:
    """Historique complet des prises d'un client, la plus récente d'abord (RG3)."""
    obtenir_client(db, client_id)
    requete = (
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
    )
    return list(db.scalars(requete))


def dernieres_mesures_du_client(db: Session, client_id: int) -> Mesure | None:
    """La prise la plus récente d'un client, ou None s'il n'en a aucune (RG3, RG9)."""
    requete = (
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
        .limit(1)
    )
    return db.scalar(requete)


def obtenir_derniere_mesure(db: Session, client_id: int) -> Mesure:
    """Les dernières mesures d'un client (route 20). 404 s'il n'en a aucune."""
    obtenir_client(db, client_id)
    mesure = dernieres_mesures_du_client(db, client_id)
    if mesure is None:
        raise RessourceIntrouvable("Ce client n'a encore aucune prise de mesures")
    return mesure


def obtenir_mesure(db: Session, mesure_id: int) -> Mesure:
    """Une prise de mesures. 404 si elle n'existe pas."""
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise RessourceIntrouvable(f"Aucune prise de mesures avec l'identifiant {mesure_id}")
    return mesure


def modifier_mesure(db: Session, mesure_id: int, donnees: MesureUpdate) -> Mesure:
    """Corrige une erreur de saisie (route 22). 422 si plus aucune mesure ne resterait."""
    mesure = obtenir_mesure(db, mesure_id)
    changements = donnees.model_dump(exclude_unset=True)

    verifier_champs_non_vides(changements, effacables=CHAMPS_EFFACABLES)

    # RG2 : on calcule l'état final AVANT de modifier quoi que ce soit
    reste_une_mesure = any(
        changements.get(champ, getattr(mesure, champ)) is not None for champ in CHAMPS_MESURES
    )
    if not reste_une_mesure:
        raise DonneesInvalides("Cette correction supprimerait toutes les mesures : il doit en rester au moins une")

    for champ, valeur in changements.items():
        setattr(mesure, champ, valeur)
    return mesure


def supprimer_mesure(db: Session, mesure_id: int) -> None:
    """Supprime une prise de mesures (route 23). 409 si une commande l'utilise (RG4)."""
    mesure = obtenir_mesure(db, mesure_id)

    numero = db.scalar(select(Commande.numero).where(Commande.mesure_id == mesure.id).limit(1))
    if numero is not None:
        raise Conflit(f"Ces mesures sont utilisées par la commande {numero} : elles ne peuvent pas être supprimées")

    db.delete(mesure)
    db.flush()