from datetime import datetime
from app.extensions import db


class Post(db.Model):
    """Modèle pour les publications dans la communauté"""

    __tablename__ = "post"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, onupdate=datetime.utcnow)
    est_epingle = db.Column(db.Boolean, default=False)
    est_public = db.Column(db.Boolean, default=True)
    # vues should be an integer counter (number of views). It was mistakenly
    # defined as Boolean which caused ValueError when assigning numbers like 5.
    vues = db.Column(db.Integer, default=0)

    # Clés étrangères
    auteur_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False)
    filiere_id = db.Column(db.Integer, db.ForeignKey(
        "filiere.id"), nullable=False)

    # Relations
    auteur = db.relationship("User", back_populates="posts")
    filiere = db.relationship("Filiere", back_populates="posts")
    # pieces_jointes sera défini après que PieceJointe soit défini
    pieces_jointes = db.relationship(
        "PieceJointe", back_populates="post", cascade="all, delete-orphan")
    # commentaires sera défini après que Commentaire soit défini
    commentaires = db.relationship(
        "Commentaire", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        """Retourne a string representation of the post.

        The string representation is of the form "<Post {title}>" where
        {title} is the title of the post, truncated to 50 characters.

        :return: A string representation of the post.
        :rtype: str
        """
        return f"<Post {self.titre[:50]}>"

    @property
    def nb_commentaires(self):
        """
        Retourne le nombre de commentaires sur le post.

        :return: Le nombre de commentaires sur le post.
        :rtype: int
        """
        return len(self.commentaires)

    @property
    def est_modifie(self):
        """
        Indique si le post a été modifié depuis sa création.

        :return: True si le post a été modifié, False sinon.
        :rtype: bool
        """
        return self.date_modification and self.date_modification > self.date_creation

    # Note: `est_epingle` and `vues` are defined as columns above. Avoid
    # redefining properties with the same name to prevent recursion or
    # attribute shadowing. If a helper is needed, use a different name.
