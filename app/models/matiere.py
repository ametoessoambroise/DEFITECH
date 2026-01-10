from app.extensions import db

class Matiere(db.Model):
    """Modèle pour les matières"""

    __tablename__ = "matiere"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    filiere_id = db.Column(db.Integer, db.ForeignKey("filiere.id"), nullable=False)
    enseignant_id = db.Column(
        db.Integer, db.ForeignKey("enseignant.id"), nullable=False
    )
    code = db.Column(db.String(20), nullable=True)  # Code de la matière (ex: INF101)
    annee = db.Column(
        db.String(20), nullable=False, default="1ère année"
    )  # Ajout de l'année
    credit = db.Column(db.Integer, nullable=False, default=6)  # Ajout des crédits
    semestre = db.Column(db.Integer, nullable=False, default=1)  # Ajout du semestre

    def validate_credits(self):
        """Valide que les crédits sont entre 2 et 6 selon la norme ECTS"""
        if not (2 <= self.credit <= 6):
            return False, "Les crédits doivent être entre 2 et 6 selon la norme ECTS"
        return True, ""

    # Relations
    filiere = db.relationship("Filiere", backref="matieres")
    enseignant = db.relationship("Enseignant", backref="matieres")
    rooms = db.relationship("Room", back_populates="course", lazy=True)

    def __repr__(self):
        return f"<Matiere {self.nom}>"
