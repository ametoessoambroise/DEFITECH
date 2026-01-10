from app.extensions import db
from datetime import date


class EvaluationPeriod(db.Model):
    """
    Période d'évaluation ouverte pour la saisie des notes.
    Ex: "Devoirs Semestre 1", "Session Examens S1", etc.
    """

    __tablename__ = "evaluation_period"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Type d'évaluation autorisé pendant cette période
    # DEVOIR, EXAMEN, RATTRAPAGE
    type_eval = db.Column(db.String(20), nullable=False)

    # Restreindre à un semestre spécifique si besoin
    semester = db.Column(db.Integer, nullable=True)

    def is_open(self):
        today = date.today()
        return self.start_date <= today <= self.end_date

    def __repr__(self):
        return f"<EvaluationPeriod {self.name} ({self.type_eval})>"
