from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import Conflit, DonneesInvalides, RessourceIntrouvable
from app.models import Commande, HistoriqueStatut, LigneCommande, StatutCommande, Utilisateur
from app.schemas.commande import CommandeCreate, LigneCreate
from app.services.catalogue import obtenir_type_vetement
from app.services.clients import obtenir_client
from app.services.mesures import dernieres_mesures_du_client, obtenir_mesure


# --- Outils internes ----------------------------------------------------------


def _choisir_mesure(db: Session, client_id: int, mesure_id: int | None) -> int | None:
    """RG9 : mesures fournies (du même client), sinon les dernières du client, s'il en a."""
    if mesure_id is not None:
        mesure = obtenir_mesure(db, mesure_id)  # 404 si inconnues
        if mesure.client_id != client_id:
            raise DonneesInvalides("Ces mesures appartiennent à un autre client que celui de la commande")
        return mesure.id

    dernieres = dernieres_mesures_du_client(db, client_id)
    return dernieres.id if dernieres is not None else None


def _preparer_ligne(db: Session, donnees: LigneCreate) -> tuple[LigneCommande, int]:
    """RG6 : prestation active, prix du catalogue par défaut. Renvoie la ligne et le délai."""
    type_vetement = obtenir_type_vetement(db, donnees.type_vetement_id)  # 404 si inconnue
    if not type_vetement.actif:
        raise DonneesInvalides(f"La prestation « {type_vetement.nom} » n'est plus proposée au catalogue")

    prix = donnees.prix_unitaire if donnees.prix_unitaire is not None else type_vetement.prix_base
    ligne = LigneCommande(
        type_vetement=type_vetement,
        description=donnees.description,
        quantite=donnees.quantite,
        prix_unitaire=prix,
    )
    return ligne, type_vetement.delai_jours


def _prochain_id_commande(db: Session) -> int:
    """Réserve le prochain identifiant auprès de la séquence, avant l'insertion (RG5)."""
    return db.scalar(select(func.nextval("commandes_id_seq")))


def _formater_numero(annee: int, commande_id: int) -> str:
    """RG5 : CMD-AAAA-NNNNN, par exemple CMD-2026-00017."""
    return f"CMD-{annee}-{commande_id:05d}"


# --- Règles réutilisables -------------------------------------------------------


def recalculer_montant_total(commande: Commande) -> None:
    """RG7 : total = somme (quantité × prix unitaire) − remise.

    La remise ne peut pas dépasser la somme des prestations (422), et le total
    ne peut jamais redescendre sous le montant déjà payé (409).
    """
    somme_prestations = sum(ligne.sous_total for ligne in commande.lignes)
    if commande.remise > somme_prestations:
        raise DonneesInvalides(
            f"La remise ({commande.remise} F) dépasse la somme des prestations ({somme_prestations} F)"
        )

    nouveau_total = somme_prestations - commande.remise
    if nouveau_total < commande.montant_paye:
        raise Conflit(
            f"Le total ({nouveau_total} F) serait inférieur au montant déjà payé ({commande.montant_paye} F)"
        )
    commande.montant_total = nouveau_total


# --- Création et lecture ---------------------------------------------------------


def creer_commande(db: Session, donnees: CommandeCreate, auteur: Utilisateur) -> Commande:
    """Crée une commande en appliquant RG5 à RG9 et RG15 (route 24)."""
    obtenir_client(db, donnees.client_id)  # 404 si inconnu
    mesure_id = _choisir_mesure(db, donnees.client_id, donnees.mesure_id)

    lignes: list[LigneCommande] = []
    delais: list[int] = []
    for donnees_ligne in donnees.lignes:
        ligne, delai = _preparer_ligne(db, donnees_ligne)
        lignes.append(ligne)
        delais.append(delai)

    # RG8 : date prévue = date de commande + le plus long délai, sauf si fournie
    date_commande = date.today()
    date_prevue = donnees.date_livraison_prevue or date_commande + timedelta(days=max(delais))
    if date_prevue < date_commande:
        raise DonneesInvalides("La date de livraison prévue ne peut pas précéder la date de commande")

    commande_id = _prochain_id_commande(db)
    commande = Commande(
        id=commande_id,
        numero=_formater_numero(date_commande.year, commande_id),
        client_id=donnees.client_id,
        mesure_id=mesure_id,
        statut=StatutCommande.en_attente,
        date_commande=date_commande,
        date_livraison_prevue=date_prevue,
        remise=donnees.remise,
        montant_paye=0,  # explicite : les valeurs par défaut ne sont appliquées qu'au flush
        notes=donnees.notes,
        cree_par_id=auteur.id,
        lignes=lignes,
    )
    recalculer_montant_total(commande)

    # RG15 : la création inscrit la première ligne de l'historique (ancien statut vide)
    commande.historique.append(
        HistoriqueStatut(
            ancien_statut=None,
            nouveau_statut=StatutCommande.en_attente,
            commentaire="Création de la commande",
            utilisateur_id=auteur.id,
        )
    )

    db.add(commande)
    db.flush()
    return commande


def obtenir_commande(db: Session, commande_id: int) -> Commande:
    """Une commande avec son client, ses lignes et son historique (route 26). 404 si inconnue."""
    requete = (
        select(Commande)
        .where(Commande.id == commande_id)
        .options(
            joinedload(Commande.client),
            selectinload(Commande.lignes).joinedload(LigneCommande.type_vetement),
            selectinload(Commande.historique),
        )
    )
    commande = db.scalar(requete)
    if commande is None:
        raise RessourceIntrouvable(f"Aucune commande avec l'identifiant {commande_id}")
    return commande