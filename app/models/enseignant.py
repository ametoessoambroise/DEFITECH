from app.extensions import db


class Enseignant(db.Model):
    """Modèle pour les enseignants"""

    __tablename__ = "enseignant"
    __table_args__ = (db.UniqueConstraint("user_id", name="unique_enseignant_user"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    specialite = db.Column(db.String(100), nullable=True)
    grade = db.Column(db.String(50), nullable=True)
    filieres_enseignees = db.Column(db.String(500), nullable=True)
    annees_enseignees = db.Column(db.String(500), nullable=True)
    date_embauche = db.Column(db.Date, nullable=True)

    # Relations
    filieres_admin = db.relationship(
        "FiliereAdmin", back_populates="enseignant", cascade="all, delete-orphan"
    )
    # Relationship avec User
    user = db.relationship("User", back_populates="enseignant")

    def __repr__(self):
        return f"<Enseignant {self.user.nom} {self.user.prenom}>"

    @property
    def nom_complet(self):
        """Retourne le nom complet de l'enseignant"""
        if self.user:
            return f"{self.user.prenom} {self.user.nom}"
        return "Enseignant sans utilisateur associé"
