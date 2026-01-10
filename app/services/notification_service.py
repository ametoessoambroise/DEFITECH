from app.models.notification import Notification
from app.models.parent import Parent
from app.email_utils import (
    send_grade_notification_parent,
    send_absence_notification_parent,
)
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def notify_grade_recorded(etudiant, matiere, type_eval, note_val):
        """
        Notifie l'étudiant et ses parents d'une nouvelle note.
        """
        # 1. Notifier l'étudiant (In-app)
        try:
            Notification.creer_notification(
                user_id=etudiant.user_id,
                titre=f"Nouvelle note : {matiere.nom}",
                message=f"Votre note de {type_eval} en {matiere.nom} a été saisie : {note_val}/20.",
                type="info",
                element_id=matiere.id,
                element_type="grade",
            )
        except Exception as e:
            logger.error(f"Error notifying student grade: {e}")

        # 2. Notifier les parents (In-app + Email)
        parents = Parent.query.filter_by(etudiant_id=etudiant.id).all()
        for parent in parents:
            if parent.user_id:
                # In-app notification for parent
                try:
                    Notification.creer_notification(
                        user_id=parent.user_id,
                        titre=f"Suivi : Nouvelle note ({etudiant.user.prenom})",
                        message=f"Une nouvelle note ({type_eval}) a été enregistrée pour {etudiant.user.prenom} en {matiere.nom} : {note_val}/20.",
                        type="info",
                        element_id=matiere.id,
                        element_type="grade",
                    )
                except Exception as e:
                    logger.error(f"Error notifying parent in-app: {e}")

                # Email notification for parent
                try:
                    send_grade_notification_parent(
                        parent.user, etudiant, matiere, type_eval, note_val
                    )
                except Exception as e:
                    logger.error(f"Error sending grade email to parent: {e}")

    @staticmethod
    def notify_absence_recorded(etudiant, matiere, date_abs):
        """
        Notifie l'étudiant et ses parents d'une absence.
        """
        # 1. Notifier l'étudiant (In-app)
        try:
            Notification.creer_notification(
                user_id=etudiant.user_id,
                titre=f"Alerte Absence : {matiere.nom}",
                message=f"Vous avez été marqué absent au cours de {matiere.nom} le {date_abs}.",
                type="warning",
                element_id=matiere.id,
                element_type="absence",
            )
        except Exception as e:
            logger.error(f"Error notifying student absence: {e}")

        # 2. Notifier les parents (In-app + Email)
        parents = Parent.query.filter_by(etudiant_id=etudiant.id).all()
        for parent in parents:
            if parent.user_id:
                # In-app notification for parent
                try:
                    Notification.creer_notification(
                        user_id=parent.user_id,
                        titre=f"Alerte Absence ({etudiant.user.prenom})",
                        message=f"{etudiant.user.prenom} a été marqué absent en {matiere.nom} le {date_abs}.",
                        type="warning",
                        element_id=matiere.id,
                        element_type="absence",
                    )
                except Exception as e:
                    logger.error(f"Error notifying parent in-app: {e}")

                # Email notification for parent
                try:
                    send_absence_notification_parent(
                        parent.user, etudiant, matiere, date_abs
                    )
                except Exception as e:
                    logger.error(f"Error sending absence email to parent: {e}")
