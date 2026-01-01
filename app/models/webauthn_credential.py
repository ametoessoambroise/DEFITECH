from datetime import datetime
from app.extensions import db


class WebauthnCredential(db.Model):
    __tablename__ = "webauthn_credentials"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    # Identifiant unique de la clé (généré par le navigateur)
    credential_id = db.Column(db.String(255), unique=True, nullable=False)

    # Clé publique (encodée en base64 pour le stockage)
    public_key = db.Column(db.Text, nullable=False)

    # Type de transport (usb, ble, nfc, internal)
    transports = db.Column(db.String(255), nullable=True)

    # Compteur de signatures (utilisé pour détecter les clones)
    sign_count = db.Column(db.Integer, default=0, nullable=False)

    # Nom amical de l'appareil (ex: "iPhone de Jean", "Yubikey Chrome")
    device_name = db.Column(db.String(100), nullable=True)

    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    last_use = db.Column(db.DateTime, nullable=True)

    # Relation
    user = db.relationship(
        "User", backref=db.backref("webauthn_credentials", cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<WebauthnCredential {self.device_name} for User {self.user_id}>"
