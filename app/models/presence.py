"""
Modèle pour les présences des étudiants

Ce modèle permet de stocker les présences des étudiants dans la base de données.

Les champs sont:
- id: Identifiant unique de la présence
- etudiant_id: Identifiant de l'étudiant
- enseignant_id: Identifiant de l'enseignant qui a marqué la présence
- matiere_id: Identifiant de la matière
- date_cours: Date du cours
- heure_debut: Heure de début du cours
- heure_fin: Heure de fin du cours
- present: Booléen indiquant si l'étudiant est présent ou non
- heure_marquee: Horodatage de la marque de présence

Les méthodes sont:
- __repr__: Retourne une représentation de l'objet sous forme de chaîne de caractères
"""

from datetime import datetime
from app.extensions import db


class Presence(db.Model):
    __tablename__ = "presence"

    id = db.Column(db.Integer, primary_key=True)
    etudiant_id = db.Column(db.Integer, db.ForeignKey("etudiant.id"), nullable=False)
    enseignant_id = db.Column(db.Integer, db.ForeignKey("enseignant.id"), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=False)
    date_cours = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)
    present = db.Column(db.Boolean, default=False)
    heure_marquee = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    etudiant = db.relationship("Etudiant", backref="presences")
    enseignant = db.relationship("Enseignant", backref="presences_marquees")
    matiere = db.relationship("Matiere", backref="presences")

    __table_args__ = (
        db.UniqueConstraint(
            'etudiant_id', 'matiere_id', 'date_cours', 'heure_debut',
            name='_etudiant_matiere_date_heure_uc'
        ),
    )

    def __repr__(self):
        return (
            f"<Presence id={self.id} etudiant_id={self.etudiant_id} "
            f"matiere_id={self.matiere_id} date={self.date_cours} "
            f"{self.heure_debut}-{self.heure_fin} present={self.present}>"
        )
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON"""
        return {
            'id': self.id,
            'etudiant_id': self.etudiant_id,
            'enseignant_id': self.enseignant_id,
            'matiere_id': self.matiere_id,
            'date_cours': self.date_cours.isoformat() if self.date_cours else None,
            'heure_debut': self.heure_debut.strftime('%H:%M') if self.heure_debut else None,
            'heure_fin': self.heure_fin.strftime('%H:%M') if self.heure_fin else None,
            'present': self.present,
            'heure_marquee': self.heure_marquee.isoformat() if self.heure_marquee else None
        }
