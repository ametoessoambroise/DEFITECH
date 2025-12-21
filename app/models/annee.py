from app.extensions import db


class Annee(db.Model):
    """Modèle pour les années d'étude"""

    __tablename__ = "annee"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self):
        return f"<Annee {self.nom}>"
