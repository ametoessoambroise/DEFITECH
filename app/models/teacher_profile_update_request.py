from app.extensions import db
from datetime import datetime


class TeacherProfileUpdateRequest(db.Model):
    """Modèle pour les demandes de modification du profil enseignant"""

    __tablename__ = "teacher_profile_update_request"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Informations personnelles
    nom = db.Column(db.String(100), nullable=True)
    prenom = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    adresse = db.Column(db.String(200), nullable=True)
    ville = db.Column(db.String(100), nullable=True)
    code_postal = db.Column(db.String(10), nullable=True)
    pays = db.Column(db.String(100), nullable=True)
    # Informations enseignant
    specialite = db.Column(db.String(100), nullable=True)
    grade = db.Column(db.String(50), nullable=True)
    filieres_enseignees = db.Column(db.String(500), nullable=True)
    annees_enseignees = db.Column(db.String(500), nullable=True)
    date_embauche = db.Column(db.Date, nullable=True)
    # Photo de profil
    photo_profil = db.Column(db.String(255), nullable=True)

    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    statut = db.Column(db.String(20), default="en_attente")  # en_attente, approuve, rejete
    commentaire_admin = db.Column(db.Text, nullable=True)

    # Relations
    user = db.relationship("User", back_populates="profile_update_requests")

    def __repr__(self):
        return f"<TeacherProfileUpdateRequest {self.user.email} - {self.statut}>"
