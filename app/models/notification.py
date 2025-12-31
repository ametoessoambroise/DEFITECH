from datetime import datetime, timezone
from app.extensions import db


class Notification(db.Model):
    """Modèle pour les notifications utilisateur"""

    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    # canonical column name used in DB
    date_created = db.Column(db.DateTime, default=datetime.now(tz=timezone.utc))
    is_read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(50))  # 'post', 'comment', 'system', etc.
    lien = db.Column(db.String(500))  # Colonne persistante pour les liens

    # Clé étrangère vers l'utilisateur destinataire
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Champs pour référencer l'élément concerné (optionnel)
    element_id = db.Column(db.Integer)  # ID de l'élément lié (post, commentaire, etc.)
    element_type = db.Column(db.String(50))  # Type d'élément lié

    # Backwards/forwards compatibility aliases: some parts of the codebase
    # or older migrations/templates use French names (date_creation, est_lue, type_notification, utilisateur_id)
    # and others use English names (date_created, is_read, type, user_id). Provide synonyms so both work.
    # SQLAlchemy synonym for column-level aliasing
    date_creation = db.synonym("date_created")
    est_lue = db.synonym("is_read")
    type_notification = db.synonym("type")
    utilisateur_id = db.synonym("user_id")

    # Relation
    utilisateur = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.id} pour utilisateur {self.user_id}>"

    def marquer_comme_lue(self):
        """Marque la notification comme lue"""
        self.est_lue = True
        db.session.commit()

    @property
    def link(self):
        """Return a usable URL/path for the notification.
        Priority:
        - if a `lien` column value exists, return it
        - otherwise, if `element_type` is known, return a simple path based on it
        - else return None
        """
        if self.lien:
            return self.lien
        # Fallbacks: provide simple path patterns so templates can link to items
        if self.element_type == "post" and self.element_id:
            return f"/community/post/{self.element_id}"
        if self.element_type == "comment" and self.element_id:
            return f"/community/post/{self.element_id}"
        if self.element_type == "teacher_request" and self.element_id:
            return f"/admin/review-teacher-request/{self.element_id}"
        return None

    @classmethod
    def creer_notification(
        cls,
        user_id,
        titre,
        message,
        type=None,
        element_id=None,
        element_type=None,
        link=None,
    ):
        """Crée une nouvelle notification et l'envoie en temps réel via Socket.IO"""
        notification = cls(
            user_id=user_id,
            titre=titre,
            message=message,
            type=type,
            element_id=element_id,
            element_type=element_type,
            lien=link,
        )
        db.session.add(notification)
        db.session.commit()

        # Envoi en temps réel si possible
        try:
            from app.extensions import socketio

            socketio.emit(
                "new_notification",
                {
                    "id": notification.id,
                    "titre": titre,
                    "message": message,
                    "type": type or "info",
                    "date": datetime.now(tz=timezone.utc).isoformat(),
                },
                room=f"user_{user_id}",
            )
        except Exception as e:
            # Ne pas bloquer la création si le socket échoue
            print(f"[NOTIF ERROR] Error emitting via socket: {e}")

        return notification
