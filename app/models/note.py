"""
Fichier contenant le modèle de données pour les notes des étudiants.

Le modèle de données Note contient les informations suivantes :
    - id : identifiant unique de la note
    - etudiant_id : identifiant de l'étudiant lié à la note
    - matiere_id : identifiant de la matière liée à la note
    - type_evaluation : type d'évaluation (par exemple, "examen", "devoir", etc.)
    - valeur : valeur de la note
    - date_evaluation : date de l'évaluation

"""

from app.extensions import db
from datetime import datetime


class Note(db.Model):
    __tablename__ = "note"

    id = db.Column(db.Integer, primary_key=True)
    etudiant_id = db.Column(db.Integer, db.ForeignKey("etudiant.id"), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=True)
    type_evaluation = db.Column(db.String(100), nullable=True)
    note = db.Column(db.Float, nullable=True)
    date_evaluation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    etudiant = db.relationship("Etudiant", backref="notes")
    matiere = db.relationship("Matiere", backref="notes")

    def __repr__(self):
        return f"<Note id={self.id} etudiant_id={self.etudiant_id} note={self.note}>"
