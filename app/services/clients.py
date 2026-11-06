from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import exists, func, or_, select

from app.core.exceptions import Conflit, RessourceIntrouvable
from app.services.commun import paginer, verifier_champs_non_vides
from app.models import Client, Commande, GenreClient, Mesure, StatutCommande
from app.schemas.client import ClientCreate, ClientResume, ClientUpdate, nettoyer_telephone



MESSAGE_TELEPHONE_PRIS = "Un client existe déjà avec ce numéro de téléphone"

# Champs facultatifs : on peut les effacer en envoyant null
CHAMPS_EFFACABLES = {"email", "adresse", "genre", "notes"}


def _telephone_deja_pris(db: Session, telephone: str, sauf_id: int | None = None) -> bool:
    """Vrai si un autre client a ce numéro (déjà normalisé)."""
    requete = select(Client.id).where(Client.telephone == telephone)
    if sauf_id is not None:
        requete = requete.where(Client.id != sauf_id)
    return db.scalar(requete) is not None


def creer_client(db: Session, donnees: ClientCreate) -> Client:
    """Crée un client. Lève Conflit si le téléphone est déjà utilisé (RG1)."""
    if _telephone_deja_pris(db, donnees.telephone):
        raise Conflit(MESSAGE_TELEPHONE_PRIS)

    client = Client(**donnees.model_dump())
    db.add(client)
    try:
        db.flush()
    except IntegrityError:
        raise Conflit(MESSAGE_TELEPHONE_PRIS) from None
    return client


def lister_clients(
    db: Session,
    q: str | None,
    genre: GenreClient | None,
    limit: int,
    offset: int,
) -> tuple[list[Client], int]:
    """Liste paginée, triée par nom puis prénom. q cherche dans nom, prénom et téléphone."""
    requete = select(Client).order_by(Client.nom, Client.prenom, Client.id)

    if q:
        q = q.strip()
        conditions = [
            Client.nom.icontains(q, autoescape=True),
            Client.prenom.icontains(q, autoescape=True),
        ]
        telephone = nettoyer_telephone(q)
        if telephone:
            conditions.append(Client.telephone.contains(telephone, autoescape=True))
        requete = requete.where(or_(*conditions))

    if genre is not None:
        requete = requete.where(Client.genre == genre)

    return paginer(db, requete, limit, offset)


def obtenir_client(db: Session, client_id: int) -> Client:
    """Renvoie un client. Lève RessourceIntrouvable s'il n'existe pas."""
    client = db.get(Client, client_id)
    if client is None:
        raise RessourceIntrouvable(f"Aucun client avec l'identifiant {client_id}")
    return client


def modifier_client(db: Session, client_id: int, donnees: ClientUpdate) -> Client:
    """Modification partielle. nom, prenom et telephone ne peuvent pas être vidés."""
    client = obtenir_client(db, client_id)
    changements = donnees.model_dump(exclude_unset=True)

    verifier_champs_non_vides(changements, effacables=CHAMPS_EFFACABLES)

    # Garder son propre numéro n'est pas un doublon : on s'exclut de la recherche
    if "telephone" in changements and _telephone_deja_pris(db, changements["telephone"], sauf_id=client.id):
        raise Conflit(MESSAGE_TELEPHONE_PRIS)

    for champ, valeur in changements.items():
        setattr(client, champ, valeur)

    try:
        db.flush()
    except IntegrityError:
        raise Conflit(MESSAGE_TELEPHONE_PRIS) from None
    return client


def supprimer_client(db: Session, client_id: int) -> None:
    """Supprime un client et ses mesures (route 11). 409 s'il a des commandes (RG4)."""
    client = obtenir_client(db, client_id)

    nb_commandes = db.scalar(select(func.count(Commande.id)).where(Commande.client_id == client.id))
    if nb_commandes:
        raise Conflit(f"Ce client a {nb_commandes} commande(s) : il ne peut pas être supprimé")

    db.delete(client)  # ses mesures sont supprimées en cascade par la base
    db.flush()


def resume_client(db: Session, client_id: int) -> ClientResume:
    """Résumé financier d'un client (route 13). Les commandes annulées sont exclues."""
    obtenir_client(db, client_id)

    requete = select(
        func.count(Commande.id),
        func.coalesce(func.sum(Commande.montant_total), 0),
        func.coalesce(func.sum(Commande.montant_paye), 0),
        func.max(Commande.date_commande),
    ).where(Commande.client_id == client_id, Commande.statut != StatutCommande.annulee)
    nb_commandes, chiffre_affaires, total_paye, derniere_commande = db.execute(requete).one()

    a_des_mesures = db.scalar(select(exists().where(Mesure.client_id == client_id)))

    return ClientResume(
        nb_commandes=nb_commandes,
        chiffre_affaires=chiffre_affaires,
        total_paye=total_paye,
        solde_du=chiffre_affaires - total_paye,
        derniere_commande=derniere_commande,
        a_des_mesures=a_des_mesures,
    )