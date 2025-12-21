from datetime import datetime, timedelta
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class StudyProgress(db.Model):
    """
    Modèle pour suivre la progression d'un étudiant dans son apprentissage.
    Stocke les statistiques et les métriques d'apprentissage.
    """
    __tablename__ = 'study_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Statistiques générales
    total_study_time_seconds = db.Column(db.Integer, default=0)  # Temps total d'étude en secondes
    total_documents = db.Column(db.Integer, default=0)           # Nombre total de documents
    total_flashcards = db.Column(db.Integer, default=0)          # Nombre total de cartes mémoire
    total_quizzes = db.Column(db.Integer, default=0)             # Nombre total de quiz complétés
    total_questions_answered = db.Column(db.Integer, default=0)  # Nombre total de questions répondues
    total_correct_answers = db.Column(db.Integer, default=0)     # Nombre total de bonnes réponses
    
    # Suivi des objectifs
    daily_goal_minutes = db.Column(db.Integer, default=30)       # Objectif quotidien en minutes
    streak_days = db.Column(db.Integer, default=0)               # Nombre de jours consécutifs d'étude
    last_study_date = db.Column(db.Date, nullable=True)          # Dernier jour d'étude
    
    # Suivi par sujet/domaine (stocké en JSON pour la flexibilité)
    subjects_progress = db.Column(JSONB, default=dict)  # Ex: {"maths": {"score": 85, "last_studied": "2023-01-01"}}
    
    # Préférences d'apprentissage
    preferred_study_times = db.Column(JSONB, default=list)  # Ex: ["morning", "evening"]
    learning_style = db.Column(db.String(50), nullable=True)  # Ex: "visual", "auditory", "kinesthetic"
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('study_progress', uselist=False), uselist=False)
    
    @classmethod
    def get_or_create(cls, user_id):
        """Récupère la progression d'un utilisateur ou la crée si elle n'existe pas."""
        progress = cls.query.filter_by(user_id=user_id).first()
        if not progress:
            progress = cls(user_id=user_id)
            db.session.add(progress)
            db.session.commit()
        return progress

    def update_streak(self):
        """Met à jour la série de jours consécutifs d'étude."""
        today = datetime.utcnow().date()
        
        # Si c'est la première fois qu'on étudie
        if not self.last_study_date:
            self.streak_days = 1
        else:
            # Vérifier si la dernière étude était hier
            yesterday = today - timedelta(days=1)
            if self.last_study_date == yesterday:
                # Incrémenter la série
                self.streak_days += 1
            elif self.last_study_date < yesterday:
                # Réinitialiser la série si plus d'un jour s'est écoulé
                self.streak_days = 1
            # Si la dernière étude était aujourd'hui, on ne fait rien
            
        self.last_study_date = today
        db.session.commit()
    
    def add_study_time(self, seconds, subject=None):
        """Ajoute du temps d'étude et met à jour les statistiques."""
        self.total_study_time_seconds += seconds
        
        # Mettre à jour la progression par sujet si spécifié
        if subject:
            if not self.subjects_progress:
                self.subjects_progress = {}
                
            if subject not in self.subjects_progress:
                self.subjects_progress[subject] = {
                    'study_time_seconds': 0,
                    'score': 0,
                    'last_studied': datetime.utcnow().isoformat()
                }
            
            self.subjects_progress[subject]['study_time_seconds'] += seconds
            self.subjects_progress[subject]['last_studied'] = datetime.utcnow().isoformat()
        
        # Mettre à jour la série de jours consécutifs
        self.update_streak()
        
        db.session.commit()
    
    def update_quiz_results(self, correct_answers, total_questions, subject=None):
        """Met à jour les statistiques après un quiz."""
        self.total_questions_answered += total_questions
        self.total_correct_answers += correct_answers
        self.total_quizzes += 1
        
        # Mettre à jour la progression par sujet si spécifié
        if subject:
            if not self.subjects_progress:
                self.subjects_progress = {}
                
            if subject not in self.subjects_progress:
                self.subjects_progress[subject] = {
                    'total_questions': 0,
                    'correct_answers': 0,
                    'score': 0,
                    'last_studied': datetime.utcnow().isoformat()
                }
            
            # Mettre à jour les totaux
            self.subjects_progress[subject]['total_questions'] = self.subjects_progress[subject].get('total_questions', 0) + total_questions
            self.subjects_progress[subject]['correct_answers'] = self.subjects_progress[subject].get('correct_answers', 0) + correct_answers
            
            # Calculer le score moyen
            if self.subjects_progress[subject]['total_questions'] > 0:
                self.subjects_progress[subject]['score'] = round(
                    (self.subjects_progress[subject]['correct_answers'] / self.subjects_progress[subject]['total_questions']) * 100,
                    1
                )
            
            self.subjects_progress[subject]['last_studied'] = datetime.utcnow().isoformat()
        
        db.session.commit()
    
    def get_overall_score(self):
        """Calcule le score global de l'étudiant."""
        if self.total_questions_answered == 0:
            return 0
        return round((self.total_correct_answers / self.total_questions_answered) * 100, 1)
    
    def get_study_time_formatted(self):
        """Retourne le temps d'étude total formaté (heures, minutes, secondes)."""
        hours = self.total_study_time_seconds // 3600
        minutes = (self.total_study_time_seconds % 3600) // 60
        seconds = self.total_study_time_seconds % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def to_dict(self):
        """Convertit la progression en dictionnaire."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total_study_time_seconds': self.total_study_time_seconds,
            'total_study_time_formatted': self.get_study_time_formatted(),
            'total_documents': self.total_documents,
            'total_flashcards': self.total_flashcards,
            'total_quizzes': self.total_quizzes,
            'total_questions_answered': self.total_questions_answered,
            'total_correct_answers': self.total_correct_answers,
            'overall_score': self.get_overall_score(),
            'daily_goal_minutes': self.daily_goal_minutes,
            'daily_goal_progress': self._calculate_daily_goal_progress(),
            'streak_days': self.streak_days,
            'last_study_date': self.last_study_date.isoformat() if self.last_study_date else None,
            'subjects_progress': self.subjects_progress or {},
            'preferred_study_times': self.preferred_study_times or [],
            'learning_style': self.learning_style,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def _calculate_daily_goal_progress(self):
        """Calcule la progression vers l'objectif quotidien."""
        if self.daily_goal_minutes == 0:
            return 0
        
        minutes_studied = self.total_study_time_seconds / 60
        progress = (minutes_studied / self.daily_goal_minutes) * 100
        return min(round(progress, 1), 100)  # Ne pas dépasser 100%
    
    def __repr__(self):
        return f'<StudyProgress User: {self.user_id}, Score: {self.get_overall_score()}%>'
