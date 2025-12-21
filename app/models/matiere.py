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
    annee = db.Column(db.String(20), nullable=False, default="1ère année")  # Ajout de l'année
    credit = db.Column(db.Integer, nullable=False, default=6)  # Ajout des crédits

    # Relations
    filiere = db.relationship("Filiere", backref="matieres")
    enseignant = db.relationship("Enseignant", backref="matieres")
    rooms = db.relationship("Room", back_populates="course", lazy=True)

    def __repr__(self):
        return f"<Matiere {self.nom}>"
