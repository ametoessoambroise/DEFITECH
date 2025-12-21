from app.extensions import db


class Filiere(db.Model):
    """Modèle pour la table filiere"""

    __tablename__ = "filiere"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type_formation = db.Column(db.String(20), nullable=False, default="LICENCE")

    # Relations
    admins = db.relationship(
        "FiliereAdmin", back_populates="filiere", cascade="all, delete-orphan"
    )
    # posts sera défini après que Post soit défini
    posts = db.relationship("Post", back_populates="filiere", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Filiere {self.nom}>"


class FiliereAdmin(db.Model):
    """Table de jointure pour la relation many-to-many entre Enseignant et Filiere"""

    __tablename__ = "filiere_admin"

    id = db.Column(db.Integer, primary_key=True)
    filiere_id = db.Column(
        db.Integer, db.ForeignKey("filiere.id", ondelete="CASCADE"), nullable=False
    )
    enseignant_id = db.Column(
        db.Integer, db.ForeignKey("enseignant.id", ondelete="CASCADE"), nullable=False
    )
    # In some DBs/older migrations the column is named `date_attribution`.
    # Map the actual DB column to `date_attribution` and provide a synonym
    # `date_nomination` so code that expects either name continues to work.
    date_attribution = db.Column(
        'date_attribution', db.DateTime, default=db.func.current_timestamp()
    )
    date_nomination = db.synonym('date_attribution')

    # Relations (seront définies après que les modèles soient créés)
    filiere = db.relationship("Filiere", back_populates="admins")
    # enseignant sera défini après que Enseignant soit défini
    enseignant = db.relationship("Enseignant", back_populates="filieres_admin")

    __table_args__ = (
        db.UniqueConstraint(
            "filiere_id", "enseignant_id", name="_filiere_enseignant_uc"
        ),
    )

    def __repr__(self):
        return f"<FiliereAdmin {self.filiere.nom} - Enseignant {self.enseignant_id}>"
