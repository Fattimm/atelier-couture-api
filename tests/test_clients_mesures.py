"""Tests des clients et des mesures (RG1 à RG4)."""

from datetime import date

import pytest

from app.schemas.client import normaliser_telephone


# --- RG1 : normalisation du téléphone (tests unitaires) --------------------------


@pytest.mark.parametrize(
    "saisie",
    ["77 123 45 67", "771234567", "77.123.45.67", "77-123-45-67", "(77) 123 45 67"],
)
def test_rg1_normalisation_du_telephone(saisie):
    assert normaliser_telephone(saisie) == "771234567"


@pytest.mark.parametrize("saisie", ["12345", "77 ABC 45 67", "+" + "1" * 21, ""])
def test_rg1_telephone_invalide(saisie):
    with pytest.raises(ValueError):
        normaliser_telephone(saisie)


# --- RG1 : unicité du téléphone (tests d'intégration) ----------------------------


def test_rg1_meme_numero_autrement_ecrit_refuse(client, entetes, creer_client):
    creer_client(telephone="77 123 45 67")

    reponse = client.post(
        "/api/v1/clients",
        json={"nom": "Diop", "prenom": "Fatou", "telephone": "771234567"},
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 409


def test_rg1_numero_invalide_refuse(client, entetes):
    reponse = client.post(
        "/api/v1/clients",
        json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 12"},
        headers=entetes("accueil"),
    )

    assert reponse.status_code == 422


def test_garder_son_propre_numero_n_est_pas_un_doublon(client, entetes, creer_client):
    fatou = creer_client(telephone="77 123 45 67")

    reponse = client.patch(f"/api/v1/clients/{fatou['id']}", json={"telephone": "77.123.45.67"}, headers=entetes("accueil"))

    assert reponse.status_code == 200


def test_prendre_le_numero_d_un_autre_client_refuse(client, entetes, creer_client):
    creer_client(telephone="76 555 12 12")
    fatou = creer_client(telephone="77 123 45 67")

    reponse = client.patch(f"/api/v1/clients/{fatou['id']}", json={"telephone": "765551212"}, headers=entetes("accueil"))

    assert reponse.status_code == 409


def test_nom_ne_peut_pas_etre_vide(client, entetes, creer_client):
    fatou = creer_client()

    reponse = client.patch(f"/api/v1/clients/{fatou['id']}", json={"nom": None}, headers=entetes("accueil"))

    assert reponse.status_code == 422


# --- Recherche et pagination (route 8) --------------------------------------------


def test_recherche_par_nom_et_par_telephone(client, entetes, creer_client):
    creer_client(nom="Diop", telephone="77 123 45 67")
    creer_client(nom="Fall", telephone="70 888 99 00")

    par_nom = client.get("/api/v1/clients", params={"q": "dio"}, headers=entetes("accueil")).json()
    par_tel = client.get("/api/v1/clients", params={"q": "70 888"}, headers=entetes("accueil")).json()

    assert [c["nom"] for c in par_nom["items"]] == ["Diop"]
    assert [c["nom"] for c in par_tel["items"]] == ["Fall"]


def test_pagination_renvoie_le_total(client, entetes, creer_client):
    for nom in ["Ba", "Cisse", "Diop"]:
        creer_client(nom=nom)

    page = client.get("/api/v1/clients", params={"limit": 2, "offset": 0}, headers=entetes("accueil")).json()

    assert len(page["items"]) == 2
    assert page["total"] == 3
    assert [c["nom"] for c in page["items"]] == ["Ba", "Cisse"]  # tri par nom


# --- RG2 : contenu d'une prise de mesures -----------------------------------------


def test_rg2_prise_sans_aucune_mesure_refusee(client, entetes, creer_client):
    fatou = creer_client()

    reponse = client.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"notes": "vide"}, headers=entetes("tailleur"))

    assert reponse.status_code == 422


@pytest.mark.parametrize("valeur", [0, -5, 301])
def test_rg2_mesure_hors_limites_refusee(client, entetes, creer_client, valeur):
    fatou = creer_client()

    reponse = client.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_cou": valeur}, headers=entetes("tailleur"))

    assert reponse.status_code == 422


def test_prise_de_mesures_par_le_tailleur(creer_client, prendre_mesures, utilisateurs):
    fatou = creer_client()

    prise = prendre_mesures(fatou["id"], tour_cou=38.5)

    assert prise["prise_par_id"] == utilisateurs["tailleur"].id
    assert prise["date_prise"] == date.today().isoformat()
    assert prise["tour_cou"] == 38.5


def test_rg2_correction_qui_supprimerait_toutes_les_mesures_refusee(client, entetes, creer_client, prendre_mesures):
    prise = prendre_mesures(creer_client()["id"], tour_cou=38)

    reponse = client.patch(f"/api/v1/mesures/{prise['id']}", json={"tour_cou": None}, headers=entetes("tailleur"))

    assert reponse.status_code == 422


# --- RG3 : historique et dernières mesures ----------------------------------------


def test_rg3_dernieres_mesures_et_historique(client, entetes, creer_client, prendre_mesures):
    fatou = creer_client()
    premiere = prendre_mesures(fatou["id"], tour_taille=74)
    seconde = prendre_mesures(fatou["id"], tour_taille=76)  # même jour : départagée par l'id

    derniere = client.get(f"/api/v1/clients/{fatou['id']}/mesures/derniere", headers=entetes("accueil")).json()
    historique = client.get(f"/api/v1/clients/{fatou['id']}/mesures", headers=entetes("accueil")).json()

    assert derniere["id"] == seconde["id"]
    assert [m["id"] for m in historique] == [seconde["id"], premiere["id"]]


def test_rg3_client_sans_mesures_renvoie_404(client, entetes, creer_client):
    fatou = creer_client()

    reponse = client.get(f"/api/v1/clients/{fatou['id']}/mesures/derniere", headers=entetes("accueil"))

    assert reponse.status_code == 404


# --- RG4 : suppressions protégées --------------------------------------------------


def test_rg4_client_avec_commande_non_supprimable(client, entetes, creer_client, creer_commande):
    fatou = creer_client()
    creer_commande(fatou["id"])

    reponse = client.delete(f"/api/v1/clients/{fatou['id']}", headers=entetes("admin"))

    assert reponse.status_code == 409


def test_rg4_mesures_utilisees_par_une_commande_non_supprimables(client, entetes, creer_client, prendre_mesures, creer_commande):
    fatou = creer_client()
    prise = prendre_mesures(fatou["id"])
    creer_commande(fatou["id"])  # rattache automatiquement les dernières mesures (RG9)

    reponse = client.delete(f"/api/v1/mesures/{prise['id']}", headers=entetes("tailleur"))

    assert reponse.status_code == 409


def test_suppression_d_un_client_supprime_ses_mesures(client, entetes, creer_client, prendre_mesures):
    fatou = creer_client()
    prise = prendre_mesures(fatou["id"])

    suppression = client.delete(f"/api/v1/clients/{fatou['id']}", headers=entetes("admin"))
    mesure_apres = client.get(f"/api/v1/mesures/{prise['id']}", headers=entetes("admin"))

    assert suppression.status_code == 204
    assert mesure_apres.status_code == 404