"""
Modèle PomodoroSession pour suivre les sessions d'étude avec la technique Pomodoro
"""

from datetime import datetime
from app.extensions import db


class PomodoroSession(db.Model):
    """
    Modèle pour stocker les sessions Pomodoro des étudiants
    """

    __tablename__ = "pomodoro_sessions"

    id = db.Column(db.Integer, primary_key=True)
    etudiant_id = db.Column(
        db.Integer, db.ForeignKey("etudiant.id"), nullable=False, index=True
    )
    matiere_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=True)

    # Informations sur la session
    date_debut = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_fin = db.Column(db.DateTime, nullable=True)
    duree_prevue = db.Column(db.Integer, nullable=False, default=25)  # Durée en minutes
    duree_reelle = db.Column(db.Integer, nullable=True)  # Durée réelle en minutes

    # Type de session
    type_session = db.Column(
        db.String(20), nullable=False, default="travail"
    )  # 'travail' ou 'pause'
    statut = db.Column(
        db.String(20), nullable=False, default="en_cours"
    )  # 'en_cours', 'terminee', 'interrompue'

    # Métadonnées
    titre = db.Column(db.String(200), nullable=True)  # Titre de la session
    description = db.Column(db.Text, nullable=True)  # Description/notes
    tache_associee = db.Column(db.String(200), nullable=True)  # Tâche ou devoir associé

    # Pause
    pause_prise = db.Column(
        db.Boolean, default=False
    )  # Si la pause a été prise après cette session
    duree_pause = db.Column(db.Integer, nullable=True)  # Durée de la pause en minutes

    # Statistiques
    nombre_interruptions = db.Column(
        db.Integer, default=0
    )  # Nombre d'interruptions pendant la session
    niveau_concentration = db.Column(
        db.Integer, nullable=True
    )  # Auto-évaluation de 1 à 5

    # Timestamps
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_modification = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations
    etudiant = db.relationship("Etudiant", backref="pomodoro_sessions", lazy=True)
    matiere = db.relationship("Matiere", backref="pomodoro_sessions", lazy=True)

    def __repr__(self):
        return f"<PomodoroSession {self.id} - Etudiant {self.etudiant_id} - {self.type_session} - {self.statut}>"

    def to_dict(self):
        """Convertit la session en dictionnaire"""
        return {
            "id": self.id,
            "etudiant_id": self.etudiant_id,
            "matiere_id": self.matiere_id,
            "matiere_nom": self.matiere.nom if self.matiere else None,
            "date_debut": self.date_debut.isoformat() if self.date_debut else None,
            "date_fin": self.date_fin.isoformat() if self.date_fin else None,
            "duree_prevue": self.duree_prevue,
            "duree_reelle": self.duree_reelle,
            "type_session": self.type_session,
            "statut": self.statut,
            "titre": self.titre,
            "description": self.description,
            "tache_associee": self.tache_associee,
            "pause_prise": self.pause_prise,
            "duree_pause": self.duree_pause,
            "nombre_interruptions": self.nombre_interruptions,
            "niveau_concentration": self.niveau_concentration,
            "date_creation": self.date_creation.isoformat()
            if self.date_creation
            else None,
        }

    def marquer_terminee(self):
        """Marque la session comme terminée"""
        self.statut = "terminee"
        self.date_fin = datetime.utcnow()
        if self.date_debut:
            self.duree_reelle = int(
                (self.date_fin - self.date_debut).total_seconds() / 60
            )

    def marquer_interrompue(self):
        """Marque la session comme interrompue"""
        self.statut = "interrompue"
        self.date_fin = datetime.utcnow()
        if self.date_debut:
            self.duree_reelle = int(
                (self.date_fin - self.date_debut).total_seconds() / 60
            )

    def ajouter_interruption(self):
        """Incrémente le compteur d'interruptions"""
        self.nombre_interruptions += 1

    @staticmethod
    def get_stats_etudiant(etudiant_id, periode="today"):
        """
        Récupère les statistiques Pomodoro pour un étudiant

        Args:
            etudiant_id: ID de l'étudiant
            periode: 'today', 'week', 'month', 'all'

        Returns:
            dict: Statistiques de la période
        """
        from datetime import timedelta

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if periode == "today":
            date_debut = today
        elif periode == "week":
            date_debut = today - timedelta(days=today.weekday())
        elif periode == "month":
            date_debut = today.replace(day=1)
        else:  # all
            date_debut = datetime(2000, 1, 1)

        sessions = PomodoroSession.query.filter(
            PomodoroSession.etudiant_id == etudiant_id,
            PomodoroSession.date_debut >= date_debut,
            PomodoroSession.type_session == "travail",
        ).all()

        sessions_terminees = [s for s in sessions if s.statut == "terminee"]
        total_minutes = sum(s.duree_reelle or 0 for s in sessions_terminees)
        pauses_prises = sum(1 for s in sessions_terminees if s.pause_prise)

        stats = {
            "sessions_completed": len(sessions_terminees),
            "total_minutes": total_minutes,
            "breaks_taken": pauses_prises,
            "average_duration": (
                total_minutes / len(sessions_terminees) if sessions_terminees else 0
            ),
            "interruptions_total": sum(s.nombre_interruptions for s in sessions),
        }

        return stats

    @staticmethod
    def get_stats_par_matiere(etudiant_id, days=7):
        """
        Récupère les statistiques par matière pour les X derniers jours

        Args:
            etudiant_id: ID de l'étudiant
            days: Nombre de jours à analyser

        Returns:
            list: Liste des statistiques par matière
        """
        from datetime import timedelta
        from sqlalchemy import func

        date_debut = datetime.now() - timedelta(days=days)

        stats = (
            db.session.query(
                PomodoroSession.matiere_id,
                func.count(PomodoroSession.id).label("nombre_sessions"),
                func.sum(PomodoroSession.duree_reelle).label("total_minutes"),
            )
            .filter(
                PomodoroSession.etudiant_id == etudiant_id,
                PomodoroSession.date_debut >= date_debut,
                PomodoroSession.statut == "terminee",
                PomodoroSession.type_session == "travail",
                PomodoroSession.matiere_id.isnot(None),
            )
            .group_by(PomodoroSession.matiere_id)
            .all()
        )

        return [
            {
                "matiere_id": s.matiere_id,
                "nombre_sessions": s.nombre_sessions,
                "total_minutes": s.total_minutes or 0,
            }
            for s in stats
        ]
