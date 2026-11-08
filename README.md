# API de gestion d'un atelier de couture

Projet final du module **Développement d'API avec FastAPI et PostgreSQL**.

API REST pour l'atelier de couture de Mamadou, à Dakar : clients et historique de leurs mesures,
commandes et suivi de la production, acomptes et soldes (espèces, Wave, Orange Money...),
livraisons, et statistiques pour le patron.

## Technologies

| Élément | Choix |
|---|---|
| Langage | Python 3.12 |
| Framework | FastAPI (documentation interactive sur `/docs`) |
| Base de données | PostgreSQL 17 |
| Accès aux données | SQLAlchemy 2 (`Mapped`, `mapped_column`, `select`) |
| Migrations | Alembic |
| Validation | Pydantic 2 (schémas distincts pour création, modification, lecture) |
| Sécurité | Argon2 (pwdlib), jetons JWT (PyJWT) |
| Tests | pytest et `TestClient` |
| Conteneurs | Docker et Docker Compose |

## Démarrage rapide avec Docker (recommandé)
atelier-couture-api
Prérequis : **Docker** et **Docker Compose** (`docker compose version`).

```bash
git clone https://github.com/Fattimm/atelier-couture-api.gitatelier-couture-api
cd atelier-couture-api
cp .env.example .env
```

Dans `.env`, remplacez au minimum `JWT_SECRET_KEY` par une clé longue et aléatoire :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Puis :

```bash
docker compose up --build
```

Au démarrage, le conteneur de l'API applique automatiquement les migrations (`alembic upgrade head`),
crée le premier administrateur et le catalogue de départ (`python -m app.seed`), puis lance le serveur.

- Documentation interactive : <http://localhost:8000/docs>
- Santé de l'API : <http://localhost:8000/health>

**Ports déjà occupés ?** Si un PostgreSQL local occupe le port 5432 ou un autre service le port 8000,
changez `POSTGRES_PORT` (par exemple `5433`) ou `API_PORT` dans `.env`. Si vous changez `POSTGRES_PORT`,
mettez le même port dans `DATABASE_URL` et `TEST_DATABASE_URL`.

## Comptes de test

| Rôle | Identifiant | Mot de passe |
|---|---|---|
| Administrateur | `ADMIN_EMAIL` du `.env` (`admin@atelier.sn` par défaut) | `change_me` du `.env` |

L'administrateur est créé par le script d'initialisation. Les comptes **accueil** et **tailleur** se créent
ensuite avec la route `POST /api/v1/utilisateurs` (connecté en administrateur), par exemple :

```json
{ "email": "accueil@atelier.sn", "nom_complet": "Awa Ndiaye", "mot_de_passe": "Accueil2026", "role": "accueil" }
```
```json
{ "email": "tailleur@atelier.sn", "nom_complet": "Yacine DIA", "mot_de_passe": "Tailleur2026", "role": "tailleur" }
```

**Se connecter dans Swagger** : bouton **Authorize**, puis `username` = e-mail et `password` = mot de passe.

## Lancer les tests

Les tests utilisent une base séparée, `atelier_test`, créée automatiquement au premier démarrage
de PostgreSQL (`docker/init-db/01-base-de-test.sql`). Chaque test s'exécute dans une transaction
annulée à la fin : les données de développement ne sont jamais touchées.

```bash
docker compose up -d db              # la base doit être démarrée
python3.12 -m venv .venv
source .venv/bin/activate            # Windows : .venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Résultat attendu : **138 tests réussis**. Quelques options utiles :

```bash
pytest -v                # nom et résultat de chaque test
pytest -k rg19           # seulement les tests d'une règle de gestion
pytest -k scenario       # le scénario de démonstration de l'annexe A
```

## Développement en local (sans conteneur pour l'API)

```bash
docker compose up -d db
source .venv/bin/activate
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

## Architecture

```
app/
├── main.py          # application FastAPI, gestionnaires d'erreurs, routeurs
├── seed.py          # python -m app.seed : administrateur et catalogue de départ
├── core/            # configuration (.env), base de données, sécurité, dépendances, exceptions
├── models/          # modèles SQLAlchemy (une table par classe)
├── schemas/         # schémas Pydantic (création, modification, lecture)
├── services/        # règles de gestion (RG1 à RG24), indépendantes du HTTP
└── routers/         # un fichier par domaine : droits → service → validation de la transaction
alembic/versions/    # migrations du schéma
tests/               # tests pytest (une base de test isolée)
docker/              # script de démarrage de l'API et initialisation de PostgreSQL
```

- Les **routeurs** vérifient les droits, appellent un service, puis valident la transaction (`commit`).
- Les **services** contiennent toute la logique métier et lèvent des **exceptions métier**
  (`Conflit`, `DonneesInvalides`...), converties en réponses `{"detail": "..."}` par un gestionnaire unique.
- Les **schémas de lecture** ne contiennent jamais le hash du mot de passe.
- Les erreurs de validation (422) sont traduites en français, sans renvoyer les valeurs reçues.

## Routes réalisées

Toutes les routes sont préfixées par `/api/v1`, sauf `/health`. Les 44 routes de l'énoncé sont réalisées.

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 1 | POST | `/auth/login` | Public |
| 2 | GET | `/auth/me` | Connecté |
| 3 | POST | `/utilisateurs` | Admin |
| 4 | GET | `/utilisateurs` | Admin |
| 5 | GET | `/utilisateurs/{id}` | Admin |
| 6 | PATCH | `/utilisateurs/{id}` | Admin |
| 7 | POST | `/clients` | Tous |
| 8 | GET | `/clients` | Tous |
| 9 | GET | `/clients/{id}` | Tous |
| 10 | PATCH | `/clients/{id}` | Tous |
| 11 | DELETE | `/clients/{id}` | Admin |
| 12 | GET | `/clients/{id}/commandes` | Tous |
| 13 | GET | `/clients/{id}/resume` | Tous |
| 14 | POST | `/catalogue` | Admin |
| 15 | GET | `/catalogue` | Tous |
| 16 | GET | `/catalogue/{id}` | Tous |
| 17 | PATCH | `/catalogue/{id}` | Admin |
| 18 | POST | `/clients/{id}/mesures` | Tailleur |
| 19 | GET | `/clients/{id}/mesures` | Tous |
| 20 | GET | `/clients/{id}/mesures/derniere` | Tous |
| 21 | GET | `/mesures/{id}` | Tous |
| 22 | PATCH | `/mesures/{id}` | Tailleur |
| 23 | DELETE | `/mesures/{id}` | Tailleur |
| 24 | POST | `/commandes` | Accueil |
| 25 | GET | `/commandes` | Tous |
| 26 | GET | `/commandes/{id}` | Tous |
| 27 | PATCH | `/commandes/{id}` | Accueil |
| 28 | POST | `/commandes/{id}/statut` | Tous (RG13, RG14) |
| 29 | GET | `/commandes/{id}/historique` | Tous |
| 30 | POST | `/commandes/{id}/lignes` | Accueil |
| 31 | DELETE | `/commandes/{id}/lignes/{ligne_id}` | Accueil |
| 32 | POST | `/commandes/{id}/paiements` | Accueil |
| 33 | GET | `/commandes/{id}/paiements` | Tous |
| 34 | DELETE | `/paiements/{id}` | Admin |
| 35 | PUT | `/commandes/{id}/livraison` | Accueil |
| 36 | GET | `/commandes/{id}/livraison` | Tous |
| 37 | POST | `/commandes/{id}/livraison/confirmer` | Accueil |
| 38 | GET | `/livraisons` | Tous |
| 39 | GET | `/statistiques/tableau-de-bord` | Admin |
| 40 | GET | `/statistiques/chiffre-affaires` | Admin |
| 41 | GET | `/statistiques/types-vetement` | Admin |
| 42 | GET | `/statistiques/top-clients` | Admin |
| 43 | GET | `/statistiques/impayes` | Admin |
| 44 | GET | `/health` | Public |

L'administrateur est autorisé sur toutes les routes.

## Choix d'interprétation

Points où l'énoncé laisse une marge, et décision prise :

- **Connexion** : la section 4 parle d'un « numéro », mais le modèle de données et la route de connexion
  utilisent l'**e-mail** (`username` = e-mail). C'est l'e-mail qui est retenu.
- **Droits sur les clients** : la section 4 réserve leur gestion à l'accueil, le tableau des routes
  indique « Tous » ; le tableau des routes, plus précis, est appliqué.
- **Chemins des statistiques** : `tableau-de-bord`, `chiffre-affaires` et `types-vetement`, avec tirets.
- **Téléphone (RG1)** : la normalisation retire espaces, points, tirets et parenthèses, comme demandé ;
  l'indicatif (`+221`) n'est pas retiré, donc `+221771234567` et `771234567` restent distincts.
- **Genre du client** : facultatif, pour permettre un enregistrement rapide à l'accueil.
- **Catalogue** : l'unicité du nom ne tient pas compte des majuscules (« Boubou » = « boubou »).
- **Dates** : une prise de mesures et un paiement ne peuvent pas être datés dans le futur ; la date de remise
  d'une livraison est comprise entre la date de commande et aujourd'hui.
- **Date de livraison prévue (RG8)** : calculée à la création ; elle n'est pas recalculée quand on ajoute
  une ligne, l'accueil l'ajuste avec `PATCH /commandes/{id}` (ou en planifiant la livraison, RG18).
- **Numéros de commande (RG5)** : uniques, mais pas forcément continus (une création refusée consomme
  un numéro de la séquence PostgreSQL).
- **Annulation d'un paiement** : suppression physique, comme demandé (route 34, 204).
- **Planification d'une livraison** (`PUT`) : renvoie 200, qu'elle crée ou remplace la livraison.
- **Résumé client** : `derniere_commande` est la date de la dernière commande non annulée.
- **Tableau de bord** : `nb_commandes_mois` exclut les commandes annulées ; `encaisse_mois` compte tous les
  paiements reçus dans le mois ; `commandes_pretes_a_livrer` (statut `terminee`) et `livraisons_du_jour`
  (livraisons planifiées pour aujourd'hui) sont des nombres.
- **Chiffre d'affaires par période** : la réponse rappelle la période utilisée et les totaux, en plus de la
  liste des périodes avec activité.
- **Dépendances** : aucun `requirements.txt` n'ayant été fourni, les versions exactes ont été figées avec
  `pip freeze` sous Python 3.12.

## Scénario de démonstration (annexe A)

Le parcours complet de l'annexe A est automatisé dans `tests/test_paiements_livraisons_statistiques.py`
(`test_scenario_de_demonstration`) :

```bash
pytest -k scenario -v
```