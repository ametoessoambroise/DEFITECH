from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB


class StudyDocument(db.Model):
    """
    Modèle pour stocker les documents d'étude téléversés par les utilisateurs.
    """

    __tablename__ = "study_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # pdf, docx, etc.
    file_size = db.Column(db.Integer, nullable=False)  # Taille en octets
    content_text = db.Column(db.Text, nullable=True)  # Contenu texte extrait
    content_metadata = db.Column(JSONB, nullable=True)  # Métadonnées structurées
    is_processed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations
    user = db.relationship("User", backref=db.backref("study_documents", lazy=True))
    sessions = db.relationship(
        "StudySession", backref="document", lazy=True, cascade="all, delete-orphan"
    )
    quizzes = db.relationship(
        "Quiz", backref="document", lazy=True, cascade="all, delete-orphan"
    )
    flashcards = db.relationship(
        "Flashcard", backref="document", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StudyDocument {self.title} (ID: {self.id})>"

    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "is_processed": self.is_processed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
