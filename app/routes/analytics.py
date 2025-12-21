"""
Analytics Module for DEFITECH
Comprehensive analytics and statistics for admin dashboard
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, case
from datetime import datetime, timedelta
from functools import wraps

from app.extensions import db
from app.models.user import User
from app.models.etudiant import Etudiant
from app.models.note import Note
from app.models.presence import Presence
from app.models.devoir import Devoir
from app.models.devoir_vu import DevoirVu
from app.models.matiere import Matiere
from app.models.filiere import Filiere
from app.models.notification import Notification

from app.models.resource import Resource
from app.models.post import Post
from app.models.suggestion import Suggestion, SuggestionVote


analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Accès non autorisé.", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function


@analytics_bp.route("/")
@login_required
@admin_required
def dashboard():
    """
    Page principale du tableau de bord analytique.

    Cette fonction renvoie le template HTML correspondant à la page principale
    du tableau de bord analytique. Cela permet à l'administrateur d'accéder à
    une vue d'ensemble des statistiques et des informations importantes sur la
    plateforme DEFITECH.

    Retourne:
        Un template HTML contenant le tableau de bord analytique.
    """
    return render_template("analytics/dashboard.html")


@analytics_bp.route("/api/overview")
@login_required
@admin_required
def api_overview():
    """
    Renvoie les statistiques générales de la plateforme DEFITECH.

    Cette fonction renvoie un dictionnaire contenant les statistiques suivantes :
    - total_users : Nombre total d'utilisateurs enregistrés sur la plateforme
    - active_students : Nombre d'étudiants actifs (avec un profil validé)
    - active_teachers : Nombre d'enseignants actifs (avec un profil validé)
    - pending_users : Nombre d'utilisateurs en attente de validation

    Retourne:
        Un dictionnaire contenant les statistiques générales de la plateforme.

    """
    try:
        # Statistiques utilisateurs
        total_users = User.query.count()
        active_students = User.query.filter_by(
            role="etudiant", statut="approuve"
        ).count()
        active_teachers = User.query.filter_by(
            role="enseignant", statut="approuve"
        ).count()
        pending_users = User.query.filter_by(statut="en_attente").count()

        # Statistiques académiques
        total_filieres = Filiere.query.count()
        total_matieres = Matiere.query.count()
        total_notes = Note.query.count()

        # Statistiques d'engagement
        total_resources = Resource.query.count()
        total_devoirs = Devoir.query.count()
        total_posts = Post.query.count()
        total_suggestions = Suggestion.query.count()

        # Activité récente (7 derniers jours)
        week_ago = datetime.now() - timedelta(days=7)
        new_users_week = User.query.filter(User.date_creation >= week_ago).count()
        new_resources_week = Resource.query.filter(
            Resource.date_upload >= week_ago
        ).count()

        # Taux de présence moyen
        total_presences = Presence.query.count()
        presences_presentes = Presence.query.filter_by(present=True).count()
        taux_presence = (
            (presences_presentes / total_presences * 100) if total_presences > 0 else 0
        )

        # Moyenne générale des notes
        avg_note = (
            db.session.query(func.avg(Note.note)).filter(Note.note.isnot(None)).scalar()
        )
        avg_note = round(avg_note, 2) if avg_note else 0

        data = {
            "users": {
                "total": total_users,
                "students": active_students,
                "teachers": active_teachers,
                "pending": pending_users,
                "new_this_week": new_users_week,
            },
            "academic": {
                "filieres": total_filieres,
                "matieres": total_matieres,
                "notes": total_notes,
                "average_grade": avg_note,
            },
            "engagement": {
                "resources": total_resources,
                "devoirs": total_devoirs,
                "posts": total_posts,
                "suggestions": total_suggestions,
                "new_resources_week": new_resources_week,
            },
            "attendance": {
                "total_records": total_presences,
                "present": presences_presentes,
                "rate": round(taux_presence, 2),
            },
        }

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/users/growth")
@login_required
@admin_required
def api_users_growth():
    """
    Renvoie l'évolution du nombre d'utilisateurs dans le temps.

    Cette fonction est une route API qui permet de récupérer les données
    concernant l'évolution du nombre d'utilisateurs au fil du temps. Elle
    prend en paramètre une seule argument optionnel : "period", qui peut
    prendre les valeurs "day", "week", "month" ou "year". Si ce paramètre n'est
    pas fourni, la période par défaut est "month".

    Retourne une réponse JSON contenant les informations suivantes :
        - success (bool) : Indique si la requête a été effectuée avec succès
        - data (dict) : Dictionnaire contenant les données d'évolution du nombre
            d'utilisateurs. La clé "date" représente la date de l'évolution,
            tandis que la clé "count" représente le nombre d'utilisateurs à cette
            date.

    Exemple de réponse JSON pour une requête réussie avec une période de "week" :
    {
        "success": true,
        "data": [
            {"date": "2022-W16", "count": 100},
            {"date": "2022-W17", "count": 110},
            {"date": "2022-W18", "count": 120},
            ...
        ]
    }
    """
    try:
        period = request.args.get("period", "month")  # day, week, month, year

        if period == "day":
            days = 30
            date_format = "YYYY-MM-DD"
        elif period == "week":
            days = 90
            date_format = "YYYY-W%W"
        elif period == "year":
            days = 365
            date_format = "YYYY"
        else:  # month
            days = 365
            date_format = "YYYY-MM"

        start_date = datetime.now() - timedelta(days=days)

        # Requête pour obtenir les inscriptions par période
        users_by_period = (
            db.session.query(
                func.to_char(User.date_creation, date_format).label("period"),
                func.count(User.id).label("count"),
                User.role,
            )
            .filter(User.date_creation >= start_date)
            .group_by("period", User.role)
            .all()
        )

        # Organiser les données
        data = {}
        for period_label, count, role in users_by_period:
            if period_label not in data:
                data[period_label] = {"students": 0, "teachers": 0, "admins": 0}

            if role == "etudiant":
                data[period_label]["students"] = count
            elif role == "enseignant":
                data[period_label]["teachers"] = count
            elif role == "admin":
                data[period_label]["admins"] = count

        # Convertir en liste triée
        result = [
            {
                "period": period_label,
                "students": values["students"],
                "teachers": values["teachers"],
                "admins": values["admins"],
                "total": values["students"] + values["teachers"] + values["admins"],
            }
            for period_label, values in sorted(data.items())
        ]

        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/students/performance")
@login_required
@admin_required
def api_students_performance():
    """
    Cette fonction analyse la performance des étudiants. Elle effectue une requête
    sur la base de données pour obtenir les moyennes des notes et le nombre de notes
    pour chaque filière et année. Si des filières et/ou des années spécifiques sont
    fournies en paramètre, la requête est filtrée en conséquence.

    Paramètres:
        filiere (str, facultatif): Filière pour laquelle obtenir les données de performance
            (exemple: 'L1INFO')
        annee (str, facultatif): Année pour laquelle obtenir les données de performance
            (exemple: '2019')

    Retourne:
        Une réponse JSON contenant les informations suivantes :
            - success (bool): Indique si la requête a été effectuée avec succès
            - data (list): Liste des résultats pour chaque filière et année, avec les
                informations suivantes :
                - filiere (str): Filière pour laquelle les données ont été obtenues
                - annee (str): Année pour laquelle les données ont été obtenues
                - moyenne (float): Moyenne des notes pour la filière et l'année
                - nb_notes (int): Nombre de notes pour la filière et l'année

    Exemple de réponse JSON :
    {
        "success": true,
        "data": [
            {
                "filiere": "L1INFO",
                "annee": "2019",
                "moyenne": 12.5,
                "nb_notes": 10
            },
            {
                "filiere": "L1INFO",
                "annee": "2020",
                "moyenne": 14.2,
                "nb_notes": 15
            }
        ]
    }
    """
    try:
        filiere = request.args.get("filiere")
        annee = request.args.get("annee")

        # Requête de base pour les notes
        query = (
            db.session.query(
                Etudiant.filiere,
                Etudiant.annee,
                func.avg(Note.note).label("moyenne"),
                func.count(Note.id).label("nb_notes"),
            )
            .join(Note, Note.etudiant_id == Etudiant.id)
            .filter(Note.note.isnot(None))
        )

        # Filtres
        if filiere:
            query = query.filter(Etudiant.filiere == filiere)
        if annee:
            query = query.filter(Etudiant.annee == annee)

        # Grouper par filière et année
        results = query.group_by(Etudiant.filiere, Etudiant.annee).all()

        # Distribution des notes (par tranches)
        distribution_query = db.session.query(
            case(
                (Note.note < 10, "0-10"),
                (Note.note < 12, "10-12"),
                (Note.note < 14, "12-14"),
                (Note.note < 16, "14-16"),
                (Note.note >= 16, "16-20"),
            ).label("tranche"),
            func.count(Note.id).label("count"),
        ).filter(Note.note.isnot(None))

        if filiere:
            distribution_query = distribution_query.join(
                Etudiant, Note.etudiant_id == Etudiant.id
            ).filter(Etudiant.filiere == filiere)

        distribution = distribution_query.group_by("tranche").all()

        # Top 10 des meilleurs étudiants
        top_students = (
            db.session.query(
                User.nom,
                User.prenom,
                Etudiant.filiere,
                Etudiant.annee,
                func.avg(Note.note).label("moyenne"),
            )
            .join(Etudiant, User.id == Etudiant.user_id)
            .join(Note, Note.etudiant_id == Etudiant.id)
            .filter(Note.note.isnot(None))
            .group_by(
                Etudiant.id, User.nom, User.prenom, Etudiant.filiere, Etudiant.annee
            )
            .order_by(func.avg(Note.note).desc())
            .limit(10)
            .all()
        )

        data = {
            "by_filiere": [
                {
                    "filiere": r.filiere,
                    "annee": r.annee,
                    "moyenne": round(r.moyenne, 2) if r.moyenne else 0,
                    "nb_notes": r.nb_notes,
                }
                for r in results
            ],
            "distribution": [{"tranche": t, "count": c} for t, c in distribution],
            "top_students": [
                {
                    "nom": f"{s.nom} {s.prenom}",
                    "filiere": s.filiere,
                    "annee": s.annee,
                    "moyenne": round(s.moyenne, 2) if s.moyenne else 0,
                }
                for s in top_students
            ],
        }

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/attendance/stats")
@login_required
@admin_required
def api_attendance_stats():
    """
    Retourne les statistiques de présence.

    Cette fonction renvoie une réponse JSON contenant les statistiques suivantes :

    - success (bool) : Indique si la requête a été effectuée avec succès
    - data (dict) : Dictionnaire contenant les statistiques de présence
        - filiere (str) : La filière sélectionnée, ou None si aucune filière n'est sélectionnée
        - annee (str) : L'année sélectionnée, ou None si aucune année n'est sélectionnée
        - days (int) : Le nombre de jours sélectionnés, ou 30 par défaut.
        - stats (dict) : Dictionnaire contenant les statistiques par jour
            - date (str) : La date en format ISO 8601
            - total (int) : Le nombre total de présence pour cette date
            - present (int) : Le nombre de présence présentes pour cette date
            - absent (int) : Le nombre de présence absentes pour cette date
            - late (int) : Le nombre de présence en retard pour cette date

    Si une exception est levée pendant le traitement de la requête, la réponse renvoyée est un dictionnaire JSON avec les clés success et error.

    """
    try:
        filiere = request.args.get("filiere")
        annee = request.args.get("annee")
        days = int(request.args.get("days", 30))

        start_date = datetime.now() - timedelta(days=days)

        # Requête de base
        query = db.session.query(
            func.date(Presence.date_cours).label("date"),
            Presence.present,
            func.count(Presence.id).label("count"),
        ).filter(Presence.date_cours >= start_date)

        # Filtres par filière et année
        if filiere or annee:
            query = query.join(Etudiant, Presence.etudiant_id == Etudiant.id)
            if filiere:
                query = query.filter(Etudiant.filiere == filiere)
            if annee:
                query = query.filter(Etudiant.annee == annee)

        results = query.group_by(func.date(Presence.date_cours), Presence.present).all()

        # Organiser les données par date
        data_by_date = {}
        for date_str, present, count in results:
            if date_str not in data_by_date:
                data_by_date[date_str] = {
                    "present": 0,
                    "absent": 0,
                }
            if present:
                data_by_date[date_str]["present"] = count
            else:
                data_by_date[date_str]["absent"] = count

        # Taux de présence par filière
        filiere_stats = (
            db.session.query(
                Etudiant.filiere,
                Presence.present,
                func.count(Presence.id).label("count"),
            )
            .join(Etudiant, Presence.etudiant_id == Etudiant.id)
            .filter(Presence.date_cours >= start_date)
            .group_by(Etudiant.filiere, Presence.present)
            .all()
        )

        # Organiser par filière
        by_filiere = {}
        for filiere_name, present, count in filiere_stats:
            if filiere_name not in by_filiere:
                by_filiere[filiere_name] = {
                    "present": 0,
                    "absent": 0,
                    "total": 0,
                }
            if present:
                by_filiere[filiere_name]["present"] = count
            else:
                by_filiere[filiere_name]["absent"] = count
            by_filiere[filiere_name]["total"] += count

        # Calculer les taux
        for filiere_name in by_filiere:
            total = by_filiere[filiere_name]["total"]
            if total > 0:
                by_filiere[filiere_name]["taux_presence"] = round(
                    by_filiere[filiere_name]["present"] / total * 100, 2
                )

        data = {
            "timeline": [
                {
                    "date": date_str,
                    "present": values["present"],
                    "absent": values["absent"],
                    "total": values["present"] + values["absent"],
                }
                for date_str, values in sorted(data_by_date.items())
            ],
            "by_filiere": [
                {"filiere": filiere_name, **values}
                for filiere_name, values in by_filiere.items()
            ],
        }

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/resources/stats")
@login_required
@admin_required
def api_resources_stats():
    """
    Renvoie les statistiques des ressources numériques.

    Cette fonction utilise la base de données pour récupérer les statistiques suivantes :

    - total_resources : Nombre total de ressources numériques enregistrées.
    - by_type : Liste des types de ressources numériques avec le nombre de ressources correspondantes.
    - by_filiere : Liste des filières avec le nombre de ressources numériques correspondantes.

    Retourne:
        Un dictionnaire contenant les statistiques des ressources numériques.
    """
    try:
        # Ressources par type
        by_type = (
            db.session.query(
                Resource.type_ressource, func.count(Resource.id).label("count")
            )
            .group_by(Resource.type_ressource)
            .all()
        )

        # Ressources par filière
        by_filiere = (
            db.session.query(Resource.filiere, func.count(Resource.id).label("count"))
            .group_by(Resource.filiere)
            .all()
        )

        # Ressources les plus récentes
        recent = (
            db.session.query(
                Resource.titre,
                Resource.type_ressource,
                Resource.filiere,
                Resource.date_upload,
                User.nom,
                User.prenom,
            )
            .join(User, Resource.enseignant_id == User.id)
            .order_by(Resource.date_upload.desc())
            .limit(10)
            .all()
        )

        # Enseignants les plus actifs
        top_contributors = (
            db.session.query(
                User.nom, User.prenom, func.count(Resource.id).label("count")
            )
            .join(Resource, Resource.enseignant_id == User.id)
            .group_by(User.id)
            .order_by(func.count(Resource.id).desc())
            .limit(10)
            .all()
        )

        # Evolution des uploads dans le temps
        days = 90
        start_date = datetime.now() - timedelta(days=days)

        timeline = (
            db.session.query(
                func.date(Resource.date_upload).label("date"),
                func.count(Resource.id).label("count"),
            )
            .filter(Resource.date_upload >= start_date)
            .group_by(func.date(Resource.date_upload))
            .all()
        )

        data = {
            "by_type": [{"type": t, "count": c} for t, c in by_type],
            "by_filiere": [{"filiere": f, "count": c} for f, c in by_filiere],
            "recent": [
                {
                    "titre": r.titre,
                    "type": r.type_ressource,
                    "filiere": r.filiere,
                    "date": r.date_upload.isoformat() if r.date_upload else None,
                    "enseignant": f"{r.nom} {r.prenom}",
                }
                for r in recent
            ],
            "top_contributors": [
                {"nom": f"{t.nom} {t.prenom}", "count": t.count}
                for t in top_contributors
            ],
            "timeline": [{"date": str(d), "count": c} for d, c in timeline],
        }

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/devoirs/stats")
@login_required
@admin_required
def api_devoirs_stats():
    """
    Renvoie les statistiques des devoirs et des examens.

    Cette fonction utilise la base de données pour récupérer les statistiques suivantes :

    - total_devoirs : Nombre total de devoirs et d'examens enregistrés.
    - devoirs_a_venir : Nombre de devoirs et d'examens à venir.
    - devoirs_passes : Nombre de devoirs et d'examens passés.
    - total_vus : Nombre total de devoirs et d'examens vus par les étudiants.
    - total_etudiants : Nombre total d'étudiants inscrits.
    - total_expected : Nombre total de devoirs et d'examens prévus (multiplication du
      nombre de devoirs par le nombre d'étudiants).
    - taux_consultation : Taux de consultation des devoirs et des examens (total_vus
      divisé par total_expected, multiplié par 100).
    - by_matiere : Liste des matières avec le nombre de devoirs correspondants.
    - recent : Liste des devoirs et examens les plus récents.

    Retourne:
        Un dictionnaire contenant les statistiques des devoirs et des examens.
    """
    try:
        # Devoirs par statut
        total_devoirs = Devoir.query.count()
        devoirs_a_venir = Devoir.query.filter(
            Devoir.date_limite > datetime.now()
        ).count()
        devoirs_passes = Devoir.query.filter(
            Devoir.date_limite <= datetime.now()
        ).count()

        # Taux de consultation des devoirs
        total_vus = DevoirVu.query.count()
        total_etudiants = Etudiant.query.count()
        total_expected = total_devoirs * total_etudiants if total_devoirs > 0 else 0

        taux_consultation = (
            (total_vus / total_expected * 100) if total_expected > 0 else 0
        )

        # Devoirs par matière (simplifier car pas de matiere_id dans Devoir)
        by_matiere = []

        # Devoirs récents
        recent = (
            db.session.query(
                Devoir.titre,
                Devoir.type,
                Devoir.date_limite,
                Devoir.filiere,
                Devoir.annee,
            )
            .order_by(Devoir.date_creation.desc())
            .limit(10)
            .all()
        )

        data = {
            "overview": {
                "total": total_devoirs,
                "a_venir": devoirs_a_venir,
                "passes": devoirs_passes,
                "taux_consultation": round(taux_consultation, 2),
            },
            "by_matiere": [{"matiere": m, "count": c} for m, c in by_matiere],
            "recent": [
                {
                    "titre": d.titre,
                    "type": d.type,
                    "date_rendu": d.date_limite.isoformat() if d.date_limite else None,
                    "filiere": d.filiere,
                    "annee": d.annee,
                    "matiere": "Non spécifié",
                }
                for d in recent
            ],
        }

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/engagement/stats")
@login_required
@admin_required
def api_engagement_stats():
    """
    Renvoie les statistiques d'engagement des utilisateurs.

    Cette fonction renvoie un dictionnaire contenant les statistiques suivantes :
    - total_posts : Nombre total de posts communautaires créés depuis le début, ou depuis le début des derniers jours si 'days' est spécifié
    - total_suggestions : Nombre total de suggestions créées depuis le début, ou depuis le début des derniurs jours si 'days' est spécifié
    - suggestions_ouvertes : Nombre total de suggestions ouvertes depuis le début, ou depuis le début des derniurs jours si 'days' est spécifié
    - total_votes : Nombre total de votes sur les suggestions depuis le début

    Args:
        None

    Returns:
        Un dictionnaire contenant les statistiques d'engagement des utilisateurs.
    """
    try:
        days = int(request.args.get("days", 30))
        start_date = datetime.now() - timedelta(days=days)

        # Posts communautaires
        total_posts = Post.query.filter(Post.date_creation >= start_date).count()

        # Suggestions
        total_suggestions = Suggestion.query.filter(
            Suggestion.date_creation >= start_date
        ).count()
        suggestions_ouvertes = Suggestion.query.filter(
            Suggestion.date_creation >= start_date, Suggestion.statut == "ouverte"
        ).count()

        # Votes sur suggestions
        total_votes = SuggestionVote.query.count()

        # Notifications envoyées
        notifications_sent = Notification.query.filter(
            Notification.date_created >= start_date
        ).count()
        notifications_read = Notification.query.filter(
            Notification.date_created >= start_date, Notification.est_lue
        ).count()

        taux_lecture = (
            (notifications_read / notifications_sent * 100)
            if notifications_sent > 0
            else 0
        )

        # Utilisateurs actifs (ayant effectué une action récente)
        active_users = (
            db.session.query(func.count(func.distinct(Post.auteur_id)))
            .filter(Post.date_creation >= start_date)
            .scalar()
            or 0
        )

        total_users = User.query.filter_by(statut="approuve").count()
        taux_engagement = (active_users / total_users * 100) if total_users > 0 else 0

        data = {
            "overview": {
                "active_users": active_users,
                "total_users": total_users,
                "taux_engagement": round(taux_engagement, 2),
            },
            "community": {
                "posts": total_posts,
                "suggestions": total_suggestions,
                "suggestions_ouvertes": suggestions_ouvertes,
                "votes": total_votes,
            },
            "notifications": {
                "sent": notifications_sent,
                "read": notifications_read,
                "taux_lecture": round(taux_lecture, 2),
            },
        }

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/export")
@login_required
@admin_required
def api_export_analytics():
    """
    Exporte les données analytiques en format JSON.

    Cette fonction renvoie une réponse JSON contenant les données analytiques
    extraites de la base de données. Le format de la réponse dépend du type
    de rapport spécifié dans le paramètre "type". Le paramètre "period" est
    utilisé pour spécifier la période de l'analyse (par exemple, "30 jours"
    ou "tous les mois").

    Paramètres:
        type (str): Le type de rapport à générer. Seuls les rapports "overview"
            sont supportés. Si aucun type n'est spécifié, le rapport par défaut
            est "overview".
        period (str): La période de l'analyse à effectuer. Par exemple, "30 jours"
            ou "tous les mois". Par défaut, la période est de "30 jours".

    Retourne:
        Une réponse JSON contenant les données analytiques. Le format de la réponse
        dépend du type de rapport spécifié dans le paramètre "type".

    Exemple de réponse JSON pour un rapport "overview" sur une période de "30 jours" :
    {
        "generated_at": "2023-01-01T12:00:00",
        "report_type": "overview",
        "period": "30 jours",
        "active_users": 100,
        "total_users": 200,
        "taux_engagement": 50.0,
        "posts": 1000,
        "suggestions": 2000,
        "suggestions_ouvertes": 1000,
        "votes": 5000,
        "notifications_sent": 10000,
        "notifications_read": 5000,
        "taux_lecture": 50.0
    }
    """
    try:
        report_type = request.args.get("type", "overview")

        # Selon le type de rapport, générer les données appropriées
        if report_type == "overview":
            # Appeler toutes les fonctions d'analyse
            data = {
                "generated_at": datetime.now().isoformat(),
                "report_type": "overview",
                "period": request.args.get("period", "30 days"),
            }

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
