"""Tests des droits par rôle (section 4) et de la gestion des comptes (RG24)."""

import pytest

from app.models import RoleUtilisateur

ROLES = [role.value for role in RoleUtilisateur]

# (méthode, chemin, rôles autorisés) — l'administrateur est autorisé à tout faire
DROITS = [
    ("GET", "/api/v1/utilisateurs", {"admin"}),
    ("POST", "/api/v1/catalogue", {"admin"}),
    ("GET", "/api/v1/catalogue", {"admin", "accueil", "tailleur"}),
    ("GET", "/api/v1/clients", {"admin", "accueil", "tailleur"}),
    ("DELETE", "/api/v1/clients/1", {"admin"}),
    ("POST", "/api/v1/clients/1/mesures", {"admin", "tailleur"}),
    ("PATCH", "/api/v1/mesures/1", {"admin", "tailleur"}),
    ("POST", "/api/v1/commandes", {"admin", "accueil"}),
    ("PATCH", "/api/v1/commandes/1", {"admin", "accueil"}),
    ("POST", "/api/v1/commandes/1/paiements", {"admin", "accueil"}),
    ("DELETE", "/api/v1/paiements/1", {"admin"}),
    ("PUT", "/api/v1/commandes/1/livraison", {"admin", "accueil"}),
    ("POST", "/api/v1/commandes/1/livraison/confirmer", {"admin", "accueil"}),
    ("GET", "/api/v1/statistiques/tableau-de-bord", {"admin"}),
    ("GET", "/api/v1/statistiques/impayes", {"admin"}),
]


# --- Droits par rôle ------------------------------------------------------------


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("methode, chemin, roles_autorises", DROITS)
def test_droits_par_role(client, entetes, methode, chemin, roles_autorises, role):
    reponse = client.request(methode, chemin, headers=entetes(role), json={} if methode != "GET" else None)

    if role in roles_autorises:
        assert reponse.status_code not in (401, 403), f"{role} devrait pouvoir appeler {methode} {chemin}"
    else:
        assert reponse.status_code == 403, f"{role} ne devrait pas pouvoir appeler {methode} {chemin}"


@pytest.mark.parametrize("methode, chemin, _roles", DROITS)
def test_toutes_les_routes_protegees_exigent_un_jeton(client, methode, chemin, _roles):
    reponse = client.request(methode, chemin, json={} if methode != "GET" else None)

    assert reponse.status_code == 401


# --- Gestion des comptes (routes 3 à 6) ----------------------------------------


def test_creation_de_compte_puis_doublon_refuse(client, entetes):
    nouveau = {"email": "Nouveau@Test.sn", "nom_complet": "Nouvel employé", "mot_de_passe": "Bienvenue26", "role": "tailleur"}

    premier = client.post("/api/v1/utilisateurs", json=nouveau, headers=entetes("admin"))
    doublon = client.post("/api/v1/utilisateurs", json=nouveau, headers=entetes("admin"))

    assert premier.status_code == 201
    assert premier.json()["email"] == "nouveau@test.sn"  # e-mail normalisé
    assert "mot_de_passe" not in premier.json() and "mot_de_passe_hash" not in premier.json()
    assert doublon.status_code == 409


def test_rg21_mot_de_passe_trop_court_refuse(client, entetes):
    compte = {"email": "court@test.sn", "nom_complet": "Mot de passe court", "mot_de_passe": "1234567", "role": "accueil"}

    reponse = client.post("/api/v1/utilisateurs", json=compte, headers=entetes("admin"))

    assert reponse.status_code == 422


def test_rg24_admin_ne_peut_pas_se_desactiver(client, entetes, utilisateurs):
    admin_id = utilisateurs["admin"].id

    reponse = client.patch(f"/api/v1/utilisateurs/{admin_id}", json={"actif": False}, headers=entetes("admin"))

    assert reponse.status_code == 409


def test_rg24_admin_ne_peut_pas_retirer_son_propre_role(client, entetes, utilisateurs):
    admin_id = utilisateurs["admin"].id

    reponse = client.patch(f"/api/v1/utilisateurs/{admin_id}", json={"role": "accueil"}, headers=entetes("admin"))

    assert reponse.status_code == 409


def test_admin_peut_desactiver_un_autre_compte(client, entetes, utilisateurs):
    tailleur_id = utilisateurs["tailleur"].id

    reponse = client.patch(f"/api/v1/utilisateurs/{tailleur_id}", json={"actif": False}, headers=entetes("admin"))

    assert reponse.status_code == 200
    assert reponse.json()["actif"] is False