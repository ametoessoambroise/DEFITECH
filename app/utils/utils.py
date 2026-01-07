"""Utility functions for the DEFITECH application."""

# ==========================================
# YEAR NORMALIZATION UTILITIES
# ==========================================

# Mapping global des variantes d'années vers un format standard
# Utilisé pour éviter les confusions entre "1 ere annee", "1ère année", etc.
ANNEE_MAPPING = {
    "1 ere annee": "1ère année",
    "1ere annee": "1ère année",
    "1 ère année": "1ère année",
    "1ere année": "1ère année",
    "1ère annee": "1ère année",
    "2 eme annee": "2ème année",
    "2eme annee": "2ème année",
    "2 ème année": "2ème année",
    "2eme année": "2ème année",
    "2ème annee": "2ème année",
    "3 eme annee": "3ème année",
    "3eme annee": "3ème année",
    "3 ème année": "3ème année",
    "3eme année": "3ème année",
    "3ème annee": "3ème année",
    "4 eme annee": "4ème année",
    "4eme annee": "4ème année",
    "4 ème année": "4ème année",
    "4eme année": "4ème année",
    "4ème annee": "4ème année",
    "5 eme annee": "5ème année",
    "5eme annee": "5ème année",
    "5 ème année": "5ème année",
    "5eme année": "5ème année",
    "5ème annee": "5ème année",
}


def normalize_annee(annee_str):
    """
    Normalise le nom d'une année pour éviter les incohérences.

    Args:
        annee_str (str): Le nom de l'année à normaliser

    Returns:
        str: Le nom normalisé de l'année, ou le nom original si aucune correspondance

    Examples:
        >>> normalize_annee("1 ere annee")
        "1ère année"
        >>> normalize_annee("2EME ANNEE")
        "2ème année"
        >>> normalize_annee("1ère année")
        "1ère année"
    """
    if not annee_str:
        return annee_str

    # Normaliser en minuscules et supprimer les espaces inutiles
    normalized = annee_str.lower().strip()

    # Retourner le mapping ou le nom original si pas de correspondance
    return ANNEE_MAPPING.get(normalized, annee_str)


ALLOWED_EXTENSIONS = {
    "pdf",
    "docx",
    "xlsx",
    "jpg",
    "jpeg",
    "png",
    "ico",
    "avif",
    "mp4",
    "avi",
    "mov",
    "zip",
    "rar",
    "7z",
    "tar",
    "gz",
    "bz2",
    "html",
    "css",
    "js",
    "jsx",
    "tsx",
    "ts",
    "py",
    "c",
    "cpp",
    "java",
    "jar",
    "class",
    "pyc",
    "pyo",
    "bat",
    "vbs",
}


def allowed_file(filename):
    """
    Vérifie si l'extension du fichier est autorisée

    Args:
        filename (str): Nom du fichier à vérifier

    Returns:
        bool: True si l'extension est autorisée, False sinon
    """
    if not filename:
        return False

    # Obtenir l'extension du fichier
    extension = filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    return extension in ALLOWED_EXTENSIONS
