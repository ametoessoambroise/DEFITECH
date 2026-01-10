"""
Modèles pour la gestion académique (Archives, Règles, Progression)
"""

from app.extensions import db
from datetime import datetime


class AcademicArchivedStudent(db.Model):
    """
    Archive annuelle immuable d'un étudiant.
    Crée automatiquement lors de la clôture de l'année.
    """

    __tablename__ = "academic_archived_student"

    id = db.Column(db.Integer, primary_key=True)
    student_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Informations académiques "Gélées" à l'instant T
    annee_academique = db.Column(db.String(50), nullable=False)  # ex: "2024-2025"
    filiere_nom = db.Column(
        db.String(100), nullable=False
    )  # Nom de la filière archivée
    niveau = db.Column(db.String(50), nullable=False)  # ex: "Licence 1"

    # Résultats consolidés
    moyenne_generale = db.Column(db.Float, nullable=False, default=0.0)
    credits_total_valides = db.Column(db.Integer, nullable=False, default=0)

    # Décision du jury
    decision_jury = db.Column(
        db.Enum(
            "ADMIS",
            "AJOURNÉ",
            "REDOUBLEMENT",
            "EXCLU",
            "EN_ATTENTE",
            name="decision_jury_enum",
        ),
        nullable=False,
        default="EN_ATTENTE",
    )

    # Métadonnées de sécurité et traçabilité
    date_archivage = db.Column(db.DateTime, default=datetime.utcnow)
    archived_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )  # Admin responsable

    # Hash de sécurité pour vérifier l'intégrité (SHA-256 des données critiques)
    security_hash = db.Column(db.String(128), nullable=True)

    # Relations
    student = db.relationship(
        "User", foreign_keys=[student_user_id], backref="academic_archives"
    )
    archivist = db.relationship("User", foreign_keys=[archived_by_id])
    grades = db.relationship(
        "AcademicArchivedGrade", backref="student_archive", cascade="all, delete-orphan"
    )

    def __repr__(self):
        if self.student:
            return f"<AcademicArchive {self.student.nom} {self.student.prenom} - {self.annee_academique}>"
        return (
            f"<AcademicArchive UserID:{self.student_user_id} - {self.annee_academique}>"
        )


class AcademicArchivedGrade(db.Model):
    """
    Archive des notes d'une matière pour un étudiant donné.
    Lié à l'archive étudiante annuelle.
    """

    __tablename__ = "academic_archived_grade"

    id = db.Column(db.Integer, primary_key=True)
    archive_id = db.Column(
        db.Integer, db.ForeignKey("academic_archived_student.id"), nullable=False
    )

    # Détails de la matière (Nom gélé)
    matiere_nom = db.Column(db.String(100), nullable=False)
    code_matiere = db.Column(db.String(50), nullable=True)
    credits_matiere = db.Column(db.Integer, nullable=False, default=0)  # Coefficient

    # Résultats
    moyenne_matiere = db.Column(db.Float, nullable=False)
    note_examen = db.Column(db.Float, nullable=True)
    note_classe = db.Column(db.Float, nullable=True)  # Moyenne Devoir + TP

    semestre = db.Column(db.Integer, nullable=False, default=1)

    # Statut de validation
    is_validated = db.Column(db.Boolean, default=False)  # True si Moyenne >= 10
    statut = db.Column(db.String(50), default="NORMAL")  # NORMAL, RATTRAPAGE

    def __repr__(self):
        return f"<ArchivedGrade {self.matiere_nom}: {self.moyenne_matiere}>"


class PromotionRule(db.Model):
    """
    Règles de passage en année supérieure configurables par l'admin.
    """

    __tablename__ = "promotion_rule"

    id = db.Column(db.Integer, primary_key=True)
    nom_regle = db.Column(
        db.String(100), unique=True, nullable=False
    )  # ex: "STANDARD_DEFITECH"

    # Seuils configurables
    seuil_moyenne_matiere = db.Column(
        db.Float, default=10.0
    )  # Seuil validation matière
    seuil_credits_passage = db.Column(db.Integer, default=45)  # Seuil crédits passage

    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<PromotionRule {self.nom_regle}>"
