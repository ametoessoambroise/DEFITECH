"""
Décorateurs de sécurité pour l'assistant IA defAI
Fournit des permissions granulaires selon le rôle et les données demandées
"""

from functools import wraps
from flask import jsonify, request, g
from flask_login import current_user
import logging
from app.services.defai_permissions import normalize_role

logger = logging.getLogger(__name__)

ROLE_FR_TO_EN = {
    "etudiant": "student",
    "enseignant": "teacher",
    "admin": "admin",
}


def get_user_role():
    """Détermine le rôle de l'utilisateur actuel"""
    if getattr(g, "is_defai_request", False):
        fr_role = getattr(g, "defai_effective_role", "etudiant")
        return ROLE_FR_TO_EN.get(normalize_role(fr_role), "student")

    if hasattr(current_user, "role"):
        fr_role = normalize_role(current_user.role)
        return ROLE_FR_TO_EN.get(fr_role, current_user.role)
    return "unknown"


def role_required(*allowed_roles):
    """
    Décorateur qui vérifie si l'utilisateur a l'un des rôles autorisés

    Args:
        *allowed_roles: Liste des rôles autorisés ('student', 'teacher', 'admin')
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentification requise"}), 401

            user_role = get_user_role()
            if user_role not in allowed_roles:
                logger.warning(
                    f"Accès non autorisé: rôle {user_role} tente d'accéder à une ressource nécessitant {allowed_roles}"
                )
                return jsonify({"error": "Accès non autorisé"}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def student_required(f):
    """Décorateur qui exige le rôle étudiant"""
    return role_required("student")(f)


def teacher_required(f):
    """Décorateur qui exige le rôle enseignant"""
    return role_required("teacher")(f)


def admin_required(f):
    """Décorateur qui exige le rôle administrateur"""
    return role_required("admin")(f)


def teacher_or_admin_required(f):
    """Décorateur qui exige le rôle enseignant ou administrateur"""
    return role_required("teacher", "admin")(f)


def check_data_permission(data_type):
    """
    Décorateur qui vérifie si l'utilisateur peut accéder au type de données demandé

    Args:
        data_type (str): Type de données ('grades', 'schedule', 'assignments', 'classes', 'stats', 'health')
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentification requise"}), 401

            user_role = get_user_role()

            # Définir les permissions par rôle et type de données
            permissions = {
                "student": {
                    "grades": True,
                    "schedule": True,
                    "assignments": True,
                    "notifications": True,
                    "profile": True,
                    "classes": False,
                    "students": False,
                    "stats": False,
                    "health": False,
                    "system": False,
                },
                "teacher": {
                    "grades": True,  # Notes des classes enseignées
                    "schedule": True,  # Emploi du temps personnel
                    "assignments": True,  # Devoirs créés
                    "notifications": True,
                    "profile": True,
                    "classes": True,  # Classes enseignées
                    "students": True,  # Étudiants des classes enseignées
                    "stats": True,  # Statistiques des classes enseignées
                    "health": False,
                    "system": False,
                },
                "admin": {
                    "grades": True,  # Toutes les notes
                    "schedule": True,  # Tous les emplois du temps
                    "assignments": True,  # Tous les devoirs
                    "notifications": True,
                    "profile": True,
                    "classes": True,  # Toutes les classes
                    "students": True,  # Tous les étudiants
                    "stats": True,  # Statistiques globales
                    "health": True,  # Santé système
                    "system": True,  # Administration système
                },
            }

            # Vérifier les permissions
            if user_role not in permissions:
                logger.warning(f"Rôle non reconnu: {user_role}")
                return jsonify({"error": "Rôle utilisateur non reconnu"}), 403

            if not permissions[user_role].get(data_type, False):
                logger.warning(
                    f"Accès non autorisé: {user_role} tente d'accéder aux données de type {data_type}"
                )
                return (
                    jsonify(
                        {
                            "error": f"Accès aux données {data_type} non autorisé pour votre rôle"
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_ownership_or_permission(resource_type, resource_id_param="id"):
    """
    Décorateur qui vérifie si l'utilisateur est propriétaire de la ressource ou a la permission

    Args:
        resource_type (str): Type de ressource ('conversation', 'message', 'assignment')
        resource_id_param (str): Nom du paramètre contenant l'ID de la ressource
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentification requise"}), 401

            user_role = get_user_role()
            resource_id = kwargs.get(resource_id_param) or request.args.get(
                resource_id_param
            )

            if not resource_id:
                return jsonify({"error": "ID de ressource manquant"}), 400

            # Les administrateurs ont accès à tout
            if user_role == "admin":
                return f(*args, **kwargs)

            # Vérification selon le type de ressource
            if resource_type == "conversation":
                if not check_conversation_ownership(current_user.id, resource_id):
                    return (
                        jsonify({"error": "Accès non autorisé à cette conversation"}),
                        403,
                    )

            elif resource_type == "assignment":
                if user_role == "student":
                    if not check_assignment_student_access(
                        current_user.id, resource_id
                    ):
                        return jsonify({"error": "Accès non autorisé à ce devoir"}), 403
                elif user_role == "teacher":
                    if not check_assignment_teacher_access(
                        current_user.id, resource_id
                    ):
                        return jsonify({"error": "Accès non autorisé à ce devoir"}), 403

            elif resource_type == "class":
                if user_role == "student":
                    if not check_class_student_membership(current_user.id, resource_id):
                        return (
                            jsonify({"error": "Accès non autorisé à cette classe"}),
                            403,
                        )
                elif user_role == "teacher":
                    if not check_class_teacher_access(current_user.id, resource_id):
                        return (
                            jsonify({"error": "Accès non autorisé à cette classe"}),
                            403,
                        )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_conversation_ownership(user_id, conversation_id):
    """Vérifie si l'utilisateur est propriétaire de la conversation"""
    try:
        from app.extensions import db

        conn = db.session()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id FROM ai_conversations 
            WHERE id = %s
        """,
            (conversation_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result and result[0] == user_id
    except Exception as e:
        logger.error(f"Erreur vérification ownership conversation: {e}")
        return False


def check_assignment_student_access(student_id, assignment_id):
    """Vérifie si l'étudiant a accès à ce devoir"""
    try:
        from app.extensions import db

        conn = db.session()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM devoirs d
            JOIN classe_devoirs cd ON d.id = cd.devoir_id
            JOIN classes cl ON cd.classe_id = cl.id
            JOIN etudiants e ON cl.id = e.classe_id
            WHERE d.id = %s AND e.user_id = %s
        """,
            (assignment_id, student_id),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result and result[0] > 0
    except Exception as e:
        logger.error(f"Erreur vérification accès devoir étudiant: {e}")
        return False


def check_assignment_teacher_access(teacher_id, assignment_id):
    """Vérifie si l'enseignant a accès à ce devoir"""
    try:
        from app.extensions import db

        conn = db.session()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM devoirs 
            WHERE id = %s AND enseignant_id = %s
        """,
            (assignment_id, teacher_id),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result and result[0] > 0
    except Exception as e:
        logger.error(f"Erreur vérification accès devoir enseignant: {e}")
        return False


def check_class_student_membership(student_id, class_id):
    """Vérifie si l'étudiant est membre de cette classe"""
    try:
        from app.extensions import db

        conn = db.session()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM etudiants e
            JOIN classes cl ON e.classe_id = cl.id
            WHERE cl.id = %s AND e.user_id = %s
        """,
            (class_id, student_id),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result and result[0] > 0
    except Exception as e:
        logger.error(f"Erreur vérification appartenance classe étudiant: {e}")
        return False


def check_class_teacher_access(teacher_id, class_id):
    """Vérifie si l'enseignant a accès à cette classe"""
    try:
        from app.extensions import db

        conn = db.session()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM classe_enseignants 
            WHERE classe_id = %s AND enseignant_id = %s
        """,
            (class_id, teacher_id),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result and result[0] > 0
    except Exception as e:
        logger.error(f"Erreur vérification accès classe enseignant: {e}")
        return False


def rate_limit(max_requests=10, window_seconds=60):
    """
    Décorateur de limitation de débit pour les API

    Args:
        max_requests (int): Nombre maximum de requêtes autorisées
        window_seconds (int): Période de temps en secondes
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentification requise"}), 401

            # Pour l'instant, implémentation simple avec logging
            # Dans une version production, utiliser Redis ou une base de données
            user_id = current_user.id
            logger.info(f"Rate limit check: user {user_id}, endpoint {f.__name__}")

            # TODO: Implémenter un vrai système de rate limiting
            # Pour l'instant, on laisse passer

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_request_data(required_fields=None, optional_fields=None):
    """
    Décorateur qui valide les données de la requête

    Args:
        required_fields (list): Champs obligatoires
        optional_fields (list): Champs optionnels autorisés
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request

            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            errors = []

            # Vérifier les champs obligatoires
            if required_fields:
                for field in required_fields:
                    if field not in data or not data[field]:
                        errors.append(f"Champ obligatoire manquant: {field}")

            # Vérifier qu'il n'y a pas de champs non autorisés
            if optional_fields:
                allowed_fields = set(required_fields or []) | set(optional_fields)
                for field in data:
                    if field not in allowed_fields:
                        errors.append(f"Champ non autorisé: {field}")

            if errors:
                return jsonify({"error": "Données invalides", "details": errors}), 400

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def log_api_access():
    """Décorateur qui log l'accès aux API"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request

            user_id = current_user.id if current_user.is_authenticated else "anonymous"
            user_role = get_user_role()
            endpoint = request.endpoint
            method = request.method
            ip = request.remote_addr

            logger.info(
                f"API Access: {method} {endpoint} by user {user_id} (role: {user_role}) from {ip}"
            )

            return f(*args, **kwargs)

        return decorated_function

    return decorator
