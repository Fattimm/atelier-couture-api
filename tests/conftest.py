"""Fixtures communes à tous les tests.

Chaque test s'exécute dans une transaction annulée à la fin : la base de test
redevient vide entre deux tests (isolation).
"""

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hacher_mot_de_passe
from app.main import app
from app.models import RoleUtilisateur, TypeVetement, Utilisateur

if not settings.test_database_url:
    raise RuntimeError("Définissez TEST_DATABASE_URL dans le .env pour lancer les tests")

engine_test = create_engine(settings.test_database_url)

MOT_DE_PASSE = "MotDePasse123"
_HASH_MOT_DE_PASSE = hacher_mot_de_passe(MOT_DE_PASSE)  # calculé une seule fois (Argon2 est lent)


@pytest.fixture(scope="session", autouse=True)
def schema_de_test() -> Generator[None, None, None]:
    """Crée toutes les tables une fois au début des tests, et les supprime à la fin."""
    Base.metadata.drop_all(engine_test)  # au cas où une exécution précédente aurait été interrompue
    Base.metadata.create_all(engine_test)
    yield
    Base.metadata.drop_all(engine_test)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Une session dans une transaction annulée à la fin du test.

    Les commit() des routes ne valident qu'un point de sauvegarde, à l'intérieur
    de cette transaction : le rollback final annule tout.
    """
    connexion = engine_test.connect()
    transaction = connexion.begin()
    session = Session(
        bind=connexion,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    yield session
    session.close()
    transaction.rollback()
    connexion.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """Un client HTTP de test, dont les routes utilisent la session du test."""

    def get_db_de_test() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = get_db_de_test
    with TestClient(app) as client_de_test:
        yield client_de_test
    app.dependency_overrides.clear()


@pytest.fixture
def utilisateurs(db: Session) -> dict[str, Utilisateur]:
    """Un compte par rôle : admin, accueil, tailleur (mot de passe : MOT_DE_PASSE)."""
    comptes = {
        role.value: Utilisateur(
            email=f"{role.value}@test.sn",
            nom_complet=f"Compte {role.value}",
            mot_de_passe_hash=_HASH_MOT_DE_PASSE,
            role=role,
        )
        for role in RoleUtilisateur
    }
    db.add_all(comptes.values())
    db.flush()
    return comptes


@pytest.fixture
def entetes(client: TestClient, utilisateurs: dict[str, Utilisateur]) -> Callable[[str], dict[str, str]]:
    """Fabrique les en-têtes d'authentification d'un rôle : entetes("accueil")."""
    cache: dict[str, dict[str, str]] = {}

    def _entetes(role: str) -> dict[str, str]:
        if role not in cache:
            reponse = client.post(
                "/api/v1/auth/login",
                data={"username": utilisateurs[role].email, "password": MOT_DE_PASSE},
            )
            assert reponse.status_code == 200, reponse.text
            cache[role] = {"Authorization": f"Bearer {reponse.json()['access_token']}"}
        return cache[role]

    return _entetes


@pytest.fixture
def catalogue(db: Session) -> dict[str, TypeVetement]:
    """Quelques prestations, dont une retirée du catalogue."""
    prestations = {
        "boubou": TypeVetement(nom="Boubou", prix_base=35_000, delai_jours=10),
        "pantalon": TypeVetement(nom="Pantalon", prix_base=12_000, delai_jours=4),
        "ancienne": TypeVetement(nom="Ancienne prestation", prix_base=5_000, delai_jours=2, actif=False),
    }
    db.add_all(prestations.values())
    db.flush()
    return prestations