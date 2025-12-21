"""
Middleware Flask pour sécuriser les requêtes internes de DefAI
Intercepte les requêtes venant de DefAI et valide les accès aux routes autorisées
"""

import logging
import hashlib
import hmac
import time
from flask import request, jsonify, g
from functools import wraps
from typing import Dict, Tuple, Optional
from app.services.defai_permissions import (
    DEFAI_ALLOWED_ENDPOINTS,
    DEFAI_CONFIG,
    is_endpoint_allowed,
    normalize_role,
)

logger = logging.getLogger(__name__)


class DefAIMiddleware:
    """Middleware pour sécuriser les requêtes internes de DefAI"""

    def __init__(self, app=None):
        self.app = app
        self.secret_key = None
        self.access_key = "defai-internal-key"
        self.allowed_endpoints = {}
        self.request_cache = {}  # Cache pour anti-replay
        self.cache_ttl = 300  # 5 minutes TTL pour le cache

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialise le middleware avec l'application Flask"""
        self.app = app
        self.secret_key = app.config.get("DEFAI_SECRET_KEY", "default-defai-secret-key")
        self.access_key = app.config.get("DEFAI_ACCESS_KEY", "defai-internal-key")
        self.cache_ttl = app.config.get(
            "DEFAI_CACHE_TTL", DEFAI_CONFIG.get("cache_ttl", 300)
        )

        # Charger les endpoints autorisés
        self._load_allowed_endpoints()

        # Enregistrer le middleware avant chaque requête
        app.before_request(self._before_request)
        app.after_request(self._after_request)

        logger.info("DefAI middleware initialisé")

    def _load_allowed_endpoints(self):
        """Charge la liste des endpoints autorisés depuis la configuration"""
        # Configuration par défaut basée sur defai_permissions
        self.allowed_endpoints = self.app.config.get(
            "DEFAI_ALLOWED_ENDPOINTS",
            DEFAI_ALLOWED_ENDPOINTS,
        )

    def _is_defai_request(self) -> bool:
        """Vérifie si la requête vient de DefAI"""
        return request.headers.get("X-DefAI-Key") is not None

    def _validate_auth(self) -> Tuple[bool, str]:
        """Valide l'authentification DefAI"""
        defai_key = request.headers.get("X-DefAI-Key")
        if not defai_key:
            return False, "Missing X-DefAI-Key header"
        if defai_key != self.access_key:
            return False, "Invalid DefAI key"

        # Vérifier la clé HMAC avec timestamp
        timestamp = request.headers.get("X-DefAI-Timestamp")
        signature = request.headers.get("X-DefAI-Signature")

        if not timestamp or not signature:
            return False, "Missing timestamp or signature"

        try:
            # Vérifier que le timestamp est récent (anti-replay)
            ts = int(timestamp)
            current_ts = int(time.time())
            if abs(current_ts - ts) > 300:  # 5 minutes max
                return False, "Timestamp too old"

            # Vérifier la signature HMAC
            expected_signature = self._generate_signature(
                request.method, request.path, request.get_data(silent=True) or b"", ts
            )

            if not hmac.compare_digest(signature, expected_signature):
                return False, "Invalid signature"

            # Vérifier anti-replay
            cache_key = f"{request.method}:{request.path}:{ts}"
            if cache_key in self.request_cache:
                return False, "Replay attack detected"

            # Ajouter au cache
            self.request_cache[cache_key] = ts
            self._cleanup_cache()

            return True, "Authentication successful"

        except Exception as e:
            logger.error(f"Erreur validation auth DefAI: {e}")
            return False, f"Authentication error: {str(e)}"

    def _generate_signature(
        self, method: str, path: str, body: bytes, timestamp: int
    ) -> str:
        """Génère une signature HMAC pour la requête"""
        message = f"{method}:{path}:{timestamp}:{body.decode('utf-8', errors='ignore')}"
        return hmac.new(
            self.secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _is_endpoint_allowed(self) -> Tuple[bool, str]:
        """Vérifie si l'endpoint demandé est autorisé"""
        method = request.method
        path = request.path
        role = getattr(g, "defai_effective_role", "etudiant")
        return is_endpoint_allowed(role, method, path)

    def _cleanup_cache(self):
        """Nettoie le cache des requêtes expirées"""
        current_time = time.time()
        expired_keys = [
            key
            for key, ts in self.request_cache.items()
            if current_time - ts > self.cache_ttl
        ]
        for key in expired_keys:
            del self.request_cache[key]

    def _prepare_defai_context(self):
        """Stocke les informations utiles sur la requête DefAI"""
        normalized_role = normalize_role(
            request.headers.get("X-DefAI-User-Role", "etudiant")
        )
        user_id = request.headers.get("X-DefAI-User-Id")
        request_id = request.headers.get(
            "X-DefAI-Request-Id", f"defai-{int(time.time())}"
        )
        g.defai_request_id = request_id
        g.defai_target_user_id = user_id
        g.defai_effective_role = normalized_role

    def _before_request(self):
        """Middleware exécuté avant chaque requête"""
        if not self._is_defai_request():
            return None  # Ce n'est pas une requête DefAI, continuer normalement

        # Valider l'authentification
        is_valid, message = self._validate_auth()
        if not is_valid:
            logger.warning(f"DefAI auth failed: {message}")
            return jsonify({"error": "Authentication failed", "message": message}), 401

        # Préparer le contexte DefAI (rôle, user_id, etc.)
        self._prepare_defai_context()

        # Valider l'endpoint
        is_allowed, message = self._is_endpoint_allowed()
        if not is_allowed:
            logger.warning(f"DefAI endpoint not allowed: {message}")
            return jsonify({"error": "Access denied", "message": message}), 403

        # Ajouter des informations au contexte global
        g.is_defai_request = True
        g.defai_timestamp = request.headers.get("X-DefAI-Timestamp")

        # Logger la requête
        logger.info(f"DefAI request: {request.method} {request.path}")

        return None

    def _after_request(self, response):
        """Middleware exécuté après chaque requête"""
        if hasattr(g, "is_defai_request") and g.is_defai_request:
            # Logger la réponse pour audit
            logger.info(
                f"DefAI response: {response.status_code} {request.method} {request.path}"
            )

            # Ajouter des headers de sécurité
            response.headers["X-DefAI-Processed"] = "true"
            response.headers["X-DefAI-Timestamp"] = str(int(time.time()))

        return response


# Fonction décorateur pour protéger les routes DefAI
def require_defai_auth(f):
    """Décorateur pour exiger une authentification DefAI sur une route spécifique"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, "is_defai_request") or not g.is_defai_request:
            return (
                jsonify(
                    {
                        "error": "DefAI authentication required",
                        "message": "This endpoint requires DefAI authentication",
                    }
                ),
                401,
            )
        return f(*args, **kwargs)

    return decorated_function


# Fonction utilitaire pour générer des headers DefAI
def generate_defai_headers(
    method: str,
    path: str,
    body: bytes = None,
    secret_key: str = None,
    access_key: str = "defai-internal",
    user_role: str = "etudiant",
    user_id: Optional[str] = None,
) -> Dict[str, str]:
    """Génère les headers nécessaires pour une requête DefAI"""
    if body is None:
        body = b""

    timestamp = str(int(time.time()))

    # Générer la signature
    message = f"{method}:{path}:{timestamp}:{body.decode('utf-8', errors='ignore')}"
    signature = hmac.new(
        (secret_key or "default-defai-secret-key").encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "X-DefAI-Key": access_key,
        "X-DefAI-Timestamp": timestamp,
        "X-DefAI-Signature": signature,
        "X-DefAI-User-Role": user_role,
        "Content-Type": "application/json",
    }
    if user_id:
        headers["X-DefAI-User-Id"] = str(user_id)
    return headers
