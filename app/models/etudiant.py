from app.extensions import db


class Etudiant(db.Model):
    """Modèle pour les étudiants"""

    __tablename__ = "etudiant"

    id = db.Column(db.Integer, primary_key=True)
    # Ensure the foreign key points to the current users table (plural) which the
    # User model maps to.
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    filiere = db.Column(db.String(100), nullable=False)
    annee = db.Column(db.String(20), nullable=False)
    numero_etudiant = db.Column(db.String(20), unique=True, nullable=False)

    # Informations détaillées issues de la fiche d'inscription
    lieu_naissance = db.Column(db.String(100))
    nationalite = db.Column(db.String(50))
    bac_serie = db.Column(db.String(20))
    bac_annee = db.Column(db.String(4))
    etablissement_provenance = db.Column(db.String(150))
    modalite_paiement = db.Column(db.String(50))  # Comptant, 3 Tranches, 7 Tranches
    autres_modalites = db.Column(db.Text)
    modalites_choisies = db.Column(db.String(200))

    # Code de liaison pour les parents (généré à la création)
    code_parent = db.Column(db.String(10), unique=True, index=True)

    # Relation avec User
    user = db.relationship("User", back_populates="etudiant")
    # Relation avec Parent
    parents = db.relationship(
        "Parent", back_populates="etudiant", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Etudiant {self.numero_etudiant}>"
