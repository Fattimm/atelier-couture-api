from datetime import date, timedelta

from sqlalchemy import and_, func, not_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.schemas.commande import CommandeCreate, LigneCreate, StatutChangement
from app.services.catalogue import obtenir_type_vetement
from app.services.clients import obtenir_client
from app.services.mesures import dernieres_mesures_du_client, obtenir_mesure
from app.core.exceptions import ActionInterdite, Conflit, DonneesInvalides, RessourceIntrouvable
from app.models import (Commande, HistoriqueStatut, LigneCommande, RoleUtilisateur, StatutCommande, Utilisateur,)
from app.services.commun import paginer

# --- Outils internes ----------------------------------------------------------

# Workflow des statuts (section 6 de l'énoncé) : statut actuel → statuts suivants autorisés
TRANSITIONS: dict[StatutCommande, set[StatutCommande]] = {
    StatutCommande.en_attente: {StatutCommande.en_coupe, StatutCommande.annulee},
    StatutCommande.en_coupe: {StatutCommande.en_couture, StatutCommande.annulee},
    StatutCommande.en_couture: {StatutCommande.essayage, StatutCommande.terminee, StatutCommande.annulee},
    StatutCommande.essayage: {StatutCommande.retouches, StatutCommande.terminee, StatutCommande.annulee},
    StatutCommande.retouches: {StatutCommande.essayage, StatutCommande.terminee, StatutCommande.annulee},
    StatutCommande.terminee: {StatutCommande.livree},  # uniquement par la confirmation de livraison
    StatutCommande.livree: set(),  # statut final
    StatutCommande.annulee: set(),  # statut final
}

STATUTS_FINAUX = {StatutCommande.livree, StatutCommande.annulee}


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


# --- Workflow des statuts ----------------------------------------------------


def enregistrer_changement_statut(
    commande: Commande,
    nouveau_statut: StatutCommande,
    auteur: Utilisateur,
    commentaire: str | None,
) -> None:
    """RG15 : applique le nouveau statut et l'inscrit dans l'historique."""
    commande.historique.append(
        HistoriqueStatut(
            ancien_statut=commande.statut,
            nouveau_statut=nouveau_statut,
            commentaire=commentaire,
            utilisateur_id=auteur.id,
        )
    )
    commande.statut = nouveau_statut


def changer_statut(
    db: Session,
    commande_id: int,
    donnees: StatutChangement,
    auteur: Utilisateur,
) -> Commande:
    """Fait évoluer le statut selon le workflow (route 28). Applique RG12 à RG15."""
    commande = obtenir_commande(db, commande_id)
    actuel, demande = commande.statut, donnees.statut
    commentaire = donnees.commentaire or None  # un commentaire vide compte comme absent

    # RG14 : le tailleur ne peut pas annuler une commande
    if demande == StatutCommande.annulee and auteur.role == RoleUtilisateur.tailleur:
        raise ActionInterdite("Le tailleur ne peut pas annuler une commande")

    # RG13 : demander le statut déjà en cours est refusé
    if demande == actuel:
        raise Conflit(f"La commande est déjà au statut {actuel.value}")

    # RG13 : « livree » résulte uniquement de la confirmation de livraison
    if demande == StatutCommande.livree:
        raise Conflit(
            "Le statut livree ne peut pas être posé ici : il résulte de la confirmation de livraison"
        )

    # RG12 : une commande livrée ou annulée n'est plus modifiable
    if actuel in STATUTS_FINAUX:
        raise Conflit(f"La commande est {actuel.value} : elle n'est plus modifiable")

    # Workflow : la transition doit figurer dans le tableau
    if demande not in TRANSITIONS[actuel]:
        possibles = sorted(s.value for s in TRANSITIONS[actuel] if s != StatutCommande.livree)
        liste = ", ".join(possibles) if possibles else "aucun (seule la confirmation de livraison est possible)"
        raise Conflit(f"Transition interdite : {actuel.value} → {demande.value}. Statuts possibles : {liste}")

    # RG14 : annuler une commande qui a reçu un acompte exige un commentaire
    if demande == StatutCommande.annulee and commande.montant_paye > 0 and commentaire is None:
        raise DonneesInvalides(
            f"Cette commande a reçu {commande.montant_paye} F : indiquez en commentaire "
            "ce que devient cet argent (remboursement, avoir...)"
        )

    enregistrer_changement_statut(commande, demande, auteur, commentaire)
    db.flush()
    return commande


def lister_historique(db: Session, commande_id: int) -> list[HistoriqueStatut]:
    """Changements de statut d'une commande, dans l'ordre chronologique (route 29)."""
    return obtenir_commande(db, commande_id).historique


# --- Liste des commandes -------------------------------------------------------


def _condition_en_retard():
    """RG11 en SQL : date prévue dépassée, et commande ni livrée ni annulée.

    C'est la même règle que la propriété Commande.en_retard (version Python) :
    toute modification de l'une doit être reportée sur l'autre.
    """
    return and_(
        Commande.date_livraison_prevue < date.today(),
        Commande.statut.not_in(STATUTS_FINAUX),
    )


def lister_commandes(
    db: Session,
    *,
    statut: StatutCommande | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    numero: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Commande], int]:
    """Liste paginée, la plus récente d'abord, avec filtres facultatifs (route 25)."""
    if date_min is not None and date_max is not None and date_min > date_max:
        raise DonneesInvalides("date_min ne peut pas être postérieure à date_max")

    requete = (
        select(Commande)
        .options(selectinload(Commande.client))
        .order_by(Commande.date_commande.desc(), Commande.id.desc())
    )

    if statut is not None:
        requete = requete.where(Commande.statut == statut)
    if client_id is not None:
        requete = requete.where(Commande.client_id == client_id)
    if date_min is not None:
        requete = requete.where(Commande.date_commande >= date_min)
    if date_max is not None:
        requete = requete.where(Commande.date_commande <= date_max)
    if numero:
        requete = requete.where(Commande.numero.icontains(numero.strip(), autoescape=True))
    if en_retard is True:
        requete = requete.where(_condition_en_retard())
    elif en_retard is False:
        requete = requete.where(not_(_condition_en_retard()))

    return paginer(db, requete, limit, offset)