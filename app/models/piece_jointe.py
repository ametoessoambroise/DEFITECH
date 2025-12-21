import os
from app.extensions import db


class PieceJointe(db.Model):
    """Modèle pour les pièces jointes des publications"""

    __tablename__ = "piece_jointe"

    id = db.Column(db.Integer, primary_key=True)
    nom_fichier = db.Column(db.String(255), nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=False)
    type_fichier = db.Column(db.String(100), nullable=False)
    taille = db.Column(db.Integer, nullable=False)  # Taille en octets
    date_upload = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Clé étrangère
    post_id = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="CASCADE"), nullable=False
    )

    # Relations
    # post sera défini après que Post soit défini
    post = db.relationship("Post", back_populates="pieces_jointes")

    def __repr__(self):
        return f"<PieceJointe {self.nom_fichier}>"

    @property
    def extension(self):
        return os.path.splitext(self.nom_fichier)[1].lower()

    @property
    def est_image(self):
        return self.type_fichier.startswith("image/")

    @property
    def taille_formattee(self):
        # Convertit la taille en unités lisibles (Ko, Mo, Go)
        taille = self.taille  # Utiliser une variable locale
        for unit in ["o", "Ko", "Mo", "Go"]:
            if taille < 1024.0:
                return f"{taille:.1f} {unit}"
            taille /= 1024.0
        return f"{taille:.1f} Go"
