"""
Ce fichier contient le modèle Devoir qui représente un devoir à valider par un enseignant.

Le modèle Devoir contient les champs suivants :
    - id : identifiant unique du devoir
    - titre : titre du devoir
    - description : description du devoir
    - type : type du devoir (par exemple, "travail", "examen", etc.)
    - filiere : filière du devoir
    - annee : année du devoir
    - enseignant_id : identifiant de l'enseignant qui a créé le devoir
    - date_creation : date de création du devoir
    - date_limite : date limite pour valider le devoir
    - fichier : chemin du fichier lié au devoir (si applicable)

Le modèle Devoir contient également une méthode __repr__ qui retourne une représentation texte du devoir sous la forme "<Devoir id=<id> titre=<titre>>".

Le modèle Devoir est associé à une table "devoir" dans la base de données."
"""

from app.extensions import db
from datetime import datetime


class Devoir(db.Model):
    __tablename__ = "devoir"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(100), nullable=True)
    filiere = db.Column(db.String(100), nullable=True)
    annee = db.Column(db.String(100), nullable=True)
    enseignant_id = db.Column(db.Integer, db.ForeignKey("enseignant.id"), nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_limite = db.Column(db.DateTime, nullable=True)
    fichier = db.Column(db.String(255), nullable=True)

    # Relations
    enseignant = db.relationship("Enseignant", backref="devoirs")
    matiere_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=True)
    matiere = db.relationship("Matiere", backref="devoirs")

    def __repr__(self):
        return f"<Devoir id={self.id} titre={self.titre}>"
