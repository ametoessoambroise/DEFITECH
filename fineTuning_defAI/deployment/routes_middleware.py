"""
Middleware de routes pour DefAI en production
Intégre l'API DefAI dans la plateforme universitaire existante
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

# Flask
from flask import Flask, request, jsonify, g, current_app
from flask_cors import CORS

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DefAIMiddleware:
    """Middleware pour intégrer DefAI dans une application Flask existante"""

    def __init__(self, app: Flask = None, defai_url: str = "http://localhost:5000"):
        self.defai_url = defai_url
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialise le middleware sur l'application Flask"""
        self.app = app

        # Configuration
        app.config.setdefault("DEFAI_URL", self.defai_url)
        app.config.setdefault("DEFAI_TIMEOUT", 30)
        app.config.setdefault("DEFAI_ENABLED", True)

        # Enregistrer le middleware
        app.before_request(self._before_request)
        app.after_request(self._after_request)

        logger.info("Middleware DefAI initialisé")

    def _before_request(self):
        """Exécuté avant chaque requête"""
        if not self.app.config.get("DEFAI_ENABLED"):
            return

        # Enregistrer la requête pour analyse
        g.request_start_time = datetime.now()
        g.defai_context = {
            "method": request.method,
            "path": request.path,
            "user_agent": request.headers.get("User-Agent", ""),
            "ip": request.remote_addr,
            "timestamp": g.request_start_time.isoformat(),
        }

    def _after_request(self, response):
        """Exécuté après chaque requête"""
        if not self.app.config.get("DEFAI_ENABLED"):
            return response

        # Calculer la durée
        if hasattr(g, "request_start_time"):
            duration = (datetime.now() - g.request_start_time).total_seconds()
            g.defai_context["duration"] = duration
            g.defai_context["status_code"] = response.status_code

            # Envoyer les données à DefAI pour analyse (asynchrone)
            self._log_to_defai(g.defai_context)

        return response

    def _log_to_defai(self, context: Dict[str, Any]):
        """Envoie les données de la requête à DefAI pour analyse"""
        try:
            # Envoyer en arrière-plan pour ne pas bloquer la requête
            import threading

            def log_async():
                try:
                    requests.post(
                        f"{self.defai_url}/routes/log", json=context, timeout=5
                    )
                except Exception as e:
                    logger.warning(f"Impossible de logger vers DefAI: {e}")

            thread = threading.Thread(target=log_async)
            thread.daemon = True
            thread.start()

        except Exception as e:
            logger.warning(f"Erreur dans le logging DefAI: {e}")

    def get_assistance(
        self, query: str, user_role: str = "user"
    ) -> Optional[Dict[str, Any]]:
        """Obtient de l'assistance de DefAI"""
        try:
            response = requests.post(
                f"{self.defai_url}/assist",
                json={"query": query, "user_role": user_role},
                timeout=self.app.config.get("DEFAI_TIMEOUT", 30),
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur DefAI: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erreur lors de la communication avec DefAI: {e}")
            return None

    def analyze_error(self, error_info: str) -> Optional[Dict[str, Any]]:
        """Analyse une erreur avec DefAI"""
        try:
            response = requests.post(
                f"{self.defai_url}/debug/error",
                json={"error_info": error_info},
                timeout=self.app.config.get("DEFAI_TIMEOUT", 30),
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur DefAI: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse d'erreur: {e}")
            return None

    def suggest_routes(self, user_activity: str) -> Optional[Dict[str, Any]]:
        """Obtient des suggestions de routes de DefAI"""
        try:
            response = requests.post(
                f"{self.defai_url}/routes/suggest",
                json={"user_activity": user_activity},
                timeout=self.app.config.get("DEFAI_TIMEOUT", 30),
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur DefAI: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erreur lors de la suggestion de routes: {e}")
            return None


def create_defai_app(config_path: str = None) -> Flask:
    """Crée une application Flask avec DefAI intégré"""
    app = Flask(__name__)
    CORS(app)

    # Charger la configuration
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            app.config.update(config)
    else:
        # Configuration par défaut
        app.config.update(
            {
                "DEFAI_URL": os.getenv("DEFAI_URL", "http://localhost:5000"),
                "DEFAI_TIMEOUT": int(os.getenv("DEFAI_TIMEOUT", 30)),
                "DEFAI_ENABLED": os.getenv("DEFAI_ENABLED", "true").lower() == "true",
            }
        )

    # Initialiser le middleware
    defai_middleware = DefAIMiddleware(app)

    # Routes API avec intégration DefAI
    @app.route("/api/defai/chat", methods=["POST"])
    def defai_chat():
        """Endpoint de chat avec DefAI"""
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"error": "Message requis"}), 400

        try:
            response = requests.post(
                f"{app.config['DEFAI_URL']}/chat",
                json=data,
                timeout=app.config["DEFAI_TIMEOUT"],
            )

            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({"error": "Service DefAI indisponible"}), 503

        except Exception as e:
            logger.error(f"Erreur communication DefAI: {e}")
            return jsonify({"error": "Service DefAI indisponible"}), 503

    @app.route("/api/defai/assist", methods=["POST"])
    def defai_assist():
        """Assistance DefAI pour les utilisateurs"""
        data = request.get_json()

        if not data or "query" not in data:
            return jsonify({"error": "Query requise"}), 400

        assistance = defai_middleware.get_assistance(
            data["query"], data.get("user_role", "user")
        )

        if assistance:
            return jsonify(assistance)
        else:
            return jsonify({"error": "Service DefAI indisponible"}), 503

    @app.route("/api/defai/analyze", methods=["POST"])
    def defai_analyze():
        """Analyse DefAI"""
        data = request.get_json()

        if not data or "context" not in data:
            return jsonify({"error": "Contexte requis"}), 400

        try:
            response = requests.post(
                f"{app.config['DEFAI_URL']}/analyze",
                json=data,
                timeout=app.config["DEFAI_TIMEOUT"],
            )

            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({"error": "Service DefAI indisponible"}), 503

        except Exception as e:
            logger.error(f"Erreur communication DefAI: {e}")
            return jsonify({"error": "Service DefAI indisponible"}), 503

    @app.route("/api/defai/routes/suggest", methods=["POST"])
    def defai_suggest_routes():
        """Suggestions de routes DefAI"""
        data = request.get_json()

        if not data or "user_activity" not in data:
            return jsonify({"error": "Activité utilisateur requise"}), 400

        suggestions = defai_middleware.suggest_routes(data["user_activity"])

        if suggestions:
            return jsonify(suggestions)
        else:
            return jsonify({"error": "Service DefAI indisponible"}), 503

    @app.route("/api/defai/debug/error", methods=["POST"])
    def defai_debug_error():
        """Débogage d'erreurs DefAI"""
        data = request.get_json()

        if not data or "error_info" not in data:
            return jsonify({"error": "Informations d'erreur requises"}), 400

        debug_help = defai_middleware.analyze_error(data["error_info"])

        if debug_help:
            return jsonify(debug_help)
        else:
            return jsonify({"error": "Service DefAI indisponible"}), 503

    @app.route("/api/defai/health", methods=["GET"])
    def defai_health():
        """Vérification de l'état de DefAI"""
        try:
            response = requests.get(f"{app.config['DEFAI_URL']}/health", timeout=5)

            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return (
                    jsonify(
                        {"status": "unhealthy", "error": "Service DefAI indisponible"}
                    ),
                    503,
                )

        except Exception as e:
            logger.error(f"Erreur vérification DefAI: {e}")
            return (
                jsonify({"status": "unhealthy", "error": "Service DefAI indisponible"}),
                503,
            )

    # Routes de l'application existante (exemples)
    @app.route("/dashboard")
    def dashboard():
        """Tableau de bord avec suggestions DefAI"""
        # Obtenir des suggestions basées sur l'activité récente
        activity_data = {
            "user_activity": f"Utilisateur accède au dashboard depuis {request.remote_addr}"
        }

        suggestions = defai_middleware.suggest_routes(json.dumps(activity_data))

        return jsonify(
            {
                "dashboard": "Bienvenue sur le dashboard",
                "defai_suggestions": (
                    suggestions.get("suggestions") if suggestions else None
                ),
            }
        )

    @app.route("/courses")
    def courses():
        """Page des cours avec assistance DefAI"""
        return jsonify(
            {
                "courses": "Liste des cours",
                "defai_assistance": "Disponible via /api/defai/assist",
            }
        )

    @app.errorhandler(404)
    def not_found_error(error):
        """Gestion des erreurs 404 avec DefAI"""
        error_info = f"Erreur 404: Page {request.path} non trouvée"
        debug_help = defai_middleware.analyze_error(error_info)

        return (
            jsonify(
                {
                    "error": "Page non trouvée",
                    "defai_help": debug_help.get("debug_help") if debug_help else None,
                }
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        """Gestion des erreurs 500 avec DefAI"""
        error_info = f"Erreur 500: Erreur interne du serveur sur {request.path}"
        debug_help = defai_middleware.analyze_error(error_info)

        return (
            jsonify(
                {
                    "error": "Erreur interne du serveur",
                    "defai_help": debug_help.get("debug_help") if debug_help else None,
                }
            ),
            500,
        )

    return app


def with_defai_assistance(user_role: str = "user"):
    """Décorateur pour ajouter l'assistance DefAI à une route"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Vérifier si une assistance est demandée
            if request.args.get("defai_help") == "true":
                defai_middleware = current_app.extensions.get("defai_middleware")
                if defai_middleware:
                    # Obtenir de l'assistance basée sur la requête
                    query = f"Assistance pour la route {request.method} {request.path}"
                    assistance = defai_middleware.get_assistance(query, user_role)

                    # Ajouter l'assistance à la réponse
                    result = f(*args, **kwargs)
                    if isinstance(result, dict):
                        result["defai_assistance"] = (
                            assistance.get("assistance") if assistance else None
                        )
                    elif isinstance(result, tuple):
                        response_dict = result[0]
                        if isinstance(response_dict, dict):
                            response_dict["defai_assistance"] = (
                                assistance.get("assistance") if assistance else None
                            )
                        result = (response_dict, result[1])
                    return result

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Configuration pour le déploiement
def create_production_config() -> Dict[str, Any]:
    """Crée une configuration pour la production"""
    return {
        "DEFAI_URL": os.getenv("DEFAI_URL", "http://defai-service:5000"),
        "DEFAI_TIMEOUT": int(os.getenv("DEFAI_TIMEOUT", 30)),
        "DEFAI_ENABLED": os.getenv("DEFAI_ENABLED", "true").lower() == "true",
        "SECRET_KEY": os.getenv("SECRET_KEY", "your-secret-key"),
        "DEBUG": False,
    }


def create_development_config() -> Dict[str, Any]:
    """Crée une configuration pour le développement"""
    return {
        "DEFAI_URL": os.getenv("DEFAI_URL", "http://localhost:5000"),
        "DEFAI_TIMEOUT": int(os.getenv("DEFAI_TIMEOUT", 30)),
        "DEFAI_ENABLED": os.getenv("DEFAI_ENABLED", "true").lower() == "true",
        "SECRET_KEY": "dev-secret-key",
        "DEBUG": True,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Application Flask avec DefAI intégré")
    parser.add_argument("--config", help="Fichier de configuration JSON")
    parser.add_argument("--host", default="0.0.0.0", help="Host de l'application")
    parser.add_argument("--port", type=int, default=8000, help="Port de l'application")
    parser.add_argument("--debug", action="store_true", help="Mode debug")
    parser.add_argument("--production", action="store_true", help="Mode production")

    args = parser.parse_args()

    # Configuration
    if args.production:
        config = create_production_config()
    else:
        config = create_development_config()

    if args.debug:
        config["DEBUG"] = True

    # Créer l'application
    app = create_defai_app(args.config)

    # Démarrer l'application
    logger.info(f"Démarrage de l'application DefAI sur {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=config["DEBUG"])
