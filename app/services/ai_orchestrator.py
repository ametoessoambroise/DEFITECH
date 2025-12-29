"""
Module orchestrateur pour l'assistant IA defAI
Gère les requêtes internes et la collecte de données selon le rôle utilisateur
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from app.extensions import db
from app.services.defai_client import get_defai_client
from app.models.note import Note
from app.models.matiere import Matiere
from app.models.user import User
from app.services.defai_sql_executor import execute_sql_readonly, ALLOWED_TABLES_BY_ROLE

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Orchestrateur pour les requêtes internes de l'IA"""

    def __init__(self):
        # Initialiser le client DefAI pour les requêtes internes
        self.defai_client = get_defai_client()

        # Liste blanche des requêtes autorisées par rôle
        self.allowed_requests = {
            "etudiant": [
                "discover_routes",  # Nouvelle fonctionnalité
                "discover_available_requests",
                "get_student_grades",
                "get_student_averages",
                "get_student_schedule",
                "get_student_notifications",
                "get_student_weak_subjects",
                "get_student_progression",
                "get_student_assignments",
                "get_student_attendance",
                "get_subject_performance",
                "get_grade_trends",
                "get_class_comparison",
                "get_missing_assignments",
                "get_academic_info",
                "get_all_users",
            ],
            "enseignant": [
                "discover_routes",  # Nouvelle fonctionnalité
                "discover_available_requests",
                "get_teacher_classes",
                "get_class_grades",
                "get_class_statistics",
                "get_student_performance",
                "get_teacher_assignments",
                "get_teacher_notifications",
                "get_subject_statistics",
                "get_best_students",
                "get_struggling_students",
                "get_student_detailed_grades",
                "get_student_attendance_detail",
                "get_class_progression",
                "get_all_users",
            ],
            "admin": [
                "discover_routes",  # Nouvelle fonctionnalité
                "discover_available_requests",
                "get_platform_statistics",
                "get_user_statistics",
                "get_recent_activities",
                "get_system_notifications",
                "get_enrollment_stats",
                "get_course_statistics",
                "get_performance_metrics",
                "get_usage_analytics",
                "get_all_users",
                "get_all_student_grades",
                "get_all_students",
                "get_all_teachers",
                "get_all_admins",
                "get_users_by_role",
                "get_student_grades",
                "get_student_averages",
                "get_student_schedule",
                "get_student_notifications",
                "get_student_weak_subjects",
                "get_student_progression",
                "get_student_assignments",
                "get_student_attendance",
                "get_teacher_classes",
                "get_class_grades",
                "get_class_statistics",
                "get_student_performance",
                "get_teacher_assignments",
                "get_teacher_notifications",
                "get_subject_statistics",
                "get_best_students",
                "get_struggling_students",
            ],
        }

    def _execute_get_all_users(self, admin_id):
        """Récupère la liste complète de tous les utilisateurs (admin only)"""
        try:
            # Récupérer tous les utilisateurs avec leurs informations
            users_result = db.session.execute(
                text(
                    """
                    SELECT 
                        u.id,
                        u.nom,
                        u.prenom,
                        u.email,
                        u.role,
                        u.sexe,
                        u.telephone,
                        u.date_creation,
                        u.date_naissance,
                        CASE 
                            WHEN u.role = 'etudiant' THEN e.filiere
                            WHEN u.role = 'enseignant' THEN NULL
                            ELSE NULL
                        END as filiere_nom,
                        CASE 
                            WHEN u.role = 'etudiant' THEN e.annee
                            ELSE NULL
                        END as annee
                    FROM users u
                    LEFT JOIN etudiant e ON u.id = e.user_id AND u.role = 'etudiant'
                    LEFT JOIN enseignant ens ON u.id = ens.user_id AND u.role = 'enseignant'
                    ORDER BY u.date_creation DESC
                """
                )
            ).fetchall()

            users_list = []
            stats = {
                "total": 0,
                "etudiants": 0,
                "enseignants": 0,
                "admins": 0,
                "par_filiere": {},
            }

            for row in users_result:
                user_data = {
                    "id": row[0],
                    "nom": row[1],
                    "prenom": row[2],
                    "email": row[3],
                    "role": row[4],
                    "sexe": row[5],
                    "telephone": row[6],
                    "date_creation": row[7].isoformat() if row[7] else None,
                    "date_naissance": row[8].isoformat() if row[8] else None,
                    "filiere_nom": row[9],
                    "annee": row[10],
                }
                users_list.append(user_data)

                # Calculer les statistiques
                stats["total"] += 1
                if row[4] == "etudiant":
                    stats["etudiants"] += 1
                    if row[9]:  # Si filière existe
                        stats["par_filiere"][row[9]] = (
                            stats["par_filiere"].get(row[9], 0) + 1
                        )
                elif row[4] == "enseignant":
                    stats["enseignants"] += 1
                elif row[4] == "admin":
                    stats["admins"] += 1

            return {
                "success": True,
                "data": {
                    "users": users_list,
                    "statistics": stats,
                    "total_count": len(users_list),
                },
            }

        except Exception as e:
            logger.error(f"Erreur récupération liste utilisateurs: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_all_students(self, admin_id):
        """Récupère la liste complète de tous les étudiants (admin only)"""
        try:
            # Récupérer uniquement les étudiants avec leurs informations
            students_result = db.session.execute(
                text(
                    """
                    SELECT 
                        u.id,
                        u.nom,
                        u.prenom,
                        u.email,
                        u.sexe,
                        u.telephone,
                        u.date_creation,
                        u.date_naissance,
                        e.filiere,
                        e.annee
                    FROM users u
                    INNER JOIN etudiant e ON u.id = e.user_id
                    WHERE u.role = 'etudiant'
                    ORDER BY e.filiere, e.annee, u.nom
                """
                )
            ).fetchall()

            students_list = []
            stats = {"total": 0, "par_filiere": {}, "par_annee": {}}

            for row in students_result:
                student_data = {
                    "id": row[0],
                    "nom": row[1],
                    "prenom": row[2],
                    "email": row[3],
                    "sexe": row[4],
                    "telephone": row[5],
                    "date_creation": row[6].isoformat() if row[6] else None,
                    "date_naissance": row[7].isoformat() if row[7] else None,
                    "filiere": row[8],
                    "annee": row[9],
                }
                students_list.append(student_data)

                # Calculer les statistiques
                stats["total"] += 1
                if row[8]:  # Si filière existe
                    stats["par_filiere"][row[8]] = (
                        stats["par_filiere"].get(row[8], 0) + 1
                    )
                if row[9]:  # Si année existe
                    stats["par_annee"][row[9]] = stats["par_annee"].get(row[9], 0) + 1

            return {
                "success": True,
                "data": {
                    "students": students_list,
                    "statistics": stats,
                    "total_count": len(students_list),
                },
            }

        except Exception as e:
            logger.error(f"Erreur récupération liste étudiants: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_all_teachers(self, admin_id):
        """Récupère la liste complète de tous les enseignants (admin only)"""
        try:
            # Récupérer uniquement les enseignants avec leurs informations
            teachers_result = db.session.execute(
                text(
                    """
                    SELECT 
                        u.id,
                        u.nom,
                        u.prenom,
                        u.email,
                        u.sexe,
                        u.telephone,
                        u.date_creation,
                        u.date_naissance,
                        ens.specialite,
                        ens.departement
                    FROM users u
                    INNER JOIN enseignant ens ON u.id = ens.user_id
                    WHERE u.role = 'enseignant'
                    ORDER BY u.nom, u.prenom
                """
                )
            ).fetchall()

            teachers_list = []
            stats = {"total": 0, "par_specialite": {}, "par_departement": {}}

            for row in teachers_result:
                teacher_data = {
                    "id": row[0],
                    "nom": row[1],
                    "prenom": row[2],
                    "email": row[3],
                    "sexe": row[4],
                    "telephone": row[5],
                    "date_creation": row[6].isoformat() if row[6] else None,
                    "date_naissance": row[7].isoformat() if row[7] else None,
                    "specialite": row[8],
                    "departement": row[9],
                }
                teachers_list.append(teacher_data)

                # Calculer les statistiques
                stats["total"] += 1
                if row[8]:  # Si spécialité existe
                    stats["par_specialite"][row[8]] = (
                        stats["par_specialite"].get(row[8], 0) + 1
                    )
                if row[9]:  # Si département existe
                    stats["par_departement"][row[9]] = (
                        stats["par_departement"].get(row[9], 0) + 1
                    )

            return {
                "success": True,
                "data": {
                    "teachers": teachers_list,
                    "statistics": stats,
                    "total_count": len(teachers_list),
                },
            }

        except Exception as e:
            logger.error(f"Erreur récupération liste enseignants: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_all_admins(self, admin_id):
        """Récupère la liste complète de tous les administrateurs (admin only)"""
        try:
            # Récupérer uniquement les administrateurs
            admins_result = db.session.execute(
                text(
                    """
                    SELECT 
                        u.id,
                        u.nom,
                        u.prenom,
                        u.email,
                        u.sexe,
                        u.telephone,
                        u.date_creation,
                        u.date_naissance
                    FROM users u
                    WHERE u.role = 'admin'
                    ORDER BY u.date_creation DESC, u.nom
                """
                )
            ).fetchall()

            admins_list = []
            stats = {"total": 0, "creation_dates": {}}

            for row in admins_result:
                admin_data = {
                    "id": row[0],
                    "nom": row[1],
                    "prenom": row[2],
                    "email": row[3],
                    "sexe": row[4],
                    "telephone": row[5],
                    "date_creation": row[6].isoformat() if row[6] else None,
                    "date_naissance": row[7].isoformat() if row[7] else None,
                }
                admins_list.append(admin_data)

                # Calculer les statistiques
                stats["total"] += 1
                if row[6]:  # Si date de création existe
                    creation_year = row[6].year
                    stats["creation_dates"][str(creation_year)] = (
                        stats["creation_dates"].get(str(creation_year), 0) + 1
                    )

            return {
                "success": True,
                "data": {
                    "admins": admins_list,
                    "statistics": stats,
                    "total_count": len(admins_list),
                },
            }

        except Exception as e:
            logger.error(f"Erreur récupération liste administrateurs: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_all_student_grades(self, admin_id):
        """Récupère toutes les notes de tous les étudiants"""
        try:
            from sqlalchemy import text

            result = db.session.execute(
                text(
                    """
                    SELECT
                        e.id AS etudiant_id,
                        u.nom AS nom_etudiant,
                        u.prenom AS prenom_etudiant,
                        u.email AS email_etudiant,
                        e.filiere AS filiere,
                        e.annee AS annee,
                        m.nom AS nom_matiere,
                        n.note,
                        n.date_evaluation,
                        n.type_evaluation
                    FROM note n
                    JOIN etudiant e ON n.etudiant_id = e.id
                    JOIN users u ON e.user_id = u.id
                    LEFT JOIN matiere m ON n.matiere_id = m.id
                    ORDER BY u.nom, u.prenom, m.nom, n.date_evaluation DESC
                """
                )
            )

            grades_data = []
            appreciation_counts = {}
            notes_values = []

            for row in result:
                row_mapping = row._mapping if hasattr(row, "_mapping") else row
                grade = dict(row_mapping)

                note_value = grade.get("note")
                if note_value is not None:
                    note_float = float(note_value)
                    grade["note"] = note_float
                    notes_values.append(note_float)

                    if note_float >= 14:
                        appreciation = "Bien"
                    elif note_float >= 10:
                        appreciation = "Passable"
                    else:
                        appreciation = "Insuffisant"
                else:
                    appreciation = "Non évalué"

                grade["appreciation"] = appreciation
                appreciation_counts[appreciation] = (
                    appreciation_counts.get(appreciation, 0) + 1
                )

                if grade.get("date_evaluation"):
                    grade["date_evaluation"] = grade["date_evaluation"].isoformat()

                grades_data.append(grade)

            stats = {
                "total_notes": len(grades_data),
                "nombre_etudiants_avec_notes": len(
                    {g["etudiant_id"] for g in grades_data}
                ),
                "nombre_matieres": len(
                    {g["nom_matiere"] for g in grades_data if g.get("nom_matiere")}
                ),
                "repartition_appreciation": appreciation_counts,
            }

            if notes_values:
                moyenne_generale = sum(notes_values) / len(notes_values)
                stats["moyenne_generale"] = round(moyenne_generale, 2)

            logger.info(
                "Admin %s a récupéré %s notes via get_all_student_grades",
                admin_id,
                stats["total_notes"],
            )

            return {
                "success": True,
                "data": grades_data,
                "stats": stats,
            }

        except Exception as e:
            logger.error(f"Erreur récupération toutes les notes étudiants: {e}")
            return {
                "success": False,
                "error": f"Erreur lors de la récupération des notes: {str(e)}",
            }

    def _execute_get_users_by_role(self, admin_id, role_filter=None):
        """Récupère la liste des utilisateurs par rôle spécifique (admin only)"""
        try:
            # Si aucun filtre explicite, retourner tous les utilisateurs
            if not role_filter:
                logger.info(
                    "get_users_by_role sans filtre explicite, récupération complète"
                )
                return self._execute_get_all_users(admin_id)

            # Valider que le rôle est valide
            valid_roles = ["etudiant", "enseignant", "admin"]
            if role_filter not in valid_roles:
                return {
                    "success": False,
                    "error": f"Rôle invalide. Rôles valides: {', '.join(valid_roles)}",
                }

            # Construire la requête selon le rôle
            if role_filter == "etudiant":
                query_result = db.session.execute(
                    text(
                        """
                        SELECT 
                            u.id,
                            u.nom,
                            u.prenom,
                            u.email,
                            u.sexe,
                            u.telephone,
                            u.date_creation,
                            u.date_naissance,
                            e.filiere,
                            e.annee
                        FROM users u
                        INNER JOIN etudiant e ON u.id = e.user_id
                        WHERE u.role = 'etudiant'
                        ORDER BY e.filiere, e.annee, u.nom
                    """
                    )
                ).fetchall()

                users_list = []
                stats = {"total": 0, "par_filiere": {}, "par_annee": {}}

                for row in query_result:
                    user_data = {
                        "id": row[0],
                        "nom": row[1],
                        "prenom": row[2],
                        "email": row[3],
                        "sexe": row[4],
                        "telephone": row[5],
                        "date_creation": row[6].isoformat() if row[6] else None,
                        "date_naissance": row[7].isoformat() if row[7] else None,
                        "filiere": row[8],
                        "annee": row[9],
                    }
                    users_list.append(user_data)
                    stats["total"] += 1
                    if row[8]:
                        stats["par_filiere"][row[8]] = (
                            stats["par_filiere"].get(row[8], 0) + 1
                        )
                    if row[9]:
                        stats["par_annee"][row[9]] = (
                            stats["par_annee"].get(row[9], 0) + 1
                        )

                return {
                    "success": True,
                    "data": {
                        "users": users_list,
                        "statistics": stats,
                        "total_count": len(users_list),
                        "role": role_filter,
                    },
                }

            elif role_filter == "enseignant":
                query_result = db.session.execute(
                    text(
                        """
                        SELECT 
                            u.id,
                            u.nom,
                            u.prenom,
                            u.email,
                            u.sexe,
                            u.telephone,
                            u.date_creation,
                            u.date_naissance,
                            ens.specialite,
                            ens.departement
                        FROM users u
                        INNER JOIN enseignant ens ON u.id = ens.user_id
                        WHERE u.role = 'enseignant'
                        ORDER BY u.nom, u.prenom
                    """
                    )
                ).fetchall()

                users_list = []
                stats = {"total": 0, "par_specialite": {}, "par_departement": {}}

                for row in query_result:
                    user_data = {
                        "id": row[0],
                        "nom": row[1],
                        "prenom": row[2],
                        "email": row[3],
                        "sexe": row[4],
                        "telephone": row[5],
                        "date_creation": row[6].isoformat() if row[6] else None,
                        "date_naissance": row[7].isoformat() if row[7] else None,
                        "specialite": row[8],
                        "departement": row[9],
                    }
                    users_list.append(user_data)
                    stats["total"] += 1
                    if row[8]:
                        stats["par_specialite"][row[8]] = (
                            stats["par_specialite"].get(row[8], 0) + 1
                        )
                    if row[9]:
                        stats["par_departement"][row[9]] = (
                            stats["par_departement"].get(row[9], 0) + 1
                        )

                return {
                    "success": True,
                    "data": {
                        "users": users_list,
                        "statistics": stats,
                        "total_count": len(users_list),
                        "role": role_filter,
                    },
                }

            elif role_filter == "admin":
                query_result = db.session.execute(
                    text(
                        """
                        SELECT 
                            u.id,
                            u.nom,
                            u.prenom,
                            u.email,
                            u.sexe,
                            u.telephone,
                            u.date_creation,
                            u.date_naissance
                        FROM users u
                        WHERE u.role = 'admin'
                        ORDER BY u.date_creation DESC, u.nom
                    """
                    )
                ).fetchall()

                users_list = []
                stats = {"total": 0, "creation_dates": {}}

                for row in query_result:
                    user_data = {
                        "id": row[0],
                        "nom": row[1],
                        "prenom": row[2],
                        "email": row[3],
                        "sexe": row[4],
                        "telephone": row[5],
                        "date_creation": row[6].isoformat() if row[6] else None,
                        "date_naissance": row[7].isoformat() if row[7] else None,
                    }
                    users_list.append(user_data)
                    stats["total"] += 1
                    if row[6]:
                        creation_year = row[6].year
                        stats["creation_dates"][str(creation_year)] = (
                            stats["creation_dates"].get(str(creation_year), 0) + 1
                        )

                return {
                    "success": True,
                    "data": {
                        "users": users_list,
                        "statistics": stats,
                        "total_count": len(users_list),
                        "role": role_filter,
                    },
                }

        except Exception as e:
            logger.error(
                f"Erreur récupération utilisateurs par rôle {role_filter}: {e}"
            )
            return {"success": False, "error": str(e)}

    def _execute_with_defai_client(self, query: str, user_id: int, user_role: str):
        """Exécute la requête en utilisant le client DefAI"""
        try:
            # Mapper les requêtes vers les endpoints DefAI
            endpoint_mapping = {
                "get_student_grades": {
                    "method": "GET",
                    "path": "/api/role-data/etudiant/grades",
                    "role": "etudiant",
                    "query_param": "student_id",
                },
                "get_student_schedule": {
                    "method": "GET",
                    "path": "/api/role-data/etudiant/schedule",
                    "role": "etudiant",
                    "query_param": "student_id",
                },
                "get_student_notifications": {
                    "method": "GET",
                    "path": "/api/role-data/etudiant/notifications",
                    "role": "etudiant",
                    "query_param": "student_id",
                },
                "get_teacher_classes": {
                    "method": "GET",
                    "path": "/api/role-data/enseignant/classes",
                    "role": "enseignant",
                    "query_param": "teacher_id",
                },
                "get_platform_stats": {
                    "method": "GET",
                    "path": "/api/role-data/admin/platform-stats",
                    "role": "admin",
                },
                "get_all_users": {
                    "method": "GET",
                    "path": "/api/users",
                    "role": "admin",
                },
                "get_user_info": {
                    "method": "GET",
                    "path": f"/api/users/{user_id}",
                    "role": "admin",
                },
            }

            selected_config = None
            for key, config in endpoint_mapping.items():
                if key.lower() in query.lower():
                    selected_config = config
                    break

            if not selected_config:
                raise ValueError(
                    f"Aucun endpoint DefAI trouvé pour la requête: {query}"
                )

            method = selected_config.get("method", "GET").upper()
            path = selected_config["path"]
            target_role = selected_config.get("role", user_role)
            query_param = selected_config.get("query_param")

            if query_param and user_id is not None:
                endpoint = f"{path}?{query_param}={user_id}"
            else:
                endpoint = path

            # Exécuter la requête via le client DefAI
            if method == "GET":
                result = self.defai_client.get_json(
                    endpoint,
                    user_role=target_role,
                    user_id=user_id,
                )
            elif method == "POST":
                result = self.defai_client.post_json(
                    endpoint,
                    {"query": query},
                    user_role=target_role,
                    user_id=user_id,
                )
            else:
                result = self.defai_client.get_json(
                    endpoint,
                    user_role=target_role,
                    user_id=user_id,
                )

            return {
                "success": True,
                "data": result,
                "method": "defai_client",
                "endpoint": endpoint,
            }

        except Exception as e:
            logger.error(f"Erreur client DefAI: {e}")
            raise e

    def get_user_context(self, user_id, user_role):
        # Normaliser le rôle en français pour la logique interne
        role_map = {"student": "etudiant", "teacher": "enseignant", "admin": "admin"}
        user_role_fr = role_map.get(user_role, user_role)
        """Récupère le contexte complet d'un utilisateur selon son rôle"""
        try:
            context = {
                "user_id": user_id,
                "role": user_role,
                "timestamp": datetime.now().isoformat(),
                "profile": self._get_user_profile(user_id),
            }

            # Ajouter le contexte spécifique selon le rôle
            if user_role_fr == "etudiant":
                context.update(self._get_student_context(user_id))
            elif user_role_fr == "enseignant":
                context.update(self._get_teacher_context(user_id))
            elif user_role_fr == "admin":
                context.update(self._get_admin_context())

            # Inject available navigation routes for the user role
            try:
                from app.utils.route_discover import RouteDiscovery

                # Harmoniser le rôle (anglais -> français) pour RouteDiscovery
                role_map = {
                    "student": "etudiant",
                    "teacher": "enseignant",
                    "admin": "admin",
                }
                discovery_role = user_role_fr
                context["available_routes"] = RouteDiscovery().get_available_routes(
                    discovery_role
                )
                # Ajouter la liste des tables SQL autorisées pour l'IA
                tables_allowed = ALLOWED_TABLES_BY_ROLE.get(discovery_role, [])
                if not tables_allowed:  # admin => accès complet
                    try:
                        from app.services.defai_sql_executor import _ALL_TABLES

                        tables_allowed = _ALL_TABLES
                    except ImportError:
                        pass
                context["allowed_tables"] = tables_allowed
            except Exception as _e:
                logger.error(f"Erreur chargement routes disponibles: {_e}")
            return context

        except Exception as e:
            logger.error(f"Erreur récupération contexte utilisateur {user_id}: {e}")
            return {"error": str(e)}

    def _get_user_profile(self, user_id):
        """Récupère le profil de base d'un utilisateur"""
        try:
            user_obj = User.query.get(user_id)

            if user_obj:
                return {
                    "id": user_obj.id,
                    "nom": user_obj.nom,
                    "prenom": user_obj.prenom,
                    "email": user_obj.email,
                    "role": user_obj.role,
                    "date_naissance": (
                        user_obj.date_naissance.isoformat()
                        if user_obj.date_naissance
                        else None
                    ),
                    "sexe": user_obj.sexe,
                    "telephone": user_obj.telephone,
                }
            else:
                return None

        except Exception as e:
            logger.error(f"Erreur récupération profil utilisateur {user_id}: {e}")
            return None

    def _get_student_context(self, student_id):
        """Récupère le contexte spécifique à un étudiant"""
        context = {
            "academic_info": self._get_student_academic_info(student_id),
            "grades": self._get_student_grades_summary(student_id),
            "schedule": self._get_student_schedule_summary(student_id),
            "recent_notifications": self._get_student_notifications(
                student_id, limit=5
            ),
            "assignments": self._get_student_assignments_summary(student_id),
        }
        return context

    def _get_student_academic_info(self, student_id):
        """Informations académiques de l'étudiant"""
        try:
            result = db.session.execute(
                text(
                    """
                    SELECT s.id, s.filiere, s.filiere as class_name,
                           CURRENT_DATE as date_creation, '2024-2025'
                    FROM etudiant s
                    WHERE s.user_id = :student_id
                """
                ),
                {"student_id": student_id},
            ).fetchone()

            if result:
                return {
                    "student_number": result[0],
                    "class_name": result[0],
                    # "class_name": result[2],
                    "enrollment_date": result[3].isoformat() if result[3] else None,
                    "academic_year": result[4],
                }
            return {}

        except Exception as e:
            logger.error(f"Erreur infos académiques étudiant: {e}")
            return {}

    def _get_student_grades_summary(self, student_id):
        """Résumé des notes de l'étudiant"""
        try:
            # Récupérer les notes par matière
            grades_by_subject = (
                db.session.query(
                    Matiere.nom,
                    db.func.avg(Note.note).label("avg_grade"),
                    db.func.count(Note.id).label("grade_count"),
                    db.func.min(Note.note).label("min_grade"),
                    db.func.max(Note.note).label("max_grade"),
                )
                .join(Note, Matiere.id == Note.matiere_id)
                .filter(Note.etudiant_id == student_id)
                .group_by(Matiere.id, Matiere.nom)
                .order_by(db.desc("avg_grade"))
                .all()
            )

            subjects = []
            general_avg = 0
            total_grades = 0

            for row in grades_by_subject:
                subjects.append(
                    {
                        "name": row.nom,
                        "average": float(row.avg_grade) if row.avg_grade else 0,
                        "grade_count": row.grade_count,
                        "min_grade": row.min_grade,
                        "max_grade": row.max_grade,
                    }
                )

                general_avg += float(row.avg_grade) if row.avg_grade else 0
                total_grades += row.grade_count

            # Calculer la moyenne générale
            if total_grades > 0:
                general_avg = general_avg / len(subjects)

            # Identifier les matières faibles (< 10)
            weak_subjects = [s["name"] for s in subjects if s["average"] < 10]

            return {
                "subjects": subjects,
                "general_average": general_avg,
                "total_grades": total_grades,
                "weak_subjects": weak_subjects,
            }

        except Exception as e:
            logger.error(f"Erreur récupération notes étudiant {student_id}: {e}")
            return {
                "subjects": [],
                "general_average": 0,
                "total_grades": 0,
                "weak_subjects": [],
            }

    def _get_student_schedule_summary(self, student_id):
        """Résumé de l'emploi du temps de l'étudiant"""
        try:
            # Récupérer la classe de l'étudiant
            result = db.session.execute(
                text("SELECT filiere FROM etudiant WHERE user_id = :student_id"),
                {"student_id": student_id},
            ).fetchone()

            if not result:
                return {}

            class_name = result[0]

            # Cours des prochains jours
            schedule_result = db.session.execute(
                text(
                    """
                    SELECT ec.jour, ec.heure_debut, ec.heure_fin,
                           m.nom as subject_name,
                           'Salle A' as room_name
                    FROM emploi_temps ec
                    JOIN matiere m ON ec.matiere_id = m.id
                    WHERE ec.enseignant_id IN (
                        SELECT e.id FROM enseignant e 
                        WHERE e.filieres_enseignees ILIKE CONCAT('%', :class_name, '%')
                    )
                    ORDER BY ec.jour, ec.heure_debut
                    LIMIT 10
                """
                ),
                {"class_name": class_name},
            ).fetchall()

            schedule = []
            for row in schedule_result:
                schedule.append(
                    {
                        "day": row[0],
                        "start_time": row[1].isoformat() if row[1] else None,
                        "end_time": row[2].isoformat() if row[2] else None,
                        "subject": row[3],
                        "room": row[4],
                    }
                )

            return {"schedule": schedule}

        except Exception as e:
            logger.error(f"Erreur emploi du temps étudiant: {e}")
            return {"schedule": []}

    def _get_student_notifications(self, student_id, limit=10):
        """Notifications récentes de l'étudiant"""
        try:
            result = db.session.execute(
                text(
                    """
                    SELECT id, titre, message, type, date_created, is_read
                    FROM notification
                    WHERE user_id = :student_id
                    ORDER BY date_created DESC
                    LIMIT :limit
                """
                ),
                {"student_id": student_id, "limit": limit},
            ).fetchall()

            notifications = []
            for row in result:
                notifications.append(
                    {
                        "id": row[0],
                        "titre": row[1],
                        "message": row[2],
                        "type": row[3],
                        "date_created": row[4].isoformat() if row[4] else None,
                        "is_read": row[5],
                    }
                )

            return notifications

        except Exception as e:
            logger.error(f"Erreur notifications étudiant: {e}")
            return []

    def _get_student_assignments_summary(self, student_id):
        """Résumé des devoirs de l'étudiant"""
        try:
            # Récupérer la classe de l'étudiant
            class_result = db.session.execute(
                text("SELECT filiere FROM etudiant WHERE user_id = :student_id"),
                {"student_id": student_id},
            ).fetchone()

            if not class_result:
                return {}

            class_name = class_result[0]

            # Devoirs à venir et en retard
            assignments_result = db.session.execute(
                text(
                    """
                    SELECT a.id, a.titre, a.description, a.date_limite,
                           m.nom as subject_name, a.type
                    FROM devoir a
                    JOIN matiere m ON a.matiere_id = m.id
                    WHERE a.filiere = :class_name
                    ORDER BY a.date_limite ASC
                """
                ),
                {"class_name": class_name},
            ).fetchall()

            assignments = []
            for row in assignments_result:
                assignments.append(
                    {
                        "id": row[0],
                        "titre": row[1],
                        "description": row[2],
                        "date_limite": row[3].isoformat() if row[3] else None,
                        "subject_name": row[4],
                        "type": row[5],
                    }
                )

            return {"assignments": assignments}

        except Exception as e:
            logger.error(f"Erreur devoirs étudiant: {e}")
            return {"assignments": []}

    def _get_teacher_context(self, teacher_id):
        """Récupère le contexte spécifique à un enseignant"""
        context = {
            "teaching_info": self._get_teacher_teaching_info(teacher_id),
            "classes": self._get_teacher_classes_summary(teacher_id),
            "recent_activities": self._get_teacher_recent_activities(teacher_id),
            "notifications": self._get_teacher_notifications(teacher_id, limit=5),
        }
        return context

    def _get_teacher_teaching_info(self, teacher_id):
        """Informations d'enseignement"""
        try:
            result = db.session.execute(
                text(
                    """
                    SELECT e.id, e.specialite, e.date_embauche
                    FROM enseignant e
                    WHERE e.user_id = :teacher_id
                """
                ),
                {"teacher_id": teacher_id},
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "specialite": result[1],
                    "hire_date": result[2].isoformat() if result[2] else None,
                }
            return {}

        except Exception as e:
            logger.error(f"Erreur infos enseignant: {e}")
            return {}

    def _get_teacher_classes_summary(self, teacher_id):
        """Résumé des classes de l'enseignant"""
        try:
            result = db.session.execute(
                text(
                    """
                    SELECT c.id, c.nom, f.nom as filiere_name,
                           COUNT(e.id) as student_count
                    FROM matiere c
                    LEFT JOIN filiere f ON c.filiere_id = f.id
                    LEFT JOIN etudiant e ON f.nom = e.filiere
                    WHERE c.enseignant_id = :teacher_id
                    GROUP BY c.id, c.nom, f.nom
                    ORDER BY c.nom
                """
                ),
                {"teacher_id": teacher_id},
            ).fetchall()

            classes = []
            total_students = 0

            for row in result:
                class_info = {
                    "id": row[0],
                    "nom": row[1],
                    "filiere": row[2],
                    "student_count": row[3],
                }
                classes.append(class_info)
                total_students += row[3]

            return {
                "classes": classes,
                "total_classes": len(classes),
                "total_students": total_students,
            }

        except Exception as e:
            logger.error(f"Erreur classes enseignant: {e}")
            return {}

    def _get_teacher_recent_activities(self, teacher_id):
        """Activités récentes de l'enseignant"""
        try:
            activities = []

            # Devoirs récemment créés
            assignments_result = db.session.execute(
                text(
                    """
                    SELECT 'assignment_created' as type, a.titre, a.date_creation as created_at,
                           c.nom as class_name
                    FROM devoir a
                    JOIN matiere c ON a.matiere_id = c.id
                    WHERE a.enseignant_id = :teacher_id AND a.date_creation >= :date
                    ORDER BY a.date_creation DESC
                    LIMIT 3
                """
                ),
                {"teacher_id": teacher_id, "date": datetime.now() - timedelta(days=7)},
            ).fetchall()

            for row in assignments_result:
                activities.append(
                    {
                        "type": row[0],
                        "title": row[1],
                        "date": row[2].isoformat() if row[2] else None,
                        "details": f"Classe: {row[3]}",
                    }
                )

            # Notes récemment ajoutées
            grades_result = db.session.execute(
                text(
                    """
                    SELECT 'grades_added' as type, COUNT(*) as count, g.date_evaluation as created_at,
                           m.nom as subject_name
                    FROM note g
                    JOIN matiere m ON g.matiere_id = m.id
                    WHERE m.enseignant_id = :teacher_id AND g.date_evaluation >= :date
                    GROUP BY g.date_evaluation, m.nom
                    ORDER BY g.date_evaluation DESC
                    LIMIT 3
                """
                ),
                {"teacher_id": teacher_id, "date": datetime.now() - timedelta(days=7)},
            ).fetchall()

            for row in grades_result:
                activities.append(
                    {
                        "type": row[0],
                        "title": f"{row[1]} notes ajoutées",
                        "date": row[2].isoformat() if row[2] else None,
                        "details": f"Matière: {row[3]}",
                    }
                )

            return activities

        except Exception as e:
            logger.error(f"Erreur activités enseignant: {e}")
            return []

    def _get_teacher_notifications(self, teacher_id, limit=10):
        """Notifications récentes de l'enseignant"""
        try:
            result = db.session.execute(
                text(
                    """
                    SELECT id, titre, message, type, date_created, is_read
                    FROM notification
                    WHERE user_id = :teacher_id
                    ORDER BY date_created DESC
                    LIMIT :limit
                """
                ),
                {"teacher_id": teacher_id, "limit": limit},
            ).fetchall()

            notifications = []
            for row in result:
                notifications.append(
                    {
                        "id": row[0],
                        "title": row[1],
                        "message": row[2],
                        "type": row[3],
                        "created_at": row[4].isoformat() if row[4] else None,
                        "is_read": row[5],
                    }
                )

            return notifications

        except Exception as e:
            logger.error(f"Erreur notifications enseignant: {e}")
            return []

    def _get_admin_context(self):
        """Récupère le contexte spécifique à un administrateur"""
        context = {
            "platform_stats": self._get_platform_statistics(),
            "recent_activities": self._get_admin_recent_activities(),
            "system_health": self._get_system_health(),
        }
        return context

    def _get_platform_statistics(self):
        """Statistiques globales de la plateforme"""
        try:
            stats = {}

            # Statistiques utilisateurs
            users_result = db.session.execute(
                text(
                    """
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN role = 'etudiant' THEN 1 END) as students,
                        COUNT(CASE WHEN role = 'enseignant' THEN 1 END) as teachers,
                        COUNT(CASE WHEN role = 'admin' THEN 1 END) as admins
                    FROM users
                """
                )
            ).fetchone()

            if users_result:
                stats["users"] = {
                    "total": users_result[0],
                    "students": users_result[1],
                    "teachers": users_result[2],
                    "admins": users_result[3],
                }

            # Statistiques académiques
            academic_result = db.session.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM filiere) as total_classes,
                        (SELECT COUNT(*) FROM matiere) as total_subjects,
                        (SELECT COUNT(*) FROM note) as total_grades
                """
                )
            ).fetchone()

            if academic_result:
                stats["academic"] = {
                    "classes": academic_result[0],
                    "subjects": academic_result[1],
                    "grades": academic_result[2],
                }

            # Nouveaux utilisateurs cette semaine
            new_users_result = db.session.execute(
                text("SELECT COUNT(*) FROM users WHERE date_creation >= :date"),
                {"date": datetime.now() - timedelta(days=7)},
            ).fetchone()

            new_users = new_users_result[0] if new_users_result else 0
            stats["users"]["new_this_week"] = new_users

            return stats

        except Exception as e:
            logger.error(f"Erreur statistiques plateforme: {e}")
            return {}

    def _get_admin_recent_activities(self):
        """Activités récentes pour l'admin"""
        try:
            activities = []

            # Nouveaux inscrits
            users_result = db.session.execute(
                text(
                    """
                    SELECT 'new_user' as type, u.email, u.date_creation as created_at,
                           CASE WHEN u.role = 'etudiant' THEN 'Étudiant'
                                WHEN u.role = 'enseignant' THEN 'Enseignant'
                                WHEN u.role = 'admin' THEN 'Admin'
                                ELSE 'Inconnu' END as role
                    FROM users u
                    WHERE u.date_creation >= :date
                    ORDER BY u.date_creation DESC
                    LIMIT 5
                """
                ),
                {"date": datetime.now() - timedelta(days=7)},
            ).fetchall()

            for row in users_result:
                activities.append(
                    {
                        "type": row[0],
                        "title": f"Nouvel utilisateur: {row[1]}",
                        "date": row[2].isoformat() if row[2] else None,
                        "details": f"Rôle: {row[3]}",
                    }
                )

            # Nouvelles classes (pas de colonne date_creation dans filiere)
            # classes_result = db.session.execute(
            #     text(
            #         """
            #         SELECT 'new_class' as type, f.nom, f.date_creation as created_at
            #         FROM filiere f
            #         WHERE f.date_creation >= :date
            #         ORDER BY f.date_creation DESC
            #         LIMIT 3
            #     """
            #     ),
            #     {"date": datetime.now() - timedelta(days=7)},
            # ).fetchall()

            # for row in classes_result:
            #     activities.append(
            #         {
            #             "type": row[0],
            #             "title": f"Nouvelle classe: {row[1]}",
            #             "date": row[2].isoformat() if row[2] else None,
            #             "details": "",
            #         }
            #     )

            return activities

        except Exception as e:
            logger.error(f"Erreur activités admin: {e}")
            return []

    def _get_system_health(self):
        """État de santé du système"""
        try:
            return {
                "database_status": "healthy",
                "last_check": datetime.now().isoformat(),
                "active_sessions": 0,  # À implémenter avec les sessions
                "system_load": "normal",  # À implémenter avec monitoring
            }
        except Exception as e:
            logger.error(f"Erreur santé système: {e}")
            return {"database_status": "error", "error": str(e)}

    def _execute_discover_available_requests(self, user_id):
        """Retourne la liste de toutes les routes disponibles pour le rôle de l'utilisateur"""
        try:
            # Récupérer le rôle de l'utilisateur
            user_obj = User.query.get(user_id)
            if not user_obj:
                return {"success": False, "error": "Utilisateur non trouvé"}

            user_role = user_obj.role

            # Utiliser le nouveau système de découverte de routes
            from app.utils.route_discovery_db import RouteDiscoveryDB

            discovery = RouteDiscoveryDB(db.session)

            # Obtenir les suggestions de routes pour le rôle
            suggested_routes = discovery.get_route_suggestions(user_role)

            # Formater les résultats pour compatibilité avec l'ancien système
            routes_info = {
                "discover_available_requests": "Découvrir toutes les routes disponibles via le nouveau système routes_catalog",
            }

            # Ajouter les routes suggérées
            for i, route in enumerate(suggested_routes):
                route_key = f"route_{i+1}"
                routes_info[route_key] = (
                    f"{route['url']} - {route['description'][:100]}..."
                )

            return {
                "success": True,
                "available_requests": routes_info,
                "total_routes": len(suggested_routes),
                "user_role": user_role,
                "categories": list(
                    set(route["category"] for route in suggested_routes)
                ),
            }

        except Exception as e:
            logger.error(f"Erreur lors de la découverte des routes: {e}")
            return {"success": False, "error": str(e)}

    def _categorize_request(self, request_name):
        """Catégorise une requête pour mieux l'organiser"""
        if "student" in request_name and request_name != "get_all_users":
            return "donnees_etudiant"
        elif "teacher" in request_name:
            return "donnees_enseignant"
        elif "class" in request_name or "subject" in request_name:
            return "donnees_classe"
        elif (
            "platform" in request_name
            or "system" in request_name
            or "user" in request_name
        ):
            return "administration"
        else:
            return "general"

    def execute_request(self, request_type, user_id, user_role, request_context=None):
        """Exécute une requête interne autorisée"""
        try:
            # Mapper les rôles français vers anglais si nécessaire
            role_mapping = {
                "etudiant": "etudiant",
                "enseignant": "enseignant",
                "admin": "admin",
                "student": "etudiant",
                "teacher": "enseignant",
            }

            mapped_role = role_mapping.get(user_role, user_role)

            # Vérifier si la requête est autorisée pour ce rôle
            if (
                mapped_role != "admin"
                and request_type not in self.allowed_requests.get(mapped_role, [])
            ):
                logger.warning(
                    f"Requête {request_type} non autorisée pour le rôle {mapped_role}"
                )
                return {
                    "success": False,
                    "error": f"Requête {request_type} non autorisée pour le rôle {mapped_role}",
                }

            # Router vers la méthode appropriée
            method_name = f"_execute_{request_type}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                logger.info(f"Exécution de {method_name} pour user_id={user_id}")
                if request_type == "get_users_by_role":
                    role_filter = self._extract_role_from_context(request_context)
                    return method(user_id, role_filter)
                return method(user_id)
            else:
                logger.error(f"Méthode {method_name} non implémentée")
                return {
                    "success": False,
                    "error": f"Méthode {method_name} non implémentée",
                }

        except Exception as e:
            logger.error(f"Erreur exécution requête {request_type}: {e}")
            return {"success": False, "error": str(e)}

    # Méthodes d'exécution spécifiques
    def _execute_get_student_grades(self, student_id):
        """Récupère les notes détaillées d'un étudiant"""
        try:
            grades = (
                db.session.query(
                    Note.id,
                    Note.note,
                    Note.type_evaluation,
                    Note.date_evaluation,
                    Matiere.nom.label("subject_name"),
                )
                .join(Matiere, Note.matiere_id == Matiere.id)
                .filter(Note.etudiant_id == student_id)
                .order_by(Note.date_evaluation.desc())
                .all()
            )

            grades_data = []
            for row in grades:
                grades_data.append(
                    {
                        "id": row.id,
                        "value": float(row.note),
                        "comment": row.type_evaluation,
                        "created_at": (
                            row.date_evaluation.isoformat()
                            if row.date_evaluation
                            else None
                        ),
                        "subject_name": row.subject_name,
                    }
                )

            return {"success": True, "data": {"grades": grades_data}}

        except Exception as e:
            logger.error(f"Erreur exécution get_student_grades: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_student_averages(self, student_id):
        """Calcule les moyennes détaillées d'un étudiant"""
        return {
            "success": True,
            "data": {"averages": self._get_student_grades_summary(student_id)},
        }

    def _execute_get_student_weak_subjects(self, student_id):
        """Identifie les matières faibles d'un étudiant"""
        grades_summary = self._get_student_grades_summary(student_id)
        weak_subjects = grades_summary.get("weak_subjects", [])

        return {"success": True, "data": {"weak_subjects": weak_subjects}}

    def _execute_get_class_statistics(self, teacher_id):
        """Statistiques détaillées des classes d'un enseignant"""
        try:
            result = db.session.execute(
                text(
                    """
                    SELECT c.id, c.nom, COUNT(e.id) as student_count,
                           AVG(n.note) as class_average,
                           COUNT(n.id) as total_grades
                    FROM matiere c
                    LEFT JOIN etudiant e ON 1=1
                    LEFT JOIN note n ON e.id = n.etudiant_id AND n.matiere_id = c.id
                    WHERE c.enseignant_id = :teacher_id
                    GROUP BY c.id, c.nom
                    ORDER BY c.nom
                """
                ),
                {"teacher_id": teacher_id},
            ).fetchall()

            classes_stats = []
            for row in result:
                classes_stats.append(
                    {
                        "class_name": row[0],
                        # "class_name": row[1],
                        "student_count": row[2],
                        "class_average": float(row[3]) if row[3] else 0,
                        "total_grades": row[4],
                    }
                )

            return {"success": True, "data": classes_stats}

        except Exception as e:
            logger.error(f"Erreur statistiques classes: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_user_statistics(self, admin_id):
        """Statistiques détaillées des utilisateurs"""
        try:
            stats = {}

            # Évolution des inscriptions
            registration_result = db.session.execute(
                text(
                    """
                    SELECT DATE(date_creation) as date, COUNT(*) as count
                    FROM users
                    WHERE date_creation >= :date
                    GROUP BY DATE(date_creation)
                    ORDER BY date DESC
                    LIMIT 30
                """
                ),
                {"date": datetime.now() - timedelta(days=30)},
            ).fetchall()

            registration_trend = []
            for row in registration_result:
                registration_trend.append(
                    {
                        "date": row[0].isoformat() if row[0] else None,
                        "new_users": row[1],
                    }
                )

            stats["registration_trend"] = registration_trend

            # Distribution par rôle
            role_result = db.session.execute(
                text(
                    """
                    SELECT 
                        CASE WHEN role = 'etudiant' THEN 'Étudiants'
                             WHEN role = 'enseignant' THEN 'Enseignants'
                             WHEN role = 'admin' THEN 'Admins'
                             ELSE 'Autres' END as role,
                        COUNT(*) as count
                    FROM users
                    GROUP BY role
                """
                )
            ).fetchall()

            role_distribution = []
            for row in role_result:
                role_distribution.append({"role": row[0], "count": row[1]})

            stats["role_distribution"] = role_distribution

            return {"success": True, "data": stats}

        except Exception as e:
            logger.error(f"Erreur statistiques utilisateurs: {e}")
            return {"success": False, "error": str(e)}

    def _is_next_class(self, class_info):
        """Détermine si un cours est dans un proche avenir"""
        # Implémentation simplifiée - à améliorer avec la logique temporelle réelle
        return True

    def _get_student_progression(self, student_id):
        """Analyse la progression de l'étudiant dans le temps"""
        # À implémenter avec l'historique des notes
        return {"success": True, "data": {"progression": []}}

    def _get_best_students(self, teacher_id):
        """Identifie les meilleurs étudiants des classes de l'enseignant"""
        # À implémenter
        return {"success": True, "data": {"best_students": []}}

    def _get_struggling_students(self, teacher_id):
        """Identifie les étudiants en difficulté"""
        # À implémenter
        return {"success": True, "data": {"struggling_students": []}}

    # --- Nouvelles méthodes (découverte / analyse) ---

    def _execute_discover_routes(self, user_id):
        """Découvre toutes les routes disponibles pour l'utilisateur"""
        try:
            user_obj = User.query.get(user_id)
            if not user_obj:
                return {"success": False, "error": "Utilisateur non trouvé"}

            user_role = user_obj.role

            # Utiliser le nouveau système de découverte de routes
            from app.utils.route_discovery_db import RouteDiscoveryDB

            discovery = RouteDiscoveryDB(db.session)

            # Obtenir les suggestions de routes pour le rôle
            suggested_routes = discovery.get_route_suggestions(user_role)

            # Formater pour l'IA
            routes_info = []
            for route in suggested_routes:
                routes_info.append(
                    {
                        "url": route["url"],
                        "description": route["description"],
                        "category": route["category"],
                        "roles": route["roles"],
                    }
                )

            return {
                "success": True,
                "data": {
                    "routes": routes_info,
                    "total_found": len(routes_info),
                    "user_role": user_role,
                    "categories": list(
                        set(route["category"] for route in suggested_routes)
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Erreur découverte routes: {e}")
            return {"success": False, "error": str(e)}

    def _execute_fetch_route_data(self, user_id, endpoint: str):
        """Récupère les données d'une route spécifique"""
        try:
            user_obj = User.query.get(user_id)
            if not user_obj:
                return {"success": False, "error": "Utilisateur non trouvé"}

            user_role = user_obj.role
            result = self.route_accessor.fetch_route_data(endpoint, user_role)

            return result

        except Exception as e:
            logger.error(f"Erreur accès route {endpoint}: {e}")
            return {"success": False, "error": str(e)}

    def _execute_analyze_query(self, user_id, query: str):
        """Analyse une requête et récupère automatiquement les données pertinentes"""
        try:
            user_obj = User.query.get(user_id)
            if not user_obj:
                return {"success": False, "error": "Utilisateur non trouvé"}

            user_role = user_obj.role
            result = self.route_accessor.analyze_query_and_fetch(query, user_role)

            return result

        except Exception as e:
            logger.error(f"Erreur analyse requête: {e}")
            return {"success": False, "error": str(e)}

    def execute_sql_readonly(self, sql: str, user_role: str):
        """Exécute une requête SQL sécurisée en lecture seule via defai_sql_executor"""
        return execute_sql_readonly(sql, user_role)

    def execute_smart_request(self, query: str, user_id: int, user_role: str):
        """
        Exécute une requête intelligente en analysant automatiquement
        quelles routes accéder pour obtenir les données nécessaires
        """
        try:
            logger.info(f"Exécution requête intelligente: {query}")

            # Essayer d'utiliser le client DefAI pour les requêtes internes
            try:
                return self._execute_with_defai_client(query, user_id, user_role)
            except Exception as e:
                logger.warning(f"Échec client DefAI, utilisation méthode locale: {e}")
                # Fallback vers la méthode locale existante

            # Analyser la requête et récupérer automatiquement les données
            result = self._execute_analyze_query(user_id, query)

            if result["success"]:
                formatted_data = self._format_data_for_ai(result)
                return {
                    "success": True,
                    "data": formatted_data,
                    "routes_accessed": result.get("routes_accessed", []),
                }
            return result

        except Exception as e:
            logger.error(f"Erreur requête intelligente: {e}")
            return {"success": False, "error": str(e)}

    def _format_data_for_ai(self, raw_data: dict) -> dict:
        """Formate les données brutes pour qu'elles soient facilement utilisables par l'IA."""
        formatted = {
            "summary": f"Données récupérées de {len(raw_data.get('routes_accessed', []))} route(s)",
            "data_sources": [],
        }

        for route in raw_data.get("routes_accessed", []):
            source = {
                "source": route["description"],
                "type": route["data_type"],
                "data": {},
            }

            # Extraire les données du type correspondant
            data_type = route["data_type"]
            if data_type in raw_data.get("combined_data", {}):
                extracted = raw_data["combined_data"][data_type]["extracted_data"]

                # Formatter les tableaux
                if "tables" in extracted:
                    source["data"]["tables"] = self._format_tables(extracted["tables"])

                # Formatter les statistiques
                if "statistics" in extracted:
                    source["data"]["statistics"] = extracted["statistics"]

                # Formatter les listes
                if "lists" in extracted:
                    source["data"]["lists"] = extracted["lists"]

            formatted["data_sources"].append(source)

        return formatted

    def _format_tables(self, tables: list[dict]) -> list[dict]:
        """Formate les tableaux pour l'IA."""
        formatted_tables = []

        for table in tables:
            if "headers" in table and "rows" in table:
                # Convertir en liste de dictionnaires
                table_data = []
                headers = table["headers"]

                for row in table["rows"]:
                    if len(row) == len(headers):
                        row_dict = {headers[i]: row[i] for i in range(len(headers))}
                        table_data.append(row_dict)

                formatted_tables.append(
                    {
                        "columns": headers,
                        "data": table_data,
                        "row_count": len(table_data),
                    }
                )

        return formatted_tables

    def _extract_role_from_context(self, context: dict | None) -> str | None:
        """Déduit le rôle demandé à partir de la description d'une requête."""
        if not context or not isinstance(context, dict):
            return None

        text_parts = []
        for key in ("description", "query", "content", "type"):
            value = context.get(key)
            if value and isinstance(value, str):
                text_parts.append(value.lower())

        raw_text = " ".join(text_parts)
        if not raw_text:
            return None

        role_keywords = {
            "etudiant": [
                "étudiant",
                "etudiant",
                "eleve",
                "élève",
                "student",
                "apprenant",
            ],
            "enseignant": ["enseignant", "professeur", "teacher", "formateur"],
            "admin": ["admin", "administrateur", "administrator", "gestionnaire"],
        }

        for role, keywords in role_keywords.items():
            if any(keyword in raw_text for keyword in keywords):
                return role
        return None
