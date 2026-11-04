import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RoleUtilisateur(enum.StrEnum):
    """Les trois rôles possibles dans l'atelier."""

    admin = "admin"
    tailleur = "tailleur"
    accueil = "accueil"


class Utilisateur(Base):
    """Un membre du personnel de l'atelier, qui se connecte à l'API."""

    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    nom_complet: Mapped[str] = mapped_column(String(150))
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[RoleUtilisateur] = mapped_column(
        Enum(RoleUtilisateur, name="role_utilisateur")
    )
    actif: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )