"""Tests des paiements, des livraisons et des statistiques (RG16 à RG20),
et du scénario complet de démonstration (annexe A)."""

from datetime import date, timedelta

from app.models import RoleUtilisateur


# --- Fonctions d'aide --------------------------------------------------------


def payer(client, entetes, commande_id, montant, **extra):
    return client.post(
        f"/api/v1/commandes/{commande_id}/paiements",
        json={"montant": montant, "mode": "especes", **extra},
        headers=entetes("accueil"),
    )


def amener_a_terminee(client, entetes, commande_id):
    for statut in ["en_coupe", "en_couture", "terminee"]:
        reponse = client.post(
            f"/api/v1/commandes/{commande_id}/statut", json={"statut": statut}, headers=entetes("tailleur")
        )
        assert reponse.status_code == 200, reponse.text


def confirmer(client, entetes, commande_id, **corps):
    return client.post(
        f"/api/v1/commandes/{commande_id}/livraison/confirmer", json=corps or None, headers=entetes("accueil")
    )


# --- RG16 : encaissement ------------------------------------------------------


def test_rg16_paiement_superieur_au_solde_refuse(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])  # 35 000

    reponse = payer(client, entetes, commande["id"], 40_000)

    assert reponse.status_code == 409
    assert "35000" in reponse.json()["detail"]  # le message indique le solde restant


def test_rg16_paiement_nul_ou_date_future_refuse(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    demain = (date.today() + timedelta(days=1)).isoformat()

    assert payer(client, entetes, commande["id"], 0).status_code == 422
    assert payer(client, entetes, commande["id"], 1_000, date_paiement=demain).status_code == 422


def test_rg16_paiement_refuse_sur_commande_annulee(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    client.post(f"/api/v1/commandes/{commande['id']}/statut", json={"statut": "annulee"}, headers=entetes("accueil"))

    reponse = payer(client, entetes, commande["id"], 1_000)

    assert reponse.status_code == 409


def test_paiements_mettent_a_jour_le_solde(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    payer(client, entetes, commande["id"], 10_000)
    payer(client, entetes, commande["id"], 5_000)

    detail = client.get(f"/api/v1/commandes/{commande['id']}", headers=entetes("accueil")).json()

    assert detail["montant_paye"] == 15_000
    assert detail["solde"] == 35_000 - 15_000
    assert [p["montant"] for p in detail["paiements"]] == [10_000, 5_000]  # ordre de saisie


# --- RG17 : annulation d'un paiement -----------------------------------------


def test_rg17_annuler_un_paiement_recalcule_le_solde(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    paiement = payer(client, entetes, commande["id"], 10_000).json()

    suppression = client.delete(f"/api/v1/paiements/{paiement['id']}", headers=entetes("admin"))
    detail = client.get(f"/api/v1/commandes/{commande['id']}", headers=entetes("admin")).json()

    assert suppression.status_code == 204
    assert detail["montant_paye"] == 0
    assert detail["solde"] == 35_000


# --- RG18 : planification ------------------------------------------------------


def test_rg18_livraison_a_domicile_exige_une_adresse(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])

    reponse = client.put(
        f"/api/v1/commandes/{commande['id']}/livraison",
        json={"mode": "domicile", "date_prevue": date.today().isoformat()},
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 422


def test_rg18_replanifier_modifie_la_livraison_et_la_date_prevue(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    url = f"/api/v1/commandes/{commande['id']}/livraison"
    dans_15_jours = (date.today() + timedelta(days=15)).isoformat()

    premiere = client.put(url, json={"mode": "retrait_atelier", "date_prevue": date.today().isoformat()}, headers=entetes("accueil"))
    seconde = client.put(url, json={"mode": "domicile", "date_prevue": dans_15_jours, "adresse": "Dakar"}, headers=entetes("accueil"))
    detail = client.get(f"/api/v1/commandes/{commande['id']}", headers=entetes("accueil")).json()

    assert seconde.status_code == 200
    assert seconde.json()["id"] == premiere.json()["id"]  # la même livraison, modifiée
    assert detail["date_livraison_prevue"] == dans_15_jours  # la commande suit la livraison


# --- RG19 et RG20 : confirmation de livraison --------------------------------


def test_rg19_commande_non_terminee_ne_peut_pas_etre_livree(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])

    assert confirmer(client, entetes, commande["id"]).status_code == 409


def test_rg19_commande_non_soldee_refusee_avec_le_montant_impaye(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    payer(client, entetes, commande["id"], 20_000)
    amener_a_terminee(client, entetes, commande["id"])

    reponse = confirmer(client, entetes, commande["id"])

    assert reponse.status_code == 409
    assert "15000" in reponse.json()["detail"]


def test_rg19_rg20_solde_impaye_autorise_et_retrait_atelier_automatique(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    payer(client, entetes, commande["id"], 20_000)
    amener_a_terminee(client, entetes, commande["id"])

    reponse = confirmer(client, entetes, commande["id"], autoriser_solde_impaye=True)
    historique = client.get(f"/api/v1/commandes/{commande['id']}/historique", headers=entetes("accueil")).json()

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "livree"
    assert corps["solde"] == 15_000  # la dette reste visible
    assert corps["livraison"]["mode"] == "retrait_atelier"  # créée automatiquement (RG20)
    assert "15000" in historique[-1]["commentaire"]  # mention inscrite dans l'historique (RG19)


def test_rg20_confirmation_renseigne_les_dates_reelles(client, entetes, creer_client, creer_commande):
    commande = creer_commande(creer_client()["id"])
    payer(client, entetes, commande["id"], 35_000)
    amener_a_terminee(client, entetes, commande["id"])

    corps = confirmer(client, entetes, commande["id"]).json()

    aujourd_hui = date.today().isoformat()
    assert corps["statut"] == "livree"
    assert corps["date_livraison_reelle"] == aujourd_hui
    assert corps["livraison"]["statut"] == "livree"
    assert corps["livraison"]["date_effective"] == aujourd_hui


# --- Statistiques -------------------------------------------------------------


def test_tableau_de_bord_valeurs_exactes(client, entetes, creer_client, creer_commande):
    fatou = creer_client()
    gardee = creer_commande(fatou["id"])  # 35 000
    annulee = creer_commande(fatou["id"])  # 35 000, annulée ensuite
    payer(client, entetes, gardee["id"], 10_000)
    client.post(f"/api/v1/commandes/{annulee['id']}/statut", json={"statut": "annulee"}, headers=entetes("accueil"))

    tableau = client.get("/api/v1/statistiques/tableau-de-bord", headers=entetes("admin")).json()

    assert tableau["chiffre_affaires_mois"] == 35_000  # la commande annulée est exclue
    assert tableau["encaisse_mois"] == 10_000
    assert tableau["nb_commandes_mois"] == 1
    assert tableau["reste_a_encaisser"] == 25_000
    assert tableau["commandes_par_statut"]["en_attente"] == 1
    assert tableau["commandes_par_statut"]["annulee"] == 1
    assert len(tableau["commandes_par_statut"]) == 8  # tous les statuts, même à 0
    assert tableau["commandes_par_statut"]["essayage"] == 0


def test_chiffre_affaires_periode_incoherente_refusee(client, entetes):
    reponse = client.get(
        "/api/v1/statistiques/chiffre-affaires",
        params={"date_debut": "2026-12-01", "date_fin": "2026-11-01"},
        headers=entetes("admin"),
    )

    assert reponse.status_code == 422


def test_ventes_par_prestation_avant_remise(client, entetes, creer_client, creer_commande, catalogue):
    creer_commande(
        creer_client()["id"],
        lignes=[{"type_vetement_id": catalogue["boubou"].id, "quantite": 2}],
        remise=5_000,
    )

    ventes = client.get("/api/v1/statistiques/types-vetement", headers=entetes("admin")).json()

    assert ventes == [
        {"type_vetement_id": catalogue["boubou"].id, "nom": "Boubou", "quantite_vendue": 2, "chiffre_affaires": 70_000}
    ]


def test_top_clients_classes_par_chiffre_d_affaires(client, entetes, creer_client, creer_commande, catalogue):
    petit = creer_client(nom="Ba")
    grand = creer_client(nom="Sow")
    creer_commande(petit["id"], lignes=[{"type_vetement_id": catalogue["pantalon"].id}])  # 12 000
    creer_commande(grand["id"])  # 35 000

    classement = client.get("/api/v1/statistiques/top-clients", params={"limite": 1}, headers=entetes("admin")).json()

    assert len(classement) == 1
    assert classement[0]["client_id"] == grand["id"]


# --- Annexe A : le scénario complet de démonstration -------------------------


def test_scenario_de_demonstration(client, entetes, catalogue):
    accueil, tailleur, admin = entetes("accueil"), entetes("tailleur"), entetes("admin")

    # 1. L'accueil crée Fatou Diop ; un second client avec le même numéro est refusé
    fatou = client.post("/api/v1/clients", json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67"}, headers=accueil)
    assert fatou.status_code == 201
    fatou_id = fatou.json()["id"]
    doublon = client.post("/api/v1/clients", json={"nom": "Diop", "prenom": "Fatou", "telephone": "771234567"}, headers=accueil)
    assert doublon.status_code == 409

    # 2. Le tailleur prend les mesures ; l'accueil qui tente la même action reçoit 403
    mesures = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_poitrine": 92, "tour_taille": 74}, headers=tailleur)
    assert mesures.status_code == 201
    assert client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_cou": 38}, headers=accueil).status_code == 403

    # 3. Commande : 2 boubous et 1 pantalon à prix négocié, avec une remise
    commande = client.post(
        "/api/v1/commandes",
        json={
            "client_id": fatou_id,
            "lignes": [
                {"type_vetement_id": catalogue["boubou"].id, "quantite": 2},
                {"type_vetement_id": catalogue["pantalon"].id, "prix_unitaire": 10_000},
            ],
            "remise": 5_000,
        },
        headers=accueil,
    ).json()
    assert commande["numero"].startswith(f"CMD-{date.today().year}-")
    assert commande["montant_total"] == 75_000
    assert commande["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    assert commande["mesure_id"] == mesures.json()["id"]
    url_commande = f"/api/v1/commandes/{commande['id']}"

    # 4. L'accueil tente de passer à « terminee » : refusé, avec les statuts possibles
    refus = client.post(f"{url_commande}/statut", json={"statut": "terminee"}, headers=accueil)
    assert refus.status_code == 409
    assert "Statuts possibles : annulee, en_coupe" in refus.json()["detail"]

    # 5. Le tailleur fait avancer la commande, avec un aller-retour essayage / retouches
    for statut in ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]:
        assert client.post(f"{url_commande}/statut", json={"statut": statut}, headers=tailleur).status_code == 200
    assert len(client.get(f"{url_commande}/historique", headers=accueil).json()) == 7

    # 6. Acompte Wave ; un paiement supérieur au solde est refusé
    assert client.post(f"{url_commande}/paiements", json={"montant": 30_000, "mode": "wave"}, headers=accueil).status_code == 201
    assert client.post(f"{url_commande}/paiements", json={"montant": 50_000, "mode": "especes"}, headers=accueil).status_code == 409

    # 7. Confirmation de livraison refusée : solde non payé
    assert client.post(f"{url_commande}/livraison/confirmer", headers=accueil).status_code == 409

    # 8. Encaissement du solde, puis confirmation : commande livrée, solde à 0
    assert client.post(f"{url_commande}/paiements", json={"montant": 45_000, "mode": "orange_money"}, headers=accueil).status_code == 201
    livree = client.post(f"{url_commande}/livraison/confirmer", headers=accueil).json()
    assert livree["statut"] == "livree"
    assert livree["solde"] == 0

    # 9. Le chiffre d'affaires du mois a augmenté du montant de la commande ; l'accueil reçoit 403
    tableau = client.get("/api/v1/statistiques/tableau-de-bord", headers=admin).json()
    assert tableau["chiffre_affaires_mois"] == 75_000
    assert client.get("/api/v1/statistiques/tableau-de-bord", headers=accueil).status_code == 403

    # 10. Impayés et commandes en retard : la commande, soldée et livrée, n'y figure pas
    impayes = client.get("/api/v1/statistiques/impayes", headers=admin).json()
    en_retard = client.get("/api/v1/commandes", params={"en_retard": True}, headers=admin).json()
    assert commande["id"] not in [c["id"] for c in impayes["items"]]
    assert commande["id"] not in [c["id"] for c in en_retard["items"]]