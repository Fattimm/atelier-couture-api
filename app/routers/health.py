from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["Santé"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Vérifie que l'API répond et que la base de données est joignable."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de données ne répond pas",
        )
    return {"status": "ok"}