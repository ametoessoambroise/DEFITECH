from app.extensions import db


class AcademicYearConfig(db.Model):
    """
    Configuration globale de l'année académique.
    Définit les bornes de l'année et la séparation des semestres.
    Il ne devrait y avoir qu'une seule instance active (ou une par année si historique).
    Pour simplifier, on stocke la config courante.
    """

    __tablename__ = "academic_year_config"

    id = db.Column(db.Integer, primary_key=True)
    current_year = db.Column(db.String(20), nullable=False)  # ex: "2025-2026"

    start_date = db.Column(db.Date, nullable=False)  # Début des cours
    end_date = db.Column(db.Date, nullable=False)  # Fin de l'année

    semester_split_date = db.Column(db.Date, nullable=True)  # Date de fin S1 / Début S2

    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<AcademicYearConfig {self.current_year}>"
