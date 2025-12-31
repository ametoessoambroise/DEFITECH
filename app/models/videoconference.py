"""
Modèles pour le système de visioconférence

Ce module contient les modèles pour gérer les salles de visioconférence,
les participants et les logs d'activité.
"""

from datetime import datetime
from app.extensions import db
from sqlalchemy import event
import uuid


class Room(db.Model):
    """
    Modèle représentant une salle de visioconférence

    Attributes:
        id (int): Identifiant unique de la salle
        name (str): Nom de la salle
        course_id (int): Référence à la matière
        host_id (int): Référence à l'utilisateur hôte
        room_token (str): Token unique pour accéder à la salle
        created_at (datetime): Date de création
        is_active (bool): Si la salle est active
        participants: Relation avec les participants
        activities: Relation avec les logs d'activité
    """

    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relations
    course = db.relationship("Matiere", back_populates="rooms")
    host = db.relationship(
        "User", backref=db.backref("hosted_rooms", lazy=True), foreign_keys=[host_id]
    )
    participants = db.relationship(
        "RoomParticipant", backref="room", lazy=True, cascade="all, delete-orphan"
    )
    activities = db.relationship(
        "RoomActivityLog", backref="room", lazy=True, cascade="all, delete-orphan"
    )

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    creator = db.relationship(
        "User", backref="created_rooms", foreign_keys=[created_by]
    )

    def __init__(self, **kwargs):
        super(Room, self).__init__(**kwargs)
        if not self.room_token:
            self.room_token = str(uuid.uuid4())
        if not self.created_by and self.host_id:
            self.created_by = self.host_id

    def __repr__(self):
        return f"<Room {self.name} (ID: {self.id})>"


class RoomParticipant(db.Model):
    """
    Modèle représentant un participant à une visioconférence

    Attributes:
        id (int): Identifiant unique
        room_id (int): Référence à la salle
        user_id (int): Référence à l'utilisateur
        joined_at (datetime): Date d'entrée
        left_at (datetime): Date de sortie (NULL si toujours présent)
        role (str): Rôle dans la visioconférence
    """

    __tablename__ = "room_participants"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    left_at = db.Column(db.DateTime, nullable=True)
    role = db.Column(
        db.String(20), nullable=False
    )  # 'host', 'teacher', 'student', 'guest'

    # Relations
    user = db.relationship("User", backref=db.backref("room_participations", lazy=True))

    def __repr__(self):
        return f"<RoomParticipant {self.user_id} in Room {self.room_id}>"


class RoomActivityLog(db.Model):
    """
    Modèle pour le journal d'activité des salles de visioconférence

    Attributes:
        id (int): Identifiant unique
        room_id (int): Référence à la salle
        user_id (int): Référence à l'utilisateur (peut être NULL pour les actions système)
        action (str): Type d'action
        details (str): Détails supplémentaires
        timestamp (datetime): Horodatage de l'action
    """

    __tablename__ = "room_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    user = db.relationship("User", backref=db.backref("room_activities", lazy=True))

    def __repr__(self):
        return f"<RoomActivityLog {self.action} in Room {self.room_id} at {self.timestamp}>"


# Événements
@event.listens_for(RoomParticipant, "after_insert")
def log_join_activity(mapper, connection, target):
    """Enregistre automatiquement l'entrée d'un participant"""
    log = RoomActivityLog(
        room_id=target.room_id,
        user_id=target.user_id,
        action="joined",
        details=f"Rôle: {target.role}",
    )
    db.session.add(log)


@event.listens_for(RoomParticipant, "before_update")
def log_leave_activity(mapper, connection, target):
    """Enregistre automatiquement la sortie d'un participant"""
    if target.left_at is not None and target._left_at_was_none():
        log = RoomActivityLog(
            room_id=target.room_id,
            user_id=target.user_id,
            action="left",
            details=f"Temps passé: {target.left_at - target.joined_at}",
        )
        db.session.add(log)


def _left_at_was_none(self):
    """Vérifie si left_at était None avant la mise à jour"""
    state = db.inspect(self)
    hist = state.attrs.left_at.history
    return hist.has_changes() and hist.unchanged[0] is None


# Ajout de la méthode à la classe
RoomParticipant._left_at_was_none = _left_at_was_none


class Inscription(db.Model):
    """
    Modèle pour gérer les inscriptions des étudiants aux cours
    """

    __tablename__ = "inscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=False)
    statut = db.Column(db.String(20), default="active")  # active, inactive, pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations
    user = db.relationship("User", backref=db.backref("inscriptions", lazy=True))
    course = db.relationship("Matiere", backref=db.backref("inscriptions", lazy=True))

    def __repr__(self):
        return f"<Inscription {self.user_id} - {self.course_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "statut": self.statut,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RoomInvitation(db.Model):
    """
    Modèle pour suivre les invitations envoyées aux salles de visioconférence
    """

    __tablename__ = "room_invitations"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, sent, failed, accepted
    error_message = db.Column(db.Text, nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)

    # Relations
    room = db.relationship("Room", backref=db.backref("invitations", lazy=True))
    user = db.relationship("User", backref=db.backref("room_invitations", lazy=True))

    def __repr__(self):
        return f"<RoomInvitation {self.id} - Room:{self.room_id} - User:{self.user_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "error_message": self.error_message,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
        }

    def mark_as_accepted(self):
        """Marque l'invitation comme acceptée"""
        self.status = "accepted"
        self.accepted_at = datetime.utcnow()
        db.session.commit()
