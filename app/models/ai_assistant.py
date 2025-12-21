"""
Modèles SQLAlchemy pour l'assistant IA defAI
"""

import uuid
from datetime import datetime
from app.extensions import db
from sqlalchemy import CheckConstraint


class AIConversation(db.Model):
    __tablename__ = "ai_conversations"

    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(
        db.String(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(255), default="Nouvelle conversation")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active = db.Column(db.Boolean, default=True)

    user_role = db.Column(db.String(20), nullable=False)
    __table_args__ = (CheckConstraint("user_role IN ('student', 'teacher', 'admin')"),)

    context_data = db.Column(db.JSON, default=dict)

    messages = db.relationship(
        "AIMessage",
        backref="conversation",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "link": self.link,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "user_role": self.user_role,
            "context_data": self.context_data or {},
        }


class AIMessage(db.Model):
    __tablename__ = "ai_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message_type = db.Column(db.String(20), nullable=False)
    __table_args__ = (
        CheckConstraint("message_type IN ('user', 'assistant', 'system')"),
    )

    content = db.Column(db.Text, nullable=False)

    # IMPORTANT : renommer metadata
    extra_data = db.Column(db.JSON, default=dict)
    
    # Gestion des pièces jointes (images, fichiers)
    attachments = db.Column(db.JSON, default=list)  # Liste des fichiers attachés
    
    # Métadonnées pour le quota d'images
    image_count = db.Column(db.Integer, default=0)  # Nombre d'images dans ce message
    has_generated_image = db.Column(db.Boolean, default=False)  # Si l'IA a généré une image

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # L’ordre des messages dans la conversation
    message_order = db.Column(db.Integer, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_type": self.message_type,
            "content": self.content,
            "extra_data": self.extra_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "message_order": self.message_order,
        }


class Dataset(db.Model):
    """
    Modèle pour stocker les interactions utilisateur/IA destinées à l'entraînement
    """

    __tablename__ = "dataset"

    id = db.Column(db.Integer, primary_key=True)
    input_text = db.Column(db.Text, nullable=False, comment="Requête de l'utilisateur")
    output_text = db.Column(db.Text, nullable=False, comment="Réponse de l'IA")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Métadonnées optionnelles pour l'entraînement
    user_role = db.Column(
        db.String(20), comment="Rôle de l'utilisateur (etudiant, enseignant, admin)"
    )
    conversation_id = db.Column(db.Integer, comment="ID de la conversation d'origine")
    tokens_used = db.Column(db.Integer, default=0, comment="Nombre de tokens utilisés")

    __table_args__ = (
        CheckConstraint("user_role IN ('etudiant', 'enseignant', 'admin', NULL)"),
        db.Index("idx_dataset_created_at", "created_at"),
        db.Index("idx_dataset_user_role", "user_role"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "input": self.input_text,
            "output": self.output_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_role": self.user_role,
            "conversation_id": self.conversation_id,
            "tokens_used": self.tokens_used,
        }

    def to_training_format(self):
        """
        Retourne le format idéal pour l'entraînement (uniquement input/output)
        """
        return {"input": self.input_text, "output": self.output_text}
