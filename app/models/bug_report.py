from datetime import datetime
from app import db

class BugReport(db.Model):
    __tablename__ = 'bug_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    steps_to_reproduce = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, wont_fix
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    image_path = db.Column(db.String(500))
    admin_notes = db.Column(db.Text, nullable=True)  # Notes internes pour les administrateurs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='bug_reports')
    
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user': {
                'id': self.user.id,
                'full_name': f"{self.user.prenom} {self.user.nom}",
                'role': self.user.role
            }
        }
