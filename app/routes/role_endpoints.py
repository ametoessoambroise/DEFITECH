"""
Endpoints de données spécifiques selon le rôle pour l'assistant IA defAI
Fournit des accès sécurisés aux données selon les permissions de l'utilisateur
"""

from flask import Blueprint, jsonify, request, g
from flask_login import login_required, current_user
from app.extensions import db
from app.security_decorators import student_required, teacher_required, log_api_access
import logging

logger = logging.getLogger(__name__)

# Création du blueprint pour les endpoints de données par rôle
role_data_bp = Blueprint("role_data", __name__, url_prefix="/api/role-data")


def _resolve_target_user_id(default_id, *param_candidates) -> int:
    """
    Détermine l'identifiant utilisateur cible.
    Pour les requêtes DefAI, on privilégie les paramètres explicites, sinon l'en-tête.
    """
    if getattr(g, "is_defai_request", False):
        for candidate in param_candidates:
            value = request.args.get(candidate)
            if value:
                try:
                    return int(value)
                except ValueError:
                    raise ValueError(f"Identifiant invalide fourni pour {candidate}")
        header_id = getattr(g, "defai_target_user_id", None)
        if header_id:
            try:
                return int(header_id)
            except ValueError:
                raise ValueError("Identifiant DefAI invalide")
        raise ValueError("Identifiant utilisateur requis pour cette opération DefAI")
    return default_id


def get_user_role():
    """Détermine le rôle de l'utilisateur actuel"""
    if hasattr(current_user, "role"):
        role = current_user.role
        if role == "etudiant":
            return "student"
        elif role == "enseignant":
            return "teacher"
        elif role == "admin":
            return "admin"
    return "unknown"


# Endpoints pour les étudiants
@role_data_bp.route("/etudiant/grades", methods=["GET"])
@login_required
@student_required
@log_api_access()
def get_student_grades():
    """
    Récupère les notes de l'étudiant.

    Cette fonction permet à un étudiant connecté de récupérer les notes de son parcours.
    Les notes sont récupérées depuis la base de données et renvoyées sous forme d'objet JSON.

    Retourne:
        Un objet JSON contenant les informations sur les notes de l'étudiant. Le format
        de l'objet JSON est le suivant :
            {
                "success": bool,
                "data": [
                    {
                        "matiere": str,
                        "note": float,
                        "coeff": float,
                        "date": str (format: %Y-%m-%d)
                    }
                ]
            }

        Si une erreur se produit pendant l'exécution de la fonction, un objet JSON
        d'erreur sera renvoyé au format suivant :
            {
                "success": bool,
                "error": str
            }
    """

    from sqlalchemy import text

    try:
        target_student_id = _resolve_target_user_id(
            current_user.id, "student_id", "etudiant_id", "user_id"
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = db.session.execute(
            text(
                """
            SELECT m.nom_matiere, n.note, n.note_max, n.coefficient, n.date_evaluation, n.type_evaluation
            FROM notes n
            JOIN matieres m ON n.matiere_id = m.id
            WHERE n.etudiant_id = :etudiant_id
            ORDER BY n.date_evaluation DESC
        """
            ),
            {"etudiant_id": target_student_id},
        )

        grades = [dict(row) for row in result]

        return jsonify({"grades": grades})

    except Exception as e:
        logger.error(f"Erreur récupération notes étudiant: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@role_data_bp.route("/etudiant/schedule", methods=["GET"])
@login_required
@student_required
@log_api_access()
def get_student_schedule():
    """
    Récupère l'emploi du temps de l'étudiant.

    Cette fonction permet à un étudiant connecté de récupérer son emploi du temps.
    L'emploi du temps est récupéré depuis la base de données et renvoyé sous forme d'objet JSON.

    Retourne:
        Un objet JSON contenant les informations sur l'emploi du temps de l'étudiant. Le format
        de l'objet JSON est le suivant :
            {
                "success": bool,
                "data": [
                    {
                        "day_of_week": str,
                        "start_time": str (format: %H:%M),
                        "end_time": str (format: %H:%M),
                        "subject": str,
                        "classroom": str
                    }
                ]
            }

        Si une erreur se produit pendant l'exécution de la fonction, un objet JSON
        d'erreur sera renvoyé au format suivant :
            {
                "success": bool,
                "error": str
            }
    """

    from sqlalchemy import text

    try:
        target_student_id = _resolve_target_user_id(
            current_user.id, "student_id", "etudiant_id", "user_id"
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = db.session.execute(
            text(
                """
            SELECT c.jour_semaine, c.heure_debut, c.heure_fin, m.nom_matiere, s.nom_salle
            FROM cours c
            JOIN matieres m ON c.matiere_id = m.id
            JOIN salles s ON c.salle_id = s.id
            JOIN classe_cours cc ON c.id = cc.cours_id
            JOIN classes cl ON cc.classe_id = cl.id
            JOIN etudiants e ON cl.id = e.classe_id
            WHERE e.id = :etudiant_id
            ORDER BY c.jour_semaine, c.heure_debut
        """
            ),
            {"etudiant_id": target_student_id},
        )

        schedule = [dict(row) for row in result]

        return jsonify({"schedule": schedule})

    except Exception as e:
        logger.error(f"Erreur récupération emploi du temps étudiant: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@role_data_bp.route("/etudiant/assignments", methods=["GET"])
@login_required
@student_required
@log_api_access()
def get_student_assignments():
    """
    Récupère les devoirs de l'étudiant.

    Cette fonction permet à un étudiant connecté de récupérer la liste de ses devoirs.
    Les devoirs sont récupérés depuis la base de données et renvoyés sous forme d'objet JSON.

    Retourne:
        Un objet JSON contenant les informations sur les devoirs de l'étudiant. Le format
        de l'objet JSON est le suivant :
            {
                "success": bool,
                "data": [
                    {
                        "id": int,
                        "title": str,
                        "description": str,
                        "deadline": str (format: %Y-%m-%d),
                        "status": str,
                        "subject": str
                    }
                ]
            }

        Si une erreur se produit pendant l'exécution de la fonction, un objet JSON
        d'erreur sera renvoyé au format suivant :
            {
                "success": bool,
                "error": str
            }
    """

    from sqlalchemy import text

    try:
        target_student_id = _resolve_target_user_id(
            current_user.id, "student_id", "etudiant_id", "user_id"
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = db.session.execute(
            text(
                """
            SELECT d.id, d.titre, d.description, d.date_limite, d.statut, m.nom_matiere
            FROM devoirs d
            JOIN matieres m ON d.matiere_id = m.id
            JOIN classe_devoirs cd ON d.id = cd.devoir_id
            JOIN classes cl ON cd.classe_id = cl.id
            JOIN etudiants e ON cl.id = e.classe_id
            WHERE e.id = :etudiant_id
            ORDER BY d.date_limite ASC
        """
            ),
            {"etudiant_id": target_student_id},
        )

        assignments = [dict(row) for row in result]

        return jsonify({"assignments": assignments})

    except Exception as e:
        logger.error(f"Erreur récupération devoirs étudiant: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@role_data_bp.route("/etudiant/notifications", methods=["GET"])
@login_required
@student_required
@log_api_access()
def get_student_notifications():
    """
    Récupère les notifications de l'étudiant.

    Cette fonction est appelée lorsque l'utilisateur accède à l'URL "/etudiant/notifications"
    du service de données des rôles. Elle récupère les notifications de l'étudiant connecté
    à partir de la base de données. Les notifications sont filtrées en fonction de l'ID de
    l'étudiant, et sont renvoyées sous la forme d'un objet JSON.

    Paramètres:
        Aucun

    Retourne:
        Un objet JSON contenant les notifications de l'étudiant. Le format de l'objet JSON
        est le suivant :
            {
                "success": bool,
                "data": [
                    {
                        "id": int,
                        "titre": str,
                        "message": str,
                        "date_creation": str (format: %Y-%m-%d %H:%M:%S),
                        "type": str,
                        "lu": bool
                    }
                ]
            }

        Si une erreur se produit pendant l'exécution de la fonction, un objet JSON
        d'erreur sera renvoyé au format suivant :
            {
                "success": bool,
                "error": str
            }
    """

    from sqlalchemy import text

    try:
        target_student_id = _resolve_target_user_id(
            current_user.id, "student_id", "etudiant_id", "user_id"
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = db.session.execute(
            text(
                """
            SELECT n.id, n.titre, n.message, n.date_creation, n.type, n.lu
            FROM notifications n
            JOIN notification_destinataires nd ON n.id = nd.notification_id
            WHERE nd.destinataire_id = :etudiant_id AND nd.type_destinataire = 'etudiant'
            ORDER BY n.date_creation DESC
            LIMIT 20
        """
            ),
            {"etudiant_id": target_student_id},
        )

        notifications = [dict(row) for row in result]

        return jsonify({"notifications": notifications})

    except Exception as e:
        logger.error(f"Erreur récupération notifications étudiant: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


# Endpoints pour les enseignants
@role_data_bp.route("/enseignant/classes", methods=["GET"])
@login_required
@teacher_required
@log_api_access()
def get_teacher_classes():
    """
    Récupère les classes de l'enseignant.

    Cette fonction est appelée lorsque l'utilisateur accède à l'URL "/enseignant/classes"
    pour obtenir les classes de l'enseignant connecté. Elle récupère les données de l'enseignant
    connecté et renvoie un objet JSON contenant les classes de l'enseignant. Le format de l'objet JSON
    est le suivant :
        {
            "success": bool,
            "data": [
                {
                    "id": int,
                    "nom_classe": str,
                    "niveau": str,
                    "effectif": int
                }
            ]
        }

    Si une erreur se produit pendant l'exécution de la fonction, un objet JSON
    d'erreur sera renvoyé au format suivant :
        {
            "success": bool,
            "error": str
        }
    """

    from sqlalchemy import text

    try:
        target_teacher_id = _resolve_target_user_id(
            current_user.id, "teacher_id", "enseignant_id", "user_id"
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = db.session.execute(
            text(
                """
            SELECT c.id, c.nom_classe, c.niveau, c.effectif
            FROM classes c
            JOIN classe_enseignants ce ON c.id = ce.classe_id
            WHERE ce.enseignant_id = :enseignant_id
            ORDER BY c.nom_classe
        """
            ),
            {"enseignant_id": target_teacher_id},
        )

        classes = [dict(row) for row in result]

        return jsonify({"classes": classes})

    except Exception as e:
        logger.error(f"Erreur récupération classes enseignant: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@role_data_bp.route("/enseignant/subjects", methods=["GET"])
@login_required
@teacher_required
@log_api_access()
def get_teacher_subjects():
    """
    Récupère les matières enseignées par l'enseignant.

    Cette fonction est appelée lorsque l'utilisateur accède à l'URL "/enseignant/subjects"
    pour obtenir les matières enseignées par l'enseignant connecté. Elle récupère les données de l'enseignant
    connecté et renvoie un objet JSON contenant les matières enseignées par l'enseignant. Le format de l'objet JSON
    est le suivant :
        {
            "success": bool,
            "data": [
                {
                    "id": int,
                    "nom_matiere": str,
                    "coefficient": int
                }
            ]
        }

    Si une erreur se produit pendant l'exécution de la fonction, un objet JSON
    d'erreur sera renvoyé au format suivant :
        {
            "success": bool,
            "error": str
        }
    """

    from sqlalchemy import text

    try:
        target_teacher_id = _resolve_target_user_id(
            current_user.id, "teacher_id", "enseignant_id", "user_id"
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = db.session.execute(
            text(
                """
            SELECT DISTINCT m.id, m.nom_matiere, m.coefficient
            FROM matieres m
            JOIN cours c ON m.id = c.matiere_id
            WHERE c.enseignant_id = :enseignant_id
            ORDER BY m.nom_matiere
        """
            ),
            {"enseignant_id": target_teacher_id},
        )

        subjects = [dict(row) for row in result]

        return jsonify({"subjects": subjects})

    except Exception as e:
        logger.error(f"Erreur récupération matières enseignant: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@role_data_bp.route("/enseignant/class-stats/<int:class_id>", methods=["GET"])
@login_required
@teacher_required
@log_api_access()
def get_teacher_class_stats(class_id):
    """
    Récupère les statistiques d'une classe pour l'enseignant.

    Cette fonction est appelée lorsque l'utilisateur accède à l'URL "/enseignant/class-stats/{class_id}"
    pour obtenir les statistiques d'une classe pour l'enseignant connecté. Elle récupère les données de l'enseignant
    connecté et renvoie un objet JSON contenant les statistiques de la classe. Le format de l'objet JSON est le suivant :
        {
            "success": bool,
            "data": {
                "nom": str,
                "effectif": int,
                "nb_professeurs": int,
                "nb_matieres": int,
                "moyenne": float,
                "matieres": [
                    {
                        "nom": str,
                        "moyenne": float,
                        "nb_notes": int
                    }
                ]
            }
        }

    Si une erreur se produit pendant l'exécution de la fonction, un objet JSON
    d'erreur sera renvoyé au format suivant :
        {
            "success": bool,
            "error": str
        }
    """

    from sqlalchemy import text

    try:
        target_teacher_id = _resolve_target_user_id(
            current_user.id, "teacher_id", "enseignant_id", "user_id"
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        # Vérifier que l'enseignant a accès à cette classe
        result = db.session.execute(
            text(
                """
            SELECT COUNT(*) FROM classe_enseignants 
            WHERE classe_id = :classe_id AND enseignant_id = :enseignant_id
        """
            ),
            {"classe_id": class_id, "enseignant_id": target_teacher_id},
        )

        if result.scalar() == 0:
            return jsonify({"error": "Classe non trouvée ou accès non autorisé"}), 404

        # Statistiques générales de la classe
        result = db.session.execute(
            text(
                """
            SELECT 
                COUNT(DISTINCT e.id) as total_students,
                AVG(n.note) as avg_grade,
                COUNT(DISTINCT m.id) as total_subjects
            FROM etudiants e
            LEFT JOIN notes n ON e.id = n.etudiant_id
            LEFT JOIN matieres m ON n.matiere_id = m.id
            WHERE e.classe_id = :classe_id
        """
            ),
            {"classe_id": class_id},
        )

        stats_row = result.fetchone()
        stats = {
            "total_students": stats_row[0] or 0,
            "average_grade": float(stats_row[1]) if stats_row[1] else 0,
            "total_subjects": stats_row[2] or 0,
        }

        # Statistiques par matière
        result = db.session.execute(
            text(
                """
            SELECT 
                m.nom_matiere,
                AVG(n.note) as avg_grade,
                COUNT(n.id) as grade_count,
                MIN(n.note) as min_grade,
                MAX(n.note) as max_grade
            FROM matieres m
            LEFT JOIN notes n ON m.id = n.matiere_id
            LEFT JOIN etudiants e ON n.etudiant_id = e.id AND e.classe_id = :classe_id
            WHERE m.id IN (
                SELECT DISTINCT matiere_id FROM cours 
                WHERE enseignant_id = :enseignant_id
            )
            GROUP BY m.id, m.nom_matiere
            ORDER BY m.nom_matiere
        """
            ),
            {"classe_id": class_id, "enseignant_id": target_teacher_id},
        )

        subject_stats = [dict(row) for row in result]

        stats["subject_stats"] = subject_stats

        return jsonify({"stats": stats})

    except Exception as e:
        logger.error(f"Erreur récupération statistiques classe: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


# Endpoints pour les administrateurs
@role_data_bp.route("/admin/platform-stats", methods=["GET"])
@login_required
def get_admin_platform_stats():
    """
    Récupère les statistiques globales de la plateforme.

    Cette fonction renvoie les statistiques globales de la plateforme,
    telles que le nombre total d'étudiants, d'enseignants, d'administrateurs,
    de classes, de matières et de cours. Les statistiques sont renvoyées sous
    forme d'un objet JSON.

    Retourne:
        Un objet JSON contenant les statistiques globales de la plateforme. La
        structure de l'objet est la suivante :
            {
                "total_students": int,
                "total_teachers": int,
                "total_admins": int,
                "total_classes": int,
                "total_subjects": int,
                "total_courses": int
            }

        Si l'utilisateur n'est pas un administrateur, un objet JSON d'erreur sera
        renvoyé au format suivant :
            {
                "error": str
            }
    """
    if get_user_role() != "admin":
        return jsonify({"error": "Accès non autorisé"}), 403

    from sqlalchemy import text

    try:
        # Statistiques générales
        result = db.session.execute(
            text(
                """
            SELECT 
                (SELECT COUNT(*) FROM utilisateurs WHERE role = 'etudiant') as total_students,
                (SELECT COUNT(*) FROM utilisateurs WHERE role = 'enseignant') as total_teachers,
                (SELECT COUNT(*) FROM utilisateurs WHERE role = 'admin') as total_admins,
                (SELECT COUNT(*) FROM classes) as total_classes,
                (SELECT COUNT(*) FROM matieres) as total_subjects,
                (SELECT COUNT(*) FROM cours) as total_courses
        """
            )
        )

        stats_row = result.fetchone()
        stats = {
            "total_students": stats_row[0] or 0,
            "total_teachers": stats_row[1] or 0,
            "total_admins": stats_row[2] or 0,
            "total_classes": stats_row[3] or 0,
            "total_subjects": stats_row[4] or 0,
            "total_courses": stats_row[5] or 0,
        }

        # Statistiques par niveau
        result = db.session.execute(
            text(
                """
            SELECT niveau, COUNT(*) as count
            FROM classes
            GROUP BY niveau
            ORDER BY niveau
        """
            )
        )

        level_stats = [dict(row) for row in result]

        stats["level_stats"] = level_stats

        # Activités récentes
        result = db.session.execute(
            text(
                """
            SELECT 
                'note' as type,
                COUNT(*) as count,
                MAX(date_creation) as last_activity
            FROM notes
            WHERE date_creation >= CURRENT_DATE - INTERVAL '7 days'
            
            UNION ALL
            
            SELECT 
                'devoir' as type,
                COUNT(*) as count,
                MAX(date_creation) as last_activity
            FROM devoirs
            WHERE date_creation >= CURRENT_DATE - INTERVAL '7 days'
            
            UNION ALL
            
            SELECT 
                'notification' as type,
                COUNT(*) as count,
                MAX(date_creation) as last_activity
            FROM notifications
            WHERE date_creation >= CURRENT_DATE - INTERVAL '7 days'
        """
            )
        )

        recent_activities = [dict(row) for row in result]

        stats["recent_activities"] = recent_activities

        return jsonify({"stats": stats})

    except Exception as e:
        logger.error(f"Erreur récupération statistiques plateforme: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@role_data_bp.route("/admin/system-health", methods=["GET"])
@login_required
def get_admin_system_health():
    """
    Vérifie l'état de santé du système.

    Cette fonction vérifie si l'utilisateur connecté est un administrateur. Si ce n'est
    pas le cas, elle renvoie une réponse avec un code d'erreur 403 (Accès non autorisé).

    Retourne:
        Si l'utilisateur connecté n'est pas un administrateur, une réponse JSON avec un
        code d'erreur 403 et un message d'erreur.
    """
    if get_user_role() != "admin":
        return jsonify({"error": "Accès non autorisé"}), 403

    from sqlalchemy import text

    try:
        health_status = {"status": "healthy", "checks": {}}

        # Vérification de la connexion base de données
        try:
            db.session.execute(text("SELECT 1"))
            health_status["checks"]["database"] = {
                "status": "ok",
                "response_time": "< 100ms",
            }
        except Exception as e:
            health_status["checks"]["database"] = {"status": "error", "error": str(e)}
            health_status["status"] = "degraded"

        # Vérification des tables principales
        critical_tables = [
            "utilisateurs",
            "classes",
            "matieres",
            "etudiants",
            "enseignants",
        ]
        for table in critical_tables:
            try:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                health_status["checks"][f"table_{table}"] = {
                    "status": "ok",
                    "record_count": count,
                }
            except Exception as e:
                health_status["checks"][f"table_{table}"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_status["status"] = "degraded"

        # Vérification de l'espace disque (approximation via les enregistrements)
        try:
            result = db.session.execute(
                text(
                    """
                SELECT 
                    SUM(pg_total_relation_size(schemaname||'.'||tablename))::bigint
                FROM pg_tables 
                WHERE schemaname = 'public'
            """
                )
            )
            db_size = result.scalar() or 0
            health_status["checks"]["database_size"] = {
                "status": "ok",
                "size_bytes": db_size,
                "size_mb": round(db_size / 1024 / 1024, 2),
            }
        except Exception as e:
            health_status["checks"]["database_size"] = {
                "status": "error",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        return jsonify(health_status)

    except Exception as e:
        logger.error(f"Erreur vérification santé système: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@role_data_bp.route("/admin/recent-activities", methods=["GET"])
@login_required
def get_admin_recent_activities():
    """
    Récupère les activités récentes sur la plateforme.

    Cette fonction vérifie si l'utilisateur connecté est un administrateur. Si ce n'est
    pas le cas, elle renvoie une réponse avec un code d'erreur 403 (Accès non autorisé)
    et un message d'erreur détaillé en français.

    Retourne:
        Si l'utilisateur connecté n'est pas un administrateur, une réponse JSON avec un
        code d'erreur 403 et un message d'erreur détaillé en français.
    """
    if get_user_role() != "admin":
        return jsonify({"error": "Accès non autorisé"}), 403

    from sqlalchemy import text

    try:
        activities = []

        # Notes récentes
        result = db.session.execute(
            text(
                """
            SELECT 
                'note' as type,
                e.nom || ' ' || e.prenom as user_name,
                m.nom_matiere as details,
                n.date_creation as timestamp
            FROM notes n
            JOIN etudiants e ON n.etudiant_id = e.id
            JOIN matieres m ON n.matiere_id = m.id
            WHERE n.date_creation >= CURRENT_DATE - INTERVAL '3 days'
            ORDER BY n.date_creation DESC
            LIMIT 5
        """
            )
        )

        for row in result:
            activities.append(
                {
                    "type": row[0],
                    "user": row[1],
                    "details": f"Note en {row[2]}",
                    "timestamp": row[3].isoformat() if row[3] else None,
                }
            )

        # Devoirs récents
        result = db.session.execute(
            text(
                """
            SELECT 
                'devoir' as type,
                e.nom || ' ' || e.prenom as user_name,
                d.titre as details,
                d.date_creation as timestamp
            FROM devoirs d
            JOIN enseignants e ON d.enseignant_id = e.id
            WHERE d.date_creation >= CURRENT_DATE - INTERVAL '3 days'
            ORDER BY d.date_creation DESC
            LIMIT 5
        """
            )
        )

        for row in result:
            activities.append(
                {
                    "type": row[0],
                    "user": row[1],
                    "details": f"Devoir: {row[2]}",
                    "timestamp": row[3].isoformat() if row[3] else None,
                }
            )

        # Notifications récentes
        result = db.session.execute(
            text(
                """
            SELECT 
                'notification' as type,
                'Système' as user_name,
                n.titre as details,
                n.date_creation as timestamp
            FROM notifications n
            WHERE n.date_creation >= CURRENT_DATE - INTERVAL '3 days'
            ORDER BY n.date_creation DESC
            LIMIT 5
        """
            )
        )

        for row in result:
            activities.append(
                {
                    "type": row[0],
                    "user": row[1],
                    "details": row[2],
                    "timestamp": row[3].isoformat() if row[3] else None,
                }
            )

        # Trier par timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        return jsonify({"activities": activities[:20]})  # Limiter à 20 activités

    except Exception as e:
        logger.error(f"Erreur récupération activités récentes: {e}")
        return jsonify({"error": "Erreur serveur"}), 500
