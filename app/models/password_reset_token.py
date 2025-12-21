from datetime import datetime
from app.extensions import db


class PasswordResetToken(db.Model):
    """Modèle pour les jetons de réinitialisation de mot de passe"""

    __tablename__ = "password_reset_token"

    id = db.Column(db.Integer, primary_key=True)
    # Ensure this foreign key targets the 'users' table (plural) to match the
    # User model's __tablename__ and Alembic migrations.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<PasswordResetToken {self.id} for user {self.user_id}>"

    def is_valid(self):
        return not self.is_used and datetime.utcnow() < self.expires_at
