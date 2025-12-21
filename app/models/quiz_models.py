from datetime import datetime
from enum import Enum
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class QuizType(Enum):
    """Types de quiz disponibles."""
    MULTIPLE_CHOICE = 'multiple_choice'
    TRUE_FALSE = 'true_false'
    SHORT_ANSWER = 'short_answer'
    MATCHING = 'matching'
    FILL_BLANK = 'fill_blank'

class QuizDifficulty(Enum):
    """Niveaux de difficulté des quiz."""
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'

class Quiz(db.Model):
    """
    Modèle pour stocker les quiz générés à partir des documents.
    """
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('study_documents.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    quiz_type = db.Column(db.String(50), nullable=False, default=QuizType.MULTIPLE_CHOICE.value)
    difficulty = db.Column(db.String(20), nullable=False, default=QuizDifficulty.MEDIUM.value)
    is_adaptive = db.Column(db.Boolean, default=True, nullable=False)
    time_limit_minutes = db.Column(db.Integer, nullable=True)  # Durée limite en minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('quizzes', lazy=True))
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_questions=True):
        """Convertit le quiz en dictionnaire."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'title': self.title,
            'description': self.description,
            'quiz_type': self.quiz_type,
            'difficulty': self.difficulty,
            'is_adaptive': self.is_adaptive,
            'time_limit_minutes': self.time_limit_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'question_count': len(self.questions) if self.questions else 0,
            'attempt_count': len(self.attempts) if self.attempts else 0
        }
        
        if include_questions and self.questions:
            result['questions'] = [q.to_dict() for q in self.questions]
            
        return result
    
    def __repr__(self):
        return f'<Quiz {self.title} (ID: {self.id})>'


class Question(db.Model):
    """
    Modèle pour les questions d'un quiz.
    """
    __tablename__ = 'quiz_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False, default=QuizType.MULTIPLE_CHOICE.value)
    options = db.Column(JSONB, nullable=True)  # Pour les QCM: [{"text": "...", "is_correct": true/false}, ...]
    correct_answer = db.Column(JSONB, nullable=True)  # Peut être une chaîne, un tableau, un objet, etc.
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=False, default=QuizDifficulty.MEDIUM.value)
    points = db.Column(db.Integer, default=1, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    
    # Pour le suivi des performances
    times_answered = db.Column(db.Integer, default=0, nullable=False)
    times_correct = db.Column(db.Integer, default=0, nullable=False)
    
    # Relations
    answers = db.relationship('QuizAnswer', backref='question', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_answers=False):
        """Convertit la question en dictionnaire."""
        result = {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'options': self.options,
            'correct_answer': self.correct_answer if include_answers or self.quiz.show_correct_answers else None,
            'explanation': self.explanation if include_answers or self.quiz.show_correct_answers else None,
            'difficulty': self.difficulty,
            'points': self.points,
            'order': self.order,
            'times_answered': self.times_answered,
            'times_correct': self.times_correct,
            'accuracy': round((self.times_correct / self.times_answered * 100), 1) if self.times_answered > 0 else 0
        }
        
        if include_answers and self.answers:
            result['user_answers'] = [a.to_dict() for a in self.answers]
            
        return result
    
    def record_answer(self, is_correct, user_id=None, attempt_id=None, commit=True):
        """Enregistre une réponse à cette question."""
        self.times_answered += 1
        if is_correct:
            self.times_correct += 1
            
        if user_id and attempt_id:
            answer = QuizAnswer(
                question_id=self.id,
                user_id=user_id,
                quiz_attempt_id=attempt_id,
                is_correct=is_correct,
                answered_at=datetime.utcnow()
            )
            db.session.add(answer)
        
        if commit:
            db.session.commit()
    
    def __repr__(self):
        return f'<Question {self.id} (Quiz: {self.quiz_id})>'


class QuizAttempt(db.Model):
    """
    Modèle pour suivre les tentatives de quiz des utilisateurs.
    """
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=True)  # Score en pourcentage
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    time_spent_seconds = db.Column(db.Integer, default=0)  # Temps passé en secondes
    
    # Relations
    user = db.relationship('User', backref=db.backref('quiz_attempts', lazy=True))
    answers = db.relationship('QuizAnswer', backref='attempt', lazy=True, cascade='all, delete-orphan')
    
    def complete_attempt(self, commit=True):
        """Marque la tentative comme terminée et calcule le score."""
        if not self.is_completed:
            self.end_time = datetime.utcnow()
            self.is_completed = True
            
            # Calculer le temps passé
            if self.start_time and self.end_time:
                self.time_spent_seconds = int((self.end_time - self.start_time).total_seconds())
            
            # Calculer le score
            if self.answers:
                correct = sum(1 for a in self.answers if a.is_correct)
                self.score = round((correct / len(self.answers)) * 100, 2)
            
            if commit:
                db.session.commit()
    
    def to_dict(self, include_answers=True):
        """Convertit la tentative en dictionnaire."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'score': self.score,
            'is_completed': self.is_completed,
            'time_spent_seconds': self.time_spent_seconds,
            'time_spent_formatted': self._format_time_spent()
        }
        
        if include_answers and self.answers:
            result['answers'] = [a.to_dict() for a in self.answers]
            
        return result
    
    def _format_time_spent(self):
        """Formate le temps passé en format lisible."""
        if not self.time_spent_seconds:
            return "0s"
            
        minutes = self.time_spent_seconds // 60
        seconds = self.time_spent_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    
    def __repr__(self):
        return f'<QuizAttempt {self.id} (User: {self.user_id}, Quiz: {self.quiz_id}, Score: {self.score}%)>'


class QuizAnswer(db.Model):
    """
    Modèle pour stocker les réponses des utilisateurs aux questions de quiz.
    """
    __tablename__ = 'quiz_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_questions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'), nullable=False)
    answer_data = db.Column(JSONB, nullable=True)  # Peut stocker n'importe quel type de réponse
    is_correct = db.Column(db.Boolean, nullable=False)
    points_earned = db.Column(db.Float, default=0.0, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    user = db.relationship('User', backref=db.backref('quiz_answers', lazy=True))
    
    def to_dict(self):
        """Convertit la réponse en dictionnaire."""
        return {
            'id': self.id,
            'question_id': self.question_id,
            'user_id': self.user_id,
            'quiz_attempt_id': self.quiz_attempt_id,
            'answer_data': self.answer_data,
            'is_correct': self.is_correct,
            'points_earned': self.points_earned,
            'feedback': self.feedback,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None
        }
    
    def __repr__(self):
        return f'<QuizAnswer {self.id} (User: {self.user_id}, Question: {self.question_id}, Correct: {self.is_correct})>'
