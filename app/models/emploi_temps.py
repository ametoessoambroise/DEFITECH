"""
Modèle pour les emplois du temps des enseignants

Contient les informations relatives aux emplois du temps des enseignants.
Les emplois du temps sont créés par les enseignants et sont associés à une matière, une filière et un enseignant.

Attributes:
    id (int): Identifiant unique de l'emploi du temps.
    enseignant_id (int): Identifiant de l'enseignant lié à l'emploi du temps.
    filiere_id (int): Identifiant de la filière liée à l'emploi du temps.
    matiere_id (int): Identifiant de la matière liée à l'emploi du temps.
    jour (str): Jour de l'emploi du temps (ex: "Lundi", "Mardi", etc.).
    heure_debut (time): Heure de début du cours.
    heure_fin (time): Heure de fin du cours.
    salle (str): Salle où a lieu le cours.
"""

from app.extensions import db


class EmploiTemps(db.Model):
    __tablename__ = "emploi_temps"
    __table_args__ = (
        # Un enseignant ne peut pas avoir deux cours en même temps
        db.UniqueConstraint(
            "enseignant_id",
            "jour",
            "heure_debut",
            "heure_fin",
            name="_enseignant_jour_creneau_uc",
        ),
        # Une salle ne peut pas être occupée deux fois en même temps (seulement si salle définie)
        # On utilise un Index partiel au lieu d'une UniqueConstraint standard
        db.Index(
            "idx_salle_jour_creneau_unique",
            "salle",
            "jour",
            "heure_debut",
            "heure_fin",
            unique=True,
            postgresql_where=db.text("salle IS NOT NULL"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    enseignant_id = db.Column(
        db.Integer, db.ForeignKey("enseignant.id"), nullable=False
    )
    filiere_id = db.Column(db.Integer, db.ForeignKey("filiere.id"), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=False)
    jour = db.Column(db.String(50), nullable=False)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)
    salle = db.Column(db.String(100), nullable=True)

    # Relationships
    enseignant = db.relationship("Enseignant", backref="emplois_temps")
    filiere = db.relationship("Filiere", backref="emplois_temps")
    matiere = db.relationship("Matiere", backref="emplois_temps")

    def __repr__(self):
        return (
            f"<EmploiTemps id={self.id} enseignant_id={self.enseignant_id} "
            f"matiere_id={self.matiere_id} {self.jour} {self.heure_debut}-{self.heure_fin}>"
        )

    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON"""
        return {
            "id": self.id,
            "enseignant_id": self.enseignant_id,
            "filiere_id": self.filiere_id,
            "matiere_id": self.matiere_id,
            "jour": self.jour,
            "heure_debut": (
                self.heure_debut.strftime("%H:%M") if self.heure_debut else None
            ),
            "heure_fin": self.heure_fin.strftime("%H:%M") if self.heure_fin else None,
            "salle": self.salle,
        }
