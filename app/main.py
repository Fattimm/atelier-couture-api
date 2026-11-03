from fastapi import FastAPI

from app.core.config import settings
from app.routers import health

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="API de gestion d'un atelier de couture : clients, mesures, commandes, paiements et livraisons.",
)

# Route de santé, hors préfixe /api/v1
app.include_router(health.router)

# Les routeurs métier seront ajoutés ici avec le préfixe /api/v1
API_PREFIX = "/api/v1"