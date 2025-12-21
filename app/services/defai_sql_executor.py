"""defai_sql_executor.py
Module utilitaire pour valider et exécuter en toute sécurité des requêtes SQL en lecture seule.

Règles appliquées :
- Seules les requêtes commençant par SELECT sont autorisées.
- Pas de SELECT * (les colonnes doivent être explicites).
- Les mots-clés potentiellement dangereux sont interdits (INSERT, UPDATE, DELETE, DROP, ALTER, UNION, etc.).
- Aucune exécution de plusieurs instructions « ; ».
- Tables accessibles limitées par rôle via une whitelist.
- Résultats limités à 100 lignes pour éviter les charges lourdes.
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect
from app.extensions import db

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Construction dynamique de la liste des tables disponibles dans la base
#   → lazy-init pour éviter l'erreur "Working outside of application context"
# -----------------------------------------------------------------------------

_ALL_TABLES: List[str] | None = None


def get_all_tables() -> List[str]:
    """Retourne la liste des tables en cache ou la récupère via SQLAlchemy."""
    global _ALL_TABLES
    if _ALL_TABLES is not None:
        return _ALL_TABLES

    try:
        _ALL_TABLES = inspect(db.engine).get_table_names()
    except Exception as _e:
        logger.warning("Impossible de récupérer la liste des tables: %s", _e)
        _ALL_TABLES = []
    return _ALL_TABLES


# Whitelist des tables par rôle
ALLOWED_TABLES_BY_ROLE: Dict[str, List[str]] = {
    # Étudiant : accès lecture aux tables académiques principales
    "etudiant": [
        "note",
        "matiere",
        "etudiant",
        "filiere",
        "devoir",
        "emploi_temps",
        "inscriptions",
        "presence",
    ],
    # Enseignant : tables étudiant + gestion de classe et évaluations
    "enseignant": [
        "note",
        "matiere",
        "etudiant",
        "filiere",
        "classe",
        "devoir",
        "quiz_questions",
        "quiz_attempts",
        "quiz_answers",
        "emploi_temps",
    ],
    # Administrateur : toutes les tables (liste vide = pas de restriction)
    "admin": [],
}

# Fonction utilitaire pour obtenir la whitelist complète selon rôle


def get_allowed_tables_for_role(role: str) -> List[str]:
    """Liste des tables autorisées pour un rôle (admin = toutes)."""
    if role == "admin":
        return get_all_tables()
    base = ALLOWED_TABLES_BY_ROLE.get(role, [])
    # Compléter dynamiquement avec toute nouvelle table absente
    all_tables = get_all_tables()
    return list(dict.fromkeys(base + [t for t in all_tables if t not in base]))


# Regex préparées
SELECT_PATTERN = re.compile(r"^\s*select\s+", re.IGNORECASE | re.DOTALL)
STAR_PATTERN = re.compile(r"\*")
INVALID_KEYWORDS_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|union|;|--|\/\*)\b",
    re.IGNORECASE,
)
TABLE_PATTERN = re.compile(r"from\s+([a-zA-Z_][\w]*)", re.IGNORECASE)
LIMIT_PATTERN = re.compile(r"limit\s+(\d+)", re.IGNORECASE)

MAX_ROWS = 100


class SQLValidationError(Exception):
    """Erreur levée lorsque la requête SQL n'est pas conforme aux règles."""


class SQLExecutor:
    """Valide et exécute une requête SQL en lecture seule."""

    def __init__(self, user_role: str):
        self.user_role = user_role
        self.allowed_tables: List[str] = ALLOWED_TABLES_BY_ROLE.get(user_role, [])

    # ---------------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------------
    def _validate(self, sql: str) -> None:
        sql_lower = sql.lower()

        # Doit commencer par SELECT
        if not SELECT_PATTERN.match(sql_lower):
            raise SQLValidationError("Seules les requêtes SELECT sont autorisées.")

        # Pas de SELECT *
        if STAR_PATTERN.search(sql):
            raise SQLValidationError(
                "L'utilisation de SELECT * est interdite. Spécifiez les colonnes."
            )

        # Pas de mots-clés ou structures interdites
        if INVALID_KEYWORDS_PATTERN.search(sql_lower):
            raise SQLValidationError(
                "La requête contient des mots-clés ou structures interdites."
            )

        # Vérifier les tables utilisées
        tables = TABLE_PATTERN.findall(sql_lower)
        if tables:
            if self.allowed_tables:  # Rôle non admin
                for table in tables:
                    if table not in self.allowed_tables:
                        raise SQLValidationError(
                            f"Table interdite pour le rôle {self.user_role}: {table}"
                        )
        else:
            raise SQLValidationError("Impossible de détecter la table dans la requête.")

    # ---------------------------------------------------------------------
    # Exécution
    # ---------------------------------------------------------------------
    def execute(self, sql: str) -> Dict[str, Any]:
        """Valide puis exécute la requête et renvoie le résultat limité."""

        # Validation stricte
        self._validate(sql)

        # Appliquer un LIMIT si absent ou supérieur à MAX_ROWS
        sql_with_limit = sql
        match_limit = LIMIT_PATTERN.search(sql)
        if match_limit:
            limit_val = int(match_limit.group(1))
            if limit_val > MAX_ROWS:
                sql_with_limit = LIMIT_PATTERN.sub(f"LIMIT {MAX_ROWS}", sql)
        else:
            sql_with_limit = f"{sql.rstrip(';')} LIMIT {MAX_ROWS}"

        try:
            result = db.session.execute(text(sql_with_limit))
            columns = result.keys()
            rows_raw = result.fetchall()
            rows = [dict(zip(columns, row)) for row in rows_raw]

            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "sql": sql_with_limit,
            }
        except SQLAlchemyError as e:
            logger.error("Erreur SQLExecutor : %s", e, exc_info=True)
            return {"success": False, "error": str(e)}


# Fonction utilitaire simple


def execute_sql_readonly(sql: str, user_role: str) -> Dict[str, Any]:
    """API façade utilisée par l'orchestrateur."""
    executor = SQLExecutor(user_role)
    return executor.execute(sql)
