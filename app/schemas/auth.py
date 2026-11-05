from pydantic import BaseModel


class Jeton(BaseModel):
    """Réponse de POST /auth/login, au format OAuth2."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int