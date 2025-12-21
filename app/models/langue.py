"""
Modèle pour les langues des utilisateurs
"""
from app.extensions import db

class Langue(db.Model):
    __tablename__ = 'langues'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    niveau_ecrit = db.Column(db.String(50))  # A1, A2, B1, B2, C1, C2
    niveau_oral = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), 
                         onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'niveau_ecrit': self.niveau_ecrit,
            'niveau_oral': self.niveau_oral,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
