"""
Client interne DefAI pour faire des requêtes sécurisées vers l'application
Permet à DefAI d'envoyer des requêtes internes avec authentification automatique
"""

import logging
import json
import time
import hashlib
import hmac
import os
import uuid
import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from app.services.defai_permissions import is_endpoint_allowed, normalize_role

logger = logging.getLogger(__name__)


class DefAIClient:
    """Client interne pour les requêtes DefAI vers l'application"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret_key: Optional[str] = None,
        access_key: Optional[str] = None,
    ):
        """
        Initialise le client DefAI

        Args:
            base_url: URL de base de l'application Flask
            secret_key: Clé secrète pour la signature HMAC
            access_key: Clé partagée utilisée dans le header X-DefAI-Key
        """
        resolved_base_url = base_url or os.getenv(
            "DEFAI_BASE_URL", "http://localhost:5000"
        )
        self.base_url = resolved_base_url.rstrip("/")
        self.secret_key = secret_key or os.getenv(
            "DEFAI_SECRET_KEY", "default-defai-secret-key"
        )
        self.access_key = access_key or os.getenv(
            "DEFAI_ACCESS_KEY", "defai-internal-key"
        )
        self.session = requests.Session()

        # Configuration par défaut
        self.default_timeout = 30
        self.max_retries = 3
        self.retry_delay = 1

        # Headers par défaut
        self.session.headers.update(
            {
                "User-Agent": "DefAI-Internal-Client/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _generate_signature(
        self, method: str, path: str, body: bytes, timestamp: int
    ) -> str:
        """Génère une signature HMAC pour la requête"""
        message = f"{method}:{path}:{timestamp}:{body.decode('utf-8', errors='ignore')}"
        return hmac.new(
            self.secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _prepare_headers(
        self,
        method: str,
        path: str,
        body: bytes,
        user_role: Optional[str],
        user_id: Optional[Any],
        request_id: str,
    ) -> Dict[str, str]:
        """Prépare les headers nécessaires pour l'authentification DefAI"""
        timestamp = str(int(time.time()))
        signature = self._generate_signature(method, path, body, int(timestamp))
        normalized_role = normalize_role(user_role or "etudiant")

        headers = {
            "X-DefAI-Key": self.access_key,
            "X-DefAI-Timestamp": timestamp,
            "X-DefAI-Signature": signature,
            "X-DefAI-User-Role": normalized_role,
            "X-DefAI-Request-Id": request_id,
            "Content-Type": "application/json",
        }
        if user_id is not None:
            headers["X-DefAI-User-Id"] = str(user_id)
        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Any = None,
        params: Dict = None,
        user_role: Optional[str] = None,
        user_id: Optional[Any] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Effectue une requête avec authentification DefAI

        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint cible (ex: '/api/users')
            data: Données à envoyer (pour POST/PUT)
            params: Paramètres URL (pour GET)
            **kwargs: Arguments supplémentaires pour requests

        Returns:
            Response: Objet response de requests
        """
        normalized_role = normalize_role(user_role or "etudiant")

        # Construire l'URL complet
        url = urljoin(self.base_url, endpoint)
        parsed = urlparse(url)
        path = parsed.path

        allowed, message = is_endpoint_allowed(normalized_role, method.upper(), path)
        if not allowed:
            raise DefAIRequestError(message)

        # Préparer le payload
        body_payload = b""
        if method.upper() in ["POST", "PUT", "PATCH"] and data is not None:
            if isinstance(data, (dict, list)):
                body_payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            else:
                body_payload = str(data).encode("utf-8")

        # Préparer les headers
        headers = self._prepare_headers(
            method,
            path,
            body_payload,
            user_role=normalized_role,
            user_id=user_id,
            request_id=request_id or str(uuid.uuid4()),
        )

        # Fusionner avec les headers existants
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        # Préparer les arguments de la requête
        request_kwargs = {
            "headers": headers,
            "timeout": kwargs.pop("timeout", self.default_timeout),
            "params": params,
        }

        # Ajouter les données selon la méthode
        if method.upper() in ["POST", "PUT", "PATCH"]:
            if body_payload:
                request_kwargs["data"] = body_payload
            elif data is not None:
                request_kwargs["data"] = str(data).encode("utf-8")

        # Ajouter les autres arguments
        request_kwargs.update(kwargs)

        # Effectuer la requête avec retry
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **request_kwargs)

                # Logger la requête
                logger.info(f"DefAI request: {method} {url} -> {response.status_code}")

                return response

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    logger.warning(f"DefAI request failed (attempt {attempt + 1}): {e}")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(
                        f"DefAI request failed after {self.max_retries + 1} attempts: {e}"
                    )
                    raise

    def get(self, endpoint: str, params: Dict = None, **kwargs) -> requests.Response:
        """Effectue une requête GET"""
        return self._make_request("GET", endpoint, params=params, **kwargs)

    def post(self, endpoint: str, data: Any = None, **kwargs) -> requests.Response:
        """Effectue une requête POST"""
        return self._make_request("POST", endpoint, data=data, **kwargs)

    def put(self, endpoint: str, data: Any = None, **kwargs) -> requests.Response:
        """Effectue une requête PUT"""
        return self._make_request("PUT", endpoint, data=data, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Effectue une requête DELETE"""
        return self._make_request("DELETE", endpoint, **kwargs)

    def patch(self, endpoint: str, data: Any = None, **kwargs) -> requests.Response:
        """Effectue une requête PATCH"""
        return self._make_request("PATCH", endpoint, data=data, **kwargs)

    def get_json(self, endpoint: str, params: Dict = None, **kwargs) -> Dict[str, Any]:
        """Effectue une requête GET et retourne la réponse JSON"""
        response = self.get(endpoint, params=params, **kwargs)
        return self._handle_response(response)

    def post_json(self, endpoint: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """Effectue une requête POST et retourne la réponse JSON"""
        response = self.post(endpoint, data=data, **kwargs)
        return self._handle_response(response)

    def put_json(self, endpoint: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """Effectue une requête PUT et retourne la réponse JSON"""
        response = self.put(endpoint, data=data, **kwargs)
        return self._handle_response(response)

    def delete_json(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Effectue une requête DELETE et retourne la réponse JSON"""
        response = self.delete(endpoint, **kwargs)
        return self._handle_response(response)

    def patch_json(self, endpoint: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """Effectue une requête PATCH et retourne la réponse JSON"""
        response = self.patch(endpoint, data=data, **kwargs)
        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Gère la réponse et retourne les données JSON ou lève une exception

        Args:
            response: Objet response de requests

        Returns:
            Dict: Données JSON de la réponse

        Raises:
            DefAIRequestError: Si la requête a échoué
        """
        try:
            response.raise_for_status()

            if response.content:
                return response.json()
            else:
                return {"success": True, "message": "Request successful"}

        except requests.exceptions.HTTPError:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"DefAI HTTP error: {error_msg}")
            raise DefAIRequestError(error_msg, status_code=response.status_code)

        except json.JSONDecodeError:
            error_msg = f"Invalid JSON response: {response.text}"
            logger.error(f"DefAI JSON error: {error_msg}")
            raise DefAIRequestError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"DefAI unexpected error: {error_msg}")
            raise DefAIRequestError(error_msg)


class DefAIRequestError(Exception):
    """Exception personnalisée pour les erreurs de requête DefAI"""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# Client singleton pour faciliter l'utilisation
def get_defai_client(
    base_url: str = None, secret_key: str = None, access_key: str = None
) -> DefAIClient:
    """Retourne une instance du client DefAI (singleton pattern)"""
    if not hasattr(get_defai_client, "_instance") or get_defai_client._instance is None:
        get_defai_client._instance = DefAIClient(base_url, secret_key, access_key)
    return get_defai_client._instance


# Fonctions utilitaires pour les opérations courantes
class DefAIHelper:
    """Classe utilitaire avec des méthodes courantes pour DefAI"""

    def __init__(self, client: DefAIClient = None):
        self.client = client or get_defai_client()

    def get_user_conversations(self, user_id: int) -> Dict[str, Any]:
        """Récupère les conversations d'un utilisateur"""
        return self.client.get_json(f"/ai/conversations?user_id={user_id}")

    def create_conversation(
        self, user_id: int, user_role: str, title: str = None
    ) -> Dict[str, Any]:
        """Crée une nouvelle conversation"""
        data = {
            "user_id": user_id,
            "user_role": user_role,
            "title": title or "Nouvelle conversation",
        }
        return self.client.post_json("/ai/conversations", data)

    def send_message(
        self, conversation_id: int, message: str, user_id: int
    ) -> Dict[str, Any]:
        """Envoie un message dans une conversation"""
        data = {
            "conversation_id": conversation_id,
            "message": message,
            "user_id": user_id,
        }
        return self.client.post_json("/ai/chat", data)

    def get_student_grades(self, student_id: int) -> Dict[str, Any]:
        """Récupère les notes d'un étudiant"""
        return self.client.get_json(
            f"/api/role-data/etudiant/grades?student_id={student_id}",
            user_role="etudiant",
            user_id=student_id,
        )

    def get_student_schedule(self, student_id: int) -> Dict[str, Any]:
        """Récupère l'emploi du temps d'un étudiant"""
        return self.client.get_json(
            f"/api/role-data/etudiant/schedule?student_id={student_id}",
            user_role="etudiant",
            user_id=student_id,
        )

    def get_teacher_classes(self, teacher_id: int) -> Dict[str, Any]:
        """Récupère les classes d'un enseignant"""
        return self.client.get_json(
            f"/api/role-data/enseignant/classes?teacher_id={teacher_id}",
            user_role="enseignant",
            user_id=teacher_id,
        )

    def get_platform_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de la plateforme (admin only)"""
        return self.client.get_json(
            "/api/role-data/admin/platform-stats",
            user_role="admin",
        )

    def notify_users(
        self, message: str, target_roles: list = None, target_users: list = None
    ) -> Dict[str, Any]:
        """Envoie une notification aux utilisateurs"""
        data = {
            "message": message,
            "target_roles": target_roles or [],
            "target_users": target_users or [],
        }
        return self.client.post_json(
            "/api/role-data/admin/notify",
            data,
            user_role="admin",
        )

    def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Récupère les informations d'un utilisateur"""
        return self.client.get_json(
            f"/api/users/{user_id}",
            user_role="admin",
            user_id=user_id,
        )

    def update_grade(self, grade_id: int, grade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour une note (enseignant/admin only)"""
        return self.client.put_json(
            f"/api/grades/{grade_id}",
            grade_data,
            user_role="enseignant",
        )

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouvel utilisateur (admin only)"""
        return self.client.post_json(
            "/api/users",
            user_data,
            user_role="admin",
        )


# Export des classes et fonctions principales
__all__ = ["DefAIClient", "DefAIRequestError", "get_defai_client", "DefAIHelper"]
