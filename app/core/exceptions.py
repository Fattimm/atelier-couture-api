"""Exceptions métier levées par les services.

Les services ne connaissent pas le HTTP : ils lèvent ces exceptions, et un
gestionnaire unique (dans main.py) les convertit en réponses HTTP au format
{"detail": "..."}.
"""


# ---------------------------------------------------------------------------
# Traduction des erreurs de validation Pydantic (422) en français
# ---------------------------------------------------------------------------

TRADUCTIONS_VALIDATION = {
    "missing": "champ obligatoire manquant",
    "extra_forbidden": "champ non autorisé",
    "string_too_short": "doit contenir au moins {min_length} caractère(s)",
    "string_too_long": "doit contenir au plus {max_length} caractère(s)",
    "string_type": "doit être une chaîne de caractères",
    "too_short": "doit contenir au moins {min_length} élément(s)",
    "int_parsing": "doit être un nombre entier",
    "int_type": "doit être un nombre entier",
    "float_parsing": "doit être un nombre",
    "bool_parsing": "doit valoir true ou false",
    "bool_type": "doit valoir true ou false",
    "date_parsing": "doit être une date au format AAAA-MM-JJ",
    "date_from_datetime_parsing": "doit être une date au format AAAA-MM-JJ",
    "greater_than": "doit être strictement supérieur à {gt}",
    "greater_than_equal": "doit être supérieur ou égal à {ge}",
    "less_than": "doit être strictement inférieur à {lt}",
    "less_than_equal": "doit être inférieur ou égal à {le}",
    "enum": "valeur non autorisée (valeurs possibles : {expected})",
    "json_invalid": "le corps de la requête n'est pas un JSON valide",
}


class ErreurMetier(Exception):
    """Classe mère de toutes les erreurs métier."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RessourceIntrouvable(ErreurMetier):
    """La ressource demandée n'existe pas (404)."""

    status_code = 404


class Conflit(ErreurMetier):
    """L'action entre en conflit avec l'état actuel : doublon, transition interdite... (409)."""

    status_code = 409


class DonneesInvalides(ErreurMetier):
    """Une valeur est interdite par une règle de gestion (422)."""

    status_code = 422


class ActionInterdite(ErreurMetier):
    """Le rôle de l'utilisateur ne permet pas cette action métier (403)."""

    status_code = 403


def traduire_erreur_validation(erreur: dict) -> str:
    """Transforme une erreur Pydantic en phrase française : "champ : explication"."""
    # loc = ("body", "mot_de_passe") : on retire la première partie (body, query, path)
    champ = ".".join(str(partie) for partie in erreur["loc"][1:]) or "requête"
    type_erreur = erreur["type"]
    contexte = erreur.get("ctx", {})

    if type_erreur == "value_error":
        # Erreur levée par un validateur (le nôtre ou celui des e-mails)
        explication = erreur["msg"].removeprefix("Value error, ")
        if "email" in explication.lower():
            explication = "adresse e-mail invalide"
    elif type_erreur in TRADUCTIONS_VALIDATION:
        try:
            explication = TRADUCTIONS_VALIDATION[type_erreur].format(**contexte)
        except KeyError:
            explication = erreur["msg"]
        explication = explication.replace("' or '", "', '")
    else:
        explication = erreur["msg"]  # cas rare non traduit : on garde le message d'origine

    return f"{champ} : {explication}"