"""
Modèle pour la gestion des suggestions de la boîte à suggestions

Ce modèle gère :
- Les suggestions soumises par les utilisateurs
- Les votes (Oui/Non) des utilisateurs
- Les réponses des administrateurs
- Le statut des suggestions
"""

from app.extensions import db
from datetime import datetime


class Suggestion(db.Model):
    """
    Modèle pour les suggestions de la boîte à suggestions

    Attributs:
        id (int): Identifiant unique de la suggestion
        contenu (str): Contenu de la suggestion
        auteur_anonyme (str): Nom anonyme de l'auteur (optionnel)
        email_contact (str): Email de contact (optionnel)
        statut (str): Statut de la suggestion ('ouverte', 'en_cours', 'fermee', 'rejetee')
        date_creation (datetime): Date de création
        date_modification (datetime): Date de dernière modification

    Relations:
        votes: Liste des votes associés à cette suggestion
        reponses: Liste des réponses des administrateurs
    """

    __tablename__ = "suggestions"

    id = db.Column(db.Integer, primary_key=True)
    contenu = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    auteur_anonyme = db.Column(db.String(100))
    email_contact = db.Column(db.String(120))
    statut = db.Column(db.String(20), default="ouverte")
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations
    user = db.relationship("User", backref="suggestions")
    votes = db.relationship(
        "SuggestionVote", back_populates="suggestion", cascade="all, delete-orphan"
    )
    reponses = db.relationship(
        "SuggestionReponse",
        back_populates="suggestion",
        cascade="all, delete-orphan",
        order_by="SuggestionReponse.date_creation.desc()",
    )

    def __repr__(self):
        return f"<Suggestion {self.id}: {self.contenu[:50]}...>"

    @property
    def votes_oui(self):
        """Nombre de votes 'oui'"""
        return len([vote for vote in self.votes if vote.type_vote == "oui"])

    @property
    def votes_non(self):
        """Nombre de votes 'non'"""
        return len([vote for vote in self.votes if vote.type_vote == "non"])

    @property
    def total_votes(self):
        """Nombre total de votes"""
        return len(self.votes)

    def has_user_voted(self, user_id=None, session_id=None):
        """Vérifie si un utilisateur a déjà voté"""
        if user_id:
            return any(vote.user_id == user_id for vote in self.votes)
        elif session_id:
            return any(vote.session_id == session_id for vote in self.votes)
        return False

    def get_user_vote(self, user_id=None, session_id=None):
        """Récupère le vote d'un utilisateur"""
        if user_id:
            for vote in self.votes:
                if vote.user_id == user_id:
                    return vote
        elif session_id:
            for vote in self.votes:
                if vote.session_id == session_id:
                    return vote
        return None


class SuggestionVote(db.Model):
    """
    Modèle pour les votes sur les suggestions

    Attributs:
        id (int): Identifiant unique du vote
        suggestion_id (int): ID de la suggestion votée
        user_id (int): ID de l'utilisateur (optionnel, pour les utilisateurs connectés)
        session_id (str): ID de session (pour les utilisateurs anonymes)
        type_vote (str): Type de vote ('oui' ou 'non')
        date_creation (datetime): Date du vote
    """

    __tablename__ = "suggestion_votes"

    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(
        db.Integer, db.ForeignKey("suggestions.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    session_id = db.Column(
        db.String(255), nullable=True
    )  # Pour les utilisateurs non connectés
    type_vote = db.Column(db.String(10), nullable=False)  # 'oui' ou 'non'
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    suggestion = db.relationship("Suggestion", back_populates="votes")
    user = db.relationship("User", backref="suggestion_votes")

    def __repr__(self):
        return f"<SuggestionVote {self.id}: {self.type_vote}>"


class SuggestionReponse(db.Model):
    """
    Modèle pour les réponses des administrateurs aux suggestions

    Attributs:
        id (int): Identifiant unique de la réponse
        suggestion_id (int): ID de la suggestion
        admin_id (int): ID de l'administrateur qui répond
        contenu (str): Contenu de la réponse
        date_creation (datetime): Date de la réponse
    """

    __tablename__ = "suggestion_reponses"

    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(
        db.Integer, db.ForeignKey("suggestions.id"), nullable=False
    )
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    suggestion = db.relationship("Suggestion", back_populates="reponses")
    admin = db.relationship("User", backref="suggestion_reponses")

    def __repr__(self):
        return f"<SuggestionReponse {self.id}: {self.contenu[:50]}...>"
