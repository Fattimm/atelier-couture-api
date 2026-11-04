"""Script d'initialisation : python -m app.seed

Crée le premier administrateur à partir des variables d'environnement.
Le script est idempotent : on peut le relancer sans créer de doublon.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hacher_mot_de_passe
from app.models import RoleUtilisateur, Utilisateur


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


def main() -> None:
    with SessionLocal() as db:
        creer_admin(db)
        db.commit()
    print("Initialisation terminée.")


if __name__ == "__main__":
    main()