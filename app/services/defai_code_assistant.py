"""
Service de gestion du contexte de code pour l'assistant DEFAI.

Ce service extrait, formate et prépare le contexte de code pour les requêtes
provenant de l'extension VS Code Intelitech.
"""

import re
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class CodeContext:
    """Représente le contexte de code extrait."""

    language: str
    file_path: str
    selected_code: Optional[str] = None
    line_range: Optional[Dict[str, int]] = None
    full_file_content: Optional[str] = None


class DefaiCodeAssistantService:
    """Service principal pour l'assistance de code DEFAI."""

    # Patterns sensibles à supprimer du code
    SENSITIVE_PATTERNS = [
        (r'(api[_-]?key\s*[=:]\s*["\'])[^"\']+(["\'])', r"\1***MASKED***\2"),
        (r'(password\s*[=:]\s*["\'])[^"\']+(["\'])', r"\1***MASKED***\2"),
        (r'(secret\s*[=:]\s*["\'])[^"\']+(["\'])', r"\1***MASKED***\2"),
        (r'(token\s*[=:]\s*["\'])[^"\']+(["\'])', r"\1***MASKED***\2"),
        (r"(bearer\s+)[a-zA-Z0-9_\-]+", r"\1***MASKED***"),
    ]

    # Extensions de fichiers → Langages
    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React (JSX)",
        ".tsx": "React (TSX)",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".cs": "C#",
        ".php": "PHP",
        ".rb": "Ruby",
        ".go": "Go",
        ".rs": "Rust",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".dart": "Dart",
        ".html": "HTML",
        ".css": "CSS",
        ".sql": "SQL",
        ".sh": "Shell",
        ".bash": "Bash",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".xml": "XML",
        ".md": "Markdown",
    }

    @staticmethod
    def detect_language(file_path: str) -> str:
        """
        Détecte le langage de programmation à partir de l'extension du fichier.

        Args:
            file_path: Chemin du fichier

        Returns:
            Nom du langage détecté ou 'Unknown'
        """
        if not file_path:
            return "Unknown"

        # Extraire l'extension
        extension = "." + file_path.split(".")[-1] if "." in file_path else ""
        return DefaiCodeAssistantService.LANGUAGE_MAP.get(extension.lower(), "Unknown")

    @staticmethod
    def sanitize_code(code: str) -> str:
        """
        Nettoie le code des informations sensibles (API keys, passwords, etc.).

        Args:
            code: Code source à nettoyer

        Returns:
            Code nettoyé avec les informations sensibles masquées
        """
        if not code:
            return code

        sanitized = code
        for pattern, replacement in DefaiCodeAssistantService.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def extract_context(
        file_path: str,
        selected_code: Optional[str] = None,
        language: Optional[str] = None,
        line_range: Optional[Dict[str, int]] = None,
        full_file_content: Optional[str] = None,
    ) -> CodeContext:
        """
        Extrait et structure le contexte de code.

        Args:
            file_path: Chemin du fichier
            selected_code: Code sélectionné par l'utilisateur
            language: Langage (auto-détecté si non fourni)
            line_range: Plage de lignes {"start": 10, "end": 25}
            full_file_content: Contenu complet du fichier (optionnel)

        Returns:
            Objet CodeContext structuré
        """
        # Auto-détection du langage si non fourni
        if not language:
            language = DefaiCodeAssistantService.detect_language(file_path)

        # Sanitize selected code
        sanitized_selection = (
            DefaiCodeAssistantService.sanitize_code(selected_code)
            if selected_code
            else None
        )

        # Sanitize full content if provided (limité à 10000 chars pour éviter surcharge)
        sanitized_full_content = None
        if full_file_content:
            sanitized_full_content = DefaiCodeAssistantService.sanitize_code(
                full_file_content[:10000]
            )

        return CodeContext(
            language=language,
            file_path=file_path,
            selected_code=sanitized_selection,
            line_range=line_range,
            full_file_content=sanitized_full_content,
        )

    @staticmethod
    def prepare_defai_payload(
        message: str,
        code_context: CodeContext,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Prépare le payload enrichi pour DEFAI.

        Args:
            message: Question de l'utilisateur
            code_context: Contexte de code extrait
            project_id: ID du projet (optionnel)
            user_id: ID de l'utilisateur

        Returns:
            Dictionnaire structuré prêt pour l'API
        """
        payload = {
            "message": message,
            "code_context": {
                "language": code_context.language,
                "file_path": code_context.file_path,
            },
            "source": "vscode_extension",
        }

        # Ajouter le code sélectionné si présent
        if code_context.selected_code:
            payload["code_context"]["selected_code"] = code_context.selected_code

        # Ajouter la plage de lignes si présente
        if code_context.line_range:
            payload["code_context"]["line_range"] = code_context.line_range

        # Ajouter le contenu complet si présent (pour analyse approfondie)
        if code_context.full_file_content:
            payload["code_context"][
                "full_file_content"
            ] = code_context.full_file_content

        # Ajouter les infos de projet si présentes
        if project_id:
            payload["project_id"] = project_id

        if user_id:
            payload["user_id"] = user_id

        return payload

    @staticmethod
    def format_code_for_ai(code: str, language: str) -> str:
        """
        Formate le code pour une meilleure compréhension par l'IA.

        Args:
            code: Code source
            language: Langage de programmation

        Returns:
            Code formaté avec des annotations pour l'IA
        """
        if not code:
            return ""

        # Ajouter des marqueurs de contexte pour l'IA
        formatted = f"```{language.lower()}\n{code}\n```"

        return formatted

    @staticmethod
    def enrich_context_for_gemini(
        base_context: Dict[str, Any], code_context: CodeContext
    ) -> Dict[str, Any]:
        """
        Enrichit le contexte utilisateur avec les informations de code.

        Args:
            base_context: Contexte utilisateur de base (rôle, etc.)
            code_context: Contexte de code

        Returns:
            Contexte enrichi pour Gemini
        """
        enriched = base_context.copy()

        # Ajouter des hints spécifiques au code
        hints = enriched.get("hints", [])
        hints.extend(
            [
                "L'utilisateur code dans VS Code ou similaire",
                f"Langage de programmation: {code_context.language}",
                "Question liée au code actuel",
                "Fournir des exemples de code concrets et précis",
                "Expliquer de manière pédagogique adaptée au niveau étudiant",
            ]
        )
        enriched["hints"] = hints

        # Ajouter le contexte de code formaté
        if code_context.selected_code:
            enriched["current_code"] = DefaiCodeAssistantService.format_code_for_ai(
                code_context.selected_code, code_context.language
            )

        enriched["coding_session"] = True
        enriched["file_context"] = code_context.file_path

        return enriched
