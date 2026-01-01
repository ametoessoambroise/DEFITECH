from functools import wraps
from flask import session, request, jsonify
from flask_login import current_user
from datetime import datetime


def app_lock_required(f):
    """
    Décorateur pour vérifier si l'application est verrouillée.
    Si verrouillée, renvoie un code 423 (Locked) pour les requêtes AJAX
    ou redirige vers la page de déverrouillage pour les requêtes normales.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_app_lock_enabled:
            # Vérifier si l'application est déverrouillée dans la session
            unlocked_until = session.get("app_unlocked_until")

            # Si pas de timestamp ou expired
            if not unlocked_until or datetime.utcnow().timestamp() > unlocked_until:
                if (
                    request.is_json
                    or request.headers.get("X-Requested-With") == "XMLHttpRequest"
                ):
                    return (
                        jsonify(
                            {"status": "locked", "message": "Application verrouillée"}
                        ),
                        423,
                    )

                # Pour les requêtes normales, on pourrait rediriger
                # (mais dans notre cas PWA, on affiche surtout un overlay JS)
                # On marque juste la session comme verrouillée pour le frontend
                session["is_app_locked"] = True

        return f(*args, **kwargs)

    return decorated_function
