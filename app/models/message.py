from datetime import datetime
from app.extensions import db


class Message(db.Model):
    """
    Modèle pour les messages de chat en temps réel entre utilisateurs.

    Un message a un expéditeur (sender) et un destinataire (receiver).
    Les utilisateurs sont stockés dans la table 'users' et référencés par leurs IDs.
    """

    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)

    # Références vers l'expéditeur et le destinataire
    sender_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    receiver_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    # Contenu du message
    content = db.Column(db.Text, nullable=False)

    # Métadonnées
    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow, index=True, nullable=False
    )
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    # Relations vers le modèle User
    sender = db.relationship(
        "User",
        foreign_keys=[sender_id],
        backref=db.backref("messages_sent", lazy="dynamic"),
    )
    receiver = db.relationship(
        "User",
        foreign_keys=[receiver_id],
        backref=db.backref("messages_received", lazy="dynamic"),
    )

    __table_args__ = (
        # Accélère les recherches sur les conversations et l'ordre chronologique
        db.Index("ix_message_pair_timestamp", "sender_id", "receiver_id", "timestamp"),
    )

    def __repr__(self):
        return f"<Message id={self.id} from={self.sender_id} to={self.receiver_id} read={self.is_read}>"

    def to_dict(self):
        """Retourne une représentation sérialisable du message."""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_read": self.is_read,
        }

    def mark_as_read(self, commit: bool = True):
        """Marque le message comme lu."""
        if not self.is_read:
            self.is_read = True
            if commit:
                db.session.commit()

    @classmethod
    def get_conversation(
        cls, user_a_id: int, user_b_id: int, limit: int = 50, offset: int = 0
    ):
        """
        Récupère l'historique des messages entre deux utilisateurs, trié par date croissante.
        Utilise une pagination simple via limit/offset.

        Args:
            user_a_id (int): ID du premier utilisateur
            user_b_id (int): ID du deuxième utilisateur
            limit (int): Nombre maximum de messages à récupérer
            offset (int): Décalage des messages (pour pagination)

        Returns:
            list[Message]: Liste des messages de la conversation
        """
        return (
            cls.query.filter(
                db.or_(
                    db.and_(cls.sender_id == user_a_id, cls.receiver_id == user_b_id),
                    db.and_(cls.sender_id == user_b_id, cls.receiver_id == user_a_id),
                )
            )
            .order_by(cls.timestamp.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
