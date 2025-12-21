from datetime import datetime, timezone
from app.extensions import db


class Commentaire(db.Model):
    """Modèle pour les commentaires sur les publications"""

    __tablename__ = "commentaire"

    id = db.Column(db.Integer, primary_key=True)
    contenu = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.now(tz=timezone.utc))
    date_modification = db.Column(db.DateTime, onupdate=datetime.now(tz=timezone.utc))

    # Clés étrangères
    auteur_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="CASCADE"), nullable=False
    )

    # Relations
    auteur = db.relationship("User", back_populates="commentaires")
    post = db.relationship("Post", back_populates="commentaires")

    def __repr__(self):
        return f"<Commentaire {self.id} sur le post {self.post_id}>"

    @property
    def est_modifie(self):
        return self.date_modification and self.date_modification > self.date_creation
