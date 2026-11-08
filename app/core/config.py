from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application, lue depuis les variables d'environnement et le fichier .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Atelier Couture API"

    # Base de données
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Premier administrateur (utilisé par le seed)
    admin_email: str | None = None
    admin_password: str | None = None
    admin_nom_complet: str = "Administrateur"

    # Base de données des tests (facultative : seuls les tests l'utilisent)
    test_database_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()