#!/bin/sh
# Script de démarrage du conteneur de l'API.
set -e

echo "1/3 - Application des migrations (alembic upgrade head)..."
alembic upgrade head

echo "2/3 - Initialisation des données (administrateur et catalogue)..."
python -m app.seed

echo "3/3 - Démarrage de l'API sur le port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000