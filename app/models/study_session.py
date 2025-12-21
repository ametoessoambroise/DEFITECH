from datetime import datetime, timedelta
from app.extensions import db


class StudySession(db.Model):
    """
    Modèle pour suivre les sessions d'étude des utilisateurs.
    """

    __tablename__ = "study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    document_id = db.Column(
        db.Integer, db.ForeignKey("study_documents.id"), nullable=True
    )
    session_type = db.Column(
        db.String(50), nullable=False
    )  # lecture, quiz, flashcards, etc.
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, default=0)  # Durée en secondes
    notes = db.Column(db.Text, nullable=True)

    # Relations
    user = db.relationship("User", backref=db.backref("study_sessions", lazy=True))

    def __init__(self, **kwargs):
        super(StudySession, self).__init__(**kwargs)
        self.start_time = datetime.utcnow()

    def end_session(self, save=True):
        """Termine la session et calcule la durée."""
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_seconds = int(
                (self.end_time - self.start_time).total_seconds()
            )
        if save:
            db.session.commit()

    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "session_type": self.session_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "notes": self.notes,
        }

    @classmethod
    def get_recent_sessions(cls, user_id, days=7):
        """Récupère les sessions récentes d'un utilisateur."""
        since_date = datetime.utcnow() - timedelta(days=days)
        return (
            cls.query.filter(cls.user_id == user_id, cls.start_time >= since_date)
            .order_by(cls.start_time.desc())
            .all()
        )

    def __repr__(self):
        return f"<StudySession {self.id} - {self.session_type} (User: {self.user_id})>"
