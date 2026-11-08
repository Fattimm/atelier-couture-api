from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.core.exceptions import DonneesInvalides

from app.services.commandes import condition_en_retard
from app.services.commun import paginer
from sqlalchemy import Date, cast, func, select
from app.models import (
    Client,
    Commande,
    LigneCommande,
    Livraison,
    Paiement,
    StatutCommande,
    StatutLivraison,
    TypeVetement,
)
from app.schemas.statistiques import (
    ChiffreAffaires,
    Granularite,
    PeriodeChiffreAffaires,
    TableauDeBord,
    TopClient,
    VenteTypeVetement,
)

NON_ANNULEE = Commande.statut != StatutCommande.annulee


def _bornes_mois(jour: date) -> tuple[date, date]:
    """Premier jour du mois de `jour`, et premier jour du mois suivant (borne exclue)."""
    debut = jour.replace(day=1)
    if debut.month == 12:
        fin = debut.replace(year=debut.year + 1, month=1)
    else:
        fin = debut.replace(month=debut.month + 1)
    return debut, fin


def tableau_de_bord(db: Session) -> TableauDeBord:
    """Indicateurs du mois courant et de la situation actuelle (route 39)."""
    aujourd_hui = date.today()
    debut_mois, debut_mois_suivant = _bornes_mois(aujourd_hui)

    # --- Mois courant ---
    commandes_du_mois = (
        NON_ANNULEE,
        Commande.date_commande >= debut_mois,
        Commande.date_commande < debut_mois_suivant,
    )
    chiffre_affaires_mois = db.scalar(
        select(func.coalesce(func.sum(Commande.montant_total), 0)).where(*commandes_du_mois)
    )
    nb_commandes_mois = db.scalar(select(func.count(Commande.id)).where(*commandes_du_mois))
    encaisse_mois = db.scalar(
        select(func.coalesce(func.sum(Paiement.montant), 0)).where(
            Paiement.date_paiement >= debut_mois,
            Paiement.date_paiement < debut_mois_suivant,
        )
    )

    # --- Situation actuelle ---
    reste_a_encaisser = db.scalar(
        select(func.coalesce(func.sum(Commande.montant_total - Commande.montant_paye), 0)).where(NON_ANNULEE)
    )

    # Tous les statuts, même à 0, complétés par un GROUP BY
    commandes_par_statut = {statut: 0 for statut in StatutCommande}
    for statut, nombre in db.execute(
        select(Commande.statut, func.count(Commande.id)).group_by(Commande.statut)
    ):
        commandes_par_statut[statut] = nombre

    nb_commandes_en_retard = db.scalar(select(func.count(Commande.id)).where(condition_en_retard()))
    livraisons_du_jour = db.scalar(
        select(func.count(Livraison.id)).where(
            Livraison.date_prevue == aujourd_hui,
            Livraison.statut == StatutLivraison.planifiee,
        )
    )

    return TableauDeBord(
        chiffre_affaires_mois=chiffre_affaires_mois,
        encaisse_mois=encaisse_mois,
        nb_commandes_mois=nb_commandes_mois,
        reste_a_encaisser=reste_a_encaisser,
        commandes_par_statut=commandes_par_statut,
        nb_commandes_en_retard=nb_commandes_en_retard,
        commandes_pretes_a_livrer=commandes_par_statut[StatutCommande.terminee],
        livraisons_du_jour=livraisons_du_jour,
    )


def lister_impayes(db: Session, limit: int, offset: int) -> tuple[list[Commande], int]:
    """Commandes non annulées non soldées, les plus urgentes d'abord (route 43)."""
    requete = (
        select(Commande)
        .options(selectinload(Commande.client))
        .where(NON_ANNULEE, Commande.montant_paye < Commande.montant_total)
        .order_by(Commande.date_livraison_prevue, Commande.id)
    )
    return paginer(db, requete, limit, offset)


# --- Période commune aux statistiques (routes 40 à 42) ------------------------


def resoudre_periode(date_debut: date | None, date_fin: date | None) -> tuple[date, date]:
    """Par défaut : du 1er du mois courant à aujourd'hui. 422 si date_debut > date_fin."""
    aujourd_hui = date.today()
    debut = date_debut or aujourd_hui.replace(day=1)
    fin = date_fin or aujourd_hui
    if debut > fin:
        raise DonneesInvalides(f"date_debut ({debut}) ne peut pas être postérieure à date_fin ({fin})")
    return debut, fin


def _periode_sql(colonne, granularite: Granularite):
    """Ramène une date au début du jour ou du mois (date_trunc), pour le regroupement."""
    unite = "day" if granularite == Granularite.jour else "month"
    return cast(func.date_trunc(unite, colonne), Date)


def _formater_periode(jour: date, granularite: Granularite) -> str:
    return jour.isoformat() if granularite == Granularite.jour else jour.strftime("%Y-%m")


# --- Route 40 -------------------------------------------------------------------


def chiffre_affaires(
    db: Session,
    granularite: Granularite,
    date_debut: date | None,
    date_fin: date | None,
) -> ChiffreAffaires:
    """Chiffre d'affaires (date de commande) et encaissements (date de paiement) par période."""
    debut, fin = resoudre_periode(date_debut, date_fin)

    periode_ca = _periode_sql(Commande.date_commande, granularite).label("periode")
    lignes_ca = db.execute(
        select(periode_ca, func.sum(Commande.montant_total))
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(periode_ca)
    ).all()

    periode_enc = _periode_sql(Paiement.date_paiement, granularite).label("periode")
    lignes_enc = db.execute(
        select(periode_enc, func.sum(Paiement.montant))
        .where(Paiement.date_paiement.between(debut, fin))
        .group_by(periode_enc)
    ).all()

    # Fusion : toutes les périodes présentes dans l'un ou l'autre des résultats
    par_periode: dict[date, dict[str, int]] = {}
    for jour, montant in lignes_ca:
        par_periode.setdefault(jour, {"chiffre_affaires": 0, "encaisse": 0})["chiffre_affaires"] = montant
    for jour, montant in lignes_enc:
        par_periode.setdefault(jour, {"chiffre_affaires": 0, "encaisse": 0})["encaisse"] = montant

    periodes = [
        PeriodeChiffreAffaires(periode=_formater_periode(jour, granularite), **valeurs)
        for jour, valeurs in sorted(par_periode.items())
    ]
    return ChiffreAffaires(
        granularite=granularite,
        date_debut=debut,
        date_fin=fin,
        total_chiffre_affaires=sum(p.chiffre_affaires for p in periodes),
        total_encaisse=sum(p.encaisse for p in periodes),
        periodes=periodes,
    )


# --- Route 41 -------------------------------------------------------------------


def ventes_par_type_vetement(db: Session, date_debut: date | None, date_fin: date | None) -> list[VenteTypeVetement]:
    """Quantité vendue et chiffre d'affaires avant remise, par prestation, du plus élevé au plus faible."""
    debut, fin = resoudre_periode(date_debut, date_fin)

    quantite = func.sum(LigneCommande.quantite).label("quantite_vendue")
    ca = func.sum(LigneCommande.quantite * LigneCommande.prix_unitaire).label("chiffre_affaires")
    requete = (
        select(TypeVetement.id, TypeVetement.nom, quantite, ca)
        .join(LigneCommande, LigneCommande.type_vetement_id == TypeVetement.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(TypeVetement.id, TypeVetement.nom)
        .order_by(ca.desc(), TypeVetement.nom)
    )
    return [
        VenteTypeVetement(type_vetement_id=ligne.id, nom=ligne.nom,
                          quantite_vendue=ligne.quantite_vendue, chiffre_affaires=ligne.chiffre_affaires)
        for ligne in db.execute(requete)
    ]


# --- Route 42 -------------------------------------------------------------------


def top_clients(db: Session, limite: int, date_debut: date | None, date_fin: date | None) -> list[TopClient]:
    """Meilleurs clients de la période, par chiffre d'affaires décroissant."""
    debut, fin = resoudre_periode(date_debut, date_fin)

    ca = func.sum(Commande.montant_total).label("chiffre_affaires")
    requete = (
        select(
            Client.id,
            Client.prenom,
            Client.nom,
            func.count(Commande.id).label("nb_commandes"),
            ca,
            func.sum(Commande.montant_total - Commande.montant_paye).label("solde_du"),
        )
        .join(Commande, Commande.client_id == Client.id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(Client.id, Client.prenom, Client.nom)
        .order_by(ca.desc(), Client.id)
        .limit(limite)
    )
    return [
        TopClient(client_id=ligne.id, client_nom=f"{ligne.prenom} {ligne.nom}", nb_commandes=ligne.nb_commandes,
                  chiffre_affaires=ligne.chiffre_affaires, solde_du=ligne.solde_du)
        for ligne in db.execute(requete)
    ]