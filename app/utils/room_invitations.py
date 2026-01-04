"""
Module pour gérer l'envoi d'invitations aux salles de visioconférence
DEPRECATED: Utiliser app.utils.room_utils à la place pour une logique consolidée et robuste.
"""

import warnings


from datetime import datetime, timedelta
import logging
from flask import url_for
from sqlalchemy import and_
from app.extensions import db
from app.email_utils import send_email
from app.models.user import User
from app.models.videoconference import RoomParticipant, Inscription, RoomInvitation

# Configuration du logger
logger = logging.getLogger(__name__)

warnings.warn(
    "app.utils.room_invitations is deprecated, use app.utils.room_utils instead",
    DeprecationWarning,
)

def get_students_for_course(course_id):
    """
    Récupère la liste des étudiants inscrits à un cours

    Args:
        course_id: ID du cours

    Returns:
        QuerySet: Liste des étudiants inscrits au cours
    """
    # Récupérer les étudiants inscrits au cours
    students = (
        User.query.join(
            Inscription,
            and_(
                Inscription.user_id == User.id,
                Inscription.course_id == course_id,
                Inscription.statut == "active",
            ),
        )
        .filter(User.role == "etudiant")
        .all()
    )

    return students


def is_course_scheduled_now(course, current_time=None):
    """
    Vérifie si le cours est prévu à l'heure actuelle selon l'emploi du temps

    Args:
        course: Objet Course
        current_time: Heure actuelle (pour les tests)

    Returns:
        bool: True si le cours est prévu maintenant, False sinon
    """
    if not current_time:
        current_time = datetime.now()

    # Récupérer le jour de la semaine actuel (0 = lundi, 6 = dimanche)
    current_weekday = current_time.weekday()

    # Convertir le jour de la semaine en format texte (ex: 'monday')
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    current_weekday_str = weekdays[current_weekday]

    # Vérifier si le cours a lieu aujourd'hui
    if not getattr(course, f"jour_{current_weekday_str}", False):
        return False

    # Vérifier l'heure du cours
    course_start = course.heure_debut
    course_end = course.heure_fin

    # Convertir en objets time pour la comparaison
    current_time_only = current_time.time()

    # Vérifier si l'heure actuelle est dans la plage du cours
    # On ajoute une marge de 15 minutes avant et après le cours
    margin = 15  # minutes
    start_time = (
        datetime.combine(datetime.today(), course_start) - timedelta(minutes=margin)
    ).time()
    end_time = (
        datetime.combine(datetime.today(), course_end) + timedelta(minutes=margin)
    ).time()

    return start_time <= current_time_only <= end_time


def send_room_invitations(room, course, teacher):
    """
    Envoie des invitations par email aux étudiants pour rejoindre une salle de visioconférence

    Args:
        room: Objet Room contenant les informations de la salle
        course: Objet Course contenant les informations du cours
        teacher: Objet User représentant l'enseignant

    Returns:
        dict: Résultat de l'opération avec le nombre d'invitations envoyées
    """
    from email_utils import send_email

    try:
        # Vérifier si le cours est prévu maintenant
        if not is_course_scheduled_now(course):
            logger.warning(f"Le cours {course.nom} n'est pas prévu en ce moment")
            return {
                "success": False,
                "message": "Le cours n'est pas prévu en ce moment",
                "invitations_sent": 0,
            }

        # Récupérer les étudiants inscrits au cours
        students = get_students_for_course(course.id)

        if not students:
            logger.warning(f"Aucun étudiant trouvé pour le cours {course.nom}")
            return {
                "success": False,
                "message": "Aucun étudiant trouvé pour ce cours",
                "invitations_sent": 0,
            }

        # Générer l'URL de la salle
        join_url = url_for(
            "videoconference.join_room", token=room.token, _external=True
        )

        # Envoyer un email à chaque étudiant
        sent_count = 0
        for student in students:
            try:
                send_email(
                    to=student.email,
                    subject=f"Cours en direct - {course.nom} - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    template_name="room_invitation",
                    user=student,
                    course=course,
                    teacher=teacher,
                    join_url=join_url,
                    current_time=datetime.now(),
                )
                sent_count += 1
                logger.info(
                    f"Invitation envoyée à {student.email} pour la salle {room.name}"
                )

                # Enregistrer l'invitation dans l'historique
                invitation = RoomInvitation(
                    room_id=room.id,
                    user_id=student.id,
                    sent_at=datetime.now(),
                    status="sent",
                )
                db.session.add(invitation)

            except Exception as e:
                logger.error(
                    f"Erreur lors de l'envoi de l'invitation à {student.email}: {str(e)}"
                )
                # Enregistrer l'échec
                invitation = RoomInvitation(
                    room_id=room.id,
                    user_id=student.id,
                    sent_at=datetime.now(),
                    status="failed",
                    error_message=str(e),
                )
                db.session.add(invitation)
                continue  # Continuer avec les étudiants suivants

        # Valider les changements en base de données
        db.session.commit()

        return {
            "success": True,
            "message": f"{sent_count} invitations envoyées avec succès",
            "invitations_sent": sent_count,
            "total_students": len(students),
        }

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'envoi des invitations: {str(e)}")
        return {
            "success": False,
            "message": f"Erreur lors de l'envoi des invitations: {str(e)}",
            "invitations_sent": 0,
        }


def send_reminder_emails(room, course, teacher):
    """
    Envoie des rappels aux étudiants qui n'ont pas encore rejoint la salle

    Args:
        room: Objet Room
        course: Objet Course
        teacher: Objet User représentant l'enseignant
    """

    # Récupérer les étudiants qui n'ont pas encore rejoint
    joined_subquery = db.session.query(RoomParticipant.user_id).filter(
        RoomParticipant.room_id == room.id
    )

    pending_students = (
        User.query.join(
            Inscription,
            and_(
                Inscription.user_id == User.id,
                Inscription.course_id == course.id,
                Inscription.statut == "active",
            ),
        )
        .filter(User.role == "etudiant", ~User.id.in_(joined_subquery))
        .all()
    )

    # Envoyer des rappels
    for student in pending_students:
        try:
            send_email(
                to=student.email,
                subject=f"Rappel - Cours en cours: {course.nom}",
                template_name="room_reminder",
                user=student,
                course=course,
                teacher=teacher,
                join_url=url_for(
                    "videoconference.join_room", token=room.token, _external=True
                ),
                current_time=datetime.now(),
            )
            logger.info(f"Rappel envoyé à {student.email} pour la salle {room.name}")
        except Exception as e:
            logger.error(
                f"Erreur lors de l'envoi du rappel à {student.email}: {str(e)}"
            )
            continue
