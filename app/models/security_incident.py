"""
Modèle pour tracking des incidents de sécurité détectés par l'IA
"""

from app.extensions import db
from datetime import datetime


class SecurityIncident(db.Model):
    """Stocke les tentatives malveillantes détectées par defAI"""

    __tablename__ = "security_incidents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Type d'alerte et détails
    alert_type = db.Column(
        db.String(100), nullable=False
    )  # prompt_request, credentials_request, etc.
    user_message = db.Column(db.Text, nullable=False)  # Message suspect
    threat_description = db.Column(db.Text, nullable=False)  # Description de la menace

    # Métadonnées
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_resolved = db.Column(db.Boolean, default=False)  # Traité ou non
    admin_notes = db.Column(db.Text)  # Notes de l'administrateur
    resolved_at = db.Column(db.DateTime)  # Date de résolution
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"))  # Admin qui a résolu

    # Relations
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("security_incidents", lazy="dynamic"),
    )
    resolver = db.relationship("User", foreign_keys=[resolved_by])

    def to_dict(self):
        """Convertit en dictionnaire pour JSON"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_info": (
                {
                    "nom": self.user.nom,
                    "prenom": self.user.prenom,
                    "email": self.user.email,
                    "role": self.user.role,
                    "photo": self.user.photo_profil,
                }
                if self.user
                else None
            ),
            "alert_type": self.alert_type,
            "user_message": self.user_message,
            "threat_description": self.threat_description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_resolved": self.is_resolved,
            "admin_notes": self.admin_notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def __repr__(self):
        return f"<SecurityIncident {self.id} - {self.alert_type} - User {self.user_id}>"
