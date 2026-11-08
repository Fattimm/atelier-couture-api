"""Tests de l'authentification et de la sécurité (RG21, RG22, RG23)."""

from app.core.security import hacher_mot_de_passe, verifier_mot_de_passe
from tests.conftest import MOT_DE_PASSE

URL_LOGIN = "/api/v1/auth/login"


def test_route_sante(client):
    reponse = client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


def test_connexion_reussie_renvoie_un_jeton(client, utilisateurs):
    reponse = client.post(URL_LOGIN, data={"username": "accueil@test.sn", "password": MOT_DE_PASSE})

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["token_type"] == "bearer"
    assert corps["expires_in"] > 0
    assert corps["access_token"]


def test_rg23_meme_message_pour_email_inconnu_et_mauvais_mot_de_passe(client, utilisateurs):
    mauvais_mdp = client.post(URL_LOGIN, data={"username": "accueil@test.sn", "password": "faux-mdp"})
    email_inconnu = client.post(URL_LOGIN, data={"username": "inconnu@test.sn", "password": "faux-mdp"})

    assert mauvais_mdp.status_code == email_inconnu.status_code == 401
    assert mauvais_mdp.json() == email_inconnu.json()


def test_route_protegee_sans_jeton_renvoie_401(client):
    reponse = client.get("/api/v1/auth/me")

    assert reponse.status_code == 401


def test_me_ne_renvoie_aucune_donnee_sensible(client, entetes):
    reponse = client.get("/api/v1/auth/me", headers=entetes("accueil"))

    assert reponse.status_code == 200
    assert reponse.json()["email"] == "accueil@test.sn"
    assert "mot_de_passe_hash" not in reponse.json()


def test_rg22_compte_desactive_refuse_meme_avec_jeton_valide(client, db, entetes, utilisateurs):
    en_tetes_accueil = entetes("accueil")  # jeton obtenu pendant que le compte est actif
    utilisateurs["accueil"].actif = False
    db.flush()

    reponse = client.get("/api/v1/auth/me", headers=en_tetes_accueil)

    assert reponse.status_code == 401


def test_rg21_mot_de_passe_hache_avec_argon2():
    hash_ = hacher_mot_de_passe("Secret2026")

    assert hash_.startswith("$argon2id$")
    assert "Secret2026" not in hash_
    assert verifier_mot_de_passe("Secret2026", hash_)
    assert not verifier_mot_de_passe("secret2026", hash_)