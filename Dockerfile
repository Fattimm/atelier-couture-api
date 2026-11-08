# Image de base : Python 3.12, version allégée
FROM python:3.12-slim

# Réglages Python et pip pour un conteneur
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /code

# 1. Les dépendances d'abord : cette couche reste en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. Puis le code de l'application
COPY . .

# 3. Un utilisateur sans privilèges pour exécuter l'API (jamais root)
RUN chmod +x docker/demarrage.sh \
    && useradd --create-home atelier
USER atelier

EXPOSE 8000

CMD ["./docker/demarrage.sh"]