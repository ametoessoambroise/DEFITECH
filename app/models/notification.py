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

    def __init__(self, *args, **kwargs):
        """Allow a transient `link` kwarg for backward compatibility.

        The `link` value is not stored in the DB by default but is kept on the
        instance as `_link`. Templates or UI code can use `notification.link`
        which will return the transient value if provided, otherwise fall back
        to constructing a URL-like path from `element_type`/`element_id`.
        """
        # Pop link so SQLAlchemy's constructor won't reject it
        self._link = kwargs.pop("link", None)
        super().__init__(*args, **kwargs)

    @property
    def link(self):
        """Return a usable URL/path for the notification.

        Priority:
        - if a transient `_link` was provided at construction, return it
        - otherwise, if `element_type` is known, return a simple path based on it
        - else return None
        """
        if getattr(self, "_link", None):
            return self._link
        # Fallbacks: provide simple path patterns so templates can link to items
        if self.element_type == "post" and self.element_id:
            return f"/community/post/{self.element_id}"
        if self.element_type == "comment" and self.element_id:
            # We don't always know the parent post id here; provide a comment path
            return f"/community/post/{self.element_id}"
        if self.element_type == "teacher_request" and self.element_id:
            return f"/admin/review-teacher-request/{self.element_id}"
        return None

    @link.setter
    def link(self, value):
        self._link = value

    @classmethod
    def creer_notification(
        cls,
        user_id,
        titre,
        message,
        type=None,
        element_id=None,
        element_type=None,
    ):
        """Crée une nouvelle notification"""
        notification = cls(
            user_id=user_id,
            titre=titre,
            message=message,
            type=type,
            element_id=element_id,
            element_type=element_type,
        )
        db.session.add(notification)
        db.session.commit()
        return notification
