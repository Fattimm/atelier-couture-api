import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GenreClient(enum.StrEnum):
    """Catégorie de vêtements du client."""

    homme = "homme"
    femme = "femme"
    enfant = "enfant"


class Client(Base):
    """Un client de l'atelier, identifié par son numéro de téléphone (RG1)."""

    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_nom_prenom", "nom", "prenom"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    telephone: Mapped[str] = mapped_column(String(21), unique=True)  # forme normalisée (RG1)
    email: Mapped[str | None] = mapped_column(String(255))
    adresse: Mapped[str | None] = mapped_column(Text)
    genre: Mapped[GenreClient | None] = mapped_column(Enum(GenreClient, name="genre_client"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )