"""
Fichier utilitaire pour l'application DEFITECH
"""

ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx',
    'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', 'mp4', 'avi',
    'mov', 'wmv', 'flv', 'webm', 'mp3', 'wav', 'ogg'
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
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    return extension in ALLOWED_EXTENSIONS
