"""Tests des commandes : montants, workflow des statuts et historique (RG5 à RG15)."""

import re
from datetime import date, timedelta

from app.models import Commande, StatutCommande


# --- Fonctions d'aide --------------------------------------------------------


def changer_statut(client, entetes, commande_id, statut, role="tailleur", **extra):
    return client.post(
        f"/api/v1/commandes/{commande_id}/statut",
        json={"statut": statut, **extra},
        headers=entetes(role),
    )


def payer(client, entetes, commande_id, montant):
    return client.post(
        f"/api/v1/commandes/{commande_id}/paiements",
        json={"montant": montant, "mode": "especes"},
        headers=entetes("accueil"),
    )


# --- RG5 : numéro de commande ------------------------------------------------


def test_rg5_format_du_numero(creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])

    assert re.fullmatch(r"CMD-\d{4}-\d{5}", commande["numero"])
    assert commande["numero"].startswith(f"CMD-{date.today().year}-")
    assert commande["numero"].endswith(f"{commande['id']:05d}")


# --- RG6 et RG7 : prix et montants -------------------------------------------


def test_rg6_rg7_prix_par_defaut_prix_negocie_et_remise(creer_client, creer_commande, catalogue):
    commande = creer_commande(
        creer_client()["id"],
        lignes=[
            {"type_vetement_id": catalogue["boubou"].id, "quantite": 2},  # prix du catalogue : 35 000
            {"type_vetement_id": catalogue["pantalon"].id, "prix_unitaire": 10_000},  # prix négocié
        ],
        remise=5_000,
    )

    assert [ligne["prix_unitaire"] for ligne in commande["lignes"]] == [35_000, 10_000]
    assert commande["montant_total"] == 2 * 35_000 + 10_000 - 5_000
    assert commande["montant_paye"] == 0
    assert commande["solde"] == commande["montant_total"]
    assert commande["statut"] == "en_attente"


def test_rg6_prestation_inactive_refusee(client, entetes, creer_client, catalogue):
    reponse = client.post(
        "/api/v1/commandes",
        json={"client_id": creer_client()["id"], "lignes": [{"type_vetement_id": catalogue["ancienne"].id}]},
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 422


def test_rg7_remise_superieure_aux_prestations_refusee(client, entetes, creer_client, catalogue):
    reponse = client.post(
        "/api/v1/commandes",
        json={
            "client_id": creer_client()["id"],
            "lignes": [{"type_vetement_id": catalogue["boubou"].id}],
            "remise": 40_000,
        },
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 422


def test_rg7_montants_imposes_par_le_client_refuses(client, entetes, creer_client, catalogue):
    reponse = client.post(
        "/api/v1/commandes",
        json={
            "client_id": creer_client()["id"],
            "lignes": [{"type_vetement_id": catalogue["boubou"].id}],
            "montant_total": 1,
        },
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 422


def test_rg7_total_jamais_sous_le_montant_deja_paye(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])  # 35 000
    payer(client, entetes, commande["id"], 30_000)

    reponse = client.patch(f"/api/v1/commandes/{commande['id']}", json={"remise": 10_000}, headers=entetes("accueil"))

    assert reponse.status_code == 409


# --- RG8 : date de livraison prévue ------------------------------------------


def test_rg8_date_prevue_par_defaut_selon_le_plus_long_delai(creer_client, creer_commande, catalogue):
    commande = creer_commande(
        creer_client()["id"],
        lignes=[
            {"type_vetement_id": catalogue["pantalon"].id},  # 4 jours
            {"type_vetement_id": catalogue["boubou"].id},  # 10 jours
        ],
    )

    assert commande["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()


def test_rg8_date_prevue_avant_la_commande_refusee(client, entetes, creer_client, catalogue):
    reponse = client.post(
        "/api/v1/commandes",
        json={
            "client_id": creer_client()["id"],
            "lignes": [{"type_vetement_id": catalogue["boubou"].id}],
            "date_livraison_prevue": (date.today() - timedelta(days=1)).isoformat(),
        },
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 422


# --- RG9 : mesures rattachées ------------------------------------------------


def test_rg9_dernieres_mesures_rattachees_automatiquement(creer_client, prendre_mesures, creer_commande):
    fatou = creer_client()
    prendre_mesures(fatou["id"], tour_taille=74)
    dernieres = prendre_mesures(fatou["id"], tour_taille=76)

    commande = creer_commande(fatou["id"])

    assert commande["mesure_id"] == dernieres["id"]


def test_rg9_client_sans_mesures(creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])

    assert commande["mesure_id"] is None


def test_rg9_mesures_d_un_autre_client_refusees(client, entetes, creer_client, prendre_mesures, catalogue):
    mesures_moussa = prendre_mesures(creer_client(nom="Ndiaye")["id"])

    reponse = client.post(
        "/api/v1/commandes",
        json={
            "client_id": creer_client(nom="Diop")["id"],
            "mesure_id": mesures_moussa["id"],
            "lignes": [{"type_vetement_id": catalogue["boubou"].id}],
        },
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 422


# --- RG10 : lignes de commande -----------------------------------------------


def test_rg10_ajout_de_ligne_recalcule_le_total(client, entetes, creer_client, creer_commande, catalogue):
    commande = creer_commande(creer_client()["id"])  # 35 000

    reponse = client.post(
        f"/api/v1/commandes/{commande['id']}/lignes",
        json={"type_vetement_id": catalogue["pantalon"].id},
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 201
    assert reponse.json()["montant_total"] == 35_000 + 12_000


def test_rg10_lignes_non_modifiables_apres_en_attente(client, entetes, creer_client, creer_commande, catalogue):
    commande = creer_commande(creer_client()["id"])
    changer_statut(client, entetes, commande["id"], "en_coupe")

    reponse = client.post(
        f"/api/v1/commandes/{commande['id']}/lignes",
        json={"type_vetement_id": catalogue["pantalon"].id},
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 409


def test_rg10_une_commande_garde_au_moins_une_ligne(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    ligne_id = commande["lignes"][0]["id"]

    reponse = client.delete(f"/api/v1/commandes/{commande['id']}/lignes/{ligne_id}", headers=entetes("accueil"))

    assert reponse.status_code == 409


# --- RG11 : retard ------------------------------------------------------------


def test_rg11_propriete_en_retard():
    hier = date.today() - timedelta(days=1)

    assert Commande(date_livraison_prevue=hier, statut=StatutCommande.en_couture).en_retard is True
    assert Commande(date_livraison_prevue=hier, statut=StatutCommande.livree).en_retard is False
    assert Commande(date_livraison_prevue=hier, statut=StatutCommande.annulee).en_retard is False
    assert Commande(date_livraison_prevue=date.today(), statut=StatutCommande.en_couture).en_retard is False


def test_rg11_filtre_en_retard(client, db, entetes, creer_client, creer_commande):
    en_retard = creer_commande(creer_client()["id"])
    a_l_heure = creer_commande(creer_client()["id"])

    # On recule les dates directement en base (impossible via l'API, à cause de RG8)
    commande = db.get(Commande, en_retard["id"])
    commande.date_commande = date.today() - timedelta(days=20)
    commande.date_livraison_prevue = date.today() - timedelta(days=5)
    db.flush()

    reponse = client.get("/api/v1/commandes", params={"en_retard": True}, headers=entetes("accueil")).json()

    ids = [c["id"] for c in reponse["items"]]
    assert en_retard["id"] in ids
    assert a_l_heure["id"] not in ids
    assert all(c["en_retard"] for c in reponse["items"])


# --- Workflow des statuts, RG12 à RG15 ----------------------------------------


def test_transition_interdite_indique_les_statuts_possibles(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])

    reponse = changer_statut(client, entetes, commande["id"], "terminee", role="accueil")

    assert reponse.status_code == 409
    assert reponse.json()["detail"] == (
        "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe"
    )


def test_parcours_de_production_avec_aller_retour_et_historique(client, entetes, creer_client, creer_commande, utilisateurs):
    commande = creer_commande(creer_client()["id"])
    parcours = ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]

    for statut in parcours:
        assert changer_statut(client, entetes, commande["id"], statut).status_code == 200

    historique = client.get(f"/api/v1/commandes/{commande['id']}/historique", headers=entetes("accueil")).json()

    # RG15 : la création inscrit la première ligne, avec un ancien statut vide
    assert historique[0]["ancien_statut"] is None
    assert historique[0]["nouveau_statut"] == "en_attente"
    assert historique[0]["utilisateur_id"] == utilisateurs["accueil"].id
    # puis un changement par étape, dans l'ordre, par le tailleur
    assert [h["nouveau_statut"] for h in historique[1:]] == parcours
    assert {h["utilisateur_id"] for h in historique[1:]} == {utilisateurs["tailleur"].id}


def test_rg13_statut_deja_en_cours_refuse(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])

    reponse = changer_statut(client, entetes, commande["id"], "en_attente", role="accueil")

    assert reponse.status_code == 409


def test_rg13_livree_interdit_par_la_route_de_statut(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    for statut in ["en_coupe", "en_couture", "terminee"]:
        changer_statut(client, entetes, commande["id"], statut)

    reponse = changer_statut(client, entetes, commande["id"], "livree", role="accueil")

    assert reponse.status_code == 409


def test_rg14_le_tailleur_ne_peut_pas_annuler(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])

    reponse = changer_statut(client, entetes, commande["id"], "annulee", role="tailleur")

    assert reponse.status_code == 403


def test_rg14_annulation_avec_acompte_exige_un_commentaire(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    payer(client, entetes, commande["id"], 5_000)

    sans_commentaire = changer_statut(client, entetes, commande["id"], "annulee", role="accueil")
    avec_commentaire = changer_statut(
        client, entetes, commande["id"], "annulee", role="accueil", commentaire="Acompte remboursé"
    )

    assert sans_commentaire.status_code == 422
    assert avec_commentaire.status_code == 200


def test_rg12_commande_annulee_n_est_plus_modifiable(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    changer_statut(client, entetes, commande["id"], "annulee", role="accueil")

    modification = client.patch(f"/api/v1/commandes/{commande['id']}", json={"notes": "x"}, headers=entetes("accueil"))
    statut = changer_statut(client, entetes, commande["id"], "en_coupe", role="accueil")

    assert modification.status_code == 409
    assert statut.status_code == 409