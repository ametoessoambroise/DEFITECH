from app.extensions import db


class Etudiant(db.Model):
    """Modèle pour les étudiants"""

    __tablename__ = "etudiant"

    id = db.Column(db.Integer, primary_key=True)
    # Ensure the foreign key points to the current users table (plural) which the
    # User model maps to.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    filiere = db.Column(db.String(100), nullable=False)
    annee = db.Column(db.String(20), nullable=False)
    numero_etudiant = db.Column(db.String(20), unique=True, nullable=False)

    # Relation avec User
    user = db.relationship("User", back_populates="etudiant")

    def __repr__(self):
        return f"<Etudiant {self.numero_etudiant}>"
