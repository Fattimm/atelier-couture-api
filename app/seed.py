"""Script d'initialisation : python -m app.seed

Crée le premier administrateur (à partir des variables d'environnement)
et les prestations du catalogue de départ (annexe B de l'énoncé).
Le script est idempotent : on peut le relancer sans créer de doublon,
et il ne modifie jamais une donnée déjà présente.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import Conflit
from app.core.security import hacher_mot_de_passe
from app.models import RoleUtilisateur, Utilisateur
from app.schemas.type_vetement import TypeVetementCreate
from app.services.catalogue import creer_type_vetement

# Annexe B : prix en FCFA, délais en jours
CATALOGUE_INITIAL = [
    {"nom": "Boubou", "description": "Boubou homme en bazin ou brodé", "prix_base": 35_000, "delai_jours": 10},
    {"nom": "Costume 2 pièces", "description": "Veste et pantalon", "prix_base": 85_000, "delai_jours": 14},
    {"nom": "Robe", "description": "Robe sur mesure", "prix_base": 30_000, "delai_jours": 7},
    {"nom": "Ensemble wax", "description": "Tenue deux pièces en wax", "prix_base": 25_000, "delai_jours": 7},
    {"nom": "Chemise", "description": "Chemise sur mesure", "prix_base": 15_000, "delai_jours": 5},
    {"nom": "Pantalon", "description": "Pantalon sur mesure", "prix_base": 12_000, "delai_jours": 4},
    {"nom": "Retouche", "description": "Ourlet, rétrécissement, remplacement de fermeture", "prix_base": 3_000, "delai_jours": 2},
]


def creer_admin(db: Session) -> None:
    """Crée le premier administrateur s'il n'existe pas encore."""
    if not settings.admin_email or not settings.admin_password:
        raise SystemExit("Erreur : ADMIN_EMAIL et ADMIN_PASSWORD doivent être définis dans le .env")

    if len(settings.admin_password) < 8:
        raise SystemExit("Erreur : ADMIN_PASSWORD doit contenir au moins 8 caractères (RG21)")

    email = settings.admin_email.strip().lower()

    existant = db.scalar(select(Utilisateur).where(Utilisateur.email == email))
    if existant is not None:
        print(f"Administrateur déjà présent ({email}) : rien à faire.")
        return

    admin = Utilisateur(
        email=email,
        nom_complet=settings.admin_nom_complet,
        mot_de_passe_hash=hacher_mot_de_passe(settings.admin_password),
        role=RoleUtilisateur.admin,
    )
    db.add(admin)
    print(f"Administrateur créé : {email}")


def creer_catalogue(db: Session) -> None:
    """Crée les prestations de l'annexe B qui n'existent pas encore (sans rien écraser)."""
    crees, deja_presents = 0, 0
    for prestation in CATALOGUE_INITIAL:
        try:
            creer_type_vetement(db, TypeVetementCreate(**prestation))
            crees += 1
        except Conflit:
            deja_presents += 1
    print(f"Catalogue : {crees} prestation(s) créée(s), {deja_presents} déjà présente(s).")


def main() -> None:
    with SessionLocal() as db:
        creer_admin(db)
        creer_catalogue(db)
        db.commit()
    print("Initialisation terminée.")


if __name__ == "__main__":
    main()