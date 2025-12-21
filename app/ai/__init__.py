"""
Package pour les fonctionnalités d'IA de l'application.
Inclut l'intégration avec Gemini et d'autres services d'IA.
"""

# Import des classes principales
from .study_buddy_ai import StudyBuddyAI
import os


def init_app(app):
    """Initialise les services d'IA avec la configuration de l'application"""
    # Vérifier si la clé API Gemini est configurée
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("La clé API Gemini n'est pas configurée")

    # Initialiser le client StudyBuddyAI
    app.study_buddy_ai = StudyBuddyAI(
        api_key=gemini_api_key, model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    )

    return app
