from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import ErreurMetier, traduire_erreur_validation

from app.core.config import settings
from app.core.exceptions import ErreurMetier
from app.routers import auth, health
from app.routers import (
    auth,
    catalogue,
    clients,
    commandes,
    health,
    livraisons,
    mesures,
    paiements,
    utilisateurs,
    statistiques,
)

API_PREFIX = "/api/v1"

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="API de gestion d'un atelier de couture : clients, mesures, commandes, paiements et livraisons.",
)


@app.exception_handler(ErreurMetier)
async def gerer_erreur_metier(request: Request, exc: ErreurMetier) -> JSONResponse:
    """Convertit toute erreur métier en réponse HTTP {"detail": "..."}."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def gerer_erreur_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Convertit les erreurs de validation en {"detail": "message en français"}."""
    messages = [traduire_erreur_validation(erreur) for erreur in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"detail": "Données invalides. " + " ; ".join(messages)},
    )


# Route de santé, hors préfixe /api/v1
app.include_router(health.router)

# Routeurs métier, avec le préfixe /api/v1
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(utilisateurs.router, prefix=API_PREFIX)
app.include_router(catalogue.router, prefix=API_PREFIX)
app.include_router(clients.router, prefix=API_PREFIX)
app.include_router(mesures.router, prefix=API_PREFIX)
app.include_router(commandes.router, prefix=API_PREFIX)
app.include_router(paiements.router, prefix=API_PREFIX)
app.include_router(livraisons.router, prefix=API_PREFIX)
app.include_router(statistiques.router, prefix=API_PREFIX)