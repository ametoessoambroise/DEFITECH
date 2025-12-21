"""
Ce fichier contient le modèle DevoirVu qui représente un devoir vu par un étudiant.

Le modèle DevoirVu contient les champs suivants :
    - id : identifiant unique du devoir vu
    - devoir_id : identifiant du devoir lié
    - etudiant_id : identifiant de l'étudiant qui a vu le devoir
    - date_vue : date à laquelle l'étudiant a vu le devoir

Le modèle DevoirVu contient également une méthode __repr__ qui retourne une représentation texte du devoir vu sous la forme "<DevoirVu id=<id> devoir_id=<devoir_id> etudiant_id=<etudiant_id>>".
"""

from app.extensions import db
from datetime import datetime


class DevoirVu(db.Model):
    __tablename__ = "devoir_vu"

    id = db.Column(db.Integer, primary_key=True)
    devoir_id = db.Column(
        db.Integer, db.ForeignKey("devoir.id", ondelete="CASCADE"), nullable=False
    )
    etudiant_id = db.Column(
        db.Integer, db.ForeignKey("etudiant.id", ondelete="CASCADE"), nullable=False
    )
    date_vue = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    devoir = db.relationship("Devoir", backref="vus")
    etudiant = db.relationship("Etudiant", backref="devoirs_vus")

    def __repr__(self):
        return f"<DevoirVu id={self.id} devoir_id={self.devoir_id} etudiant_id={self.etudiant_id}>"
