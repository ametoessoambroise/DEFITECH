from app.extensions import db


class Parent(db.Model):
    """Modèle pour les parents/tuteurs d'étudiants"""

    __tablename__ = "parents"

    id = db.Column(db.Integer, primary_key=True)
    # Lien avec l'étudiant concerné
    etudiant_id = db.Column(db.Integer, db.ForeignKey("etudiant.id"), nullable=False)

    # Informations du parent
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    profession = db.Column(db.String(100))
    organisme_employeur = db.Column(db.String(150))
    adresse = db.Column(db.Text)
    tel_bureau = db.Column(db.String(30))
    tel_domicile = db.Column(db.String(30))
    email = db.Column(db.String(255))

    # Lien optionnel avec un compte utilisateur Parent pour accès aux notes/absences
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relations
    etudiant = db.relationship("Etudiant", back_populates="parents")
    # Relation avec l'utilisateur si un compte est créé pour le parent
    user = db.relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Parent {self.nom} {self.prenom}>"
