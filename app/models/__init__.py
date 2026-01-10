# Ce fichier rend le répertoire models un package Python
"""
Expose des classes clés pour permettre des imports du type:
    from models import User, Filiere, Post, etc.
"""

# db est importé depuis extensions.py pour éviter les imports circulaires

# Import léger pour exposer au niveau du package
try:
    from .user import User  # noqa: F401
    from .teacher_profile_update_request import (
        TeacherProfileUpdateRequest,
    )  # noqa: F401
    from .resource import Resource  # noqa: F401
    from .message import Message  # noqa: F401
    from .pomodoro_session import PomodoroSession  # noqa: F401
    from .note import Note  # noqa: F401
    from .presence import Presence  # noqa: F401
    from .emploi_temps import EmploiTemps  # noqa: F401
    from .devoir import Devoir  # noqa: F401
    from .devoir_vu import DevoirVu  # noqa: F401
    from .suggestion import Suggestion  # noqa: F401
    from .ai_assistant import AIConversation, AIMessage, Dataset  # noqa: F401
    from .study_document import StudyDocument  # noqa: F401
    from .study_session import StudySession  # noqa: F401
    from .quiz_models import Quiz, Question, QuizAttempt, QuizAnswer  # noqa: F401
    from .flashcard import Flashcard, FlashcardReview  # noqa: F401
    from .study_progress import StudyProgress  # noqa: F401
    from .webauthn_credential import WebauthnCredential  # noqa: F401
    from .security_incident import SecurityIncident  # noqa: F401
    from .academic import (
        AcademicArchivedStudent,
        AcademicArchivedGrade,
        PromotionRule,
    )  # noqa: F401
    from .academic_year_config import AcademicYearConfig  # noqa: F401
    from .evaluation_period import EvaluationPeriod  # noqa: F401
except Exception:
    # Laisser silencieux pendant l'initialisation; init_models fera les imports complets
    User = None  # type: ignore
    TeacherProfileUpdateRequest = None  # type: ignore
    Resource = None  # type: ignore
    Message = None  # type: ignore
    PomodoroSession = None  # type: ignore
    Note = None  # type: ignore
    Presence = None  # type: ignore
    EmploiTemps = None  # type: ignore
    Devoir = None  # type: ignore
    DevoirVu = None  # type: ignore
    Suggestion = None  # type: ignore
    AIConversation = None  # type: ignore
    AIMessage = None  # type: ignore
    Dataset = None  # type: ignore
    StudyDocument = None  # type: ignore
    StudySession = None  # type: ignore
    Quiz = None  # type: ignore
    Question = None  # type: ignore
    QuizAttempt = None  # type: ignore
    QuizAnswer = None  # type: ignore
    Flashcard = None  # type: ignore
    FlashcardReview = None  # type: ignore
    StudyProgress = None  # type: ignore
    WebauthnCredential = None  # type: ignore
    SecurityIncident = None  # type: ignore
    AcademicArchivedStudent = None  # type: ignore
    AcademicArchivedGrade = None  # type: ignore
    PromotionRule = None  # type: ignore

    from .annee import Annee
    from .matiere import Matiere

    # Retourne un dictionnaire des modèles pour faciliter l'import


def init_models():
    """Initialise les modèles et évite les imports circulaires"""
    from .user import User
    from .etudiant import Etudiant
    from .enseignant import Enseignant
    from .filiere import Filiere, FiliereAdmin
    from .post import Post
    from .piece_jointe import PieceJointe
    from .commentaire import Commentaire
    from .notification import Notification
    from .global_notification import GlobalNotification
    from .password_reset_token import PasswordResetToken
    from .annee import Annee
    from .matiere import Matiere
    from .teacher_profile_update_request import TeacherProfileUpdateRequest
    from .pomodoro_session import PomodoroSession
    from .note import Note
    from .presence import Presence
    from .emploi_temps import EmploiTemps
    from .devoir import Devoir
    from .devoir_vu import DevoirVu
    from .suggestion import Suggestion
    from .ai_assistant import AIConversation, AIMessage, Dataset
    from .webauthn_credential import WebauthnCredential
    from .security_incident import SecurityIncident
    from .academic import (
        AcademicArchivedStudent,
        AcademicArchivedGrade,
        PromotionRule,
    )
    from .academic_year_config import AcademicYearConfig
    from .evaluation_period import EvaluationPeriod

    # Retourne un dictionnaire des modèles pour faciliter l'import
    return {
        "User": User,
        "Etudiant": Etudiant,
        "Enseignant": Enseignant,
        "Filiere": Filiere,
        "FiliereAdmin": FiliereAdmin,
        "Post": Post,
        "PieceJointe": PieceJointe,
        "Commentaire": Commentaire,
        "Notification": Notification,
        "GlobalNotification": GlobalNotification,
        "PasswordResetToken": PasswordResetToken,
        "Annee": Annee,
        "Matiere": Matiere,
        "TeacherProfileUpdateRequest": TeacherProfileUpdateRequest,
        "Resource": Resource,
        "Message": Message,
        "PomodoroSession": PomodoroSession,
        "Note": Note,
        "Presence": Presence,
        "EmploiTemps": EmploiTemps,
        "Devoir": Devoir,
        "DevoirVu": DevoirVu,
        "Suggestion": Suggestion,
        "AIConversation": AIConversation,
        "AIMessage": AIMessage,
        "Dataset": Dataset,
        "WebauthnCredential": WebauthnCredential,
        "SecurityIncident": SecurityIncident,
        "AcademicArchivedStudent": AcademicArchivedStudent,
        "AcademicArchivedGrade": AcademicArchivedGrade,
        "PromotionRule": PromotionRule,
        "AcademicYearConfig": AcademicYearConfig,
        "EvaluationPeriod": EvaluationPeriod,
    }


# Liste de tous les modèles à exposer
__all__ = [
    "User",
    "Etudiant",
    "Enseignant",
    # Modèles Study Buddy
    "StudyDocument",
    "StudySession",
    "Quiz",
    "Question",
    "QuizAttempt",
    "QuizAnswer",
    "Flashcard",
    "FlashcardReview",
    "StudyProgress",
    "Filiere",
    "FiliereAdmin",
    "Post",
    "PieceJointe",
    "Commentaire",
    "Notification",
    "GlobalNotification",
    "PasswordResetToken",
    "Annee",
    "Matiere",
    "TeacherProfileUpdateRequest",
    "Resource",
    "Message",
    "PomodoroSession",
    "Note",
    "Presence",
    "EmploiTemps",
    "Devoir",
    "DevoirVu",
    "Suggestion",
    "AIConversation",
    "AIMessage",
    "Dataset",
    "WebauthnCredential",
    "SecurityIncident",
    # Modèles de Gestion Académique
    "AcademicArchivedStudent",
    "AcademicArchivedGrade",
    "PromotionRule",
    "AcademicYearConfig",
    "EvaluationPeriod",
]
